"""有效值（RMS）、逐周期统计、三相不平衡度与序分量。

口径：
- rms(x, remove_dc=True)  ＝ 交流有效值 sqrt(mean((x-x̄)²))；remove_dc=False 为真有效值 sqrt(mean(x²))（含直流）
- 逐周期 RMS：按估计频率切成整数周期分别求 RMS，用于观察波动（max/min/std），
  电力系统电压合格率/闪变类分析常用
- 序分量：Fortescue 对称分量法，基于**基波相量**（cos 参考，RMS 相量）
  U0=(Ua+Ub+Uc)/3, U1=(Ua+aUb+a²Uc)/3, U2=(Ua+a²Ub+aUc)/3, a=e^{j2π/3}
  不平衡度 = |U2|/|U1|×100%，零序含量 = |U0|/|U1|×100%
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

PHASE_NAMES = ("A", "B", "C")


def rms(x: np.ndarray, remove_dc: bool = True) -> float:
    """有效值。空数组返回 nan（上层据此判定「本窗未计算」）。"""
    x = np.asarray(x, dtype=np.float64).ravel()
    if x.size == 0:
        return float("nan")
    if remove_dc:
        x = x - x.mean()
    return float(np.sqrt(np.mean(x * x)))


def rms_per_cycle(x: np.ndarray, fs: float, f: float, remove_dc: bool = True) -> Dict[str, float]:
    """逐周期有效值统计。

    n_cycles = floor(N·f/fs)，只用完整周期，尾部不足一周期丢弃（记 n_dropped）。
    周期边界用 round(k·fs/f) 定位——当 fs/f 非整数（如频率偏移时 6400/49.85=128.4）
    各周期样本数会有 ±1 点差异，导致逐周期值出现 ≤1/N_cycle 量级的固有波纹；
    **权威有效值是整窗 rms()，本统计仅用于观察波动**（max/min/std）。
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    out: Dict[str, float] = {"n_cycles": 0.0, "mean": float("nan"), "max": float("nan"),
                             "min": float("nan"), "std": float("nan"), "n_dropped": 0.0}
    if x.size == 0 or f <= 0 or fs <= 0:
        return out
    spc = fs / f
    n_cycles = int(np.floor(x.size / spc + 1e-9))
    if n_cycles < 1:
        out["n_dropped"] = float(x.size)
        out["mean"] = rms(x, remove_dc)   # 不足一周期时退化为整段 RMS
        out["max"] = out["mean"]
        out["min"] = out["mean"]
        return out
    edges = np.round(np.arange(n_cycles + 1, dtype=np.float64) * spc).astype(np.int64)
    edges[-1] = min(int(edges[-1]), x.size)
    vals: List[float] = []
    for k in range(n_cycles):
        seg = x[edges[k]:edges[k + 1]]
        if seg.size == 0:
            continue
        if remove_dc:
            seg = seg - seg.mean()
        vals.append(float(np.sqrt(np.mean(seg * seg))))
    if not vals:
        out["n_dropped"] = float(x.size)
        return out
    arr = np.asarray(vals, dtype=np.float64)
    n_use = int(edges[len(vals)])
    out.update({
        "n_cycles": float(len(vals)),
        "mean": float(arr.mean()),
        "max": float(arr.max()),
        "min": float(arr.min()),
        "std": float(arr.std(ddof=0)),
        "n_dropped": float(x.size - n_use),
        "samples_per_cycle": float(spc),
    })
    return out


