"""负荷辨识 · 事件检测（第 12 轮）。

数据流：SampleBlock（已做 PT/CT 变换）→ 逐周波特征（每周波的 P / Q / I_rms，total 与 A/B/C）→ 滚动周波窗
→ 多种突变检测算法并行 → 事件（算法、对象、开始/结束时刻、方向、幅值）→ 内存日志 + CSV 落盘。

设计要点
- 周波切分按 ``fs / f_nom`` 取整（6400 Hz / 50 Hz = 128 点），跨块的零头样本结转到下一块，不丢周波。
- 每个周波：P = mean(u·i)；Q 取基波单频 DFT 的无功 Q1（符号＝感性为正）；I = 周波有效值。
- 所有算法都在「最近 ``window_cycles`` 个周波」的窗上重新评估，只对**尚未确认**的区间产出新事件：
  同一算法同一对象以「事件终点全局周波序号」去重，并要求终点之后已有足够的确认周波（settle）。
  这样每条事件只会报一次，且不依赖块边界。
- 方向：up＝幅值为正（投入 / 功率增大），down＝幅值为负（切除 / 功率减小）；幅值＝事件后稳态均值 − 事件前稳态均值。

算法（参数见 ``config.NILM_ALGO_DEFAULTS``）
threshold    相邻周波差分阈值 → 起点；连续 settle 个周波极差 ≤ tol → 终点
two_window   双滑窗均值差 |mean(后) − mean(前)| 的局部极大值
cusum        双侧 CUSUM（Page）累积偏差超过 h；起点＝累积量最后一次归零处
glr          高斯均值突变的广义似然比：n0·n1/(n0+n1)·(m1−m0)²/σ² 的局部极大值
steady_state Hart 稳态分段：稳态间均值差
median_diff  中值滤波后再做阈值差分（抗尖峰）
"""
from __future__ import annotations

import csv
import math
import os

from .filelock import SHARED_FILE_LOCK
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .blocks import SampleBlock
from .timefmt import fmt_local, wall_day
from .config import AppConfig, NILM_ALGO_DEFAULTS, NILM_ALGO_NAMES, NILM_CHANNELS, NILM_W_TO_A, NilmConfig
from .nilm_auto import AUTO_MIN_CYCLES, auto_algo_params, window_stats
from .config import NILM_SCALAR_ALGOS
from .nilm_profile import ProfileError, detect_profile, load_profile, profile_summary

__all__ = ["NilmEvent", "NilmDetector", "CycleFeatures", "detect_steps", "NILM_ALGO_NAMES"]

_CSV_FIELDS = ["source_id", "id", "algorithm", "algorithm_name", "channel", "t_start", "t_start_local", "t_end", "t_end_local",
               "duration_s", "cycles", "direction", "magnitude_w", "delta_p_w", "delta_q_var", "delta_i_a",
               "pre_p_w", "post_p_w", "score", "quantity", "magnitude", "unit", "run_id",
               "device_id", "confidence", "d2", "profile_direction", "status", "quality_flags"]   # v0.90：画像匹配事件附加列
# v0.32：run_id（本次运行标识）；v0.36：quantity（p/i 检测量）、magnitude（检测量口径的 |Δ|）、unit（W/A）



def _ts(t: Optional[float]) -> str:
    if t is None or not math.isfinite(t):
        return ""
    return fmt_local(t)


@dataclass
class NilmEvent:
    id: int
    algorithm: str
    channel: str
    t_start: float
    t_end: float
    direction: str            # up / down
    magnitude_w: float        # |ΔP|
    delta_p_w: float          # 带符号 ΔP
    delta_q_var: float
    delta_i_a: float
    pre_p_w: float
    post_p_w: float
    cycles: int               # 事件持续周波数（起点→终点）
    score: float = 0.0        # 算法自身的检验量（CUSUM 累积量 / GLR 似然比 / 差分值…）
    g_start: int = 0          # 全局周波序号（内部去重用）
    g_end: int = 0
    quantity: str = "p"       # v0.36：检测量 p（有功）/ i（电流有效值）
    magnitude: float = 0.0    # 检测量口径的 |Δ|（p 时 = magnitude_w，i 时 = |ΔI|）
    unit: str = "W"
    # v0.90：设备画像匹配事件（algorithm="profile"）附加字段；其它算法为空 / 0
    device_id: str = ""
    confidence: float = 0.0           # 0~1
    d2: float = 0.0                   # 对角马氏距离 D²
    profile_direction: str = ""       # START / STOP
    status: str = ""                  # confirmed / low_confidence
    quality_flags: str = ""           # 逗号分隔：state_mismatch / ambiguous_direction / trajectory_deviates

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["algorithm_name"] = NILM_ALGO_NAMES.get(self.algorithm, self.algorithm)
        d["duration_s"] = float(self.t_end - self.t_start)
        d["t_start_local"] = _ts(self.t_start)
        d["t_end_local"] = _ts(self.t_end)
        if self.algorithm == "profile":
            d["observed_delta_p"] = self.delta_p_w
            d["estimated_device_delta_p"] = None          # 无同步校准数据：不估计设备贡献幅值（方案 §7）
        return d


