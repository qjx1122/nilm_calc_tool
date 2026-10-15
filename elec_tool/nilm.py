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
from .timefmt import fmt_local, local_day
from .config import AppConfig, NILM_ALGO_DEFAULTS, NILM_ALGO_NAMES, NILM_CHANNELS, NilmConfig

__all__ = ["NilmEvent", "NilmDetector", "CycleFeatures", "detect_steps", "NILM_ALGO_NAMES"]

_CSV_FIELDS = ["source_id", "id", "algorithm", "algorithm_name", "channel", "t_start", "t_start_local", "t_end", "t_end_local",
               "duration_s", "cycles", "direction", "magnitude_w", "delta_p_w", "delta_q_var", "delta_i_a",
               "pre_p_w", "post_p_w", "score"]


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

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["algorithm_name"] = NILM_ALGO_NAMES.get(self.algorithm, self.algorithm)
        d["duration_s"] = float(self.t_end - self.t_start)
        d["t_start_local"] = _ts(self.t_start)
        d["t_end_local"] = _ts(self.t_end)
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
    def __init__(self, cfg: NilmConfig, root: Optional[str] = None, source_id: int = 0):
        self.cfg = cfg
        self.source_id = int(source_id)
        d = os.environ.get("ELEC_TOOL_NILM_DIR") or cfg.nilm_dir
        self.dir = d if os.path.isabs(d) else os.path.join(root or os.getcwd(), d)
        self._fh = None
        self._path: Optional[str] = None
        self.rows_written = 0
        self.errors: List[str] = []

    def _open_for(self, t: float) -> None:
        day = local_day(t)
        path = os.path.join(self.dir, f"nilm_events_{day}.csv")
        if self._fh is not None and self._path == path:
            return
        self.close()
        with SHARED_FILE_LOCK:                  # v0.17.2：两侧共用同一文件，表头只写一次
            os.makedirs(self.dir, exist_ok=True)
            new = not os.path.exists(path) or os.path.getsize(path) == 0
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
                   f"{d['pre_p_w']:.3f}", f"{d['post_p_w']:.3f}", f"{d['score']:.4g}"]
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

    def __init__(self, cfg: AppConfig, root: Optional[str] = None):
        self.cfg = cfg
        self.ncfg: NilmConfig = cfg.nilm
        self._root = root
        self.feat = CycleFeatures(cfg.sampling.fs, cfg.sampling.f_nom)
        self.writer = NilmWriter(self.ncfg, root=root, source_id=int(getattr(cfg.output, "source_id", 0) or 0))
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
        # v0.21：原始周波数据保留区（独立于检测窗）：分块列表，按 cycle_keep_cycles 从头裁剪
        self._keep: List[Dict[str, np.ndarray]] = []
        self._keep_n = 0
        self._keep_g0 = 0                   # 保留区第 0 个周波的全局序号

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
            self.writer = NilmWriter(self.ncfg, root=self._root, source_id=int(getattr(self.cfg.output, "source_id", 0) or 0))

    # ---- 主入口
    def ingest(self, block: SampleBlock) -> List[Dict[str, Any]]:
        if not self.ncfg.enabled or block.n == 0:
            return []
        with self._lock:
            f = self.feat.push(block)
            m = int(f["t"].shape[0])
            if m == 0:
                return []
            self.cycles_total += m
            self._keep_push(f, m)
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

    def _evaluate(self) -> List[NilmEvent]:
        out: List[NilmEvent] = []
        L = self._t.shape[0]
        if L < 3:
            return out
        g_last = self._g0 + L - 1
        gap = int(self.ncfg.min_gap_cycles)
        for ch in self.ncfg.channels:
            ci = NILM_CHANNELS.index(ch)
            p = self._p[ci]
            level = float(np.median(np.abs(p))) if p.size else 0.0
            for algo in NILM_ALGO_DEFAULTS:
                prm = self.ncfg.params(algo)
                if not prm.get("enabled", True):
                    continue
                prm = effective_params(prm, level, float(self.ncfg.rel_tol_pct), float(self.ncfg.min_delta_pct))
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
                    dp = post - pre
                    ev = NilmEvent(id=self._next_id, algorithm=algo, channel=ch,
                                   t_start=float(self._t[onset]), t_end=float(self._t[end]),
                                   direction="up" if dp >= 0 else "down", magnitude_w=abs(float(dp)), delta_p_w=float(dp),
                                   delta_q_var=float(post_q - pre_q), delta_i_a=float(post_i - pre_i),
                                   pre_p_w=float(pre), post_p_w=float(post), cycles=int(end - onset), score=float(score),
                                   g_start=g_on, g_end=g_end)
                    self._next_id += 1
                    out.append(ev)
                    last_end = g_end
                self._last_end[key] = last_end
        out.sort(key=lambda e: (e.t_start, e.algorithm))
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

    # ---- 原始周波数据保留 / 按时间段导出（v0.21）
    def _keep_push(self, f: Dict[str, np.ndarray], m: int) -> None:
        K = int(getattr(self.ncfg, "cycle_keep_cycles", 0) or 0)
        if K <= 0:
            self._keep = []; self._keep_n = 0; self._keep_g0 = self.cycles_total
            return
        self._keep.append({"t": f["t"].copy(), "p": f["p"].copy(), "q": f["q"].copy(), "i": f["i"].copy()})
        self._keep_n += m
        while self._keep_n > K and self._keep:
            over = self._keep_n - K
            head = self._keep[0]
            hn = int(head["t"].shape[0])
            if hn <= over:
                self._keep.pop(0); self._keep_n -= hn; self._keep_g0 += hn
            else:
                self._keep[0] = {"t": head["t"][over:], "p": head["p"][:, over:], "q": head["q"][:, over:], "i": head["i"][:, over:]}
                self._keep_n -= over; self._keep_g0 += over
                break

    def keep_info(self) -> Dict[str, Any]:
        with self._lock:
            if not self._keep_n:
                return {"cycles": 0, "keep_cycles": int(getattr(self.ncfg, "cycle_keep_cycles", 0) or 0), "t_first": None, "t_last": None}
            return {"cycles": int(self._keep_n), "keep_cycles": int(getattr(self.ncfg, "cycle_keep_cycles", 0) or 0),
                    "t_first": float(self._keep[0]["t"][0]), "t_last": float(self._keep[-1]["t"][-1])}

    def cycles_between(self, t_from: Optional[float], t_to: Optional[float]) -> Dict[str, Any]:
        """保留区内 [t_from, t_to] 的全部周波：{"t": (M,), "p"/"q"/"i": (4, M), "idx": (M,) 全局周波序号}。"""
        with self._lock:
            if not self._keep_n:
                return {"t": np.zeros(0), "p": np.zeros((4, 0)), "q": np.zeros((4, 0)), "i": np.zeros((4, 0)), "idx": np.zeros(0, dtype=np.int64)}
            t = np.concatenate([c["t"] for c in self._keep])
            p = np.concatenate([c["p"] for c in self._keep], axis=1)
            q = np.concatenate([c["q"] for c in self._keep], axis=1)
            i = np.concatenate([c["i"] for c in self._keep], axis=1)
            g0 = self._keep_g0
        idx = np.arange(g0, g0 + t.shape[0], dtype=np.int64)
        mask = np.ones(t.shape[0], dtype=bool)
        if t_from is not None:
            mask &= t >= float(t_from)
        if t_to is not None:
            mask &= t <= float(t_to)
        return {"t": t[mask], "p": p[:, mask], "q": q[:, mask], "i": i[:, mask], "idx": idx[mask]}

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
            enabled_algos = [a for a in NILM_ALGO_DEFAULTS if self.ncfg.params(a).get("enabled", True)]
            return {"enabled": bool(self.ncfg.enabled), "total": total, "counts": counts, "by_channel": by_ch,
                    "by_direction": by_dir, "cycles_total": self.cycles_total, "window_fill": int(self._t.shape[0]),
                    "window_cycles": int(self.ncfg.window_cycles), "n_cycle_samples": self.feat.n_cycle,
                    "channels": list(self.ncfg.channels), "algorithms_enabled": enabled_algos,
                    "algorithm_names": NILM_ALGO_NAMES, "writer": self.writer.info(), "errors": list(self.errors),
                    "keep": {"cycles": int(self._keep_n), "keep_cycles": int(getattr(self.ncfg, "cycle_keep_cycles", 0) or 0),
                             "t_first": (float(self._keep[0]["t"][0]) if self._keep_n else None),
                             "t_last": (float(self._keep[-1]["t"][-1]) if self._keep_n else None)},
                    "notes": notes}

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
                               score=float(d.get("score") or 0.0))
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