def three_phase_rms(u: np.ndarray, fs: float, f: float, remove_dc: bool = True,
                    per_cycle: bool = True) -> Dict[str, object]:
    """三相电压或电流的有效值汇总（u 形状 (3,N)）。"""
    u = np.asarray(u, dtype=np.float64)
    if u.ndim != 2 or u.shape[0] != 3:
        raise ValueError(f"输入形状必须是 (3,N)，当前 {u.shape}")
    vals = [rms(u[k], remove_dc) for k in range(3)]
    res: Dict[str, object] = {
        "rms": {PHASE_NAMES[k]: vals[k] for k in range(3)},
        "rms_avg": float(np.nanmean(vals)) if vals else float("nan"),
        "rms_max": float(np.nanmax(vals)) if vals else float("nan"),
        "rms_min": float(np.nanmin(vals)) if vals else float("nan"),
        # 有效值偏差型不平衡度（非序分量口径，用于快速判断三相是否对称）
        "rms_unbalance_pct": float(
            100.0 * (max(vals) - min(vals)) / np.nanmean(vals)
        ) if vals and np.nanmean(vals) > 0 else float("nan"),
        "peak": {PHASE_NAMES[k]: float(np.nanmax(np.abs(u[k])) if u[k].size else float("nan")) for k in range(3)},
        "dc_mean": {PHASE_NAMES[k]: float(u[k].mean()) if u[k].size else float("nan") for k in range(3)},
        "n_samples": int(u.shape[1]),
    }
    if per_cycle:
        res["per_cycle"] = {PHASE_NAMES[k]: rms_per_cycle(u[k], fs, f, remove_dc) for k in range(3)}
    return res


def line_voltages_rms(u_phase: np.ndarray, remove_dc: bool = True) -> Dict[str, float]:
    """由相电压瞬时值求线电压有效值（时域差分，对含谐波信号严格成立）。

    uab = ua - ub, ubc = ub - uc, uca = uc - ua
    """
    u_phase = np.asarray(u_phase, dtype=np.float64)
    if u_phase.ndim != 2 or u_phase.shape[0] != 3:
        raise ValueError(f"输入形状必须是 (3,N)，当前 {u_phase.shape}")
    ua, ub, uc = u_phase
    return {
        "Uab": rms(ua - ub, remove_dc),
        "Ubc": rms(ub - uc, remove_dc),
        "Uca": rms(uc - ua, remove_dc),
    }


def phase_from_line_inst(u_line: np.ndarray) -> np.ndarray:
    """由线电压瞬时值反推相电压（假设无零序，Ua=(Uab-Uca)/3）。

    仅当 source 的电压列是线电压（transform.voltage_input='line'）时使用。
    """
    u_line = np.asarray(u_line, dtype=np.float64)
    uab, ubc, uca = u_line
    ua = (uab - uca) / 3.0
    ub = (ubc - uab) / 3.0
    uc = (uca - ubc) / 3.0
    return np.vstack([ua, ub, uc])


def symmetrical_components(phasors: np.ndarray) -> Dict[str, object]:
    """对称分量法（输入：三相基波 RMS 相量，cos 参考）。"""
    p = np.asarray(phasors, dtype=np.complex128).ravel()
    if p.size != 3:
        raise ValueError(f"相量必须是 3 个（当前 {p.size}）")
    a = np.exp(1j * 2 * np.pi / 3)
    u0 = (p[0] + p[1] + p[2]) / 3.0
    u1 = (p[0] + a * p[1] + a * a * p[2]) / 3.0
    u2 = (p[0] + a * a * p[1] + a * p[2]) / 3.0
    m1 = abs(u1)
    return {
        "U0": float(abs(u0)), "U1": float(m1), "U2": float(abs(u2)),
        "U0_angle_deg": float(np.degrees(np.angle(u0))),
        "U1_angle_deg": float(np.degrees(np.angle(u1))),
        "U2_angle_deg": float(np.degrees(np.angle(u2))),
        "zero_seq_pct": float(100.0 * abs(u0) / m1) if m1 > 0 else float("nan"),
        "negative_seq_pct": float(100.0 * abs(u2) / m1) if m1 > 0 else float("nan"),
    }


def unbalance_ratio(phasors: np.ndarray) -> float:
    """电压/电流不平衡度（%）＝ 负序 / 正序 × 100。"""
    return float(symmetrical_components(phasors)["negative_seq_pct"])


def deviation_stats(values: List[float]) -> Dict[str, float]:
    """通用统计（供 UI 表格用）。"""
    arr = np.asarray([v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))],
                     dtype=np.float64)
    if arr.size == 0:
        return {"mean": float("nan"), "max": float("nan"), "min": float("nan"), "std": float("nan")}
    return {"mean": float(arr.mean()), "max": float(arr.max()),
            "min": float(arr.min()), "std": float(arr.std(ddof=0))}
