"""负荷辨识 · 自适应算法参数（v0.87，只有总线数据、无分路标签的场景）。

启用 ``nilm.auto_params`` 后，检测器每次评估都用**当前周波窗的数据本身**推导各算法的全部数值参数，
人工不再需要用调参工具计算后手填。所有量都只依赖窗内序列（逐周波 P 或 I），没有任何需要人给的门槛：

公共统计量（``window_stats``）
    hold         采样保持长度（周波）：多尺度噪声 σ_lag（|p[t+lag]−p[t]| 的 MAD）在某个 lag 跳升 ≥20 倍并随后平台化，
                 说明原始数据是按 hold 个周波重复的（秒值×50 这类「逐位重复」数据，第 108 轮用户文件即如此）；
                 此时所有统计在按 hold 块均值抽稀后的序列上计算，周波数类参数再乘回 hold。白噪声 hold=1。
    sigma        噪声尺度：一阶差分的 MAD×1.4826/√2（差分消掉稳态电平与缓变，事件只占极少数不影响中位数）；
                 与「去掉最大 5 % |差分| 后的截尾标准差/√2」取较大者，兜底量化/逐位重复数据（MAD 可能为 0）。
    tau          噪声相关时间（周波）：差分序列自相关首次降到 1/e 的滞后，≥1。
    settle       稳定判定周波数 = clamp(3·tau + 2, 3, 20)。
    min_steady   最短可靠稳态（周波）：Allan 方差曲线拐点——块均值方差随块长 m 不再按 1/m 下降（相邻倍长比值 > 0.85）
                 的最小 m（噪声从白噪声转为漂移/闪变的平均时间）；无拐点（纯白噪声）取 2·settle；clamp(5, L/6)。
    transient    典型暂态时长（周波）：|差分| > 4·σ·√2（差分的 4σ）的超限游程（允许 ≤ settle 的间断）的最长长度
                 （最长暂态必须装得下，否则起动过程被切成多段）；下限 4·settle；上限 L/3。
    k            统一显著性倍数 = √(2·ln ARL0)，ARL0 = 一天内的周波数（f_nom×86400）——即「平均一天 ≤ 1 次虚警」；
                 这是业务层虚警容忍度，不是算法参数。
    min_delta    最小关心幅值 = max(k·σ·√(2/min_steady)·1.5, 4σ)：两段 min_steady 周波均值差的可检测下限。
    tol(n)       n 个周波的噪声极差容差 = σ·(2·√(2·ln n) + 1)（高斯极差期望 + 1σ 余量）。

各算法参数由上面的量映射（见 ``auto_algo_params``）；算法的 ``enabled`` 仍由配置决定（启停是人的选择）。
返回的参数直接写在算法函数读取的 ``*_w`` 键上（I 口径也一样，单位随检测量），相对门槛 rel_tol_pct / min_delta_pct
在自适应模式下不再叠加。
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from .config import NILM_ALGO_DEFAULTS

__all__ = ["window_stats", "auto_algo_params", "auto_params", "AUTO_MIN_CYCLES"]

AUTO_MIN_CYCLES = 60          # 窗内至少这么多（有效）周波才做自适应推导（否则本轮不评估，等数据）；采样保持数据需 ×hold


def _mad_sigma(d: np.ndarray) -> float:
    if d.size == 0:
        return 0.0
    med = float(np.median(d))
    return 1.4826 * float(np.median(np.abs(d - med))) / math.sqrt(2.0)


def _trimmed_sigma(d: np.ndarray) -> float:
    if d.size < 4:
        return float(np.std(d)) / math.sqrt(2.0) if d.size else 0.0
    a = np.abs(d)
    cut = np.quantile(a, 0.95)
    keep = d[a <= cut]
    return float(np.std(keep)) / math.sqrt(2.0) if keep.size >= 2 else 0.0


def _corr_time(d: np.ndarray, sigma: float, max_lag: int = 20) -> int:
    """差分序列自相关首次降到 1/e 的滞后（周波）。"""
    n = d.size
    if n < 8 or sigma <= 0:
        return 1
    x = d - np.mean(d)
    x = np.clip(x, -5 * sigma * math.sqrt(2.0), 5 * sigma * math.sqrt(2.0))      # 事件尖峰不参与
    v = float(np.dot(x, x))
    if v <= 0:
        return 1
    for lag in range(1, min(max_lag, n // 2) + 1):
        r = float(np.dot(x[:-lag], x[lag:])) / v
        if r < math.exp(-1.0):
            return max(1, lag)
    return max_lag


def _allan_min_steady(p: np.ndarray, lo: int, hi: int) -> int:
    """Allan 方差拐点：块均值的相邻差方差随块长 m 不再按 ~1/m 下降的最小 m。"""
    L = p.size
    prev = None
    ms = [m for m in (2, 4, 8, 16, 32, 64, 128, 256) if m * 12 <= L]      # 至少 12 块，块间差的中位数才稳
    pick = lo
    for m in ms:
        nb = L // m
        bm = p[: nb * m].reshape(nb, m).mean(axis=1)
        if bm.size < 3:
            break
        av = 0.5 * float(np.median(np.diff(bm) ** 2))          # 用中位数代替均值：抗事件
        if prev is not None and prev > 0 and av / prev > 0.85:
            pick = m
            break
        prev = av
    return int(min(max(pick, lo), max(lo, hi)))


def _transient_len(d: np.ndarray, sigma: float, settle: int, lo: int, hi: int) -> int:
    """|差分| > 4σ√2 的超限游程（允许 ≤ settle 周波间断）的最长长度，下限 4·settle。"""
    lo = max(lo, 4 * settle)
    if sigma <= 0 or d.size == 0:
        return int(min(lo, hi))
    idx = np.nonzero(np.abs(d) > 4.0 * sigma * math.sqrt(2.0))[0]
    if idx.size == 0:
        return int(min(lo, hi))
    runs = []
    a = b = int(idx[0])
    for i in idx[1:]:
        i = int(i)
        if i - b <= settle:
            b = i
        else:
            runs.append(b - a + 1); a = b = i
    runs.append(b - a + 1)
    t = int(max(runs))
    return int(min(max(t, lo), hi))


def _range_tol(sigma: float, n: int) -> float:
    n = max(2, int(n))
    return sigma * (2.0 * math.sqrt(2.0 * math.log(n)) + 1.0)


def _cusum_h(k_std: float, arl0: float) -> float:
    """Siegmund 近似反解单侧 CUSUM 门限（σ 单位）：ARL0 ≈ (exp(2k(h+1.166)) − 2k(h+1.166) − 1) / (2k²)。"""
    def arl(h: float) -> float:
        b = h + 1.166
        return (math.exp(2 * k_std * b) - 2 * k_std * b - 1) / (2 * k_std * k_std)
    lo, hi = 0.5, 60.0
    if arl(hi) < arl0:
        return hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if arl(mid) < arl0:
            lo = mid
        else:
            hi = mid
    return hi


def window_stats(p: np.ndarray, f_nom: float = 50.0) -> Optional[Dict[str, Any]]:
    """由一段逐周波序列推导公共统计量；数据不足（< AUTO_MIN_CYCLES）返回 None。"""
    p0 = np.asarray(p, dtype=np.float64)
    p0 = p0[np.isfinite(p0)]
    L0 = int(p0.size)
    if L0 < AUTO_MIN_CYCLES:
        return None
    hold, sig_lags = _hold_length(p0)
    if hold > 1:
        nb = L0 // hold
        if nb < AUTO_MIN_CYCLES:
            return None                                        # 抽稀后不足：窗太短（需 ≥ AUTO_MIN_CYCLES×hold 周波）
        p = p0[: nb * hold].reshape(nb, hold).mean(axis=1)
    else:
        p = p0
    L = int(p.size)
    d = np.diff(p)
    sigma = max(_mad_sigma(d), _trimmed_sigma(d))
    if not math.isfinite(sigma) or sigma <= 0:
        level = float(np.median(np.abs(p))) if L else 0.0
        sigma = max(abs(level) * 1e-6, 1e-9)                   # 完全平直（恒定量化值）：给一个极小尺度
    tau = _corr_time(d, sigma)
    settle = int(min(20, max(3, 3 * tau + 2)))
    min_steady = _allan_min_steady(p, lo=max(5, 2 * settle), hi=max(5, L // 6))
    transient = _transient_len(d, sigma, settle, lo=settle, hi=max(4 * settle, L // 3))
    arl0 = max(1e3, float(f_nom) * 86400.0 / hold)
    k = math.sqrt(2.0 * math.log(arl0))
    min_delta = max(k * sigma * math.sqrt(2.0 / min_steady) * 1.5, 4.0 * sigma)
    return {"n": L0, "hold": int(hold), "n_eff": L, "sigma": float(sigma), "tau": int(tau * hold), "settle": int(settle * hold),
            "min_steady": int(min_steady * hold), "transient": int(transient * hold), "k": float(k), "arl0": float(arl0),
            "min_delta": float(min_delta), "level": float(np.median(np.abs(p0))),
            "sigma_lags": {str(lg): float(v) for lg, v in sig_lags}}


_LAGS = (1, 2, 3, 5, 8, 12, 16, 25, 32, 50, 64, 100, 128, 200, 256)


def _hold_length(p: np.ndarray):
    """多尺度 σ_lag；若在某 lag 跳升 ≥20×σ_1 且随后平台化（下一档 < 1.5×），判为采样保持长度 hold。"""
    L = p.size
    lags = [lg for lg in _LAGS if lg * 8 <= L]
    sig = [(lg, _mad_sigma(p[lg:] - p[:-lg])) for lg in lags]
    s1 = sig[0][1] if sig else 0.0
    hold = 1
    for j in range(1, len(sig) - 1):
        lg, sv = sig[j]
        if s1 > 0 and sv >= 20.0 * s1 and sig[j + 1][1] < 1.5 * sv:
            hold = lg
            break
    return hold, sig


def auto_algo_params(algo: str, st: Dict[str, Any], base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """把公共统计量映射成某个算法的参数字典（覆盖 base 中的数值键，保留 enabled）。"""
    prm = dict(base or NILM_ALGO_DEFAULTS[algo])
    s, k, settle, ms, tr, md = st["sigma"], st["k"], st["settle"], st["min_steady"], st["transient"], st["min_delta"]
    if algo == "threshold":
        prm.update(min_delta_w=md, settle_cycles=settle, settle_tol_w=_range_tol(s, settle), max_rise_cycles=tr)
    elif algo == "median_diff":
        mc = settle if settle % 2 else settle + 1
        prm.update(median_cycles=int(min(11, max(3, mc))), min_delta_w=md, settle_cycles=settle,
                   settle_tol_w=_range_tol(s, settle), max_rise_cycles=tr)
    elif algo == "two_window":
        prm.update(pre_cycles=ms, post_cycles=ms, min_delta_w=md, k_sigma=k)
    elif algo == "cusum":
        drift = 0.5 * md
        h = _cusum_h(drift / s, st["arl0"]) * s
        prm.update(drift_w=drift, threshold_w=h, min_delta_w=md, settle_cycles=settle)
    elif algo == "glr":
        prm.update(window_cycles=ms, threshold=0.5 * k * k, min_delta_w=md, noise_w=s, settle_cycles=settle)
    elif algo == "steady_state":
        prm.update(tol_w=_range_tol(s, ms), min_steady_cycles=ms, min_delta_w=md, max_transient_cycles=tr)
    # A 套键与 W 套同值（算法函数只读 *_w；这里同步只为展示一致）
    for kw, ka in (("min_delta_w", "min_delta_a"), ("settle_tol_w", "settle_tol_a"), ("tol_w", "tol_a"),
                   ("drift_w", "drift_a"), ("noise_w", "noise_a"), ("threshold_w", "threshold_a")):
        if kw in prm and ka in prm:
            prm[ka] = prm[kw]
    return prm


def auto_params(p: np.ndarray, f_nom: float = 50.0, algorithms: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """一次性返回 ``{"stats": 公共统计量, "algorithms": {算法: 参数}}``；数据不足返回 None。"""
    st = window_stats(p, f_nom)
    if st is None:
        return None
    algs = {}
    for a in NILM_ALGO_DEFAULTS:
        base = dict(NILM_ALGO_DEFAULTS[a])
        if algorithms and a in algorithms:
            base.update({kk: vv for kk, vv in algorithms[a].items() if kk in base})
        algs[a] = auto_algo_params(a, st, base)
    return {"stats": st, "algorithms": algs}
