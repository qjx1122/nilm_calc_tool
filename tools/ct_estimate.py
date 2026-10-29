#!/usr/bin/env python3
"""v0.96：估计 CT 变比（与数据处理子界面「估计 CT」同一实现）。

同一台设备的一次启停，在总线侧与分路侧造成的一次侧电流台阶相同，故
    CT_未知 = CT_已知 × |ΔI_已知侧(二次)| / |ΔI_未知侧(二次)|
两侧各指定：文件、该次启停时刻、单相（A/B/C）、接线方式、CT 极性；PT/CT 变换强制关闭（直接量二次侧安培）。

示例：
    python tools/ct_estimate.py --bus-file data/bus.csv --bus-time 14:39:30 --bus-phase A --bus-wiring 3p3w --bus-invert-phases A \\
        --branch-file data/dev.csv --branch-time 14:39:30 --branch-phase A --known-side branch --known-ct 15
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
    parts = ["python", "tools/ct_estimate.py"]
    for side in ("bus", "branch"):
        d = dict(payload.get(side) or {})
        p = (out or {}).get(side, {}).get("path") or d.get("path") or ""
        parts += [f"--{side}-file", q(p), f"--{side}-time", q(d.get("t_event") or ""), f"--{side}-phase", str(d.get("phase") or "A").upper()]
        if str(d.get("wiring") or "") and str(d.get("wiring")) != "3p4w":
            parts += [f"--{side}-wiring", str(d.get("wiring"))]
        if str(d.get("reconstruct_3w") or "").lower() in ("1", "true", "on", "yes"):
            parts += [f"--{side}-reconstruct-3w"]
        if str(d.get("invert_current") or "").lower() in ("1", "true", "on", "yes"):
            parts += [f"--{side}-invert-current"]
        if d.get("invert_phases"):
            parts += [f"--{side}-invert-phases", str(d.get("invert_phases"))]
        if str(d.get("col_map_enabled") or "").lower() in ("1", "true", "on", "yes") and d.get("col_map"):
            m = d.get("col_map"); parts += [f"--{side}-col-map", q(m if isinstance(m, str) else json.dumps(m, ensure_ascii=False))]
    parts += ["--known-side", str(payload.get("known_side") or "branch"), "--known-ct", f"{float(payload.get('known_ct') or 15):g}"]
    for k in ("pre_s", "post_s", "tol_s"):
        if payload.get(k) not in (None, ""):
            parts += [f"--{k.replace('_s', '')}", f"{float(payload[k]):g}"]
    return " ".join(parts)


def _side_spec(a, side: str) -> dict:
    g = lambda k: getattr(a, f"{side}_{k}")   # noqa: E731
    spec = {"path": g("file"), "t_event": g("time"), "phase": g("phase"), "wiring": g("wiring") or "", "reconstruct_3w": "1" if g("reconstruct_3w") else "",
            "invert_current": "1" if g("invert_current") else "", "invert_phases": g("invert_phases") or ""}
    if g("col_map"):
        spec["col_map_enabled"] = "1"; spec["col_map"] = g("col_map")
    return spec


def main() -> int:
    from elec_tool.ct_estimate import CtEstimateError, estimate_ct
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for side, name in (("bus", "总线侧"), ("branch", "分路侧")):
        ap.add_argument(f"--{side}-file", required=True, help=f"{name}波形 CSV")
        ap.add_argument(f"--{side}-time", required=True, help=f"{name}该次启停时刻（完整日期时间 / epoch 秒 / HH:MM:SS[.fff]）")
        ap.add_argument(f"--{side}-phase", default="A", choices=("A", "B", "C"), help=f"{name}所用单相电流")
        ap.add_argument(f"--{side}-wiring", default=None, choices=("3p4w", "3p3w"), help=f"{name}接线方式（默认 3p4w）")
        ap.add_argument(f"--{side}-reconstruct-3w", action="store_true", help=f"{name}3P3W 虚拟中性点重构")
        ap.add_argument(f"--{side}-invert-current", action="store_true", help=f"{name}三相电流极性反转")
        ap.add_argument(f"--{side}-invert-phases", default=None, help=f"{name}分相电流极性反转，如 A / AC")
        ap.add_argument(f"--{side}-col-map", default=None, help=f'{name}离线文件列映射 JSON，如 {{"timestamp":1,"ua":2,"ia":3,...}}')
    ap.add_argument("--known-side", default="branch", choices=("bus", "branch"), help="CT 已知的一侧（默认分路侧）")
    ap.add_argument("--known-ct", type=float, default=15.0, help="已知一侧的 CT 变比（默认 15）")
    ap.add_argument("--pre", type=float, default=2.0, help="前窗（秒，默认 2）")
    ap.add_argument("--post", type=float, default=2.0, help="后窗（秒，默认 2；应 ≥ 设备启动过程时长）")
    ap.add_argument("--tol", type=float, default=1.0, help="时刻容差（秒，默认 1）")
    ap.add_argument("--config", default=None, help="出厂 / 基准配置文件（只取 f_nom、列映射缺省等；默认 configs/default.json）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    a = ap.parse_args()
    try:
        cfg = AppConfig.load(a.config or os.path.join(ROOT, "configs", "default.json"))
        out = estimate_ct(cfg, _side_spec(a, "bus"), _side_spec(a, "branch"), known_side=a.known_side, known_ct=a.known_ct,
                          pre_s=a.pre, post_s=a.post, tol_s=a.tol)
    except (CtEstimateError, ConfigError, OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2)); return 0
    from elec_tool.wave_preview import fmt_t
    for side, name in (("bus", "总线侧"), ("branch", "分路侧")):
        m = out[side]
        print(f"{name} {m['path']}  {m['phase']} 相  接线 {m['wiring']}{'+重构' if m['reconstruct_3w'] else ''}  极性反转 {'全部' if m['invert_current'] else (m['invert_phases'] or '无')}")
        print(f"  台阶时刻 {fmt_t(m['t_step'])}  前 {m['pre_a']:.4f} A → 后 {m['post_a']:.4f} A  ΔI = {m['delta_a']:+.4f} A（二次侧）  噪声 {m['noise_a']:.4f} A"
              + (f"  信噪比 {m['snr']:.1f}" if m['snr'] is not None else ""))
    print(f"已知 {out['known_side']} CT = {out['known_ct']:g}  →  估计 {out['estimated_side']} CT ≈ "
          + (f"{out['estimated_ct']:.2f}" if out['estimated_ct'] is not None else "无法估计") + f"   （{out['formula']}）")
    for n in out["notes"]:
        print("  ⚠ " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
