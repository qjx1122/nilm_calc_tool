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


# ---------------------------------------------------------------------- 间谐波（IEC 61000-4-7 分组）

def interharmonic_analysis(x: np.ndarray, fs: float, f_used: float, order_max: int,
                           n_cycles: Optional[int] = None, remove_dc: bool = True,
                           top_n: int = 10) -> Dict[str, object]:
    """单通道间谐波分析（IEC 61000-4-7 的「间谐波组 / 中心间谐波子组」口径）。

    整周期窗（n_cycles 个周波）下频率分辨率 Δf = f_used / n_cycles，h 次谐波落在 bin k_h = h·n_cycles。
    第 h 个间谐波组（h = 0 … order_max−1，介于 h 次与 h+1 次之间）：
        组有效值   IHG_h  = sqrt( Σ_{k = k_h+1 … k_{h+1}−1} C_k² )          （不含两端谐波 bin）
        中心子组   IHSG_h = sqrt( Σ_{k = k_h+2 … k_{h+1}−2} C_k² )          （再去掉紧邻谐波的各 1 个 bin，抗泄漏）
        主导间谐波 = 组内幅值最大的 bin：频率 / RMS 幅值 / 相角（cos 参考）—— 即「间谐波相量」
    总间谐波畸变率 TIHD = sqrt(Σ_h IHG_h²) / C_1 × 100%；各组含有率 IHG_h / C_1 × 100%。
    n_cycles=1（Δf = f）时组内没有 bin，全部为 0 并给出提示；IEC 推荐 10 周波（Δf=5 Hz，每组 9 个 bin）。
    """
    freqs, amp, phasor, meta = bin_spectrum(x, fs, "rect", remove_dc)
    n = int(meta["n"])
    out: Dict[str, object] = {"groups": [], "notes": []}
    if n < 2 or amp.size < 3:
        out.update({"tihd_pct": float("nan"), "fundamental_rms": float("nan"), "freq_resolution_hz": float("nan"),
                    "n_bins_per_group": 0, "max_group": None, "top": []})
        out["notes"].append("样本不足，间谐波未计算")
        return out
    if n_cycles is None or n_cycles < 1:
        n_cycles = max(1, int(round(n * f_used / fs)))
    nc = int(n_cycles)
    delta_f = float(fs / n)
    k1 = nc
    u1 = float(amp[k1]) if k1 < amp.size else float("nan")
    nyq_bin = amp.size - 1
    groups: List[Dict[str, object]] = []
    sq_sum = 0.0
    for h in range(0, int(order_max)):
        ka, kb = h * nc, (h + 1) * nc
        if kb > nyq_bin:
            break
        lo, hi = ka + 1, kb                       # [lo, hi) 不含两端谐波 bin
        if hi <= lo:
            groups.append({"h": h, "f_lo": float(ka * delta_f), "f_hi": float(kb * delta_f), "rms": 0.0,
                           "subgroup_rms": 0.0, "pct": 0.0, "dom_freq_hz": None, "dom_rms": 0.0,
                           "dom_angle_deg": None, "n_bins": 0})
            continue
        seg = amp[lo:hi]
        g = float(np.sqrt(np.sum(seg ** 2)))
        sg = float(np.sqrt(np.sum(amp[lo + 1:hi - 1] ** 2))) if hi - 1 > lo + 1 else 0.0
        j = int(np.argmax(seg))
        kd = lo + j
        groups.append({
            "h": h, "f_lo": float(ka * delta_f), "f_hi": float(kb * delta_f),
            "rms": g, "subgroup_rms": sg,
            "pct": float(100.0 * g / u1) if (np.isfinite(u1) and u1 > 0) else float("nan"),
            "dom_freq_hz": float(freqs[kd]), "dom_rms": float(amp[kd]),
            "dom_angle_deg": float(np.degrees(np.angle(phasor[kd]))), "n_bins": int(hi - lo),
        })
        sq_sum += g * g
    tihd = float(100.0 * np.sqrt(sq_sum) / u1) if (np.isfinite(u1) and u1 > 0) else float("nan")
    max_group = max(groups, key=lambda d: d["rms"]) if groups else None
    top = sorted(groups, key=lambda d: d["rms"], reverse=True)[:top_n]
    out.update({
        "fundamental_rms": u1, "tihd_pct": tihd, "freq_resolution_hz": delta_f, "n_cycles": nc,
        "n_bins_per_group": max(0, nc - 1), "n_groups": len(groups),
        "max_group": max_group, "top": top, "groups": groups,
        "total_interharmonic_rms": float(np.sqrt(sq_sum)),
    })
    if nc < 2:
        out["notes"].append("窗长仅 1 个周波：频率分辨率等于基波频率，谐波之间没有可分辨的间谐波 bin；"
                            "请把 interharmonic 窗长设为 ≥0.2 s（10 周波，IEC 61000-4-7）")
    return out


def interharmonic_analysis_3phase(x3: np.ndarray, fs: float, f_used: float, order_max: int,
                                  n_cycles: Optional[int] = None, remove_dc: bool = True) -> Dict[str, object]:
    x3 = np.asarray(x3, dtype=np.float64)
    per = {p: interharmonic_analysis(x3[k], fs, f_used, order_max, n_cycles, remove_dc) for k, p in enumerate(("A", "B", "C"))}
    tihd = {p: per[p]["tihd_pct"] for p in per}
    finite = {p: v for p, v in tihd.items() if isinstance(v, float) and np.isfinite(v)}
    worst = max(finite, key=finite.get) if finite else None
    return {"per_phase": per, "tihd_pct": tihd, "worst_phase": worst,
            "worst_tihd_pct": finite.get(worst, float("nan")) if worst else float("nan")}


# ---------------------------------------------------------------------- 直流偏置

def dc_analysis(x: np.ndarray, fs: float, f_used: float, fundamental_rms: Optional[float] = None,
                n_cycles: Optional[int] = None) -> Dict[str, object]:
    """单通道直流分量。

    直流 = 整数周期窗内的算术均值（整周期上基波及各次谐波的均值恰为 0，均值即直流，无偏）；
    同时给逐周期均值序列（观察直流漂移）与相对基波有效值的百分比 DC/X1×100%。
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    n = x.size
    if n == 0:
        return {"dc": float("nan"), "dc_pct": float("nan"), "per_cycle": [], "per_cycle_max": float("nan"),
                "per_cycle_min": float("nan"), "per_cycle_std": float("nan"), "n_cycles": 0}
    dc = float(x.mean())
    spc = fs / f_used if f_used > 0 else n
    nc = int(n_cycles) if n_cycles else int(np.floor(n / spc))
    cyc: List[float] = []
    for c in range(max(nc, 0)):
        a, b = int(round(c * spc)), int(round((c + 1) * spc))
        if b > n or b <= a:
            break
        cyc.append(float(x[a:b].mean()))
    arr = np.asarray(cyc, dtype=np.float64)
    pct = float(100.0 * dc / fundamental_rms) if (fundamental_rms and np.isfinite(fundamental_rms) and fundamental_rms > 0) else float("nan")
    return {"dc": dc, "dc_pct": pct, "per_cycle": cyc,
            "per_cycle_max": float(arr.max()) if arr.size else float("nan"),
            "per_cycle_min": float(arr.min()) if arr.size else float("nan"),
            "per_cycle_std": float(arr.std()) if arr.size else float("nan"),
            "n_cycles": int(arr.size)}
