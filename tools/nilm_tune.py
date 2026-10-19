#!/usr/bin/env python
"""负荷辨识调参助手：量一段「背景」数据的逐周波噪声，给出 6 种算法参数的建议起点。

用法（在仓库根目录、已激活 .venv）：
    python tools/nilm_tune.py --file data/xxx.csv                  # 用默认 configs/default.json 的 PT/CT 口径
    python tools/nilm_tune.py --file data/xxx.csv --config configs/site.json --channel A
    python tools/nilm_tune.py --file data/xxx.csv --min-load-w 500  # 指定现场最小关心负荷（W，计算口径），直接给出一套参数
    python tools/nilm_tune.py --file data/xxx.csv --json            # 机器可读输出（可直接 PUT /api/config 的 nilm 片段）
    python tools/nilm_tune.py --file data/只有电流.csv --min-load-a 2  # v0.38：仅电流数据 → 按电流有效值 I 统计，给 *_a（A）阈值

理想输入是**没有投切事件的稳态段**（几十秒即可）；若文件含事件，脚本用稳健统计量（中位数 / MAD）削弱其影响，
并提示「窗内极差」供判断。输出的单位与界面一致：启用 PT/CT 时为一次侧 W / A。

检测量 ``--quantity auto|p|i``（与 nilm.quantity 同义，默认 auto）：有电压按逐周波有功 P 统计、建议 ``*_w``（W）阈值；
数据源无电压（电压列未映射 / 全 0）或显式 ``i`` 时按逐周波电流有效值 I 统计、建议 ``*_a``（A）阈值，并在 JSON 里带
``quantity``，nilm_replay.py ``--params`` 会一并套用。
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


def measure(p: np.ndarray, unit: str = "W") -> dict:
    """逐周波序列（有功 W 或电流有效值 A）的噪声统计。键名不带单位，``unit`` 字段标明。"""
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
        "cycles": int(len(p)), "unit": unit, "level": level,
        "sigma_cycle": sigma, "sigma_cycle_pct": (100.0 * sigma / level if level else float("nan")),
        "max_abs_diff": float(np.max(np.abs(d))) if d.size else 0.0,
        "has_events_hint": bool(d.size and np.max(np.abs(d)) > 10 * sigma),
        "range5_p95": rng(5), "range10_p95": rng(10),
        "sigma_mean10": sig_m10,
        "min": float(p.min()), "max": float(p.max()),
    }


_SUFFIX = {"W": "_w", "A": "_a"}


def suggest(m: dict, min_load: float | None) -> dict:
    """由噪声统计给出参数建议（规则见 NILM_TUNING_GUIDE.md §2）。单位随 ``m["unit"]``：W → ``*_w``，A → ``*_a``。"""
    unit = m.get("unit", "W")
    sx = _SUFFIX[unit]
    s, lvl = m["sigma_cycle"], m["level"]
    tol = _ceil_sig(max(m["range5_p95"] * 1.2, 4 * s))                # 稳态容差：5 周波极差 95 分位 ×1.2
    noise_floor = _ceil_sig(max(6 * s, 1e-9))                        # 噪声能触发的最小「阶跃」
    if min_load is None:
        min_d = _ceil_sig(max(noise_floor, 0.02 * lvl))              # 没给最小负荷：取 6σ 与 2% 基荷的大者
        note = f"未指定 --min-load-{sx[1]}，min_delta{sx} 取 max(6σ, 2%×基荷)；请按现场最小关心负荷改"
    else:
        min_d = _ceil_sig(max(0.5 * float(min_load), noise_floor))   # 门槛放在最小负荷的一半，但不低于噪声底
        note = (f"min_delta{sx} = max(最小关心负荷/2, 6σ)" if 0.5 * min_load >= noise_floor
                else f"⚠ 最小关心负荷 {min_load:g} {unit} 的一半低于噪声底 {noise_floor:g} {unit}：该负荷无法可靠检出，门槛按噪声底给")
    k = _ceil_sig(max(0.25 * min_d, 0.5 * s))                        # CUSUM 漂移：取最小幅值的 1/4（兼顾缓慢爬坡）
    h = _ceil_sig(max(2.0 * (min_d - k), 5 * s))                     # 门限：恰为 min_delta 的阶跃约 2 周波触发；且 ≥5σ
    # 相对门槛只在「基荷远大于门槛」时有意义；基荷小（分路侧设备关着时 P≈0）会算出 >100% 甚至几千 %，
    # 配置校验 rel_tol_pct ≤ 50 / min_delta_pct ≤ 100 会拒绝 → 一律夹到合法范围，门槛以绝对值为准
    mdp = (100.0 * min_d / lvl) if lvl else 0.0
    if mdp > 50.0:
        mdp = 0.0
        note += f"；基荷相对门槛过小（基荷 < 2×min_delta{sx}），nilm.min_delta_pct 置 0，只用各算法绝对值 {unit}"
    tol10 = _ceil_sig(max(m["range10_p95"] * 1.2, 5 * s))
    noise = _ceil_sig(max(s, 1e-9))
    return {
        "note": note, "unit": unit, "quantity": "p" if unit == "W" else "i",
        "rel_tol_pct": round(min(5.0, max(0.05, 100.0 * tol / lvl)), 2) if lvl else 1.0,
        "min_delta_pct": round(mdp, 2),
        "algorithms": {
            "threshold":    {f"min_delta{sx}": min_d, "settle_cycles": 5, f"settle_tol{sx}": tol, "max_rise_cycles": 40},
            "median_diff":  {"median_cycles": 5, f"min_delta{sx}": min_d, "settle_cycles": 5, f"settle_tol{sx}": tol, "max_rise_cycles": 40},
            "two_window":   {"pre_cycles": 10, "post_cycles": 10, f"min_delta{sx}": min_d, "k_sigma": 3.0},
            "cusum":        {f"drift{sx}": k, f"threshold{sx}": h, f"min_delta{sx}": min_d, "settle_cycles": 5},
            "glr":          {"window_cycles": 15, "threshold": 25.0, f"min_delta{sx}": min_d, f"noise{sx}": noise, "settle_cycles": 5},
            "steady_state": {f"tol{sx}": tol10, "min_steady_cycles": 10, f"min_delta{sx}": min_d, "max_transient_cycles": 100},
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="背景数据 CSV（与数据源同格式）")
    ap.add_argument("--config", default=None, help="配置文件（PT/CT、fs、f_nom 由此读取；默认 configs/default.json）")
    ap.add_argument("--channel", default="total", choices=NILM_CHANNELS)
    ap.add_argument("--min-load-w", type=float, default=None, help="现场最小关心负荷（W，计算口径；P 口径用）")
    ap.add_argument("--min-load-a", type=float, default=None, help="现场最小关心负荷电流（A，计算口径；I 口径用）")
    ap.add_argument("--quantity", default="auto", choices=("auto", "p", "i"),
                    help="检测量：p 有功 / i 电流有效值 / auto（默认，数据源无电压时自动 i）")
    ap.add_argument("--max-cycles", type=int, default=30000, help="最多分析的周波数（默认 30000 ≈ 10 min@50Hz）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    a = ap.parse_args()

    cfg = load_or_default(a.config) if a.config else load_or_default(None)
    cfg.source.kind = "csv_file"; cfg.source.path = a.file
    cfg.validate()
    feat = CycleFeatures(cfg.sampling.fs, cfg.sampling.f_nom)
    ci = NILM_CHANNELS.index(a.channel)
    ps, is_, ts = [], [], []
    u_nonzero = False
    with create_source(cfg) as src:
        while True:
            blk = src.read()
            if blk is None:
                if src.exhausted:
                    break
                continue
            if not u_nonzero and np.any(np.abs(blk.u) > 0):
                u_nonzero = True
            f = feat.push(scale_block(blk, cfg.transform))
            if f["t"].size:
                ps.append(f["p"][ci]); is_.append(f["i"][ci]); ts.append(f["t"])
            if sum(len(x) for x in ps) >= a.max_cycles:
                break
    if not ps:
        print("没有读到整周波数据", file=sys.stderr)
        return 2
    qty = a.quantity if a.quantity != "auto" else ("i" if not u_nonzero else "p")
    if qty == "p" and not u_nonzero:
        print("⚠ 数据源没有电压（电压列未映射或全为 0）：有功恒为 0，无法按 P 调参；请用 --quantity i（或 auto）", file=sys.stderr)
        return 2
    unit = "W" if qty == "p" else "A"
    p = np.concatenate(ps if qty == "p" else is_); t = np.concatenate(ts)
    m = measure(p, unit)
    min_load = a.min_load_w if qty == "p" else a.min_load_a
    if qty == "i" and a.min_load_w is not None and a.min_load_a is None:
        print("提示：I 口径请用 --min-load-a（A）；--min-load-w 已忽略", file=sys.stderr)
    sg = suggest(m, min_load)
    out = {"file": a.file, "channel": a.channel, "fs": cfg.sampling.fs, "f_nom": cfg.sampling.f_nom,
           "quantity": qty, "unit": unit, "voltage_present": u_nonzero,
           "scaled": bool(cfg.transform.enabled), "t_span_s": float(t[-1] - t[0]) if len(t) > 1 else 0.0,
           "measure": m, "suggest": sg}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    sx = _SUFFIX[unit]
    print(f"文件 {a.file}  对象 {a.channel}  周波 {m['cycles']}  时长 {out['t_span_s']:.1f} s  口径 {'一次侧(PT/CT)' if out['scaled'] else '二次侧'}"
          f"  检测量 {'有功 P' if qty == 'p' else '电流有效值 I'}" + ("（数据源无电压，auto 自动选 I）" if (qty == "i" and not u_nonzero and a.quantity == "auto") else ""))
    print(f"—— 噪声统计（{unit}）——")
    print(f"  基荷 |{'P' if qty == 'p' else 'I'}| 中位数        level      = {m['level']:.4g}")
    print(f"  单周波噪声 σ(稳健)     sigma      = {m['sigma_cycle']:.4g}  ({m['sigma_cycle_pct']:.3f} % 基荷)")
    print(f"  相邻周波最大 |Δ|       max|diff|  = {m['max_abs_diff']:.4g}" + ("   ⚠ >10σ：段内含事件/尖峰，统计已用稳健口径" if m["has_events_hint"] else ""))
    print(f"  5 周波极差 95 分位     range5     = {m['range5_p95']:.4g}   → settle_tol{sx} 的依据")
    print(f"  10 周波极差 95 分位    range10    = {m['range10_p95']:.4g}   → steady_state.tol{sx} 的依据")
    print(f"  10 周波均值差 σ        sigma_m10  = {m['sigma_mean10']:.4g}   → 双滑窗/GLR 的噪声尺度")
    print(f"  范围                   [{m['min']:.4g}, {m['max']:.4g}]")
    print("—— 建议参数（起点，按 NILM_TUNING_GUIDE.md 复核）——")
    print(f"  {sg['note']}")
    print(f"  nilm.quantity = {qty}   nilm.rel_tol_pct = {sg['rel_tol_pct']}   nilm.min_delta_pct = {sg['min_delta_pct']}")
    for k, v in sg["algorithms"].items():
        print(f"  {k:13s} " + "  ".join(f"{kk}={vv:g}" if isinstance(vv, float) else f"{kk}={vv}" for kk, vv in v.items()))
    print("提示：把上面 algorithms 片段填进界面「检测参数」或 PUT /api/config {\"nilm\": {\"algorithms\": {...}}}；"
          "用含已知投切的文件回放核对漏报/误报后再微调。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