# ---------------------------------------------------------------- 逐周波特征
class CycleFeatures:
    """把连续采样切成整周波，输出每周波的 P / Q / I（4 个对象：total, A, B, C）。"""

    def __init__(self, fs: float, f_nom: float):
        self.fs = float(fs)
        self.f_nom = float(f_nom)
        self.n_cycle = max(4, int(round(self.fs / self.f_nom)))
        self.exact = abs(self.fs / self.f_nom - self.n_cycle) < 1e-9
        self._carry: Optional[SampleBlock] = None
        n = self.n_cycle
        k = np.arange(n)
        self._e = np.exp(-2j * np.pi * k / n)          # 基波单频 DFT 核

    def push(self, block: SampleBlock) -> Dict[str, np.ndarray]:
        """返回本次新增的整周波特征：t (M,), p/q/i (4, M)（顺序 total, A, B, C）。M 可能为 0。"""
        if self._carry is not None and self._carry.n:
            # 时间不连续（缺口）则丢弃结转的零头，避免把两段拼成一个假周波
            if block.n and (block.t[0] - self._carry.t[-1]) > 1.5 / self.fs:
                self._carry = None
            else:
                block = SampleBlock(t=np.concatenate([self._carry.t, block.t]),
                                    u=np.concatenate([self._carry.u, block.u], axis=1),
                                    i=np.concatenate([self._carry.i, block.i], axis=1),
                                    scaled=block.scaled, source=block.source, seq=block.seq)
        n = self.n_cycle
        m = block.n // n
        rest = block.n - m * n
        self._carry = (SampleBlock(t=block.t[m * n:], u=block.u[:, m * n:], i=block.i[:, m * n:],
                                   scaled=block.scaled, source=block.source, seq=block.seq) if rest else None)
        if m == 0:
            return {"t": np.zeros(0), "p": np.zeros((4, 0)), "q": np.zeros((4, 0)), "i": np.zeros((4, 0))}
        u = block.u[:, :m * n].reshape(3, m, n)
        i = block.i[:, :m * n].reshape(3, m, n)
        t = block.t[:m * n].reshape(m, n)[:, 0]
        p_ph = np.mean(u * i, axis=2)                                   # (3, m)
        u1 = (u @ self._e) * (2.0 / n)                                  # (3, m) 复相量
        i1 = (i @ self._e) * (2.0 / n)
        s1 = 0.5 * u1 * np.conj(i1)
        q_ph = np.imag(s1)
        i_ph = np.sqrt(np.mean(i * i, axis=2))
        p = np.vstack([p_ph.sum(axis=0), p_ph])
        q = np.vstack([q_ph.sum(axis=0), q_ph])
        irms = np.vstack([np.sqrt(np.sum(i_ph ** 2, axis=0)), i_ph])  # total 取三相均方根合成（仅作幅值参考）
        return {"t": t, "p": p, "q": q, "i": irms}


# ---------------------------------------------------------------- 各算法（纯函数：窗数组 → 候选事件）
Step = Tuple[int, int, float, float, float]     # (onset, end, pre_level, post_level, score)


def _settle_end(p: np.ndarray, start: int, settle: int, tol: float, max_rise: int) -> Optional[int]:
    """从 start 起找第一个「随后 settle 个周波极差 ≤ tol」的位置；超过 max_rise 返回 None（未结束/不可确认）。"""
    L = len(p)
    for j in range(start, min(start + max_rise, L - settle) + 1):
        seg = p[j:j + settle]
        if len(seg) < settle:
            return None
        if seg.max() - seg.min() <= tol:
            return j
    return None


def _steps_threshold(p: np.ndarray, prm: Dict[str, Any]) -> List[Step]:
    min_d, settle, tol, max_rise = float(prm["min_delta_w"]), int(prm["settle_cycles"]), float(prm["settle_tol_w"]), int(prm["max_rise_cycles"])
    out: List[Step] = []
    L = len(p)
    i = settle
    d = np.diff(p)
    # 单周波差分达到门槛一半即视为起点（阶跃落在周波边界内时会分摊到 2 个周波）；但不低于稳态容差，免得噪声触发
    trig = max(0.5 * min_d, tol)
    while i < L - settle:
        if abs(d[i - 1]) >= trig:
            onset = i
            end = _settle_end(p, onset + 1, settle, tol, max_rise)
            if end is None:
                break                           # 暂态未结束：等更多数据
            pre = float(np.mean(p[max(0, onset - settle):onset]))
            post = float(np.mean(p[end:end + settle]))
            if abs(post - pre) >= min_d:
                # 起点精修：从 onset 到 end 第一个越过中线（pre + Δ/2）的周波
                mid = pre + 0.5 * (post - pre)
                seg = p[onset:end + 1]
                cross = np.nonzero((seg - mid) * np.sign(post - pre) >= 0)[0]
                if cross.size:
                    onset = onset + int(cross[0])
                out.append((onset, end, pre, post, float(post - pre)))
            i = end + settle
            continue
        i += 1
    return out


def _steps_median(p: np.ndarray, prm: Dict[str, Any]) -> List[Step]:
    k = int(prm["median_cycles"])
    if k % 2 == 0:
        k += 1
    if len(p) < k + 2:
        return []
    half = k // 2
    pad = np.pad(p, (half, half), mode="edge")
    win = np.lib.stride_tricks.sliding_window_view(pad, k)
    pm = np.median(win, axis=1)
    return _steps_threshold(pm, prm)


def _steps_two_window(p: np.ndarray, prm: Dict[str, Any]) -> List[Step]:
    pre_n, post_n, min_d, k_sig = int(prm["pre_cycles"]), int(prm["post_cycles"]), float(prm["min_delta_w"]), float(prm["k_sigma"])
    L = len(p)
    if L < pre_n + post_n + 1:
        return []
    cs = np.concatenate([[0.0], np.cumsum(p)])
    cs2 = np.concatenate([[0.0], np.cumsum(p * p)])
    idx = np.arange(pre_n, L - post_n + 1)
    m_pre = (cs[idx] - cs[idx - pre_n]) / pre_n
    m_post = (cs[idx + post_n] - cs[idx]) / post_n
    v_pre = np.maximum((cs2[idx] - cs2[idx - pre_n]) / pre_n - m_pre ** 2, 0.0)
    delta = m_post - m_pre
    thr = np.maximum(min_d, k_sig * np.sqrt(v_pre))
    exceed = np.abs(delta) >= thr
    out: List[Step] = []
    j = 0
    while j < len(idx):
        if not exceed[j]:
            j += 1
            continue
        k0 = j
        while j < len(idx) and exceed[j]:
            j += 1
        seg = np.abs(delta[k0:j])
        pk = k0 + int(np.argmax(seg))
        onset = int(idx[pk])
        end = min(onset + post_n, L - 1)
        out.append((onset, end, float(m_pre[pk]), float(m_post[pk]), float(delta[pk])))
    return out


