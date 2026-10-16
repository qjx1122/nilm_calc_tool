#!/usr/bin/env python
"""负荷辨识调参助手：量一段「背景」数据的逐周波噪声，给出 6 种算法参数的建议起点。

用法（在仓库根目录、已激活 .venv）：
    python tools/nilm_tune.py --file data/xxx.csv                  # 用默认 configs/default.json 的 PT/CT 口径
    python tools/nilm_tune.py --file data/xxx.csv --config configs/site.json --channel A
    python tools/nilm_tune.py --file data/xxx.csv --min-load-w 500  # 指定现场最小关心负荷（W，计算口径），直接给出一套参数
    python tools/nilm_tune.py --file data/xxx.csv --json            # 机器可读输出（可直接 PUT /api/config 的 nilm 片段）

理想输入是**没有投切事件的稳态段**（几十秒即可）；若文件含事件，脚本用稳健统计量（中位数 / MAD）削弱其影响，
并提示「窗内 |P| 极差」供判断。输出的单位与界面一致：启用 PT/CT 时为一次侧 W。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from elec_tool.config import NILM_ALGO_DEFAULTS, NILM_CHANNELS, load_or_default   # noqa: E402
from elec_tool.nilm import CycleFeatures                                            # noqa: E402
from elec_tool.scaling import scale_block                                           # noqa: E402
from elec_tool.sources import create_source                                         # noqa: E402


def _ceil_sig(x: float, sig: int = 2) -> float:
    """向上取 2 位有效数字（参数填整数好记）。"""
    if x <= 0 or not math.isfinite(x):
        return 0.0
    e = math.floor(math.log10(x)) - (sig - 1)
    return math.ceil(x / 10 ** e) * 10 ** e


def measure(p: np.ndarray) -> dict:
    """逐周波有功序列的噪声统计。"""
    p = np.asarray(p, dtype=np.float64)
    d = np.diff(p)
    mad_d = float(np.median(np.abs(d - np.median(d)))) * 1.4826          # 差分的稳健 σ_d
    sigma = mad_d / math.sqrt(2.0)                                       # 单周波噪声 σ（差分方差 = 2σ²）
    level = float(np.median(np.abs(p)))
    # 5 周波 / 10 周波滚动极差的 95 分位（稳态容差直接看这个）
    # 稳健口径：取 min(95 分位, 2×中位数)，段内偶有事件时不被少数含事件的窗拉高
    def rng(n: int) -> float:
        if len(p) < n:
            return float("nan")
        w = np.lib.stride_tricks.sliding_window_view(p, n)
        r = w.max(axis=1) - w.min(axis=1)
        return float(min(np.percentile(r, 95), 2.0 * np.median(r)))
    # 相邻两个 10 周波均值之差的稳健 σ（双滑窗 / GLR 的噪声尺度；高斯噪声下 ≈ σ×sqrt(2/10)）
    if len(p) >= 30:
        m10 = np.convolve(p, np.ones(10) / 10, mode="valid")
        dm = m10[10:] - m10[:-10]
        sig_m10 = float(np.median(np.abs(dm - np.median(dm)))) * 1.4826
    else:
        sig_m10 = float("nan")
    return {
        "cycles": int(len(p)), "level_w": level,
        "sigma_cycle_w": sigma, "sigma_cycle_pct": (100.0 * sigma / level if level else float("nan")),
        "max_abs_diff_w": float(np.max(np.abs(d))) if d.size else 0.0,
        "has_events_hint": bool(d.size and np.max(np.abs(d)) > 10 * sigma),
        "range5_p95_w": rng(5), "range10_p95_w": rng(10),
        "sigma_mean10_w": sig_m10,
        "p_min_w": float(p.min()), "p_max_w": float(p.max()),
    }


def suggest(m: dict, min_load_w: float | None) -> dict:
    """由噪声统计给出参数建议（规则见 NILM_TUNING_GUIDE.md §2）。"""
    s, lvl = m["sigma_cycle_w"], m["level_w"]
    tol = _ceil_sig(max(m["range5_p95_w"] * 1.2, 4 * s))             # 稳态容差：5 周波极差 95 分位 ×1.2
    noise_floor = _ceil_sig(max(6 * s, 1e-9))                        # 噪声能触发的最小「阶跃」
    if min_load_w is None:
        min_d = _ceil_sig(max(noise_floor, 0.02 * lvl))              # 没给最小负荷：取 6σ 与 2% 基荷的大者
        note = "未指定 --min-load-w，min_delta_w 取 max(6σ, 2%×基荷)；请按现场最小关心负荷改"
    else:
        min_d = _ceil_sig(max(0.5 * float(min_load_w), noise_floor))  # 门槛放在最小负荷的一半，但不低于噪声底
        note = ("min_delta_w = max(最小关心负荷/2, 6σ)" if 0.5 * min_load_w >= noise_floor
                else f"⚠ 最小关心负荷 {min_load_w:g} W 的一半低于噪声底 {noise_floor:g} W：该负荷无法可靠检出，门槛按噪声底给")
    k = _ceil_sig(max(0.25 * min_d, 0.5 * s))                        # CUSUM 漂移：取最小幅值的 1/4（兼顾缓慢爬坡）
    h = _ceil_sig(max(2.0 * (min_d - k), 5 * s))                     # 门限：恰为 min_delta 的阶跃约 2 周波触发；且 ≥5σ
    # 相对门槛只在「基荷远大于门槛」时有意义；基荷小（分路侧设备关着时 P≈0）会算出 >100% 甚至几千 %，
    # 配置校验 rel_tol_pct ≤ 50 / min_delta_pct ≤ 100 会拒绝 → 一律夹到合法范围，门槛以绝对值 W 为准
    mdp = (100.0 * min_d / lvl) if lvl else 0.0
    if mdp > 50.0:
        mdp = 0.0
        note += "；基荷相对门槛过小（基荷 < 2×min_delta_w），nilm.min_delta_pct 置 0，只用各算法绝对值 W"
    return {
        "note": note,
        "rel_tol_pct": round(min(5.0, max(0.05, 100.0 * tol / lvl)), 2) if lvl else 1.0,
        "min_delta_pct": round(mdp, 2),
        "algorithms": {
            "threshold":    {"min_delta_w": min_d, "settle_cycles": 5, "settle_tol_w": tol, "max_rise_cycles": 40},
            "median_diff":  {"median_cycles": 5, "min_delta_w": min_d, "settle_cycles": 5, "settle_tol_w": tol, "max_rise_cycles": 40},
            "two_window":   {"pre_cycles": 10, "post_cycles": 10, "min_delta_w": min_d, "k_sigma": 3.0},
            "cusum":        {"drift_w": k, "threshold_w": h, "min_delta_w": min_d, "settle_cycles": 5},
            "glr":          {"window_cycles": 15, "threshold": 25.0, "min_delta_w": min_d, "noise_w": _ceil_sig(max(s, 1e-9)), "settle_cycles": 5},
            "steady_state": {"tol_w": _ceil_sig(max(m["range10_p95_w"] * 1.2, 5 * s)), "min_steady_cycles": 10, "min_delta_w": min_d, "max_transient_cycles": 100},
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="背景数据 CSV（与数据源同格式）")
    ap.add_argument("--config", default=None, help="配置文件（PT/CT、fs、f_nom 由此读取；默认 configs/default.json）")
    ap.add_argument("--channel", default="total", choices=NILM_CHANNELS)
    ap.add_argument("--min-load-w", type=float, default=None, help="现场最小关心负荷（W，计算口径）")
    ap.add_argument("--max-cycles", type=int, default=30000, help="最多分析的周波数（默认 30000 ≈ 10 min@50Hz）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    a = ap.parse_args()

    cfg = load_or_default(a.config) if a.config else load_or_default(None)
    cfg.source.kind = "csv_file"; cfg.source.path = a.file
    cfg.validate()
    feat = CycleFeatures(cfg.sampling.fs, cfg.sampling.f_nom)
    ci = NILM_CHANNELS.index(a.channel)
    ps, ts = [], []
    with create_source(cfg) as src:
        while True:
            blk = src.read()
            if blk is None:
                if src.exhausted:
                    break
                continue
            f = feat.push(scale_block(blk, cfg.transform))
            if f["t"].size:
                ps.append(f["p"][ci]); ts.append(f["t"])
            if sum(len(x) for x in ps) >= a.max_cycles:
                break
    if not ps:
        print("没有读到整周波数据", file=sys.stderr)
        return 2
    p = np.concatenate(ps); t = np.concatenate(ts)
    m = measure(p)
    sg = suggest(m, a.min_load_w)
    out = {"file": a.file, "channel": a.channel, "fs": cfg.sampling.fs, "f_nom": cfg.sampling.f_nom,
           "scaled": bool(cfg.transform.enabled), "t_span_s": float(t[-1] - t[0]) if len(t) > 1 else 0.0,
           "measure": m, "suggest": sg}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(f"文件 {a.file}  对象 {a.channel}  周波 {m['cycles']}  时长 {out['t_span_s']:.1f} s  口径 {'一次侧(PT/CT)' if out['scaled'] else '二次侧'}")
    print("—— 噪声统计（W）——")
    print(f"  基荷 |P| 中位数        level      = {m['level_w']:.4g}")
    print(f"  单周波噪声 σ(稳健)     sigma      = {m['sigma_cycle_w']:.4g}  ({m['sigma_cycle_pct']:.3f} % 基荷)")
    print(f"  相邻周波最大 |ΔP|      max|diff|  = {m['max_abs_diff_w']:.4g}" + ("   ⚠ >10σ：段内含事件/尖峰，统计已用稳健口径" if m["has_events_hint"] else ""))
    print(f"  5 周波极差 95 分位     range5     = {m['range5_p95_w']:.4g}   → settle_tol_w 的依据")
    print(f"  10 周波极差 95 分位    range10    = {m['range10_p95_w']:.4g}   → steady_state.tol_w 的依据")
    print(f"  10 周波均值差 σ        sigma_m10  = {m['sigma_mean10_w']:.4g}   → 双滑窗/GLR 的噪声尺度")
    print(f"  P 范围                 [{m['p_min_w']:.4g}, {m['p_max_w']:.4g}]")
    print("—— 建议参数（起点，按 NILM_TUNING_GUIDE.md 复核）——")
    print(f"  {sg['note']}")
    print(f"  nilm.rel_tol_pct = {sg['rel_tol_pct']}   nilm.min_delta_pct = {sg['min_delta_pct']}")
    for k, v in sg["algorithms"].items():
        print(f"  {k:13s} " + "  ".join(f"{kk}={vv:g}" if isinstance(vv, float) else f"{kk}={vv}" for kk, vv in v.items()))
    print("提示：把上面 algorithms 片段填进界面「检测参数」或 PUT /api/config {\"nilm\": {\"algorithms\": {...}}}；"
          "用含已知投切的文件回放核对漏报/误报后再微调。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
