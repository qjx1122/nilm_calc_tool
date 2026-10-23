#!/usr/bin/env python
"""负荷辨识调参助手：量一段「背景」数据的逐周波噪声，给出 6 种算法参数的建议起点。

用法（在仓库根目录、已激活 .venv）：
    python tools/nilm_tune.py --file data/xxx.csv                  # 用默认 configs/default.json 的 PT/CT 口径
    python tools/nilm_tune.py --file data/xxx.csv --config configs/site.json --channel A
    python tools/nilm_tune.py --file data/xxx.csv --min-load-w 500  # 指定现场最小关心负荷（W，计算口径），直接给出一套参数
    python tools/nilm_tune.py --file data/xxx.csv --json            # 机器可读输出（可直接 PUT /api/config 的 nilm 片段）
    python tools/nilm_tune.py --file data/只有电流.csv --min-load-a 2  # v0.38：仅电流数据 → 按电流有效值 I 统计，给 *_a（A）阈值
    python tools/nilm_tune.py --file data/xxx.csv --min-load-w 500 --apply
        # v0.50：在当前运行配置（--config；缺省＝configs/runtime.json，没有则 configs/default.json）基础上叠加建议参数，
        # 把更新后的**完整配置**写到输出目录 output/nilm/nilm_tuned_config_<时间戳>.json；**不改配置文件本身**
    python tools/nilm_tune.py --file data/xxx.csv --apply --out output/site_tuned.json      # 指定输出文件
    python tools/nilm_tune.py --file data/xxx.csv --apply --save-config                     # 显式要求：同时回写 --config 文件

理想输入是**没有投切事件的稳态段**（几十秒即可）；若文件含事件，脚本用稳健统计量（中位数 / MAD）削弱其影响，
并提示「窗内极差」供判断。输出的单位与界面一致：启用 PT/CT 时为一次侧 W / A。

检测量 ``--quantity auto|p|i``（与 nilm.quantity 同义；**不填时取 --config 的 nilm.quantity**，配置也没有才是 auto）：
有电压按逐周波有功 P 统计、建议 ``*_w``（W）阈值；
数据源无电压（电压列未映射 / 全 0）或显式 ``i`` 时按逐周波电流有效值 I 统计、建议 ``*_a``（A）阈值，并在 JSON 里带
``quantity``，nilm_replay.py ``--params`` 会一并套用。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from elec_tool.config import NILM_ALGO_DEFAULTS, NILM_CHANNELS, AppConfig, ConfigError, load_or_default   # noqa: E402
from elec_tool.nilm_tuning import (TuneError, _SUFFIX, _ceil_sig, export_tuned_config, measure, run_tune,   # noqa: E402,F401
                                   suggest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="背景数据 CSV（与数据源同格式）")
    ap.add_argument("--config", default=None,
                    help="基准配置文件（PT/CT、fs、f_nom 由此读取，--apply 在其基础上更新）；缺省＝当前运行配置 "
                         "configs/runtime.json，没有则 configs/default.json")
    ap.add_argument("--channel", default=None, choices=NILM_CHANNELS,
                    help="检测对象（默认：P 口径 total，I 口径 A）。I 口径没有跨相合并，只能单相（A/B/C），不接受 total")
    ap.add_argument("--min-load-w", type=float, default=None, help="现场最小关心负荷（W，计算口径；P 口径用）")
    ap.add_argument("--min-load-a", type=float, default=None, help="现场最小关心负荷电流（A，计算口径；I 口径用）")
    ap.add_argument("--min-load-auto", action="store_true",
                    help="v0.55：未手填 --min-load-w/-a 时，从文件中的投切台阶估计最小关心负荷（仅分路侧含启停的录波有效；估计不可靠则按未指定处理）")
    ap.add_argument("--quantity", default=None, choices=("auto", "p", "i"),
                    help="检测量：p 有功 / i 电流有效值 / auto（数据源无电压时自动 i）。不填时取 --config 里的 nilm.quantity（v0.45）")
    ap.add_argument("--t-start", default="", help="v0.52：分析起始时间（'2026-10-13 08:00:02.5' / '08:00:02.5' / epoch 秒；空＝文件开头）")
    ap.add_argument("--t-end", default="", help="v0.52：分析结束时间（格式同上；空＝文件结尾）")
    ap.add_argument("--duration", type=float, default=None, help="v0.52：从起始时间（或文件开头）起分析的时长（秒）；与 --t-end 同时给时取先到者")
    ap.add_argument("--custom-time", action="store_true",
                    help="v0.73：启用自定义时间（与界面波形预览一致）：时间轴＝自定义起始时间 + 行号/fs，文件时长＝点数/采样率；"
                         "--t-start/--t-end 按这条时间轴解释（完整日期时间 / epoch 秒 / HH:MM:SS），都空＝整个文件")
    ap.add_argument("--custom-time-start", default="", help="自定义起始时间（空＝文件第 1 条数据时间）")
    ap.add_argument("--custom-time-end", default="", help="自定义结束时间（空＝起始 + 点数/采样率；作为 --t-end 为空时的缺省终点）")
    ap.add_argument("--max-cycles", type=int, default=30000, help="最多分析的周波数（默认 30000 ≈ 10 min@50Hz）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    ap.add_argument("--apply", action="store_true",
                    help="v0.50：把建议参数叠加到 --config 配置上，写出更新后的完整配置到输出目录（默认 output/nilm/"
                         "nilm_tuned_config_<时间戳>.json）；不回写配置文件")
    ap.add_argument("--out", default=None, help="--apply 的输出文件路径（默认见 --apply）")
    ap.add_argument("--save-config", action="store_true",
                    help="与 --apply 连用：**额外**把更新后的配置回写到 --config 指定的文件（默认不回写；运行中的服务需重启/重新加载才生效）")
    a = ap.parse_args()

    cfg_path = a.config or _default_config_path()
    base_cfg = load_or_default(cfg_path)
    try:
        out = run_tune(base_cfg, a.file, channel=a.channel, quantity=a.quantity, min_load_w=a.min_load_w,
                       min_load_a=a.min_load_a, max_cycles=a.max_cycles, t_start=a.t_start, t_end=a.t_end,
                       custom_time=a.custom_time, custom_time_start=a.custom_time_start, custom_time_end=a.custom_time_end,
                       duration_s=a.duration, min_load_auto=a.min_load_auto)
    except (TuneError, ConfigError) as exc:
        print(f"⚠ {exc}", file=sys.stderr)
        return 2
    for n_ in out["notes"]:
        print(f"提示：{n_}", file=sys.stderr)
    qty, unit, channel, m, sg = out["quantity"], out["unit"], out["channel"], out["measure"], out["suggest"]
    q_src = "--quantity" if a.quantity else f"配置 nilm.quantity={out['quantity_requested']}"
    u_nonzero = out["voltage_present"]
    q_req = out["quantity_requested"]
    applied = None
    if a.apply:
        if a.save_config and not a.config and not os.path.isfile(cfg_path):
            print(f"⚠ --save-config 需要一个存在的配置文件（当前基准 {cfg_path} 不存在）", file=sys.stderr)
            return 2
        new_cfg, path, notes = export_tuned_config(
            base_cfg, out, out_path=a.out, meta={"base_config": cfg_path if os.path.isfile(cfg_path) else "(内置默认)"})
        applied = {"base_config": cfg_path, "saved_to": path, "changes": notes, "config_file_updated": False}
        if a.save_config:
            new_cfg.save(cfg_path)
            applied["config_file_updated"] = True
        out["applied"] = applied
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    sx = _SUFFIX[unit]
    print(f"文件 {a.file}  对象 {channel}  周波 {m['cycles']}  时长 {out['t_span_s']:.1f} s  口径 {'一次侧(PT/CT)' if out['scaled'] else '二次侧'}"
          f"  检测量 {'有功 P' if qty == 'p' else '电流有效值 I'}（{q_src}" + ("，数据源无电压 → auto 选 I" if (qty == "i" and not u_nonzero and q_req == "auto") else "") + "）")
    tr = out["t_range"]
    if not tr["whole_file"]:
        from elec_tool.timefmt import fmt_local
        print(f"时间段  {tr['start'] or '文件开头'} → {tr['end'] or ('+' + str(tr['duration_s']) + ' s' if tr['duration_s'] else '文件结尾')}"
              f"   实际 {fmt_local(tr['t_first'])} → {fmt_local(tr['t_last'])}")
    print(f"—— 噪声统计（{unit}）——")
    print(f"  基荷 |{'P' if qty == 'p' else 'I'}| 中位数        level      = {m['level']:.4g}")
    print(f"  单周波噪声 σ(稳健)     sigma      = {m['sigma_cycle']:.4g}  ({m['sigma_cycle_pct']:.3f} % 基荷)")
    print(f"  相邻周波最大 |Δ|       max|diff|  = {m['max_abs_diff']:.4g}" + ("   ⚠ >10σ：段内含事件/尖峰，统计已用稳健口径" if m["has_events_hint"] else ""))
    print(f"  5 周波极差 95 分位     range5     = {m['range5_p95']:.4g}   → settle_tol{sx} 的依据")
    print(f"  10 周波极差 95 分位    range10    = {m['range10_p95']:.4g}   → steady_state.tol{sx} 的依据")
    print(f"  10 周波均值差 σ        sigma_m10  = {m['sigma_mean10']:.4g}   → 双滑窗/GLR 的噪声尺度")
    print(f"  范围                   [{m['min']:.4g}, {m['max']:.4g}]")
    est = out["min_load_estimate"]
    print(f"—— 最小关心负荷估计（文件投切台阶）——")
    if est["candidate"] is None:
        print(f"  无法估计：{est['note']}")
    else:
        print(f"  候选 {est['candidate']:.4g} {unit}  （最小跳变 {est['min_step']:.4g}，最小台阶间距 {est['min_level_gap']:.4g}，"
              f"稳态段 {est['n_steady']}，台阶 {est['levels']}）  {'✓ 可靠' if est['reliable'] else '⚠ 不可靠'}"
              + ("" if out["min_load_source"] != "estimated" else "  → 本次已采用（--min-load-auto）"))
        print(f"  最大跳变 {est['max_step']:.4g} {unit}（最大/最小 {est['step_ratio']:.1f} 倍）"
              + (f"   ⚠ 分两簇：主负荷 ≈{est['primary_step']:.4g}（{est['n_primary']} 次）+ 二级波动 ≈{est['secondary_step']:.4g}（{est['n_secondary']} 次）"
                 f"；只关心主负荷请 --min-load-{'a' if unit == 'A' else 'w'} {est['primary_step']:.4g}" if est.get("split") else ""))
    rep = out.get("repetition") or {}
    if rep.get("suspected"):
        print(f"  ⚠ 文件疑似模板拼接：每 {rep['period_s']:g} s 逐位重复（{rep['match_pct']:.1f}%），统计与事件计数不代表真实现场")
    print("—— 建议参数（起点，按 NILM_TUNING_GUIDE.md 复核）——")
    print(f"  {sg['note']}")
    print(f"  nilm.quantity = {qty}   nilm.rel_tol_pct = {sg['rel_tol_pct']}   nilm.min_delta_pct = {sg['min_delta_pct']}"
          + (f"   nilm.window_cycles = {sg['window_cycles']}" if sg.get("window_cycles") else ""))
    tr = sg.get("transient") or {}
    if tr:
        print(f"  最长暂态 {tr.get('longest', 0)} 周波（暂态 {tr.get('n_transients', 0)} 次，锚点稳态 {tr.get('n_steady', 0)} 段）"
              + (f"，斜坡上最长伪稳态平台 {tr['max_pseudo_steady']} 周波" if tr.get("max_pseudo_steady") is not None else ""))
    for k, v in sg["algorithms"].items():
        print(f"  {k:13s} " + "  ".join(f"{kk}={vv:g}" if isinstance(vv, float) else f"{kk}={vv}" for kk, vv in v.items()))
    print("提示：把上面 algorithms 片段填进界面「检测参数」或 PUT /api/config {\"nilm\": {\"algorithms\": {...}}}；"
          "用含已知投切的文件回放核对漏报/误报后再微调。")
    if applied:
        print("—— 已更新配置（--apply）——")
        print(f"  基准配置   {applied['base_config']}")
        print(f"  已保存到   {applied['saved_to']}   （完整配置，可作 --config / ELEC_TOOL_CONFIG_PATH 使用，"
              "或 nilm_replay.py --config 回放核对）")
        print("  配置文件   " + ("已回写（--save-config）" if applied["config_file_updated"] else "未改动（默认；要回写加 --save-config）"))
    return 0


def _default_config_path() -> str:
    """未指定 --config 时的基准：与 Web 服务一致——存在 configs/runtime.json（界面保存的当前运行配置）就用它，否则 configs/default.json。"""
    env = os.environ.get("ELEC_TOOL_CONFIG_PATH", "").strip()
    if env:
        return env
    rt = os.path.join(ROOT, "configs", "runtime.json")
    return rt if os.path.isfile(rt) else os.path.join(ROOT, "configs", "default.json")


if __name__ == "__main__":
    sys.exit(main())