def _steps_cusum(p: np.ndarray, prm: Dict[str, Any]) -> List[Step]:
    k, h, min_d, settle = float(prm["drift_w"]), float(prm["threshold_w"]), float(prm["min_delta_w"]), int(prm["settle_cycles"])
    L = len(p)
    if L < 2 * settle + 1:
        return []
    out: List[Step] = []
    mu = float(np.mean(p[:settle]))
    sp = sn = 0.0
    zp = zn = 0            # 累积量最后一次为 0 的位置（＝起点估计）
    i = settle
    while i < L:
        x = p[i] - mu
        sp = max(0.0, sp + x - k)
        sn = max(0.0, sn - x - k)
        if sp == 0.0:
            zp = i
        if sn == 0.0:
            zn = i
        if sp > h or sn > h:
            onset = (zp if sp > h else zn) + 1
            score = sp if sp > h else sn
            # 终点：从触发点起找稳态（极差 ≤ 2k），找不到就用触发点
            end = _settle_end(p, i, settle, max(2.0 * k, 1e-9), 4 * settle)
            if end is None:
                if i + settle > L - 1:
                    break                       # 尚不能确认稳态，等更多数据
                end = i
            pre = mu
            post = float(np.mean(p[end:end + settle])) if end + settle <= L else float(np.mean(p[end:]))
            if abs(post - pre) >= min_d:
                out.append((onset, end, pre, post, float(score)))
            mu = post
            sp = sn = 0.0
            i = end + settle
            zp = zn = i - 1
            continue
        i += 1
    return out


def _steps_glr(p: np.ndarray, prm: Dict[str, Any]) -> List[Step]:
    w, thr, min_d, noise, settle = int(prm["window_cycles"]), float(prm["threshold"]), float(prm["min_delta_w"]), float(prm["noise_w"]), int(prm["settle_cycles"])
    L = len(p)
    if L < 2 * w + 1:
        return []
    cs = np.concatenate([[0.0], np.cumsum(p)])
    cs2 = np.concatenate([[0.0], np.cumsum(p * p)])
    idx = np.arange(w, L - w + 1)
    m0 = (cs[idx] - cs[idx - w]) / w
    m1 = (cs[idx + w] - cs[idx]) / w
    v0 = np.maximum((cs2[idx] - cs2[idx - w]) / w - m0 ** 2, 0.0)
    v1 = np.maximum((cs2[idx + w] - cs2[idx]) / w - m1 ** 2, 0.0)
    sigma2 = np.maximum(0.5 * (v0 + v1), noise ** 2)
    llr = (w * w / (2.0 * w)) * (m1 - m0) ** 2 / (2.0 * sigma2)
    exceed = (llr >= thr) & (np.abs(m1 - m0) >= min_d)
    out: List[Step] = []
    j = 0
    while j < len(idx):
        if not exceed[j]:
            j += 1
            continue
        k0 = j
        while j < len(idx) and exceed[j]:
            j += 1
        pk = k0 + int(np.argmax(llr[k0:j]))
        onset = int(idx[pk])
        end = min(onset + settle, L - 1)
        out.append((onset, end, float(m0[pk]), float(m1[pk]), float(llr[pk])))
    return out


def _steps_steady(p: np.ndarray, prm: Dict[str, Any]) -> List[Step]:
    tol, min_n, min_d, max_tr = float(prm["tol_w"]), int(prm["min_steady_cycles"]), float(prm["min_delta_w"]), int(prm["max_transient_cycles"])
    L = len(p)
    segs: List[Tuple[int, int]] = []        # 稳态段 [a, b)
    a = 0
    lo = hi = p[0] if L else 0.0
    for i in range(1, L + 1):
        if i < L:
            lo2, hi2 = min(lo, p[i]), max(hi, p[i])
            if hi2 - lo2 <= tol:
                lo, hi = lo2, hi2
                continue
        if i - a >= min_n:
            segs.append((a, i))
        if i < L:
            a, lo, hi = i, p[i], p[i]
    out: List[Step] = []
    for (a0, b0), (a1, b1) in zip(segs, segs[1:]):
        if a1 - b0 > max_tr:
            continue
        pre, post = float(np.mean(p[a0:b0])), float(np.mean(p[a1:b1]))
        if abs(post - pre) >= min_d:
            out.append((b0, a1, pre, post, float(post - pre)))
    return out


_ALGOS = {"threshold": _steps_threshold, "two_window": _steps_two_window, "cusum": _steps_cusum,
          "glr": _steps_glr, "steady_state": _steps_steady, "median_diff": _steps_median}


_TOL_KEYS = ("settle_tol_w", "tol_w", "drift_w", "noise_w", "threshold_w")


def params_for_current(prm: Dict[str, Any]) -> Dict[str, Any]:
    """I 口径：把 ``*_a``（A）的值写到算法函数读取的 ``*_w`` 键上（W 套不参与）。缺 ``*_a`` 的键保持原值。"""
    out = dict(prm)
    for kw, ka in NILM_W_TO_A.items():
        if kw in out and ka in out:
            out[kw] = float(out[ka])
    return out



def effective_params(prm: Dict[str, Any], level: float, rel_tol_pct: float, min_delta_pct: float) -> Dict[str, Any]:
    """把相对门槛折算进绝对参数：容差类取 max(绝对值, level×rel_tol_pct%)，min_delta_w 取 max(绝对值, level×min_delta_pct%)。"""
    out = dict(prm)
    lv = abs(float(level))
    for k in _TOL_KEYS:
        if k in out:
            out[k] = max(float(out[k]), lv * rel_tol_pct / 100.0)
    if "min_delta_w" in out:
        out["min_delta_w"] = max(float(out["min_delta_w"]), lv * min_delta_pct / 100.0)
    return out


def detect_steps(algo: str, p: np.ndarray, prm: Dict[str, Any]) -> List[Step]:
    """对一段逐周波序列运行指定算法，返回 (onset, end, pre, post, score) 列表（索引为该段内的位置）。"""
    return _ALGOS[algo](np.asarray(p, dtype=np.float64), prm)


def _confirm_cycles(algo: str, prm: Dict[str, Any]) -> int:
    """事件终点之后至少要再看到多少个周波才算「确认」（终点才不会随新数据改变）。"""
    if algo == "two_window":
        return int(prm["post_cycles"])
    if algo == "glr":
        return int(prm["window_cycles"])
    if algo == "steady_state":
        return int(prm["min_steady_cycles"])
    return int(prm.get("settle_cycles", 5))


