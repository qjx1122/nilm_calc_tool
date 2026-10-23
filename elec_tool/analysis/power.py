"""功率与功率因数计算（三相四线口径：输入为三相电压 + 三相电流）。

口径（可配置，结果中始终标注所用口径）：
- 有功 P：时域定义 P_k = (1/N)Σ u_k[n]·i_k[n]，P = Σ_k P_k（非正弦工况严格成立）
- 无功 Q：
    harmonic_sum（默认）＝ Σ_h U_h·I_h·sin(φ_h)，逐次谐波无功之和（严格、带符号）
    quadrature          ＝ sign·sqrt(max(S² − P², 0))，由视在反推（非正弦工况为等效值）
- 视在 S：
    arithmetic（默认）＝ Σ_k U_k,rms·I_k,rms（三相算术视在，计量常用）
    vector             ＝ sqrt(P² + Q²)（几何视在）
- 功率因数 PF = P / S（所用 S 由 apparent 口径决定）；另出基波位移因数 DPF = cos φ1 = P1/(U1·I1)
- 相量约定：cos 参考，x(t)=√2·X·cos(2πft+φ) → RMS 相量 X∠φ；
  P_h = Re(U_h·conj(I_h))，Q_h = Im(U_h·conj(I_h))；感性（电流滞后）时 Q>0
- 对账：时域 P 与「Σ_h P_h」之差即非谐波分量（间谐波/噪声/直流）贡献，结果中给 residual_pct
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from ..config import HarmonicConfig, PowerConfig
from .harmonic import dft_harmonic_phasors
from .rms import rms

PHASES = ("A", "B", "C")


def instantaneous_power(u: np.ndarray, i: np.ndarray) -> np.ndarray:
    """瞬时功率 p(t) = Σ_k u_k(t)·i_k(t)，输入 (3,N)，输出 (N,)。"""
    u = np.asarray(u, dtype=np.float64)
    i = np.asarray(i, dtype=np.float64)
    if u.shape != i.shape:
        raise ValueError(f"u/i 形状不一致：{u.shape} vs {i.shape}")
    return np.sum(u * i, axis=0)


def _phase_phasor_power(u_ph: np.ndarray, i_ph: np.ndarray, fs: float, f_used: float,
                        order_max: int, window_fn: str, remove_dc: bool) -> Dict[str, object]:
    """单相：逐次谐波相量 → P_h / Q_h / U_h / I_h。"""
    up, umeta = dft_harmonic_phasors(u_ph, fs, f_used, range(1, order_max + 1), window_fn, remove_dc)
    ip, imeta = dft_harmonic_phasors(i_ph, fs, f_used, range(1, order_max + 1), window_fn, remove_dc)
    p_h: Dict[int, float] = {}
    q_h: Dict[int, float] = {}
    s_h: Dict[int, float] = {}
    for h in range(1, order_max + 1):
        uh, ih = up.get(h, complex(np.nan)), ip.get(h, complex(np.nan))
        if not (np.isfinite(uh.real) and np.isfinite(ih.real)):
            continue
        si = uh * np.conj(ih)
        p_h[h] = float(si.real)
        q_h[h] = float(si.imag)
        s_h[h] = float(abs(uh) * abs(ih))
    return {
        "p_h": p_h, "q_h": q_h, "s_h": s_h,
        "u_phasors": up, "i_phasors": ip,
        "u_meta": umeta, "i_meta": imeta,
    }


def power_analysis(u: np.ndarray, i: np.ndarray, fs: float, f_used: float,
                   cfg: PowerConfig, harm_cfg: HarmonicConfig,
                   remove_dc: bool = True, window_fn: str = "rect",
                   n_cycles: Optional[int] = None,
                   max_series_points: int = 1200) -> Dict[str, object]:
    """三相功率全套结果。u、i 形状 (3,N)，**已变换到一次侧**。"""
    u = np.asarray(u, dtype=np.float64)
    i = np.asarray(i, dtype=np.float64)
    if u.ndim != 2 or u.shape[0] != 3 or u.shape != i.shape:
        raise ValueError(f"u/i 形状必须是 (3,N) 且一致，当前 {u.shape} / {i.shape}")
    n = u.shape[1]
    notes: List[str] = []

    # ---- 1) 时域有功（权威口径） ----
    p_phase_time = [float(np.mean(u[k] * i[k])) if n else float("nan") for k in range(3)]
    p_total_time = float(np.nansum(p_phase_time)) if n else float("nan")
    p_series = instantaneous_power(u, i) if n else np.empty(0)

    # ---- 2) 分相有效值 ----
    u_rms = [rms(u[k], remove_dc) for k in range(3)]
    i_rms = [rms(i[k], remove_dc) for k in range(3)]
    s_phase_arith = [float(u_rms[k] * i_rms[k]) for k in range(3)]

    # ---- 3) 逐次谐波相量功率 ----
    order_max = int(max(harm_cfg.order_max, 1))
    per_phase_h: List[Dict[str, object]] = []
    for k in range(3):
        per_phase_h.append(_phase_phasor_power(u[k], i[k], fs, f_used, order_max, window_fn, remove_dc))

    p_phase_harm = [float(np.nansum(list(ph["p_h"].values()))) for ph in per_phase_h]
    q_phase_harm = [float(np.nansum(list(ph["q_h"].values()))) for ph in per_phase_h]
    p_total_harm = float(np.nansum(p_phase_harm))
    q_total_harm = float(np.nansum(q_phase_harm))

    # ---- 4) 视在与无功（按配置口径） ----
    s_total_arith = float(np.nansum(s_phase_arith))
    q_total_quad = float(np.sqrt(max(s_total_arith ** 2 - p_total_time ** 2, 0.0)))
    if cfg.reactive == "harmonic_sum":
        q_total = q_total_harm
        q_mode_note = "Q=Σ_h U_h·I_h·sinφ_h（逐次谐波无功之和，严格口径，带符号）"
    else:
        # quadrature 口径本身无符号，用谐波口径的符号定方向
        q_total = float(np.copysign(q_total_quad, q_total_harm) if np.isfinite(q_total_harm) else q_total_quad)
        q_mode_note = "Q=√(S²−P²)（等效口径，符号取自逐次谐波无功之和）"
    s_total_vec = float(np.sqrt(max(p_total_time ** 2 + q_total ** 2, 0.0)))
    if cfg.apparent == "arithmetic":
        s_total = s_total_arith
        s_mode_note = "S=Σ_k U_k·I_k（三相算术视在）"
    else:
        s_total = s_total_vec
        s_mode_note = "S=√(P²+Q²)（几何视在）"

    if cfg.apparent == "vector" and cfg.reactive == "quadrature":
        notes.append(
            "⚠️ 口径退化：apparent=vector 且 reactive=quadrature 时，Q=√(S_arith²−P²) 与 S=√(P²+Q²) "
            "互相反推 ⇒ S 恒等于算术视在 S_arith，PF 恒等于 P/S_arith。"
            "若需要真正的几何视在，请设 reactive=harmonic_sum（推荐）")

    pf_total = float(p_total_time / s_total) if (np.isfinite(s_total) and s_total > 0) else float("nan")
    pf_phase = [float(p_phase_time[k] / s_phase_arith[k]) if (np.isfinite(s_phase_arith[k]) and s_phase_arith[k] > 0)
                else float("nan") for k in range(3)]
    q_phase_final = q_phase_harm if cfg.reactive == "harmonic_sum" else [
        float(np.copysign(np.sqrt(max(s_phase_arith[k] ** 2 - p_phase_time[k] ** 2, 0.0)), q_phase_harm[k]))
        for k in range(3)
    ]

    # ---- 5) 基波功率与位移因数 DPF ----
    fund: Dict[str, object] = {"enabled": bool(cfg.fundamental_power)}
    if cfg.fundamental_power:
        p1 = [float(per_phase_h[k]["p_h"].get(1, float("nan"))) for k in range(3)]
        q1 = [float(per_phase_h[k]["q_h"].get(1, float("nan"))) for k in range(3)]
        s1 = [float(per_phase_h[k]["s_h"].get(1, float("nan"))) for k in range(3)]
        u1 = [float(abs(per_phase_h[k]["u_phasors"].get(1, complex(np.nan)))) for k in range(3)]
        i1 = [float(abs(per_phase_h[k]["i_phasors"].get(1, complex(np.nan)))) for k in range(3)]
        p1_total = float(np.nansum(p1))
        q1_total = float(np.nansum(q1))
        s1_total = float(np.nansum(s1))
        dpf = float(p1_total / s1_total) if (np.isfinite(s1_total) and s1_total > 0) else float("nan")
        fund.update({
            "p1_per_phase": {PHASES[k]: p1[k] for k in range(3)},
            "q1_per_phase": {PHASES[k]: q1[k] for k in range(3)},
            "s1_per_phase": {PHASES[k]: s1[k] for k in range(3)},
            "u1_rms": {PHASES[k]: u1[k] for k in range(3)},
            "i1_rms": {PHASES[k]: i1[k] for k in range(3)},
            "p1_total": p1_total, "q1_total": q1_total, "s1_total": s1_total,
            "dpf": dpf,                                   # 位移因数 cos φ1
            "phi1_deg": float(np.degrees(np.arccos(np.clip(dpf, -1.0, 1.0)))) if np.isfinite(dpf) else float("nan"),
            "fundamental_share_pct": float(100.0 * p1_total / p_total_time)
            if (np.isfinite(p_total_time) and abs(p_total_time) > 0) else float("nan"),
        })

    # ---- 6) 对账：时域 P vs Σ_h P_h（Parseval 校验，实现自检） ----
    if np.isfinite(p_total_time) and abs(p_total_time) > 0:
        residual_pct = float(100.0 * (p_total_time - p_total_harm) / abs(p_total_time))
    else:
        residual_pct = float(p_total_time - p_total_harm)
    if abs(residual_pct) > 1.0:
        notes.append(
            f"时域 P 与逐次谐波 P 之和偏差 {residual_pct:.2f}%（>1%）："
            f"可能原因＝非整周期截断/间谐波与噪声占比高/谐波次数上限({order_max})不足"
        )

    # ---- 7) 四象限 ----
    quadrant = _quadrant(p_total_time, q_total)

    # ---- 8) 瞬时功率曲线（抽稀，供 UI 绘制） ----
    series: Dict[str, object] = {}
    if p_series.size:
        step = max(1, int(np.ceil(p_series.size / max(max_series_points, 1))))
        # v0.76：瞬时无功 / 视在波形——q_k(t)=u_k(t−T/4)·i_k(t)（电压滞后 1/4 基波周期，按 f_used 取整到采样点，窗内循环移位），
        #        s_k(t)=sqrt(p_k²+q_k²)；总量 p/q 为三相之和，s 为三相算术和（与 apparent=arithmetic 口径一致）
        lag = int(round(fs / (4.0 * f_used))) if (np.isfinite(f_used) and f_used > 0) else 0
        p_ph = [u[k] * i[k] for k in range(3)]
        q_ph = [np.roll(u[k], lag) * i[k] for k in range(3)]
        s_ph = [np.sqrt(p_ph[k] ** 2 + q_ph[k] ** 2) for k in range(3)]
        series = {
            "p_total": [float(v) for v in p_series[::step]],
            "p_per_phase": {PHASES[k]: [float(v) for v in p_ph[k][::step]] for k in range(3)},
            "q_total": [float(v) for v in sum(q_ph)[::step]],
            "q_per_phase": {PHASES[k]: [float(v) for v in q_ph[k][::step]] for k in range(3)},
            "s_total": [float(v) for v in sum(s_ph)[::step]],
            "s_per_phase": {PHASES[k]: [float(v) for v in s_ph[k][::step]] for k in range(3)},
            "q_lag_samples": lag,
            "stride": int(step),
            "n_points": int(np.ceil(p_series.size / step)),
        }

    return {
        "p_total": p_total_time,
        "q_total": q_total,
        "s_total": s_total,
        "s_total_arithmetic": s_total_arith,
        "s_total_vector": s_total_vec,
        "pf_total": pf_total,
        "p_per_phase": {PHASES[k]: p_phase_time[k] for k in range(3)},
        "q_per_phase": {PHASES[k]: q_phase_final[k] for k in range(3)},
        "s_per_phase": {PHASES[k]: s_phase_arith[k] for k in range(3)},
        "pf_per_phase": {PHASES[k]: pf_phase[k] for k in range(3)},
        "p_harmonic_sum_total": p_total_harm,
        "q_harmonic_sum_total": q_total_harm,
        "p_residual_pct": residual_pct,
        "u_rms": {PHASES[k]: u_rms[k] for k in range(3)},
        "i_rms": {PHASES[k]: i_rms[k] for k in range(3)},
        "quadrant": quadrant,
        "fundamental": fund,
        "orders_used": [1, order_max],
        "modes": {"apparent": cfg.apparent, "reactive": cfg.reactive,
                  "three_phase_mode": cfg.three_phase_mode,
                  "apparent_note": s_mode_note, "reactive_note": q_mode_note},
        "n_samples": int(n),
        "n_cycles": n_cycles,
        "f_used": float(f_used),
        "remove_dc_for_rms": bool(remove_dc),
        "window_fn": window_fn,
        "series": series,
        "notes": notes,
        "units": {"p_total": "W", "q_total": "var", "s_total": "VA", "pf_total": "-",
                  "u_rms": "V", "i_rms": "A"},
    }


def _quadrant(p: float, q: float) -> Dict[str, object]:
    """功率四象限（P 横轴、Q 纵轴）。"""
    if not (np.isfinite(p) and np.isfinite(q)):
        return {"index": None, "name": "无效", "meaning": "P/Q 非有限值"}
    if p >= 0 and q >= 0:
        idx, name, meaning = 1, "第一象限", "正向有功 + 感性无功（吸收有功、吸收无功，典型感性负荷）"
    elif p < 0 and q >= 0:
        idx, name, meaning = 2, "第二象限", "反向有功 + 感性无功（送出有功、吸收无功，如发电机进相/光伏反送）"
    elif p < 0 and q < 0:
        idx, name, meaning = 3, "第三象限", "反向有功 + 容性无功（送出有功、送出无功）"
    else:
        idx, name, meaning = 4, "第四象限", "正向有功 + 容性无功（吸收有功、送出无功，典型容性/补偿工况）"
    return {"index": idx, "name": name, "meaning": meaning,
            "p_sign": "positive" if p >= 0 else "negative",
            "q_sign": "inductive(positive)" if q >= 0 else "capacitive(negative)"}
