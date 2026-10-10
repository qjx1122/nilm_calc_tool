"""窗切分与频率估计。

需求⑥：各电气量可分别配置计算时间段（1s / 5s / …）。本模块负责把「窗长（秒）」
换算为样本数，并按策略截断：

- integer_cycles（默认，FFT 类量**必须**）：截断到整数个基波周期 → DFT  bin 恰好落在
  各次谐波上，无频谱泄漏。fs=6400Hz、f=50Hz 时 1 周期＝128 点，1s＝50 周期＝6400 点。
- full_window：严格按 length_s 取样（可能非整周期）→ 仅建议用于时域量（RMS/功率），
  FFT 类量若用此策略会泄漏，结果 meta 中会打 leakage_risk=True 告警。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from ..blocks import SampleBlock
from ..config import WindowSpec


@dataclass
class WindowCut:
    """一次窗切分的元信息（随结果一起落盘，保证口径可追溯）。"""

    quantity: str
    policy: str
    window_fn: str
    length_s_requested: float
    length_s_actual: float
    n_samples: int
    n_cycles: Optional[int]
    f_used: float
    f_source: str                 # nominal | estimated | timestamp
    t_start: float
    t_end: float
    leakage_risk: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "quantity": self.quantity,
            "policy": self.policy,
            "window_fn": self.window_fn,
            "length_s_requested": round(self.length_s_requested, 6),
            "length_s_actual": round(self.length_s_actual, 6),
            "n_samples": self.n_samples,
            "n_cycles": self.n_cycles,
            "f_used": round(self.f_used, 6),
            "f_source": self.f_source,
            "t_start": self.t_start,
            "t_end": self.t_end,
            "leakage_risk": self.leakage_risk,
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------- 频率估计

def _lowpass_fft(x: np.ndarray, fs: float, f_cut: float) -> np.ndarray:
    """FFT 理想低通（仅 numpy，不引入 scipy 依赖）——估频前滤掉谐波与噪声。"""
    n = x.size
    if n < 8:
        return x.astype(np.float64, copy=True)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    X[freqs > f_cut] = 0.0
    return np.fft.irfft(X, n=n)


def estimate_frequency_zero_crossing(x: np.ndarray, fs: float, f_min: float, f_max: float,
                                     f_nom: float = 50.0) -> Tuple[float, str]:
    """过零法估频：先低通到 1.5×f_nom 只留基波，再用线性插值过零点求周期。

    返回 (频率, 方法名)。样本不足或过零点 <2 时回退额定频率。
    精度：对干净基波信号可达 1e-3 Hz 量级（取决于数据长度）。
    """
    x = np.asarray(x, dtype=np.float64)
    if x.size < int(2 * fs / max(f_nom, 1e-6)):
        return float(f_nom), "nominal(insufficient_samples)"
    y = _lowpass_fft(x - x.mean(), fs, 1.5 * f_nom)
    # 正向过零点（线性插值亚样本定位）
    sign_change = np.where((y[:-1] <= 0.0) & (y[1:] > 0.0))[0]
    if sign_change.size < 2:
        return float(f_nom), "nominal(no_zero_crossing)"
    frac = -y[sign_change] / (y[sign_change + 1] - y[sign_change])
    crossings = (sign_change + frac) / fs
    span = crossings[-1] - crossings[0]
    n_cycles = crossings.size - 1
    if span <= 0:
        return float(f_nom), "nominal(zero_span)"
    f_est = n_cycles / span
    if not (f_min <= f_est <= f_max):
        return float(f_nom), f"nominal(out_of_range:{f_est:.3f}Hz)"
    return float(f_est), "zero_crossing"


def estimate_frequency_fft(x: np.ndarray, fs: float, f_min: float, f_max: float,
                           zero_pad: int = 8) -> Tuple[float, str]:
    """FFT 峰值 + 抛物线插值估频（过零法失败时的兜底）。"""
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    if n < 16:
        return float(fs * 0), "nominal(insufficient_samples)"
    xc = x - x.mean()
    if not np.any(np.abs(xc) > 1e-12):
        return float("nan"), "nominal(no_signal)"      # 全零/恒定信号：估频无意义
    w = np.hanning(n)
    nfft = int(n * max(1, zero_pad))
    X = np.abs(np.fft.rfft(xc * w, n=nfft))
    freqs = np.fft.rfftfreq(nfft, d=1.0 / fs)
    band = (freqs >= f_min) & (freqs <= f_max)
    if not band.any():
        return float(fs * 0), "nominal(no_band)"
    idxs = np.where(band)[0]
    k = idxs[np.argmax(X[idxs])]
    if 0 < k < X.size - 1:
        a, b, c = X[k - 1], X[k], X[k + 1]
        denom = a - 2 * b + c
        delta = 0.5 * (a - c) / denom if denom != 0 else 0.0
        delta = float(np.clip(delta, -0.5, 0.5))
    else:
        delta = 0.0
    f_est = float(freqs[k] + delta * (freqs[1] - freqs[0]))
    return f_est, "fft_interp"


def refine_frequency_baseband(x: np.ndarray, fs: float, f0: float, avg_cycles: int = 4) -> float:
    """基带相位斜率精修估频（粗估 → 精修，精度可达 1e-6 相对量级）。

    步骤：① x·e^{-j2πf0t} 搬到基带 ② 长度＝avg_cycles 个整周期的滑动平均抑制谐波与噪声
         ③ 对平滑后包络相位做 unwrap + 线性最小二乘 ④ 斜率/(2π) 即频率修正量 Δf
    为什么可行：包络相位随时间的变化率正是 (f_true − f0)，与信号幅值无关。
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    if x.size < 8 or f0 <= 0:
        return float(f0)
    m = max(2, int(round(fs / f0 * max(1, avg_cycles))))
    if x.size < 2 * m:
        m = max(2, x.size // 2)
    t = np.arange(x.size, dtype=np.float64) / fs
    y = (x - x.mean()) * np.exp(-2j * np.pi * f0 * t)
    kernel = np.ones(m, dtype=np.float64) / m
    ys = np.convolve(y, kernel, mode="valid")
    if ys.size < 4:
        return float(f0)
    ph = np.unwrap(np.angle(ys))
    good = np.abs(ys) > 1e-9 * max(float(np.max(np.abs(ys))), 1e-30)
    if good.sum() < 4:
        return float(f0)
    tt = (np.arange(ys.size, dtype=np.float64) + (m - 1) / 2.0) / fs
    tt, ph = tt[good], ph[good]
    tc = tt - tt.mean()
    denom = float(np.sum(tc * tc))
    if denom <= 0:
        return float(f0)
    slope = float(np.sum(tc * (ph - ph.mean())) / denom)
    return float(f0 + slope / (2.0 * np.pi))


def estimate_frequency(x: np.ndarray, fs: float, f_min: float, f_max: float,
                       f_nom: float = 50.0, refine: bool = True) -> Tuple[float, str]:
    """统一入口：过零法（FFT 插值兜底）粗估 → 基带相位斜率精修；越界则回退额定频率。"""
    f, how = estimate_frequency_zero_crossing(x, fs, f_min, f_max, f_nom)
    if not how.startswith("zero_crossing"):
        f2, how2 = estimate_frequency_fft(x, fs, f_min, f_max)
        if not np.isfinite(f2):
            return float(f_nom), f"nominal({how2})"
        if f_min <= f2 <= f_max:
            f, how = f2, how2
    if refine and f_min <= f <= f_max:
        f_ref = refine_frequency_baseband(x, fs, f)
        if f_min <= f_ref <= f_max:
            return f_ref, how + "+baseband_refine"
        return float(f), how + "(refine_out_of_range)"
    if not (f_min <= f <= f_max):
        return float(f_nom), f"nominal(fallback:{how})"
    return f, how


# ---------------------------------------------------------------- 窗函数

def get_window_fn(name: str, n: int) -> Tuple[np.ndarray, float]:
    """返回 (窗系数, 相干增益 sum(w)/N)。幅值校正：peak = 2|X[k]|/sum(w)。"""
    if n <= 0:
        return np.ones(0), 1.0
    if name == "hann":
        w = np.hanning(n)
    elif name == "rect":
        w = np.ones(n)
    else:
        raise ValueError(f"未知窗函数 '{name}'（支持 rect/hann）")
    return w, float(w.sum() / n)


# ---------------------------------------------------------------- 窗切分

def samples_for_seconds(seconds: float, fs: float) -> int:
    return int(round(float(seconds) * float(fs)))


def plan_window(available: int, spec: WindowSpec, quantity: str, fs: float,
                f_used: float, f_source: str, t_start: float, t_end: float) -> WindowCut:
    """根据可用样本数与窗配置，决定实际使用的样本数与周期数。

    available : 缓冲中可用样本数
    f_used    : 本次计算采用的基波频率（额定或估计值）
    """
    notes: List[str] = []
    n_req = samples_for_seconds(spec.length_s, fs)
    leakage = False

    if spec.policy == "integer_cycles":
        cyc_req = spec.length_s * f_used
        # f_used 往往是**估计值**（过零+基带精修的相对误差实测 ~3e-7），
        # 用绝对容差 1e-9 判整周期会因「差一丝不到 50 周期」而整整少算一个周期：
        # 请求 1s → 只给 49 周期(0.98s)。这里改用相对容差（1e-5·周期数），
        # 只有当 cyc_req 已经贴到整数（差 <0.001%）时才进位，语义上更正确。
        n_cycles = int(np.floor(cyc_req + max(1e-9, 1e-5 * abs(cyc_req))))
        n_cycles = max(n_cycles, int(spec.min_cycles))
        n = int(round(n_cycles * fs / f_used))
        if n > available:                       # 数据不够：降周期数
            while n_cycles > spec.min_cycles and int(round(n_cycles * fs / f_used)) > available:
                n_cycles -= 1
                n = int(round(n_cycles * fs / f_used))
            if n > available:
                n_cycles = 0
                n = max(0, available)
                notes.append(f"可用样本 {available} 不足以容纳 {spec.min_cycles} 个完整周期，本窗降级为非整周期")
                leakage = True
        if abs(n - n_req) > 0 and not notes:
            notes.append(f"整周期截断：请求 {spec.length_s}s({n_req}点) → 实际 {n_cycles} 周期({n}点)")
        actual = n / fs
    else:  # full_window
        n = min(n_req, available)
        n_cycles = None
        cyc = n * f_used / fs
        if abs(cyc - round(cyc)) > 1e-6:
            leakage = True
            notes.append(f"full_window 非整周期（{cyc:.4f} 周期），FFT 类量存在频谱泄漏风险")
        if n < n_req:
            notes.append(f"可用样本 {available} < 请求 {n_req}，本窗按 {n} 点计算")
        actual = n / fs

    if n <= 0:
        notes.append("无可用样本，本窗未计算")

    return WindowCut(
        quantity=quantity,
        policy=spec.policy,
        window_fn=spec.window_fn,
        length_s_requested=float(spec.length_s),
        length_s_actual=float(actual),
        n_samples=int(n),
        n_cycles=int(n_cycles) if n_cycles else None,
        f_used=float(f_used),
        f_source=f_source,
        t_start=float(t_start),
        t_end=float(t_end),
        leakage_risk=bool(leakage),
        notes=notes,
    )


def is_fft_quantity(quantity: str) -> bool:
    """哪些量必须整周期截断（FFT 类）。"""
    return quantity in ("fundamental", "harmonic", "spectrum")