# ---------------------------------------------------------------- 落盘
class NilmWriter:
    def __init__(self, cfg: NilmConfig, root: Optional[str] = None, source_id: int = 0, run_id: int = 0, dir_override: Optional[str] = None):
        self.cfg = cfg
        self.source_id = int(source_id)
        self.run_id = int(run_id or 0)
        d = dir_override or os.environ.get("ELEC_TOOL_NILM_DIR") or cfg.nilm_dir      # v0.59：运行目录优先
        self.dir = d if os.path.isabs(d) else os.path.join(root or os.getcwd(), d)
        self._fh = None
        self._path: Optional[str] = None
        self.rows_written = 0
        self.errors: List[str] = []

    def _open_for(self, t: float) -> None:
        day = wall_day()                        # v0.58：按墙钟本地日期分文件（t 为数据时间，不再用于命名）
        path = os.path.join(self.dir, f"nilm_events_{day}.csv")
        if self._fh is not None and self._path == path:
            return
        self.close()
        with SHARED_FILE_LOCK:                  # v0.17.2：两侧共用同一文件，表头只写一次
            os.makedirs(self.dir, exist_ok=True)
            from .events import _rotate_if_header_differs
            new = _rotate_if_header_differs(path, _CSV_FIELDS)
            self._fh = open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="")
            self._path = path
            if new:
                csv.writer(self._fh).writerow(_CSV_FIELDS)
                self._fh.flush()

    def write(self, ev: NilmEvent) -> None:
        if not self.cfg.save:
            return
        try:
            self._open_for(ev.t_start)
            d = ev.to_dict()
            row = [self.source_id, d["id"], d["algorithm"], d["algorithm_name"], d["channel"],
                   f"{d['t_start']:.4f}", d["t_start_local"], f"{d['t_end']:.4f}", d["t_end_local"],
                   f"{d['duration_s']:.4f}", d["cycles"], d["direction"],
                   f"{d['magnitude_w']:.3f}", f"{d['delta_p_w']:.3f}", f"{d['delta_q_var']:.3f}", f"{d['delta_i_a']:.4f}",
                   f"{d['pre_p_w']:.3f}", f"{d['post_p_w']:.3f}", f"{d['score']:.4g}",
                   d.get("quantity", "p"), f"{d.get('magnitude', d['magnitude_w']):.4f}", d.get("unit", "W"), self.run_id,
                   d.get("device_id", ""), f"{d.get('confidence', 0.0):.4f}", f"{d.get('d2', 0.0):.4g}", d.get("profile_direction", ""),
                   d.get("status", ""), d.get("quality_flags", "")]
            with SHARED_FILE_LOCK:
                csv.writer(self._fh).writerow(row)
                self._fh.flush()
            self.rows_written += 1
        except Exception as exc:
            msg = f"负荷事件落盘失败：{type(exc).__name__}: {exc}"
            if msg not in self.errors:
                self.errors.append(msg)

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            finally:
                self._fh = None

    def info(self) -> Dict[str, Any]:
        return {"enabled": bool(self.cfg.save), "dir": self.dir, "current_file": self._path,
                "rows_written": self.rows_written, "errors": list(self.errors)}


