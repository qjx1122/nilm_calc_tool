"""负荷辨识调参结果 → 配置（v0.50）。

`tools/nilm_tune.py` 量噪声后给出 6 种算法的建议参数；本模块负责把这份建议**叠加到一份现有配置上**并
把更新后的完整配置写到输出目录，供 nilm_tune.py ``--apply``、nilm_replay.py ``--params`` 与
Web 接口 ``POST /api/nilm/tune/apply`` 共用。

原则：
* 只改 ``nilm.quantity / rel_tol_pct / min_delta_pct / algorithms.<算法>.<已知参数>``，其余配置一律保留；
* 建议里没给的参数（如 ``enabled``、界面手改过的其它键）保持原值；
* **默认不回写配置文件**，只在输出目录（``cfg.nilm.nilm_dir``，默认 ``output/nilm``）生成
  ``nilm_tuned_config_<时间戳>.json``；要落到正式配置须显式要求（CLI ``--save-config`` / API ``persist``）。
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import NILM_ALGO_DEFAULTS, NILM_CHANNELS, AppConfig, ConfigError, parse_play_start


class TuneError(ValueError):
    """输入不满足调参条件（无整周波 / 无电压却按 P / I 口径填 total …）；``code`` 与 CLI 退出码一致（2）。"""

    code = 2


_SUFFIX = {"W": "_w", "A": "_a"}



def _ceil_sig(x: float, sig: int = 2) -> float:
    """向上取 2 位有效数字（参数填整数好记）。"""
    if x <= 0 or not math.isfinite(x):
        return 0.0
    e = math.floor(math.log10(x)) - (sig - 1)
    return math.ceil(x / 10 ** e) * 10 ** e


def _collapse_runs(p: np.ndarray, level: float, *, rtol: float = 1e-7) -> Tuple[np.ndarray, np.ndarray, float]:
    """v0.83：把**逐位相同（或只差数值舍入）的相邻周波**压成一个值。返回 ``(collapsed, run_lengths, repeat_frac)``：
    ``repeat_frac`` = 相邻周波相等的比例。真实录波相邻周波几乎不可能逐位相等；每秒一个模板复制 50 周波的合成文件
    repeat_frac≈0.98、run_lengths≈50。"""
    if p.size < 2:
        return p.copy(), np.ones(p.size, dtype=np.int64), 0.0
    tol = rtol * max(float(level), float(np.max(np.abs(p))), 1e-12)
    same = np.abs(np.diff(p)) <= tol
    starts = np.concatenate(([0], np.flatnonzero(~same) + 1))
    runs = np.diff(np.concatenate((starts, [p.size])))
    return p[starts], runs, float(np.mean(same))


_SIGMA_LAGS = (1, 2, 3, 5, 10, 20, 25, 50, 100)


def _robust_sigma_lag(p: np.ndarray, k: int) -> float:
    """滞后 k 周波差分的稳健 σ（MAD×1.4826/√2）。白噪声下与 k 无关；分段恒定（每段 N 周波同一模板 + 微小舍入）
    的序列 k<N 时趋近 0、k≥N 时等于段间跳变 σ。"""
    if p.size <= k:
        return float("nan")
    dd = p[k:] - p[:-k]
    return float(np.median(np.abs(dd - np.median(dd)))) * 1.4826 / math.sqrt(2.0)


def measure(p: np.ndarray, unit: str = "W", *, repeat_frac_limit: float = 0.2, block_ratio: float = 4.0) -> dict:
    """逐周波序列（有功 W 或电流有效值 A）的噪声统计。键名不带单位，``unit`` 字段标明。

    v0.83：**分段恒定 / 周波复制保护**。差分 MAD 以「相邻周波之差」为样本；若文件每秒由同一模板生成 N 个周波
    （相邻周波逐位相等，或只差 1e-6 量级的舍入），中位数落在 ~0 上，σ 会被量成 1e-7 量级，由它推出的 settle_tol / tol / noise
    在真实秒间抖动（1e-2 量级）面前永远满足不了，负荷辨识配不出任何事件。处理：
    * 在多个滞后 ``_SIGMA_LAGS`` 上量 σ_k（``sigma_lags``）；σ_max/σ_1 ≥ ``block_ratio`` 判为分段恒定（``repeated_cycles``），
      段长 ``repeat_run_cycles`` = σ_k 首次达到 0.9·σ_max 的滞后（相邻周波逐位相等比例 ``repeat_frac`` ≥ ``repeat_frac_limit``
      且同值段中位长 > 1 时直接用同值段长）；σ 取 σ_max（= 段间跳变尺度，``sigma_method = block``）；
    * 极差 / 均值差统计改在**段中位数序列**上做（``run`` 周波一段），极差窗长按段长折算；
    * 结果附 ``sigma_raw``（相邻差分口径）、``sigma_lags``、``repeat_frac / repeat_run_cycles / repeated_cycles / sigma_method``，
      供界面与 CLI 告警。真实录波（各滞后 σ 一致）结果与旧口径完全相同（``sigma_method = diff_mad``）。
    """
    p = np.asarray(p, dtype=np.float64)
    level = float(np.median(np.abs(p))) if p.size else 0.0
    d = np.diff(p)
    sigma_raw = _robust_sigma_lag(p, 1) if p.size > 1 else 0.0
    lags = [k for k in _SIGMA_LAGS if p.size >= 4 * k]
    sig_lags = {int(k): _robust_sigma_lag(p, k) for k in lags}
    finite = [(k, v) for k, v in sig_lags.items() if math.isfinite(v)]
    s_max = max((v for _, v in finite), default=sigma_raw)
    # 逐位相等的同值段（纯复制文件）：作为段长的直接证据
    _, runs, repeat_frac = _collapse_runs(p, level)
    run_eq = float(np.median(runs)) if runs.size else 1.0
    blocky = bool(finite and s_max > 0 and (sigma_raw <= 0 or s_max / sigma_raw >= block_ratio))
    run = 1.0
    if blocky:
        if repeat_frac >= repeat_frac_limit and run_eq > 1:
            run = run_eq
        else:
            run = float(next((k for k, v in finite if v >= 0.9 * s_max), finite[-1][0]))
            # v0.89.1：没有逐位相等证据时，还要求 σ_k 在段长处是**突变**（段长以内各档 ≤ σ_max/5）且段长之后有**平台**
            # （下一档 < 1.5×σ_max）。短文件里台阶密集（如 500 周波 5 个台阶）或长斜坡占比大时，σ_k 随滞后逐档增长、
            # 在最大滞后处才最大，以前会被误判为「分段恒定」把 σ 量成台阶尺度（MW 级），所有建议参数失真
            before = [v for k, v in finite if k <= run / 2]            # 段长一半以内（跨段对不足半数，MAD 仍是段内抖动）
            after = [v for k, v in finite if k > run]
            abrupt = bool(before) and before[-1] <= 0.2 * s_max
            plateau = bool(after) and after[0] < 1.5 * s_max
            if not (abrupt and plateau):
                blocky = False
        if run <= 1.0:                      # σ 在 lag=1 就饱和：不是分段恒定，只是普通噪声
            blocky = False
    if blocky:
        sigma, method = s_max, "block"
        nb = int(p.size // int(run))
        x = np.median(p[: nb * int(run)].reshape(nb, int(run)), axis=1) if nb >= 3 else p
        scale = run if nb >= 3 else 1.0
    else:
        sigma, method, x, scale = sigma_raw, "diff_mad", p, 1.0

    # 5 周波 / 10 周波滚动极差的 95 分位（稳态容差直接看这个）
    # 稳健口径：取 min(95 分位, 2×中位数)，段内偶有事件时不被少数含事件的窗拉高
    # 分段恒定时：原 n 周波窗最多跨 ceil(n/scale)+1 个段，极差按该窗长在段中位数序列上算
    def rng(n: int) -> float:
        if len(p) < n:
            return float("nan")
        n_eff = n if scale <= 1.0 else int(math.ceil(n / scale)) + 1
        if len(x) < n_eff:
            return float(np.max(x) - np.min(x))
        w = np.lib.stride_tricks.sliding_window_view(x, n_eff)
        r = w.max(axis=1) - w.min(axis=1)
        return float(min(np.percentile(r, 95), 2.0 * np.median(r)))
    # 相邻两个 10 周波均值之差的稳健 σ（双滑窗 / GLR 的噪声尺度；高斯噪声下 ≈ σ×sqrt(2/10)）
    # 分段恒定时两个 10 周波均值窗最多隔一个段边界，均值差 = 一次段间跳变（保守取段序列差分 σ）
    if blocky:
        dm = np.diff(x)
        sig_m10 = float(np.median(np.abs(dm - np.median(dm)))) * 1.4826 if dm.size else float("nan")
    elif len(p) >= 30:
        m10 = np.convolve(p, np.ones(10) / 10, mode="valid")
        dm = m10[10:] - m10[:-10]
        sig_m10 = float(np.median(np.abs(dm - np.median(dm)))) * 1.4826
    else:
        sig_m10 = float("nan")
    return {
        "cycles": int(len(p)), "unit": unit, "level": level,
        "sigma_cycle": sigma, "sigma_cycle_pct": (100.0 * sigma / level if level else float("nan")),
        "sigma_raw": sigma_raw, "sigma_method": method, "sigma_lags": sig_lags,
        "repeat_frac": repeat_frac, "repeat_run_cycles": run, "repeated_cycles": blocky,
        "max_abs_diff": float(np.max(np.abs(d))) if d.size else 0.0,
        "has_events_hint": bool(d.size and sigma > 0 and np.max(np.abs(d)) > 10 * sigma),
        "range5_p95": rng(5), "range10_p95": rng(10),
        "sigma_mean10": sig_m10,
        "min": float(p.min()), "max": float(p.max()),
    }


def _moving_mask(x: np.ndarray, sigma: float, *, W: int = 25, k: float = 4.0, floor: float = 0.0) -> np.ndarray:
    """"是否在动"掩码（v0.56/v0.57 共用）：W 周波滑动均值前后窗之差 |sm[i+W]−sm[i]| 超过门槛且 ≥ ±3W/4 邻域峰值一半处
    （两窗交界 i+W 附近 3 个周波）、或单周波 |Δ| > 6σ 处记为在动；再做闭运算把 < W 的缝并入。
    门槛 = max(k·σ·√(2/W), 3×dm 自身的稳健尺度(20% 分位/0.2533), floor)：第二项让纹波/非白噪声（σ 被差分 MAD 低估）不会被整段判成在动。"""
    L = int(x.size)
    moving = np.zeros(L, dtype=bool)
    if L < 2 * W + 2:
        return moving
    d1 = np.abs(np.diff(x))
    for i in np.where(d1 > 6.0 * sigma)[0]:
        moving[i:i + 2] = True
    sm = np.convolve(x, np.ones(W) / W, mode="valid")            # sm[i] = mean(x[i:i+W])
    dm = np.abs(sm[W:] - sm[:-W])                                 # 相隔 W 的两个均值窗之差，变化发生在 x[i : i+2W)
    if dm.size:
        s_dm = float(np.quantile(dm, 0.2)) / 0.2533                 # dm 自身的稳健尺度：|N(0,s)| 的 20% 分位 = 0.2533 s（用低分位，斜坡占文件一半时也只高估 ~2×）
        thr = max(k * sigma * math.sqrt(2.0 / W), 3.0 * s_dm, float(floor))
        h = (3 * W) // 4                                            # ±3W/4 邻域：硬阶跃仍只标 ±W/2；紧邻阶跃的斜坡少被压掉，且 2W 长的平台不被两侧阶跃吃掉
        pad = np.pad(dm, h, mode="edge")
        loc_max = np.lib.stride_tricks.sliding_window_view(pad, 2 * h + 1).max(axis=1)
        for i in np.where((dm > thr) & (dm >= 0.5 * loc_max))[0]:
            moving[i + W - 1: i + W + 2] = True
        i = 0
        while i < L:
            if moving[i]:
                i += 1
                continue
            j = i
            while j < L and not moving[j]:
                j += 1
            if 0 < i and j < L and j - i < W:
                moving[i:j] = True
            i = j
    return moving


def _run_adjust(sigma: float, run_cycles: float, W: int = 25) -> Tuple[int, float]:
    """v0.83：周波复制文件的滑窗 / 噪声尺度折算：W → max(W, 4×run)，σ → σ×√run（W 周波均值里只有 W/run 个独立样本，
    k·σ_eff·√(2/W) = k·σ·√(2/(W/run))）。run ≤ 1 原样返回。"""
    r = float(run_cycles or 1.0)
    if r <= 1.0:
        return int(W), float(sigma)
    return int(max(W, math.ceil(4 * r))), float(sigma) * math.sqrt(r)


SPLIT_RATIO = 10.0   # v0.80：最大/最小投切幅值比超过此值才考虑分簇
GAP_RATIO = 5.0      # v0.80：排序后相邻投切幅值比超过此值处为簇间隙


def _anchors(x: np.ndarray, moving: np.ndarray, min_steady_cycles: int) -> List[Tuple[int, int, float]]:
    """连续"不动" ≥ min_steady_cycles 的区间 → (起, 止, 均值)。"""
    out: List[Tuple[int, int, float]] = []
    L = int(x.size)
    i = 0
    while i < L:
        if moving[i]:
            i += 1
            continue
        j = i
        while j < L and not moving[j]:
            j += 1
        if j - i >= min_steady_cycles:
            out.append((i, j, float(np.mean(x[i:j]))))
        i = j
    return out


def estimate_min_load(x: np.ndarray, sigma: float, unit: str = "W", *, min_steady_cycles: int = 25,
                      jump_k: float = 8.0, merge_k: float = 6.0, run_cycles: float = 1.0) -> Dict[str, Any]:
    """v0.55：从**含投切的分路侧录波**估计"最小关心负荷"的候选值（逐周波 P 或 I 序列）。

    v0.57 改为与 ``longest_transient`` 同一套"是否在动"判据（``_moving_mask``）切稳态：原来按相邻周波 |Δ| > 8σ 切段，
    软启斜坡（每周波只变零点几 σ）和跨周波边界被劈成两半的阶跃（每半 < 8σ）都切不开，斜坡 / 两个台阶会被并进同一段、
    中位数变成无意义的中间值，候选错还标"可靠"。现在：不动 ≥ ``min_steady_cycles`` 的区间为稳态台阶（均值），
    相邻稳态之间（不论中间是硬跳变、冲击还是几十秒斜坡）的均值差为一次投切；台阶按 ``merge_k``·σ 合并去重；
    候选 = min(相邻稳态最小跳变, 台阶最小间距)。``candidate_from``：``step``＝文件里直接看到过这么大的一次投切；
    ``level_gap``＝来自两个不相邻状态之差（没直接看到这么小的投切，只是两种状态差这么多，更可能是上界候选）。
    ``reliable``：至少 2 个台阶、候选 ≥ 20σ（远离噪声底）且 ≥ 1 % 最大台阶。``jump_k`` 保留仅为兼容（不再使用）。
    总线侧多设备混合文件量出的是"所有设备里最小的一次"，不代表目标设备——调用方应只对分路侧文件使用。
    v0.83：``run_cycles`` > 1（周波复制文件，每 run_cycles 个周波同值）时，滑窗加长到 4×run、稳态门槛抬到 ≥ 2×run、
    噪声尺度按 √run 折算（均值窗内只有 W/run 个独立样本），否则每段同值周波都会被当成一个稳态台阶。
    """
    x = np.asarray(x, dtype=np.float64)
    W, sig_eff = _run_adjust(sigma, run_cycles)
    min_steady_cycles = int(max(min_steady_cycles, 2 * run_cycles)) if run_cycles > 1 else min_steady_cycles
    out: Dict[str, Any] = {"unit": unit, "candidate": None, "candidate_from": None, "min_step": None, "min_level_gap": None,
                           "levels": [], "n_steady": 0, "n_events": 0, "reliable": False, "note": ""}
    if x.size < 2 * min_steady_cycles or not (sigma > 0) or not math.isfinite(sigma):
        out["note"] = "数据太短或噪声尺度无效，无法估计"
        return out
    moving = _moving_mask(x, sig_eff, W=W)
    segs = _anchors(x, moving, min_steady_cycles)
    out["n_steady"] = len(segs)
    steps_all = [abs(segs[i + 1][2] - segs[i][2]) for i in range(len(segs) - 1)]
    steps = [v for v in steps_all if v > merge_k * sigma]
    out["n_events"] = len(steps)
    if len(segs) < 2:
        out["note"] = ("文件中未发现投切（只有 1 个稳态台阶）" if segs else "没有足够长的稳态段") + "，无法估计最小关心负荷；请改用噪声底或手填"
        return out
    levels: List[float] = []
    for lv in sorted(sg[2] for sg in segs):
        if levels and abs(lv - levels[-1]) < merge_k * sigma:
            continue
        levels.append(lv)
    gaps = [levels[i + 1] - levels[i] for i in range(len(levels) - 1)]
    out["levels"] = [float(_ceil_sig(v, 4)) if v > 0 else float(v) for v in levels]
    if not steps or not gaps:
        out["note"] = "文件中未发现投切（稳态台阶之间没有显著差异）" + "，无法估计最小关心负荷；请改用噪声底或手填"
        return out
    out["min_step"] = float(min(steps)); out["min_level_gap"] = float(min(gaps))
    cand = min(out["min_step"], out["min_level_gap"])
    out["candidate"] = float(cand)
    out["candidate_from"] = "step" if out["min_step"] <= out["min_level_gap"] else "level_gap"
    top = max(abs(v) for v in levels) or 1.0
    reliable = cand >= 20.0 * sigma and cand >= 0.01 * top
    # v0.80：投切幅值分簇——文件里既有主负荷启停（如 19 A）又有二级小波动（如 0.6 A）时，最小投切是二级波动，
    # 按它定 min_delta 会把所有二级波动当事件报出（第 103 轮现场数据）。把投切幅值按对数间隙切成两簇：
    # 最大/最小 > SPLIT_RATIO 且相邻（排序后）幅值比 > GAP_RATIO 处分簇，上簇最小值＝主负荷候选 primary_step。
    # 分簇成立时 reliable=False（强制人工决定），candidate 仍＝最小投切（兼容），另给 primary_step 供"按主负荷"选择。
    out["max_step"] = float(max(steps))
    out["step_ratio"] = float(out["max_step"] / cand) if cand > 0 else None
    out["primary_step"] = None; out["secondary_step"] = None; out["split"] = False
    sorted_steps = sorted(steps)
    if out["step_ratio"] is not None and out["step_ratio"] > SPLIT_RATIO and len(sorted_steps) >= 2:
        ratios = [sorted_steps[i + 1] / sorted_steps[i] if sorted_steps[i] > 0 else float("inf") for i in range(len(sorted_steps) - 1)]
        gi = int(np.argmax(ratios))
        if ratios[gi] > GAP_RATIO:
            out["split"] = True
            out["primary_step"] = float(sorted_steps[gi + 1]); out["secondary_step"] = float(sorted_steps[0])
            out["n_primary"] = int(len(sorted_steps) - gi - 1); out["n_secondary"] = int(gi + 1)
            reliable = False
    out["reliable"] = bool(reliable)
    n_tr = int(np.sum(np.diff(moving.astype(np.int8)) == 1) + (1 if moving[0] else 0))
    out["n_transients"] = n_tr
    out["note"] = (f"由 {len(segs)} 个稳态段（不动 ≥{min_steady_cycles} 周波）/ {len(levels)} 个台阶估计：最小跳变 {out['min_step']:.4g} {unit}，"
                   f"最大跳变 {out['max_step']:.4g} {unit}，最小台阶间距 {out['min_level_gap']:.4g} {unit} → 候选 {cand:.4g} {unit}"
                   + ("" if out["candidate_from"] == "step" else "（来自两个不相邻状态之差，文件里没直接看到这么小的一次投切）")
                   + (f"（⚠ 投切幅值分两簇：主负荷 ≈{out['primary_step']:.4g} {unit}（{out['n_primary']} 次）+ 二级波动 ≈{out['secondary_step']:.4g} {unit}"
                      f"（{out['n_secondary']} 次），相差 {out['step_ratio']:.0f} 倍；按最小投切定门槛会把二级波动全部报成事件，"
                      f"请人工决定：只关心主负荷填 {out['primary_step']:.4g}，也要二级波动填 {cand:.4g}，或另行手填）" if out["split"]
                      else ("" if reliable else f"（⚠ 候选过小：< 20σ={20 * sigma:.3g} 或 < 1% 最大台阶，可能是漂移/碎段，建议手填）"))
                   + "。仅对分路侧单设备录波有效；若现场不关心二级负荷，请手工改大")
    return out


def detect_repetition(x: np.ndarray, cycles_per_s: float, *, periods_s: Tuple[float, ...] = (1, 2, 5, 10, 15, 20, 30, 60, 120, 300),
                      rtol: float = 1e-9, min_pct: float = 80.0) -> Dict[str, Any]:
    """v0.80：检测逐周波序列是否为**模板拼接文件**（同一段录波按固定周期逐位复制）。

    真实录波的噪声不会逐位重复；若 ``x[i+k] == x[i]``（相对误差 ≤ ``rtol``）的比例 ≥ ``min_pct`` %，判定为按 ``k`` 周波
    （= period_s × cycles_per_s）周期重复。拼接文件会把同一次投切复制成多次，调参 / 误报统计都会被放大，故只做告警不改参数。
    返回 ``{"suspected", "period_s", "match_pct", "checked"}``；序列不足 2 个周期的周期不检查。
    """
    x = np.asarray(x, dtype=np.float64)
    out: Dict[str, Any] = {"suspected": False, "period_s": None, "match_pct": 0.0, "checked": []}
    best = (0.0, None)
    for ps in periods_s:
        k = int(round(float(ps) * float(cycles_per_s)))
        if k <= 0 or x.size < 2 * k:
            continue
        a, b = x[k:], x[:-k]
        pct = float(100.0 * np.mean(np.isclose(a, b, rtol=rtol, atol=0.0)))
        out["checked"].append({"period_s": float(ps), "match_pct": round(pct, 2)})
        if pct > best[0]:
            best = (pct, float(ps))
    out["match_pct"] = round(best[0], 2); out["period_s"] = best[1]
    out["suspected"] = bool(best[1] is not None and best[0] >= min_pct)
    return out


def _longest_tol_run(seg: np.ndarray, tol: float) -> int:
    """序列中"极差 ≤ tol"的最长连续子段长度（Hart 稳态分段会切出的最长一段）。"""
    seg = np.asarray(seg, dtype=np.float64)
    best = 0
    a = 0
    lo = hi = seg[0] if seg.size else 0.0
    for i in range(1, int(seg.size) + 1):
        if i < seg.size:
            lo2, hi2 = min(lo, seg[i]), max(hi, seg[i])
            if hi2 - lo2 <= tol:
                lo, hi = lo2, hi2
                continue
        best = max(best, i - a)
        if i < seg.size:
            a, lo, hi = i, seg[i], seg[i]
    return int(best)


def longest_transient(x: np.ndarray, sigma: float, min_delta: float, *, min_steady_cycles: int = 10,
                      smooth_cycles: int = 25, k: float = 4.0, tol: Optional[float] = None,
                      run_cycles: float = 1.0, hart_min_steady: Optional[int] = None) -> Dict[str, Any]:
    """v0.56：量文件中**最长的一次暂态**（两个真正稳态之间的周波数），用来给 ``steady_state.max_transient_cycles`` 定尺度。

    Hart 分段看不出软启斜坡（斜坡被切成一串"极差刚好不超 tol"的伪稳态段，相邻段差又 < min_delta）。这里改用
    "是否在动"判据：``smooth_cycles``（默认 25）周波滑动均值 ``sm``，前后两个均值窗之差 |sm[i+W]−sm[i]| > k·σ·√(2/W)
    （k=4：σ=0.019 A 时约 0.02 A/25 周波，能看见 1.5 mA/周波 的慢斜坡；下限 5%·min_delta）或单周波 |Δ| > 6σ 的位置记为"在动"，并按窗长
    外扩；连续"不动" ≥ ``min_steady_cycles`` 的区间为锚点稳态。相邻锚点均值差 ≥ ``min_delta`` 的，两锚点之间的周波数
    就是一次暂态（含窗长带来的 ≈W 周波抹边，偏保守）。返回 ``longest``（无暂态为 0）、``n_transients``、``n_steady``、
    ``transients``（最长 5 条：start/end/cycles/delta）。给了 ``tol``（steady_state 的稳态容差）时，另算暂态区间内
    Hart 分段会切出的**最长伪稳态段** ``max_pseudo_steady``：斜坡上"极差刚好不超 tol"的平台——``min_steady_cycles``
    必须大于它，稳态分段才不会把斜坡当成一串小台阶而配不出事件。
    """
    x = np.asarray(x, dtype=np.float64)
    # v0.83：周波复制文件（run_cycles>1）——滑窗 ≥ 4×run、稳态 ≥ 2×run、σ×√run，否则斜坡上每段同值周波都成"稳态锚点"，暂态被切碎
    smooth_cycles, sigma = _run_adjust(sigma, run_cycles, int(smooth_cycles))
    if run_cycles > 1:
        min_steady_cycles = int(max(min_steady_cycles, 2 * run_cycles))
    out: Dict[str, Any] = {"longest": 0, "n_transients": 0, "n_steady": 0, "transients": [], "smooth_cycles": int(smooth_cycles),
                           "run_cycles": float(run_cycles), "min_steady_cycles_used": int(min_steady_cycles)}
    L = int(x.size)
    W = max(2, int(smooth_cycles))
    if L < 2 * W + 2 * min_steady_cycles or not (sigma > 0) or not math.isfinite(sigma):
        return out
    moving = _moving_mask(x, sigma, W=W, k=k, floor=0.05 * float(min_delta))
    anchors = _anchors(x, moving, min_steady_cycles)
    # v0.83.2：锚点必须是 steady_state（Hart 分段）也认的稳态——段内要有一段 ≥ hart_min_steady 周波、极差 ≤ tol 的子段；
    # 否则软启斜坡中途的回落平台（如 0.31→0.39 来回跳的 6 s）会被"不动"判据当成稳态，把一次 46 s 的暂态切成两半，
    # max_transient_cycles / window_cycles 都按半截给，steady_state 在真实斜坡上配不出事件
    if tol is not None and tol > 0 and hart_min_steady and hart_min_steady > 0:
        anchors = [a for a in anchors if _longest_tol_run(x[a[0]:a[1]], float(tol)) >= int(hart_min_steady)]
        out["hart_min_steady"] = int(hart_min_steady)
    out["n_steady"] = len(anchors)
    trs: List[Dict[str, Any]] = []
    for (a0, b0, l0), (a1, b1, l1) in zip(anchors, anchors[1:]):
        if abs(l1 - l0) >= min_delta:
            trs.append({"start": int(b0), "end": int(a1), "cycles": int(a1 - b0), "delta": float(l1 - l0)})
    trs.sort(key=lambda d: -d["cycles"])
    out["n_transients"] = len(trs)
    out["transients"] = trs[:5]
    out["longest"] = int(trs[0]["cycles"]) if trs else 0
    if tol is not None and tol > 0 and trs:
        longest_pseudo = 0
        for tr in trs:
            seg = x[tr["start"]:tr["end"]]
            a = 0
            lo = hi = seg[0] if seg.size else 0.0
            for i in range(1, int(seg.size) + 1):
                if i < seg.size:
                    lo2, hi2 = min(lo, seg[i]), max(hi, seg[i])
                    if hi2 - lo2 <= tol:
                        lo, hi = lo2, hi2
                        continue
                longest_pseudo = max(longest_pseudo, i - a)
                if i < seg.size:
                    a, lo, hi = i, seg[i], seg[i]
        out["max_pseudo_steady"] = int(longest_pseudo)
    return out


def suggest(m: dict, min_load: float | None, x: Optional[np.ndarray] = None) -> dict:
    """由噪声统计给出参数建议（规则见 NILM_TUNING_GUIDE.md §2）。单位随 ``m["unit"]``：W → ``*_w``，A → ``*_a``。

    v0.56：给了逐周波序列 ``x`` 时，量最长暂态（``longest_transient``）；超过 100 周波（2 s）即判为慢启动 / 软启斜坡，
    ``steady_state.max_transient_cycles`` 自动放大到 ≥ 1.5× 最长暂态（向上取 2 位有效数字），并在需要时给出 ``window_cycles``
    （检测窗必须装得下 暂态 + 前后各一个稳态段，否则稳态配对在窗内永远配不成）。结果附在 ``transient`` 字段。
    """
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
    max_tr, min_steady = 100, 10
    tr: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = {}
    if x is not None:
        run = float(m.get("repeat_run_cycles") or 1.0) if m.get("repeated_cycles") else 1.0
        tr = longest_transient(x, s, min_d, tol=tol10, run_cycles=run)
        # v0.83.2：min_steady 由斜坡上最长伪平台推出后，再用它复核锚点（锚点里要有 ≥ min_steady 的 Hart 稳态子段），
        # 不满足的锚点剔除、暂态合并，迭代到稳定（最多 3 轮）
        for _ in range(3):
            pseudo0 = int(tr.get("max_pseudo_steady") or 0)
            ms0 = int(max(10, min(_ceil_sig(1.5 * pseudo0 + 1), 250))) if tr["longest"] > 100 else 10
            tr2 = longest_transient(x, s, min_d, tol=tol10, run_cycles=run, hart_min_steady=ms0)
            if tr2["longest"] == tr["longest"] and tr2["n_steady"] == tr["n_steady"]:
                break
            tr = tr2
        if tr["longest"] > 100:
            max_tr = int(_ceil_sig(1.5 * tr["longest"]))
            # 斜坡上会被 Hart 切出的伪稳态平台：min_steady_cycles 要压过它（×1.5 余量），否则斜坡被当成一串 < min_delta 的小台阶
            pseudo = int(tr.get("max_pseudo_steady") or 0)
            min_steady = int(max(10, min(_ceil_sig(1.5 * pseudo + 1), 250)))
            need_win = int(_ceil_sig(max_tr + 2 * min_steady + 20))     # 暂态 + 前后各一个稳态段 + 余量
            tr["max_transient_cycles"] = max_tr; tr["min_steady_cycles"] = min_steady
            note += (f"；文件中最长暂态 {tr['longest']} 周波（{tr['longest'] / 50:.1f} s @50Hz，慢启动/软启斜坡），"
                     f"steady_state.max_transient_cycles 放大到 {max_tr}")
            if min_steady > 10:
                note += f"、min_steady_cycles 抬到 {min_steady}（斜坡上最长伪稳态平台 {pseudo} 周波，稳态必须比它长）"
            if 1.5 * pseudo + 1 > 250:
                note += "（⚠ 伪平台过长，已封顶 250：斜坡太缓，稳态分段可能仍只报其中的硬跳变）"
            if need_win > 300:
                extra["window_cycles"] = need_win
                tr["window_cycles"] = need_win
                note += f"，nilm.window_cycles 需 ≥ {need_win}（检测窗要装得下暂态+前后稳态）"
            note += "；threshold/median_diff/two_window/glr 看不到这种斜坡，只会报其中的硬跳变"
        else:
            tr["max_transient_cycles"] = max_tr
    return {
        "note": note, "unit": unit, "quantity": "p" if unit == "W" else "i",
        **extra, "transient": tr,
        "rel_tol_pct": round(min(5.0, max(0.05, 100.0 * tol / lvl)), 2) if lvl else 1.0,
        "min_delta_pct": round(mdp, 2),
        "algorithms": {
            "threshold":    {f"min_delta{sx}": min_d, "settle_cycles": 5, f"settle_tol{sx}": tol, "max_rise_cycles": 40},
            "median_diff":  {"median_cycles": 5, f"min_delta{sx}": min_d, "settle_cycles": 5, f"settle_tol{sx}": tol, "max_rise_cycles": 40},
            "two_window":   {"pre_cycles": 10, "post_cycles": 10, f"min_delta{sx}": min_d, "k_sigma": 3.0},
            "cusum":        {f"drift{sx}": k, f"threshold{sx}": h, f"min_delta{sx}": min_d, "settle_cycles": 5},
            "glr":          {"window_cycles": 15, "threshold": 25.0, f"min_delta{sx}": min_d, f"noise{sx}": noise, "settle_cycles": 5},
            "steady_state": {f"tol{sx}": tol10, "min_steady_cycles": min_steady, f"min_delta{sx}": min_d, "max_transient_cycles": max_tr},
        },
    }


def run_tune(base: AppConfig, file: str, *, channel: Optional[str] = None, quantity: Optional[str] = None,
             min_load_w: Optional[float] = None, min_load_a: Optional[float] = None, max_cycles: int = 30000,
             t_start: str = "", t_end: str = "", duration_s: Optional[float] = None,
             min_load_auto: bool = False, custom_time: bool = False, custom_time_start: str = "",
             custom_time_end: str = "") -> Dict[str, Any]:
    """量一段背景数据的逐周波噪声并给出参数建议（``tools/nilm_tune.py`` 与 ``POST /api/process/nilm_tune`` 共用）。

    - ``min_load_auto``（v0.55）：未手填最小关心负荷时，从文件中的投切台阶估计（``estimate_min_load``），估计可靠才采用；
      结果里总是带 ``min_load_estimate`` 供复核；

    - ``base``：提供 PT/CT、fs、f_nom、列映射与缺省 ``nilm.quantity`` 的配置（不被修改）；
    - ``custom_time``（v0.73）：与波形预览同一套自定义时间：时间轴＝自定义起始时间（空＝文件第 1 条数据时间）+ 行号 / fs，
      文件时长＝数据点数 / 采样率；``t_start / t_end`` 在这条时间轴上解释（写法同波形预览：完整日期时间 / epoch 秒 / HH:MM:SS），
      都空＝整个文件；``custom_time_end`` 为缺省终点。结果 ``t_range`` 附 ``custom_time / file_duration_s / file_rows / file_t_start / file_t_end``；
    - ``t_start`` / ``t_end``：分析时间段，文本格式同播放时间段（``2026-10-13 08:00:02.5`` / ``08:00:02.5`` / epoch 秒），
      都为空＝整个文件；``duration_s``：从起点（或文件开头）起的时长（秒），与 ``t_end`` 同时给时取先到者；
    - 返回与 CLI ``--json`` 相同结构的 dict，另含 ``t_range``；输入不满足抛 ``TuneError``。
    """
    from .nilm import CycleFeatures
    from .scaling import scale_block
    from .sources import create_source
    ts_txt, te_txt = str(t_start or "").strip(), str(t_end or "").strip()
    if duration_s is not None:
        duration_s = float(duration_s)
        if not (duration_s > 0):
            raise TuneError(f"时长必须 > 0 秒（当前 {duration_s}）")
    file_meta: Dict[str, Any] = {"custom_time": bool(custom_time)}
    if custom_time:
        # v0.73：自定义时间——复用波形预览的基准构造与时间轴定位（_prep_cfg），保证两处写法 / 语义完全一致
        from .wave_preview import WaveError, _prep_cfg, file_info, make_base
        try:
            # make_base 以 base 为模板复制（nilm / transform / sampling 等全部沿用），只置入自定义时间三项并校验写法
            b2 = make_base(base, custom_time="1", custom_time_start=str(custom_time_start or ""), custom_time_end=str(custom_time_end or ""))
            info = file_info(b2, file)
            cfg = _prep_cfg(b2, file, ts_txt, te_txt, info)
        except WaveError as exc:
            raise TuneError(str(exc)) from None
        file_meta.update({"file_duration_s": float(info["duration_s"]), "file_rows": int(info["rows"]),
                          "file_t_start": float(info["t_start"]), "file_t_end": float(info["t_end"]), "fs_used": float(cfg.sampling.fs),
                          "custom_time_start": str(custom_time_start or "").strip() or None,
                          "custom_time_end": str(custom_time_end or "").strip() or None})
    else:
        cfg = AppConfig.from_dict(base.to_dict())
        cfg.source.kind = "csv_file"; cfg.source.path = file
        cfg.source.file_speed = 0.0; cfg.source.play_window = False; cfg.source.play_end_time = ""
        cfg.source.play_start_mode = "begin"; cfg.source.play_start_value = ""
        if ts_txt:
            parse_play_start("time", ts_txt)                       # 非法时间文本在这里就报 ConfigError
            cfg.source.play_start_mode = "time"; cfg.source.play_start_value = ts_txt
        if te_txt:
            parse_play_start("time", te_txt)
            cfg.source.play_end_time = te_txt
        if ts_txt and te_txt:
            a, b = parse_play_start("time", ts_txt), parse_play_start("time", te_txt)
            if a[0] == b[0] and b[1] <= a[1]:
                raise TuneError(f"结束时间必须晚于开始时间（{ts_txt} → {te_txt}）")
        cfg.validate()
    feat = CycleFeatures(cfg.sampling.fs, cfg.sampling.f_nom, harmonics=False)   # 调参只用 P/I 序列，不算谐波电流（v0.99.26）
    ps, is_, ts = [], [], []
    u_nonzero = False
    t_first: Optional[float] = None
    n_cyc = 0
    max_cycles = max(1, int(max_cycles))
    from .sources.parsing import ParseError
    try:
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
                    if t_first is None:
                        t_first = float(f["t"][0])
                    if duration_s is not None:
                        keep = f["t"] <= t_first + duration_s
                        if not keep.all():
                            ps.append(f["p"][:, keep]); is_.append(f["i"][:, keep]); ts.append(f["t"][keep])
                            n_cyc += int(keep.sum())
                            break
                    ps.append(f["p"]); is_.append(f["i"]); ts.append(f["t"])
                    n_cyc += int(f["t"].size)
                if n_cyc >= max_cycles:
                    break
    except ParseError as exc:
        raise TuneError(str(exc)) from exc
    if not ps or not sum(x.shape[1] for x in ps):
        raise TuneError("没有读到整周波数据" + ("（指定时间段内无数据，请对照文件时间范围）" if (ts_txt or te_txt) else ""))
    q_req = quantity or str(getattr(cfg.nilm, "quantity", "auto") or "auto")
    qty = q_req if q_req != "auto" else ("i" if not u_nonzero else "p")
    if qty == "p" and not u_nonzero:
        raise TuneError("数据源没有电压（电压列未映射或全为 0）：有功恒为 0，无法按 P 调参；请用 quantity=i（或 auto）")
    unit = "W" if qty == "p" else "A"
    ch = channel or ("total" if qty == "p" else "A")
    if ch not in NILM_CHANNELS:
        raise TuneError(f"检测对象必须是 {list(NILM_CHANNELS)}（当前 {ch!r}）")
    if qty == "i" and ch == "total":
        raise TuneError("仅电流（I 口径）检测不存在跨相合并（三相电流有效值不能像有功那样相加），只能单相：对象请填 A / B / C")
    ci = NILM_CHANNELS.index(ch)
    p = np.concatenate(ps if qty == "p" else is_, axis=1)[ci][:max_cycles]
    t = np.concatenate(ts)[:max_cycles]
    m = measure(p, unit)
    min_load = min_load_w if qty == "p" else min_load_a
    notes: List[str] = []
    est = estimate_min_load(p, m["sigma_cycle"], unit, run_cycles=(float(m["repeat_run_cycles"]) if m.get("repeated_cycles") else 1.0))
    min_load_source = "manual" if min_load is not None else "none"
    if min_load_auto and min_load is None:
        if est["reliable"]:
            min_load = est["candidate"]; min_load_source = "estimated"
            notes.append(f"最小关心负荷取自文件估计：{min_load:.4g} {unit}（{est['note']}）")
        else:
            notes.append("已勾选从文件估计最小关心负荷，但估计不可靠：" + est["note"] + "；本次按未指定处理（max(6σ, 2%×基荷)）")
    elif min_load_auto and min_load is not None:
        notes.append(f"已手填最小关心负荷 {min_load:g} {unit}，文件估计（{est['candidate']}）仅供参考")
    sg = suggest(m, min_load, p)
    if m.get("repeated_cycles"):
        notes.append(f"⚠ 文件疑似分段恒定 / 周波复制：约每 {m['repeat_run_cycles']:.0f} 周波一段，段内周波几乎相同（相邻周波逐位相等 {100.0 * m['repeat_frac']:.1f}%，"
                     f"相邻差分 σ={m['sigma_raw']:.3g} {unit}），段间跳变 σ={m['sigma_cycle']:.3g} {unit}（滞后 {m['repeat_run_cycles']:.0f} 周波差分）。"
                     f"相邻差分口径的 σ 失真 {m['sigma_cycle'] / m['sigma_raw']:.0f} 倍" if m['sigma_raw'] > 0 else
                     f"⚠ 文件疑似分段恒定 / 周波复制：约每 {m['repeat_run_cycles']:.0f} 周波一段，段内周波逐位相同，段间跳变 σ={m['sigma_cycle']:.3g} {unit}")
        notes[-1] += "；本次 σ / 极差 / 均值差 / 暂态 / 最小负荷估计均按段间跳变尺度重量。该文件的「噪声」实为段间跳变，建议用连续真实录波复核"
    rep = detect_repetition(p, float(cfg.sampling.f_nom))
    if rep["suspected"]:
        notes.append(f"⚠ 文件疑似模板拼接：逐周波 {unit} 序列每 {rep['period_s']:g} s 逐位重复（{rep['match_pct']:.1f}% 周波与前一周期完全相等）；"
                     "同一次投切被复制成多次，噪声统计与事件计数不代表真实现场，建议用连续真实录波调参")
    if qty == "i" and min_load_w is not None and min_load_a is None:
        notes.append("I 口径请用 min_load_a（A）；min_load_w 已忽略")
    # v0.87：对照——若启用 nilm.auto_params，运行时对这段序列（整段当作一个窗）会推导出的参数
    try:
        from .nilm_auto import auto_params as _auto
        auto = _auto(p, float(cfg.sampling.f_nom), cfg.nilm.algorithms)
    except Exception as exc:                                  # pragma: no cover
        auto = None; notes.append(f"自适应参数推导失败：{exc}")
    if auto is None:
        notes.append("自适应参数对照：序列太短（不足 60 个有效周波）无法推导")
    return {"file": file, "channel": ch, "auto_params": auto, "fs": cfg.sampling.fs, "f_nom": cfg.sampling.f_nom,
            "quantity": qty, "quantity_requested": q_req, "unit": unit, "voltage_present": u_nonzero,
            "scaled": bool(cfg.transform.enabled), "t_span_s": float(t[-1] - t[0]) if len(t) > 1 else 0.0,
            "t_range": {"start": ts_txt, "end": te_txt, "duration_s": duration_s,
                        "t_first": float(t[0]), "t_last": float(t[-1]), "whole_file": not (ts_txt or te_txt or duration_s), **file_meta},
            "min_load_used": (None if min_load is None else float(min_load)), "min_load_source": min_load_source,
            "min_load_estimate": est, "repetition": rep,
            "notes": notes, "measure": m, "suggest": sg}


def build_cli_command(file: str, *, config: Optional[str] = None, channel: Optional[str] = None,
                      quantity: Optional[str] = None, min_load_w: Optional[float] = None, min_load_a: Optional[float] = None,
                      max_cycles: Optional[int] = None, t_start: str = "", t_end: str = "", duration_s: Optional[float] = None,
                      json_out: bool = True, apply: bool = False, out: Optional[str] = None,
                      python: str = "python", min_load_auto: bool = False, custom_time: bool = False,
                      custom_time_start: str = "", custom_time_end: str = "") -> str:
    """生成与一次调参等价的 ``tools/nilm_tune.py`` 命令行（v0.54，界面结果 JSON 的 ``command`` 字段）。

    只写实际给出的参数；路径/时间含空格时加引号（POSIX 写法，Windows PowerShell 把 ``python`` 换成
    ``.\\.venv\\Scripts\\python.exe``、``/`` 换成 ``\\`` 即可）。
    """
    import shlex

    def q(v: Any) -> str:
        return shlex.quote(str(v))

    def num(v: float) -> str:
        f = float(v)
        return str(int(f)) if f.is_integer() else f"{f:g}"

    parts = [python, "tools/nilm_tune.py", "--file", q(file)]
    if config:
        parts += ["--config", q(config)]
    if channel:
        parts += ["--channel", str(channel)]
    if quantity:
        parts += ["--quantity", str(quantity)]
    if min_load_w is not None:
        parts += ["--min-load-w", num(min_load_w)]
    if min_load_a is not None:
        parts += ["--min-load-a", num(min_load_a)]
    if min_load_auto:
        parts.append("--min-load-auto")
    if str(t_start or "").strip():
        parts += ["--t-start", q(str(t_start).strip())]
    if str(t_end or "").strip():
        parts += ["--t-end", q(str(t_end).strip())]
    if duration_s is not None:
        parts += ["--duration", num(duration_s)]
    if custom_time:
        parts.append("--custom-time")
        if str(custom_time_start or "").strip():
            parts += ["--custom-time-start", q(str(custom_time_start).strip())]
        if str(custom_time_end or "").strip():
            parts += ["--custom-time-end", q(str(custom_time_end).strip())]
    if max_cycles is not None and int(max_cycles) != 30000:
        parts += ["--max-cycles", str(int(max_cycles))]
    if json_out:
        parts.append("--json")
    if apply:
        parts.append("--apply")
        if out:
            parts += ["--out", q(out)]
    return " ".join(parts)


def tune_result_path(cfg: AppConfig, name: str = "", out_dir: Optional[str] = None) -> str:
    """调参结果 JSON 的保存路径：``<nilm_dir>/<name>``，name 空＝``tune_<YYYYmmdd_HHMMSS>.json``；
    name 里的 ``{时间}`` / ``{time}`` 占位符替换为时间戳；只取文件名部分（不允许目录穿越）。"""
    d = out_dir or cfg.nilm.nilm_dir or cfg.output.export_dir or "output"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    n = os.path.basename(str(name or "").strip()) or f"tune_{stamp}.json"
    n = n.replace("{时间}", stamp).replace("{time}", stamp)
    if not n.lower().endswith(".json"):
        n += ".json"
    return os.path.join(d, n)


def _fmt(v: Any) -> str:
    return f"{v:g}" if isinstance(v, float) else f"{v}"


def apply_nilm_params(cfg: AppConfig, params: Dict[str, Any]) -> List[str]:
    """把 nilm_tune --json 的输出（整份 / 其 ``suggest`` 片段 / 直接的 nilm 片段）叠加到 ``cfg.nilm``。

    返回逐项说明行（供 CLI 打印 / API 返回）。不校验、不落盘——调用方决定。
    """
    sg = params.get("suggest", params) if isinstance(params, dict) else {}
    if isinstance(sg, dict) and "nilm" in sg and isinstance(sg["nilm"], dict):   # 允许直接给 {"nilm": {...}}
        sg = sg["nilm"]
    notes: List[str] = []
    q = sg.get("quantity") or (params.get("quantity") if isinstance(params, dict) else None)
    if q in ("auto", "p", "i"):
        cfg.nilm.quantity = q; notes.append(f"nilm.quantity = {q}")
    if "rel_tol_pct" in sg:
        cfg.nilm.rel_tol_pct = float(sg["rel_tol_pct"]); notes.append(f"nilm.rel_tol_pct = {cfg.nilm.rel_tol_pct}")
    if "min_delta_pct" in sg:
        cfg.nilm.min_delta_pct = float(sg["min_delta_pct"]); notes.append(f"nilm.min_delta_pct = {cfg.nilm.min_delta_pct}")
    if sg.get("window_cycles") is not None and int(sg["window_cycles"]) > int(cfg.nilm.window_cycles):   # v0.56：只放大不缩小
        cfg.nilm.window_cycles = int(sg["window_cycles"]); notes.append(f"nilm.window_cycles = {cfg.nilm.window_cycles}")
    for algo, prm in (sg.get("algorithms") or {}).items():
        if algo not in NILM_ALGO_DEFAULTS or not isinstance(prm, dict):
            continue
        upd = {k: v for k, v in prm.items() if k in NILM_ALGO_DEFAULTS[algo]}
        if not upd:
            continue
        cur = dict(cfg.nilm.algorithms.get(algo) or {})
        cur.update(upd)
        cfg.nilm.algorithms[algo] = cur
        notes.append(f"{algo}: " + "  ".join(f"{k}={_fmt(v)}" for k, v in upd.items()))   # 只列实际套用的键
    return notes


def tuned_config_path(cfg: AppConfig, out_dir: Optional[str] = None, tag: str = "") -> str:
    """默认输出路径：``<nilm_dir>/nilm_tuned_config[_<tag>]_<YYYYmmdd_HHMMSS>.json``。"""
    d = out_dir or cfg.nilm.nilm_dir or cfg.output.export_dir or "output"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    name = "nilm_tuned_config" + (f"_{tag}" if tag else "") + f"_{stamp}.json"
    return os.path.join(d, name)


def export_tuned_config(base: AppConfig, params: Dict[str, Any], *, out_path: Optional[str] = None,
                        out_dir: Optional[str] = None, tag: str = "",
                        meta: Optional[Dict[str, Any]] = None, source_path: Optional[str] = None) -> Tuple[AppConfig, str, List[str]]:
    """在 ``base`` 的副本上叠加建议参数，校验后写到输出目录，返回 (新配置, 文件路径, 说明行)。

    ``base`` 本身不被修改；写出的 JSON 是**完整配置**（可直接作为 ``--config`` / ELEC_TOOL_CONFIG_PATH 使用），
    附带 ``_tuning`` 元信息（来源文件、对象、时间、改动项）便于追溯；``AppConfig.from_dict`` 会忽略未知键。

    v0.74：除算法参数外，本次调参的其它配置项也一并写入（此前遗漏）：
    * ``nilm.channels`` ＝ 本次检测对象（``params["channel"]``）；
    * 自定义时间（``params["t_range"]["custom_time"]``）→ ``source.custom_time / custom_time_start / play_end_time``；
    * ``source_path`` 给定时 ``source.kind=csv_file, source.path=source_path``（界面独立基准配置没有真实文件路径时用）。
    """
    cfg = AppConfig.from_dict(base.to_dict())
    notes = apply_nilm_params(cfg, params)
    if isinstance(params, dict):
        ch = params.get("channel")
        if ch in NILM_CHANNELS and list(cfg.nilm.channels) != [ch]:
            cfg.nilm.channels = [ch]; notes.append(f"nilm.channels = ['{ch}']")
        tr = params.get("t_range") if isinstance(params.get("t_range"), dict) else {}
        if tr.get("custom_time"):
            cs = str(tr.get("custom_time_start") or ""); ce = str(tr.get("custom_time_end") or "")
            cfg.source.custom_time = True; cfg.source.custom_time_start = cs; cfg.source.play_end_time = ce
            notes.append(f"source.custom_time = true  custom_time_start = {cs or '(文件起始)'}  play_end_time = {ce or '(按采样率计算)'}")
    if source_path:
        cfg.source.kind = "csv_file"; cfg.source.path = str(source_path); notes.append(f"source.path = {source_path}")
    cfg.validate()
    path = out_path or tuned_config_path(cfg, out_dir, tag)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    data = cfg.to_dict()
    info: Dict[str, Any] = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "changes": notes}
    if isinstance(params, dict):
        for k in ("file", "channel", "quantity", "quantity_requested", "unit", "t_span_s", "min_load_used", "min_load_source",
                  "min_load_estimate", "notes", "t_range"):
            if k in params:
                info[k] = params[k]
    if meta:
        info.update(meta)
    data["_tuning"] = info
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return cfg, path, notes
