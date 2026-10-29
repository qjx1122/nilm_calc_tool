#!/usr/bin/env python3
"""v0.96：估计 CT 变比（与数据处理子界面「估计 CT」同一实现）。

同一台设备的一次启停，在总线侧与分路侧造成的一次侧电流台阶相同，故
    CT_未知 = CT_已知 × |ΔI_已知侧(二次)| / |ΔI_未知侧(二次)|
两侧各指定：文件、同一次动作的事件类型（启动/停机）与事件时间段、单相（A/B/C）、接线方式、CT 极性、本侧 CT（已知时）；PT/CT 变换强制关闭（直接量二次侧安培）。

示例：
    python tools/ct_estimate.py --bus-file data/bus.csv --bus-event stop --bus-begin 14:39:30 --bus-end 14:39:50 --bus-phase A --bus-wiring 3p3w --bus-invert-phases A \\
        --branch-file data/dev.csv --branch-event stop --branch-begin 14:39:30 --branch-end 14:39:50 --branch-phase A --branch-ct 15
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from elec_tool.config import AppConfig, ConfigError   # noqa: E402

SIDE_ARGS = ("file", "time", "phase", "wiring", "reconstruct-3w", "invert-current", "invert-phases", "col-map")


def build_cli_command(payload, out=None) -> str:
    """由界面请求体生成等价命令行。"""
    q = lambda s: f'"{s}"' if any(ch in str(s) for ch in " \t\"'") else str(s)   # noqa: E731
    on = lambda v: str(v).strip().lower() in ("1", "true", "on", "yes")   # noqa: E731
    parts = ["python", "tools/ct_estimate.py"]
    for side in ("bus", "branch"):
        d = dict(payload.get(side) or {})
        p = (out or {}).get(side, {}).get("path") or d.get("path") or ""
        parts += [f"--{side}-file", q(p), f"--{side}-event", str(d.get("event") or "start"), f"--{side}-begin", q(d.get("t_begin") or ""),
                  f"--{side}-end", q(d.get("t_end") or ""), f"--{side}-phase", str(d.get("phase") or "A").upper()]
        if str(d.get("wiring") or "") and str(d.get("wiring")) != "3p4w":
            parts += [f"--{side}-wiring", str(d.get("wiring"))]
        if on(d.get("reconstruct_3w")):
            parts += [f"--{side}-reconstruct-3w"]
        if on(d.get("invert_current")):
            parts += [f"--{side}-invert-current"]
        if d.get("invert_phases"):
            parts += [f"--{side}-invert-phases", str(d.get("invert_phases"))]
        if on(d.get("known")) and d.get("ct") not in (None, ""):
            parts += [f"--{side}-ct", f"{float(d.get('ct')):g}"]
        if on(d.get("col_map_enabled")) and d.get("col_map"):
            m = d.get("col_map"); parts += [f"--{side}-col-map", q(m if isinstance(m, str) else json.dumps(m, ensure_ascii=False))]
    if payload.get("win_cycles") not in (None, ""):
        parts += ["--win-cycles", str(int(float(payload["win_cycles"])))]
    return " ".join(parts)


def _side_spec(a, side: str) -> dict:
    g = lambda k: getattr(a, f"{side}_{k}")   # noqa: E731
    spec = {"path": g("file"), "event": g("event"), "t_begin": g("begin"), "t_end": g("end"), "phase": g("phase"), "wiring": g("wiring") or "",
            "reconstruct_3w": "1" if g("reconstruct_3w") else "", "invert_current": "1" if g("invert_current") else "", "invert_phases": g("invert_phases") or "",
            "known": "1" if g("ct") is not None else "0", "ct": g("ct")}
    if g("col_map"):
        spec["col_map_enabled"] = "1"; spec["col_map"] = g("col_map")
    return spec


def main() -> int:
    from elec_tool.ct_estimate import CtEstimateError, estimate_ct
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for side, name in (("bus", "总线侧"), ("branch", "分路侧")):
        ap.add_argument(f"--{side}-file", required=True, help=f"{name}波形 CSV")
        ap.add_argument(f"--{side}-event", default="start", choices=("start", "stop"), help=f"{name}事件类型：start 启动 / stop 停机")
        ap.add_argument(f"--{side}-begin", required=True, help=f"{name}事件开始时刻（完整日期时间 / epoch 秒 / HH:MM:SS[.fff]）")
        ap.add_argument(f"--{side}-end", required=True, help=f"{name}事件结束时刻（同上；时间段应包住整个启动 / 停机过程）")
        ap.add_argument(f"--{side}-phase", default="A", choices=("A", "B", "C"), help=f"{name}所用单相电流")
        ap.add_argument(f"--{side}-wiring", default=None, choices=("3p4w", "3p3w"), help=f"{name}接线方式（默认 3p4w）")
        ap.add_argument(f"--{side}-reconstruct-3w", action="store_true", help=f"{name}3P3W 虚拟中性点重构")
        ap.add_argument(f"--{side}-invert-current", action="store_true", help=f"{name}三相电流极性反转")
        ap.add_argument(f"--{side}-invert-phases", default=None, help=f"{name}分相电流极性反转，如 A / AC")
        ap.add_argument(f"--{side}-ct", type=float, default=None, help=f"{name}CT 变比（给出＝本侧 CT 已知，用来估计另一侧；两侧都给＝互相核对）")
        ap.add_argument(f"--{side}-col-map", default=None, help=f'{name}离线文件列映射 JSON，如 {{"timestamp":1,"ua":2,"ia":3,...}}')
    ap.add_argument("--win-cycles", type=int, default=50, help="事件前 / 后稳态取值的周波数（默认 50）")
    ap.add_argument("--config", default=None, help="出厂 / 基准配置文件（只取 f_nom 等缺省；默认 configs/default.json）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    a = ap.parse_args()
    try:
        cfg = AppConfig.load(a.config or os.path.join(ROOT, "configs", "default.json"))
        out = estimate_ct(cfg, _side_spec(a, "bus"), _side_spec(a, "branch"), win_cycles=a.win_cycles)
    except (CtEstimateError, ConfigError, OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2)); return 0
    from elec_tool.wave_preview import fmt_t
    for side, name in (("bus", "总线侧"), ("branch", "分路侧")):
        m = out[side]
        print(f"{name} {m['path']}  {m['phase']} 相  {m['event_name']} {fmt_t(m['t_begin'])} → {fmt_t(m['t_end'])}  接线 {m['wiring']}{'+重构' if m['reconstruct_3w'] else ''}"
              f"  极性反转 {'全部' if m['invert_current'] else (m['invert_phases'] or '无')}")
        print(f"  前 {m['pre_a']:.4f} A → 后 {m['post_a']:.4f} A  ΔI = {m['delta_a']:+.4f} A（二次侧，各 {m['win_cycles']} 周波中位数）  噪声 {m['noise_a']:.4f} A"
              + (f"  信噪比 {m['snr']:.1f}" if m['snr'] is not None else "") + f"  最大跳变 {fmt_t(m['t_step'])}")
    r = out["ratio_branch_over_bus"]
    print(f"ΔI分路 / ΔI总线 = {r:.4f}" if r is not None else "ΔI 比值：无法计算")
    for sd, name in (("bus", "总线侧"), ("branch", "分路侧")):
        e = out["estimates"][sd]
        if e:
            print(f"估计{name} CT ≈ {e['ct']:.2f}（由{'分路侧' if e['from'] == 'branch' else '总线侧'} CT={e['known_ct']:g} 推得）"
                  + (f"  填写值 {e['configured']:g}，偏差 {e['deviation_pct']:.1f}%" if e.get("deviation_pct") is not None else ""))
    for n in out["notes"]:
        print("  ⚠ " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
