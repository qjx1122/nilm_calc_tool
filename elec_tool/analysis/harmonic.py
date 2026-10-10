"""谐波（2~50 次）与频谱分析。

数学口径（cos 参考、RMS 相量）：
    x(t) = Σ_h √2·X_h·cos(2πh·f·t + φ_h)
    对 N 点做 rfft：X = rfft(x·w)，窗系数和 wsum = Σw
    第 k 个 bin 的 RMS 幅值 = √2·|X[k]| / wsum        （k=0 与 Nyquist bin 不乘 √2）
    第 k 个 bin 的 RMS 相量 = √2·X[k] / wsum
    h 次谐波对应 bin：k = h·f_used·N/fs ；当 N 为「整数周期」时 k = h·n_cycles 恰为整数 → 无泄漏

    THD = sqrt(Σ_{h=2..H} X_h²) / X_1 × 100%
    含有率 HR_h = X_h / X_1 × 100%
    间谐波占比 = sqrt(max(总交流能量 − Σ_{h=1..H}谐波能量, 0)) / 总交流有效值 × 100%
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..config import HarmonicConfig
from .rms import rms
from .window import get_window_fn


def _prepare(x: np.ndarray, remove_dc: bool) -> Tuple[np.ndarray, float]:
    x = np.asarray(x, dtype=np.float64).ravel()
    dc = float(x.mean()) if x.size else 0.0
    if remove_dc and x.size:
        x = x - dc
    return x, dc


def bin_spectrum(x: np.ndarray, fs: float, window_fn: str = "rect",
                 remove_dc: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, float]]:
    """全 bin 频谱。

    返回 (freqs, rms_amp, rms_phasor, meta)
    meta: n / wsum / coherent_gain / dc / delta_f / total_ac_rms
    """
    x, dc = _prepare(x, remove_dc)
    n = x.size
    if n < 2:
        return (np.empty(0), np.empty(0), np.empty(0, dtype=np.complex128),
                {"n": float(n), "wsum": 0.0, "coherent_gain": 1.0, "dc": dc,
                 "delta_f": float("nan"), "total_ac_rms": float("nan")})
    w, cg = get_window_fn(window_fn, n)
    wsum = float(w.sum())
    X = np.fft.rfft(x * w)
    phasor = X * (np.sqrt(2.0) / wsum)
    amp = np.abs(phasor)
    if amp.size:
        amp[0] = abs(X[0]) / wsum                     # DC bin 不乘 √2
        phasor[0] = X[0] / wsum
    if n % 2 == 0 and amp.size > 1:                   # Nyquist bin 不乘 √2
        amp[-1] = abs(X[-1]) / wsum
        phasor[-1] = X[-1] / wsum
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    total_ac_rms = float(np.sqrt(np.sum(amp[1:] ** 2))) if amp.size > 1 else 0.0
    meta = {"n": float(n), "wsum": wsum, "coherent_gain": cg, "dc": dc,
            "delta_f": float(fs / n), "total_ac_rms": total_ac_rms}
    return freqs, amp, phasor, meta


def harmonic_bins(n: int, fs: float, f_used: float, orders: Sequence[int]) -> Tuple[np.ndarray, bool]:
    """各次谐波对应的 bin 序号；返回 (k 数组, 是否全部落在整数 bin)。"""
    k_float = np.asarray(orders, dtype=np.float64) * f_used * n / fs
    k = np.rint(k_float).astype(np.int64)
    exact = bool(np.all(np.abs(k_float - k) < 1e-6))
    return k, exact


def dft_harmonic_phasors(x: np.ndarray, fs: float, f_used: float,
                         orders: Sequence[int], window_fn: str = "rect",
                         remove_dc: bool = True) -> Tuple[Dict[int, complex], Dict[str, object]]:
    """提取指定次数的 RMS 相量（cos 参考）。返回 (phasors, meta)。"""
    freqs, amp, phasor, meta = bin_spectrum(x, fs, window_fn, remove_dc)
    n = int(meta["n"])
    orders = [int(h) for h in orders]
    out: Dict[int, complex] = {}
    if n < 2 or amp.size == 0:
        return out, {**meta, "orders": orders, "integer_bins": False, "leakage_risk": True,
                     "out_of_range": orders}
    k, exact = harmonic_bins(n, fs, f_used, orders)
    nyq_bin = amp.size - 1
    oob: List[int] = []
    for h, kk in zip(orders, k):
        if kk <= 0 or kk > nyq_bin:
            oob.append(h)
            out[h] = complex(float("nan"), float("nan"))
        else:
            out[h] = complex(phasor[kk])
    return out, {**meta, "orders": orders, "integer_bins": exact,
                 "leakage_risk": (not exact) or window_fn != "rect",
                 "out_of_range": oob, "freq_resolution_hz": meta["delta_f"]}


def harmonic_analysis(x: np.ndarray, fs: float, f_used: float, cfg: HarmonicConfig,
                      window_fn: str = "rect", remove_dc: bool = True,
                      n_cycles: Optional[int] = None) -> Dict[str, object]:
    """单通道谐波分析（需求⑤：基波 + 2~50 次谐波 + THD + 含有率）。"""
    orders = list(range(int(cfg.order_min), int(cfg.order_max) + 1))
    all_orders = list(range(1, int(cfg.order_max) + 1))
    phasors, meta = dft_harmonic_phasors(x, fs, f_used, all_orders, window_fn, remove_dc)

    def mag(h: int) -> float:
        v = phasors.get(h, complex(float("nan")))
        return float(abs(v))

    u1 = mag(1)
    rms_orders = {h: mag(h) for h in orders}
    finite = np.array([v for v in rms_orders.values() if np.isfinite(v)], dtype=np.float64)
    thd_rms = float(np.sqrt(np.sum(finite ** 2))) if finite.size else float("nan")
    thd_pct = float(100.0 * thd_rms / u1) if (u1 and np.isfinite(u1) and u1 > 0) else float("nan")

    total_ac = float(meta.get("total_ac_rms", float("nan")))
    harm_energy = float(np.sqrt(np.sum(np.array([mag(h) for h in all_orders if np.isfinite(mag(h))]) ** 2))) \
        if all_orders else 0.0
    if np.isfinite(total_ac) and total_ac > 0:
        inter_pct = float(100.0 * np.sqrt(max(total_ac ** 2 - harm_energy ** 2, 0.0)) / total_ac)
    else:
        inter_pct = float("nan")

    finite_orders = {h: v for h, v in rms_orders.items() if np.isfinite(v)}
    max_order = max(finite_orders, key=finite_orders.get) if finite_orders else None

    return {
        "fundamental_rms": u1,
        "fundamental_peak": float(u1 * np.sqrt(2.0)) if np.isfinite(u1) else float("nan"),
        "fundamental_angle_deg": float(np.degrees(np.angle(phasors.get(1, complex(float("nan")))))),
        "total_rms": rms(x, remove_dc),
        "total_ac_rms_from_bins": total_ac,
        "orders_rms": {str(h): v for h, v in rms_orders.items()},
        "hr_pct": {str(h): (float(100.0 * v / u1) if (u1 and np.isfinite(u1) and u1 > 0 and np.isfinite(v))
                            else float("nan")) for h, v in rms_orders.items()},
        "thd_pct": thd_pct,
        "thd_rms": thd_rms,
        "interharmonic_pct": inter_pct if cfg.include_interharmonic else None,
        "max_order": max_order,
        "max_order_rms": finite_orders.get(max_order, float("nan")) if max_order else float("nan"),
        "order_range": [int(cfg.order_min), int(cfg.order_max)],
        "thd_order_max": int(cfg.thd_order_max),
        "f_used": float(f_used),
        "n_cycles": n_cycles,
        "freq_resolution_hz": float(meta.get("delta_f", float("nan"))),
        "integer_bins": bool(meta.get("integer_bins", False)),
        "leakage_risk": bool(meta.get("leakage_risk", False)),
        "window_fn": window_fn,
        "dc_removed": bool(remove_dc),
        "dc_offset": float(meta.get("dc", float("nan"))),
        "out_of_range_orders": [int(h) for h in meta.get("out_of_range", [])],
    }


def harmonic_analysis_3phase(x3: np.ndarray, fs: float, f_used: float, cfg: HarmonicConfig,
                             window_fn: str = "rect", remove_dc: bool = True,
                             n_cycles: Optional[int] = None) -> Dict[str, object]:
    """三相谐波分析：逐相结果 + 最劣相 + 三相 THD。"""
    x3 = np.asarray(x3, dtype=np.float64)
    if x3.ndim != 2 or x3.shape[0] != 3:
        raise ValueError(f"输入形状必须是 (3,N)，当前 {x3.shape}")
    names = ("A", "B", "C")
    per_phase = {names[k]: harmonic_analysis(x3[k], fs, f_used, cfg, window_fn, remove_dc, n_cycles)
                 for k in range(3)}
    thds = {p: per_phase[p]["thd_pct"] for p in names}
    finite_thd = {p: v for p, v in thds.items() if isinstance(v, float) and np.isfinite(v)}
    worst = max(finite_thd, key=finite_thd.get) if finite_thd else None
    return {"per_phase": per_phase, "thd_pct": thds, "worst_phase": worst,
            "worst_thd_pct": finite_thd.get(worst, float("nan")) if worst else float("nan")}


def spectrum_analysis(x: np.ndarray, fs: float, f_used: float, window_fn: str = "rect",
                      remove_dc: bool = True, max_points: int = 1600,
                      f_max: Optional[float] = None) -> Dict[str, object]:
    """频谱（需求⑤：频谱子界面）。

    - 全 bin RMS 幅值谱（0 ~ Nyquist）
    - 抽稀采用**桶内取最大**（max-hold），避免抽稀丢峰
    - 同时给出对数（dB）坐标，便于观察小分量
    """
    freqs, amp, phasor, meta = bin_spectrum(x, fs, window_fn, remove_dc)
    if freqs.size == 0:
        return {"freqs": [], "amp_rms": [], "amp_db": [], "n_bins": 0, "decimated": True,
                "peak": None, "nyquist_hz": fs / 2.0, "f_used": f_used,
                "window_fn": window_fn, "freq_resolution_hz": float("nan"), "notes": ["样本不足"]}
    f_limit = float(f_max) if f_max else float(fs / 2.0)
    keep = freqs <= f_limit
    f_k, a_k = freqs[keep], amp[keep]
    notes: List[str] = []
    if a_k.size > max_points > 0:
        # 桶内取最大抽稀（保峰）：幅值取桶内最大值，频率取该最大值**所在 bin**（不是桶均值，
        # 否则主峰频率会被报偏 —— 自检 S4-peak 曾暴露此问题）
        nb = int(max_points)
        n_in = int(a_k.size)
        edges = np.linspace(0, n_in, nb + 1).astype(np.int64)
        f_out, a_out = [], []
        for s, e in zip(edges[:-1], edges[1:]):
            if e <= s:
                continue
            seg = a_k[s:e]
            j = int(np.argmax(seg))
            f_out.append(float(f_k[s + j]))
            a_out.append(float(seg[j]))
        f_k, a_k = np.asarray(f_out), np.asarray(a_out)
        notes.append(f"频谱点数 {n_in} > {max_points}，已按桶内取最大抽稀"
                     "（幅值保峰、频率取峰所在 bin；抽稀后频率轴非严格等间隔，能量不守恒，仅供显示）")
    ref = max(float(np.nanmax(a_k)), 1e-12) if a_k.size else 1e-12
    a_db = 20.0 * np.log10(np.maximum(a_k, 1e-12) / ref)
    k_peak = int(np.argmax(a_k)) if a_k.size else 0
    peak = None
    if a_k.size:
        peak = {"freq_hz": float(f_k[k_peak]), "amp_rms": float(a_k[k_peak]),
                "order_approx": float(f_k[k_peak] / f_used) if f_used else None}
    return {
        "freqs": [float(v) for v in f_k],
        "amp_rms": [float(v) for v in a_k],
        "amp_db": [float(v) for v in a_db],
        "n_bins": int(freqs.size),
        "n_points_out": int(a_k.size),
        "decimated": bool(a_k.size < int(keep.sum())),
        "peak": peak,
        "nyquist_hz": float(fs / 2.0),
        "f_limit_hz": f_limit,
        "f_used": float(f_used),
        "window_fn": window_fn,
        "freq_resolution_hz": float(meta.get("delta_f", float("nan"))),
        "dc_offset": float(meta.get("dc", float("nan"))),
        "total_ac_rms": float(meta.get("total_ac_rms", float("nan"))),
        "notes": notes,
    }