# ---------------------------------------------------------------- 检测器
class NilmDetector:
    """引擎每摄入一块数据调用 ``ingest(scaled_block)``；返回本次新产生的事件（dict 列表）。线程安全。"""

    def __init__(self, cfg: AppConfig, root: Optional[str] = None, run_id: int = 0, run_dir: Optional[str] = None):
        self.cfg = cfg
        self.ncfg: NilmConfig = cfg.nilm
        self._root = root
        self.run_id = int(run_id or 0)
        self.run_dir = run_dir
        self.feat = CycleFeatures(cfg.sampling.fs, cfg.sampling.f_nom)
        self.writer = NilmWriter(self.ncfg, root=root, source_id=int(getattr(cfg.output, "source_id", 0) or 0), run_id=self.run_id, dir_override=run_dir)
        self._lock = threading.RLock()
        self._t = np.zeros(0)
        self._p = np.zeros((4, 0))
        self._q = np.zeros((4, 0))
        self._i = np.zeros((4, 0))
        self._g0 = 0                        # 窗内第 0 个元素的全局周波序号
        self.cycles_total = 0
        self._log: List[NilmEvent] = []
        self._next_id = 1
        self._last_end: Dict[Tuple[str, str], int] = {}    # (algo, channel) → 已确认事件的终点全局序号
        self.counts: Dict[str, int] = {a: 0 for a in NILM_ALGO_DEFAULTS}
        self.errors: List[str] = []
        # v0.36：电压存在性（数据源只有电流时 u 全 0）；quantity=auto 据此选检测量
        self._u_blocks = 0
        self._u_nonzero_blocks = 0
        # v0.87：自适应参数——最近一次评估每个对象推导出的公共统计量与各算法参数（供界面 / 等价命令查看）
        self.auto_last: Dict[str, Dict[str, Any]] = {}
        # v0.90：设备画像（algorithm=profile）
        self._profile: Optional[Dict[str, Any]] = None
        self._profile_err: str = ""
        self._profile_key: Tuple[str, float] = ("", 0.0)
        self.device_state: str = "unknown"                  # 画像状态机：unknown / on / off
        self.profile_last: List[Dict[str, Any]] = []        # 最近一次评估的候选（含被拒的，供界面诊断）
        self._load_profile()

    def _load_profile(self) -> None:
        """按 nilm.profile_path 加载画像（路径或文件 mtime 变化才重读）。失败不抛，记录到 _profile_err。"""
        path = str(getattr(self.ncfg, "profile_path", "") or "").strip()
        if not path:
            self._profile = None; self._profile_err = ""; self._profile_key = ("", 0.0); return
        root = self._root or os.getcwd()
        ap = path if os.path.isabs(path) else os.path.join(root, path)
        try:
            mt = os.path.getmtime(ap)
        except OSError:
            mt = 0.0
        if self._profile is not None and self._profile_key == (ap, mt):
            return
        try:
            self._profile = load_profile(ap); self._profile_err = ""
        except (ProfileError, ValueError, OSError) as exc:
            self._profile = None; self._profile_err = f"画像加载失败：{exc}"
        self._profile_key = (ap, mt)

    @property
    def auto_params_effective(self) -> bool:
        """自适应参数是否实际生效：配置开启即生效（v0.88 起总线侧 / 分路侧都支持；v0.87 曾限定总线侧 source_id=0）。"""
        return bool(getattr(self.ncfg, "auto_params", False))

    @property
    def voltage_missing(self) -> bool:
        """已摄入的块里电压从未出现过非零值（数据源无电压 / 电压列未映射）。"""
        return self._u_blocks > 0 and self._u_nonzero_blocks == 0

    @property
    def quantity_effective(self) -> str:
        q = str(getattr(self.ncfg, "quantity", "auto") or "auto")
        if q == "auto":
            return "i" if self.voltage_missing else "p"
        return q

    # ---- 配置热更新：换阈值不清历史；fs/f_nom 变化重建周波切分
    def update_config(self, cfg: AppConfig) -> None:
        with self._lock:
            self.cfg = cfg
            self.ncfg = cfg.nilm
            if (cfg.sampling.fs, cfg.sampling.f_nom) != (self.feat.fs, self.feat.f_nom):
                self.feat = CycleFeatures(cfg.sampling.fs, cfg.sampling.f_nom)
                self._t = np.zeros(0); self._p = np.zeros((4, 0)); self._q = np.zeros((4, 0)); self._i = np.zeros((4, 0))
                self._g0 += 0
            self.writer.close()
            self.writer = NilmWriter(self.ncfg, root=self._root, source_id=int(getattr(self.cfg.output, "source_id", 0) or 0), run_id=self.run_id, dir_override=self.run_dir)
            self._load_profile()

    # ---- 主入口
    def ingest(self, block: SampleBlock) -> List[Dict[str, Any]]:
        if not self.ncfg.enabled or block.n == 0:
            return []
        with self._lock:
            self._u_blocks += 1
            if np.any(np.abs(block.u) > 0):
                self._u_nonzero_blocks += 1
            f = self.feat.push(block)
            m = int(f["t"].shape[0])
            if m == 0:
                return []
            self.cycles_total += m
            self._t = np.concatenate([self._t, f["t"]])
            self._p = np.concatenate([self._p, f["p"]], axis=1)
            self._q = np.concatenate([self._q, f["q"]], axis=1)
            self._i = np.concatenate([self._i, f["i"]], axis=1)
            W = int(self.ncfg.window_cycles)
            if self._t.shape[0] > W:
                cut = self._t.shape[0] - W
                self._t = self._t[cut:]; self._p = self._p[:, cut:]; self._q = self._q[:, cut:]; self._i = self._i[:, cut:]
                self._g0 += cut
            new = self._evaluate()
            for ev in new:
                self._log.append(ev)
                self.counts[ev.algorithm] = self.counts.get(ev.algorithm, 0) + 1
                self.writer.write(ev)
            if len(self._log) > int(self.ncfg.max_log):
                self._log = self._log[-int(self.ncfg.max_log):]
            return [e.to_dict() for e in new]

    @property
    def channels_effective(self) -> List[str]:
        """实际参与检测的对象。v0.39：I 口径（仅电流）不存在「三相总」——三相电流有效值无法像有功那样相加，
        跨相合并没有物理意义，只能单相检测：去掉 total；若配置里只有 total 则改为 A/B/C 三相各自单独检测。"""
        chans = list(self.ncfg.channels)
        if self.quantity_effective == "i":
            chans = [c for c in chans if c != "total"] or ["A", "B", "C"]
        return chans

    def _evaluate(self) -> List[NilmEvent]:
        out: List[NilmEvent] = []
        L = self._t.shape[0]
        if L < 3:
            return out
        g_last = self._g0 + L - 1
        gap = int(self.ncfg.min_gap_cycles)
        qty = self.quantity_effective
        if qty == "p" and self.voltage_missing:
            msg = ("数据源无电压（电压列未映射或全为 0）：逐周波有功恒为 0，按 P 检测不会产生任何事件；"
                   "请把 nilm.quantity 设为 i（电流有效值）或 auto")
            if msg not in self.errors:
                self.errors.append(msg)
            return out
        rel_tol = float(self.ncfg.rel_tol_pct)
        min_pct = float(self.ncfg.min_delta_pct)
        auto = self.auto_params_effective
        for ch in self.channels_effective:
            ci = NILM_CHANNELS.index(ch)
            p = self._p[ci] if qty == "p" else self._i[ci]
            level = float(np.median(np.abs(p))) if p.size else 0.0
            st = None
            if auto:
                st = window_stats(p, self.feat.f_nom)
                if st is None:
                    continue                                   # 窗内数据不足 AUTO_MIN_CYCLES：等更多数据
                self.auto_last[ch] = {"stats": st, "algorithms": {}, "quantity": qty, "unit": "W" if qty == "p" else "A"}
            for algo in NILM_SCALAR_ALGOS:
                prm = self.ncfg.params(algo)
                if not prm.get("enabled", True):
                    continue
                if auto and st is not None:
                    prm = auto_algo_params(algo, st, prm)      # v0.87：全部数值参数由窗内数据推导，相对门槛不叠加
                    self.auto_last[ch]["algorithms"][algo] = {k: (round(float(v), 6) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in prm.items()}
                else:
                    if qty == "i":
                        prm = params_for_current(prm)              # v0.37：I 口径用 *_a（A）这套绝对阈值
                    prm = effective_params(prm, level, rel_tol, min_pct)
                try:
                    steps = detect_steps(algo, p, prm)
                except Exception as exc:
                    msg = f"{algo} 检测异常：{type(exc).__name__}: {exc}"
                    if msg not in self.errors:
                        self.errors.append(msg)
                    continue
                confirm = _confirm_cycles(algo, prm)
                key = (algo, ch)
                last_end = self._last_end.get(key, -1)
                for onset, end, pre, post, score in steps:
                    g_on, g_end = self._g0 + onset, self._g0 + end
                    if g_on <= last_end + gap:                  # 已报过（或与上一事件太近）
                        continue
                    if g_end + confirm > g_last:                # 终点之后数据不够，等下一块再确认
                        continue
                    settle = max(2, min(confirm, 10))
                    pre_q, post_q = self._level(self._q[ci], onset, end, settle)
                    pre_i, post_i = self._level(self._i[ci], onset, end, settle)
                    d_main = post - pre                        # 检测量口径的带符号变化（P 或 I）
                    if qty == "p":
                        dp, pre_p, post_p = d_main, pre, post
                    else:
                        pre_p, post_p = self._level(self._p[ci], onset, end, settle)
                        dp = post_p - pre_p
                        pre_i, post_i = pre, post
                    ev = NilmEvent(id=self._next_id, algorithm=algo, channel=ch,
                                   t_start=float(self._t[onset]), t_end=float(self._t[end]),
                                   direction="up" if d_main >= 0 else "down", magnitude_w=abs(float(dp)), delta_p_w=float(dp),
                                   delta_q_var=float(post_q - pre_q), delta_i_a=float(post_i - pre_i),
                                   pre_p_w=float(pre_p), post_p_w=float(post_p), cycles=int(end - onset), score=float(score),
                                   g_start=g_on, g_end=g_end, quantity=qty, magnitude=abs(float(d_main)),
                                   unit="W" if qty == "p" else "A")
                    self._next_id += 1
                    out.append(ev)
                    last_end = g_end
                self._last_end[key] = last_end
        out += self._evaluate_profile(qty, gap, g_last)
        out.sort(key=lambda e: (e.t_start, e.algorithm))
        return out

    def _evaluate_profile(self, qty: str, gap: int, g_last: int) -> List[NilmEvent]:
        """v0.90：设备画像匹配（多特征，对象固定为三相合成 total；P 口径用总有功做候选，I 口径用三相电流合成量）。"""
        prm = self.ncfg.params("profile")
        if not prm.get("enabled", False):
            return []
        if self._profile is None:
            return []
        prof = self._profile
        use_p = (qty == "p")
        if prof.get("quantity") != ("p" if use_p else "i"):
            msg = f"画像按 {prof.get('unit')} 口径构建，本侧检测量为 {'P' if use_p else 'I'}：ΔP/ΔI 特征不可比，画像匹配未运行（请统一 nilm.quantity）"
            if msg not in self.errors:
                self.errors.append(msg)
            return []
        try:
            res = detect_profile(self._p, self._q, self._i, prof, prm, use_p, self.device_state)
        except Exception as exc:
            msg = f"profile 检测异常：{type(exc).__name__}: {exc}"
            if msg not in self.errors:
                self.errors.append(msg)
            return []
        post_n = int(prof.get("post_cycles", 50))
        key = ("profile", "total")
        last_end = self._last_end.get(key, -1)
        out: List[NilmEvent] = []
        diag: List[Dict[str, Any]] = []
        for r in res:
            onset, end = r["onset"], r["end"]
            g_on, g_end = self._g0 + onset, self._g0 + end
            if g_end + post_n > g_last:                      # 事件后窗数据不够：等下一块
                continue
            m = r["match"]; f = r["feat"]
            diag.append({"t_start": float(self._t[onset]), "t_start_local": _ts(float(self._t[onset])), "direction": m["direction"],
                         "d2": round(m["d2"], 3), "d2_per_dim": round(m["d2_per_dim"], 3), "confidence": round(r["confidence"], 4),
                         "margin": (round(m["margin"], 2) if math.isfinite(m["margin"]) else None), "status": r["status"],
                         "flags": list(r["flags"]), "contrib": {k: round(v, 2) for k, v in m["contrib"].items()},
                         "vec": {k: round(float(v), 4) for k, v in f["vec"].items()}, "seen": g_on <= last_end + gap})
            if g_on <= last_end + gap:
                continue
            if not r["accepted"]:
                continue
            self.device_state = "on" if m["direction"] == "START" else "off"
            v = f["vec"]; dp = float(v["d_p"]); d_main = dp if use_p else f["d_it"]
            ev = NilmEvent(id=self._next_id, algorithm="profile", channel="total",
                           t_start=float(self._t[onset]), t_end=float(self._t[end]),
                           direction="up" if m["direction"] == "START" else "down", magnitude_w=abs(dp), delta_p_w=dp,
                           delta_q_var=float(v["d_q"]), delta_i_a=float(f["d_it"]),
                           pre_p_w=float(f["pre"]["p"]), post_p_w=float(f["post"]["p"]), cycles=int(end - onset),
                           score=float(r["confidence"]), g_start=g_on, g_end=g_end, quantity=qty, magnitude=abs(float(d_main)),
                           unit="W" if use_p else "A", device_id=str(prof.get("device_id", "")), confidence=float(r["confidence"]),
                           d2=float(m["d2"]), profile_direction=m["direction"], status=r["status"], quality_flags=",".join(r["flags"]))
            self._next_id += 1
            out.append(ev)
            last_end = g_end
        self._last_end[key] = last_end
        if diag:
            self.profile_last = diag[-20:]
        return out

    @staticmethod
    def _level(arr: np.ndarray, onset: int, end: int, n: int) -> Tuple[float, float]:
        pre = arr[max(0, onset - n):onset]
        post = arr[end:end + n]
        return (float(np.mean(pre)) if pre.size else float(arr[max(0, onset - 1)]),
                float(np.mean(post)) if post.size else float(arr[min(end, arr.size - 1)]))

    # ---- 查询
    def list(self, limit: int = 500, algos: Optional[List[str]] = None, channel: Optional[str] = None,
             since_id: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            evs = [e for e in self._log if e.id > since_id
                   and (not algos or e.algorithm in algos) and (not channel or e.channel == channel)]
        evs = evs[-limit:]
        evs.reverse()
        return [e.to_dict() for e in evs]

    def cycles(self, n: int = 300) -> Dict[str, Any]:
        """最近 n 个周波的 P/Q/I 序列（界面画图用）。"""
        with self._lock:
            n = max(1, min(int(n), self._t.shape[0])) if self._t.shape[0] else 0
            t = self._t[-n:] if n else self._t
            d = {"t": [float(x) for x in t], "n_cycle_samples": self.feat.n_cycle, "channels": {}}
            for ci, ch in enumerate(NILM_CHANNELS):
                d["channels"][ch] = {"p": [float(x) for x in self._p[ci, -n:]] if n else [],
                                     "q": [float(x) for x in self._q[ci, -n:]] if n else [],
                                     "i": [float(x) for x in self._i[ci, -n:]] if n else []}
            return d

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._log)
            counts = dict(self.counts)
            by_ch = {ch: sum(1 for e in self._log if e.channel == ch) for ch in NILM_CHANNELS}
            by_dir = {"up": sum(1 for e in self._log if e.direction == "up"),
                      "down": sum(1 for e in self._log if e.direction == "down")}
            notes: List[str] = []
            if not self.feat.exact:
                notes.append(f"fs/f_nom={self.feat.fs / self.feat.f_nom:.3f} 非整数：周波按 {self.feat.n_cycle} 点切分，"
                             "逐周波 P/Q 会有小幅泄漏抖动，建议抬高 settle_tol_w / noise_w")
            if not self.ncfg.enabled:
                notes.append("负荷辨识事件检测已禁用（nilm.enabled=false）")
            qty = self.quantity_effective
            if qty == "i":
                notes.append("检测量：电流有效值 I（" + ("数据源无电压，auto 自动切换" if self.ncfg.quantity == "auto" else "nilm.quantity=i")
                             + "）；各算法使用 A 口径阈值（min_delta_a / settle_tol_a / tol_a / drift_a / noise_a / threshold_a），"
                             "W 口径阈值不参与；rel_tol_pct / min_delta_pct 按窗内 |I| 中位数折算后与 A 阈值取较大者；"
                             "事件幅值 magnitude 为 |ΔI|（A），ΔP/ΔQ 在无电压时恒为 0")
                if "total" in self.ncfg.channels:
                    notes.append("I 口径不存在跨相合并（三相电流有效值不能像有功那样相加），只能单相检测：检测对象「三相总」已忽略，"
                                 + ("实际对象 " + "/".join(self.channels_effective)
                                    + ("（配置只有三相总 → 按 A/B/C 三相各自单独检测）" if self.channels_effective == ["A", "B", "C"] and self.ncfg.channels == ["total"] else "")))
            enabled_algos = [a for a in NILM_ALGO_DEFAULTS if self.ncfg.params(a).get("enabled", True)]
            # v0.90：画像匹配状态
            prof_on = bool(self.ncfg.params("profile").get("enabled", False))
            prof_info: Dict[str, Any] = {"enabled": prof_on, "path": str(getattr(self.ncfg, "profile_path", "") or ""), "loaded": self._profile is not None,
                                         "error": self._profile_err, "device_state": self.device_state,
                                         "summary": (profile_summary(self._profile) if self._profile else None), "last": list(self.profile_last)}
            if prof_on and not getattr(self.ncfg, "profile_path", ""):
                notes.append("设备画像匹配已勾选但 nilm.profile_path 为空：请先在数据处理页「设备画像提取」生成画像并填入路径")
            elif prof_on and self._profile_err:
                notes.append(self._profile_err)
            elif prof_on and self._profile is not None:
                pf = self._profile
                notes.append(f"设备画像匹配：设备 {pf.get('device_id')}（{pf.get('unit')} 口径，启动样本 {pf['startup']['n'] if pf.get('startup') else 0} / 停止样本 "
                             f"{pf['shutdown']['n'] if pf.get('shutdown') else 0}，前后窗 {pf.get('pre_cycles')}/{pf.get('post_cycles')} 周波）；"
                             f"对象固定为三相合成，输出观测幅值与置信度，不估计设备贡献幅值；当前设备状态 {self.device_state}")
            auto_cfg = bool(getattr(self.ncfg, "auto_params", False))
            auto_eff = self.auto_params_effective
            if auto_eff:
                side_txt = "分路侧" if int(getattr(self.cfg.output, "source_id", 0) or 0) != 0 else "总线侧"
                notes.append(f"自适应算法参数已启用（{side_txt}）：各算法全部数值参数由当前周波窗数据推导（噪声 σ=差分 MAD、稳定周波=3τ+2、最短稳态=Allan 拐点、"
                             f"暂态时长=超限游程 95% 分位、显著性倍数 k=√(2·ln ARL0)（ARL0=一天周波数）、最小幅值=max(1.5kσ√(2/最短稳态), 4σ)）；"
                             f"配置中的各算法数值与 rel_tol_pct / min_delta_pct 不参与；窗内不足 {AUTO_MIN_CYCLES} 周波时暂不评估")
            return {"enabled": bool(self.ncfg.enabled), "total": total, "auto_params": auto_cfg, "auto_params_effective": auto_eff,
                    "auto_last": {ch: dict(v) for ch, v in self.auto_last.items()}, "counts": counts, "by_channel": by_ch,
                    "by_direction": by_dir, "cycles_total": self.cycles_total, "window_fill": int(self._t.shape[0]),
                    "window_cycles": int(self.ncfg.window_cycles), "n_cycle_samples": self.feat.n_cycle,
                    "channels": list(self.ncfg.channels), "channels_effective": self.channels_effective, "algorithms_enabled": enabled_algos,
                    "quantity": str(self.ncfg.quantity), "quantity_effective": qty, "voltage_missing": self.voltage_missing,
                    "algorithm_names": NILM_ALGO_NAMES, "writer": self.writer.info(), "errors": list(self.errors),
                    "profile": prof_info, "notes": notes}

    def load_events(self, rows: List[Dict[str, Any]], replace: bool = True) -> int:
        """v0.18：把 nilm_events CSV 读回的事件（字典，见 replay_load.load_nilm_events）装入日志。"""
        with self._lock:
            if replace:
                self._log.clear()
                self.counts = {a: 0 for a in NILM_ALGO_DEFAULTS}
            n = 0
            for d in rows:
                algo = str(d.get("algorithm") or "")
                if algo not in NILM_ALGO_DEFAULTS:
                    continue
                ev = NilmEvent(id=self._next_id, algorithm=algo, channel=str(d.get("channel") or "total"),
                               t_start=float(d["t_start"]), t_end=float(d.get("t_end") or d["t_start"]),
                               direction=str(d.get("direction") or ""), magnitude_w=float(d.get("magnitude_w") or 0.0),
                               delta_p_w=float(d.get("delta_p_w") or 0.0), delta_q_var=float(d.get("delta_q_var") or 0.0),
                               delta_i_a=float(d.get("delta_i_a") or 0.0), pre_p_w=float(d.get("pre_p_w") or 0.0),
                               post_p_w=float(d.get("post_p_w") or 0.0), cycles=int(d.get("cycles") or 0),
                               score=float(d.get("score") or 0.0), quantity=str(d.get("quantity") or "p"),
                               magnitude=float(d.get("magnitude") if d.get("magnitude") not in (None, "") else (d.get("magnitude_w") or 0.0)),
                               unit=str(d.get("unit") or "W"), device_id=str(d.get("device_id") or ""),
                               confidence=float(d.get("confidence") or 0.0), d2=float(d.get("d2") or 0.0),
                               profile_direction=str(d.get("profile_direction") or ""), status=str(d.get("status") or ""),
                               quality_flags=str(d.get("quality_flags") or ""))
                self._next_id += 1
                self._log.append(ev)
                self.counts[algo] = self.counts.get(algo, 0) + 1
                n += 1
            return n

    def clear(self) -> int:
        with self._lock:
            n = len(self._log)
            self._log.clear()
            self.counts = {a: 0 for a in NILM_ALGO_DEFAULTS}
            return n

    def close(self) -> None:
        self.writer.close()


# ------------------------------------------------------------------ v0.46：离线文件按时刻装载周波窗（非运行状态下手动查看）

def load_cycles_from_file(cfg: "AppConfig", t_center: Optional[float] = None, n: int = 300,
                          path: Optional[str] = None, max_scan_cycles: int = 200000) -> Dict[str, Any]:
    """从离线 CSV（``cfg.source``，须为 csv_file）读出一段逐周波 P/Q/I 序列，供界面「周波窗」手动装载。

    - ``t_center`` 为 None：从数据起始时刻开始取前 ``n`` 个周波（默认 300）。
    - ``t_center`` 给定（epoch 秒）：以该时刻为中心取 ``n`` 个周波（前 n//2、后 n-n//2）；
      为避免定位带来的半周波偏移，从中心前 n//2+2 个周波处开始读，再按时间裁剪。
    返回与 ``NilmDetector.cycles()`` 同结构（t / channels{p,q,i} / n_cycle_samples）并附 ``source`` 说明；
    不触发检测、不落盘、不改动运行配置（在配置副本上操作）。
    """
    from .config import AppConfig
    from .scaling import scale_block
    from .sources import create_source
    c = AppConfig.from_dict(cfg.to_dict())
    if path:
        c.source.path = path
    if c.source.kind != "csv_file":
        raise ValueError(f"只能从离线文件（csv_file）装载周波窗，当前数据源为 {c.source.kind}")
    if not str(c.source.path or "").strip():
        raise ValueError("未配置离线文件路径（source.path）")
    n = max(1, min(int(n), 20000))
    cyc_s = 1.0 / float(c.sampling.f_nom)
    c.source.file_speed = 0.0
    c.source.play_window = False
    c.source.play_end_time = ""
    if t_center is None:
        c.source.play_start_mode = "begin"; c.source.play_start_value = ""
        t_from = None
    else:
        t_from = float(t_center) - (n // 2 + 2) * cyc_s
        c.source.play_start_mode = "time"; c.source.play_start_value = f"{t_from:.6f}"
    c.validate()

    def _read(want: int):
        feat = CycleFeatures(c.sampling.fs, c.sampling.f_nom)
        ts: List[np.ndarray] = []; ps: List[np.ndarray] = []; qs: List[np.ndarray] = []; is_: List[np.ndarray] = []
        got = 0; eof = False
        with create_source(c) as src:
            while got < want and got < max_scan_cycles:
                blk = src.read()
                if blk is None:
                    if src.exhausted:
                        eof = True; break
                    continue
                f = feat.push(scale_block(blk, c.transform))
                if f["t"].size:
                    ts.append(f["t"]); ps.append(f["p"]); qs.append(f["q"]); is_.append(f["i"]); got += int(f["t"].size)
        if not ts:
            return None
        return (np.concatenate(ts), np.concatenate(ps, axis=1), np.concatenate(qs, axis=1), np.concatenate(is_, axis=1), eof, feat.n_cycle)

    want = n if t_center is None else n + 6
    r = _read(want)
    if r is not None and t_center is not None and r[4] and r[0].size < n and t_from is not None:
        # 中心靠近文件末尾：往前多读「不足的周波数」，保证仍能给满 n 个
        t_from -= (n - int(r[0].size) + 2) * cyc_s
        c.source.play_start_value = f"{t_from:.6f}"
        r2 = _read(want + (n - int(r[0].size) + 2))
        r = r2 or r
    if r is None:
        raise ValueError("该时刻附近没有读到整周波数据（时刻超出文件范围或文件为空）")
    t, p, q, i, _eof, n_cycle = r
    if t_center is None:
        sl = slice(0, n)
    else:
        k = int(np.searchsorted(t, float(t_center)))            # 第一个 ≥ 中心时刻的周波
        a = max(0, k - n // 2); b = min(t.size, a + n); a = max(0, b - n)
        sl = slice(a, b)
    t = t[sl]; p = p[:, sl]; q = q[:, sl]; i = i[:, sl]
    from .config import NILM_CHANNELS
    d: Dict[str, Any] = {"ok": True, "t": [float(x) for x in t], "n_cycle_samples": n_cycle, "channels": {},
                         "source": {"path": c.source.path, "mode": ("center" if t_center is not None else "begin"),
                                    "t_center": (float(t_center) if t_center is not None else None), "n_requested": n,
                                    "n_loaded": int(t.size), "t_start": float(t[0]) if t.size else None, "t_end": float(t[-1]) if t.size else None}}
    for ci, ch in enumerate(NILM_CHANNELS):
        d["channels"][ch] = {"p": [float(x) for x in p[ci]], "q": [float(x) for x in q[ci]], "i": [float(x) for x in i[ci]]}
    if t_center is not None and t.size and not (t[0] - cyc_s <= float(t_center) <= t[-1] + cyc_s):
        d["source"]["note"] = "指定时刻不在文件数据范围内，已取最接近的一段"
    return d
