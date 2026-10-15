"""计算调度层：把「配置 + 数据」变成「各电气量结果」。

核心职责（对应需求⑤⑥）：
- 每个电气量**独立**按自己的窗长/步长/策略取数计算（互不影响）
- 结果统一为 JSON 可序列化 dict，附带口径元信息（窗长、周期数、所用频率、PT/CT、告警）
- 维护 UI 曲线所需的历史序列

物理隔离：本模块只依赖 numpy 与本包，可被 Web 壳 / Qt 壳 / CLI 复用。
"""

from __future__ import annotations

import json
import math
import threading
from array import array
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

from .blocks import SampleBlock, FrameBuffer
from .config import AppConfig, QUANTITY_KEYS, WindowSpec
from .analysis.harmonic import (dc_analysis, dft_harmonic_phasors, harmonic_analysis_3phase,
                                interharmonic_analysis_3phase, spectrum_analysis)
from .analysis.power import power_analysis
from .analysis.rms import (line_voltages_rms, rms, rms_per_cycle, symmetrical_components,
                           three_phase_rms, unbalance_ratio)
from .analysis.window import estimate_frequency, is_fft_quantity, plan_window, samples_for_seconds

PHASES = ("A", "B", "C")


def _jsonable(obj: Any) -> Any:
    """递归转 JSON 安全类型（numpy → python；nan/inf → None，避免 JSON 输出非法字面量）。"""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, (np.complex128, complex)):
        c = complex(obj)
        return {"re": _jsonable(c.real), "im": _jsonable(c.imag),
                "mag": _jsonable(abs(c)), "angle_deg": _jsonable(math.degrees(math.atan2(c.imag, c.real)))}
    if isinstance(obj, np.ndarray):
        return [_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, str) or obj is None:
        return obj
    return _jsonable(float(obj)) if isinstance(obj, (int,)) else str(obj)


@dataclass
class QuantityResult:
    key: str
    ok: bool
    values: Dict[str, Any] = field(default_factory=dict)
    series: Dict[str, Any] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)
    window: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    t_ref: float = float("nan")

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable({
            "key": self.key, "ok": self.ok, "error": self.error, "t_ref": self.t_ref,
            "window": self.window, "units": self.units,
            "values": self.values, "series": self.series,
        })


@dataclass
class MetricsResult:
    t_ref: float
    fs: float
    f_used: float
    f_source: str
    quantities: Dict[str, QuantityResult]
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable({
            "t_ref": self.t_ref,
            "fs": self.fs,
            "f_used": self.f_used,
            "f_source": self.f_source,
            "meta": self.meta,
            "quantities": {k: q.to_dict() for k, q in self.quantities.items()},
        })

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def scalar_table(self) -> List[Dict[str, Any]]:
        """扁平表（供 CLI 表格输出与 CSV 导出）：一行一个标量指标。"""
        rows: List[Dict[str, Any]] = []
        for key, q in self.quantities.items():
            if not q.ok:
                rows.append({"quantity": key, "metric": "_error", "phase": "",
                             "value": q.error, "unit": "", "window_s": q.window.get("length_s_requested")})
                continue
            for path, val in _flatten(q.values):
                unit = q.units.get(path.split(".")[0], "")
                rows.append({"quantity": key, "metric": path, "phase": "",
                             "value": val, "unit": unit,
                             "window_s": q.window.get("length_s_requested")})
        return rows


def _flatten(obj: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """把嵌套 dict 拍平为 (路径, 标量值)，列表/大数组不展开。"""
    out: List[Tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.extend(_flatten(v, path))
            elif isinstance(v, (list, tuple, np.ndarray)):
                continue
            elif isinstance(v, (int, float, np.floating, np.integer)) or v is None:
                out.append((path, None if v is None else float(v)))
            elif isinstance(v, (str, bool)):
                continue
    return out


def _pick(q: "QuantityResult", *path: str) -> Any:
    """按路径从 QuantityResult.values 取标量（失败返回 None）。"""
    cur: Any = q.values if q.ok else None
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    if isinstance(cur, (int, float, np.floating, np.integer)):
        v = float(cur)
        return None if (math.isnan(v) or math.isinf(v)) else v
    return None


# 各量趋势曲线要保留的标量（只取标量，数组类曲线由 series 单次下发）
_EXTRACTORS: Dict[str, Any] = {
    "voltage": lambda r, q: {"Ua": _pick(q, "rms", "A"), "Ub": _pick(q, "rms", "B"),
                             "Uc": _pick(q, "rms", "C"), "Uab": _pick(q, "line_rms", "Uab"),
                             "Ubc": _pick(q, "line_rms", "Ubc"), "Uca": _pick(q, "line_rms", "Uca"),
                             "unbalance_pct": _pick(q, "unbalance_pct"),
                             "U1": _pick(q, "fundamental_rms", "A")},
    "current": lambda r, q: {"Ia": _pick(q, "rms", "A"), "Ib": _pick(q, "rms", "B"),
                             "Ic": _pick(q, "rms", "C"), "In": _pick(q, "neutral_rms"),
                             "unbalance_pct": _pick(q, "unbalance_pct")},
    # v0.19：三相总 P/Q/S 之后追加分相 Pa/Pb/Pc、Qa/Qb/Qc、Sa/Sb/Sc（总览 P/Q/S 趋势图可按相显示）
    "power": lambda r, q: {"P": _pick(q, "p_total"), "Q": _pick(q, "q_total"), "S": _pick(q, "s_total"),
                           "Pa": _pick(q, "p_per_phase", "A"), "Pb": _pick(q, "p_per_phase", "B"), "Pc": _pick(q, "p_per_phase", "C"),
                           "Qa": _pick(q, "q_per_phase", "A"), "Qb": _pick(q, "q_per_phase", "B"), "Qc": _pick(q, "q_per_phase", "C"),
                           "Sa": _pick(q, "s_per_phase", "A"), "Sb": _pick(q, "s_per_phase", "B"), "Sc": _pick(q, "s_per_phase", "C")},
    "power_factor": lambda r, q: {"PF": _pick(q, "pf_total"), "DPF": _pick(q, "dpf"),
                                  "phi1_deg": _pick(q, "phi1_deg")},
    "fundamental": lambda r, q: {"f": r.f_used, "U1": _pick(q, "u1_rms_total"),
                                 "I1": _pick(q, "i1_rms_total"),
                                 "unbalance_pct": _pick(q, "unbalance_u_pct"),
                                 "phiA_deg": _pick(q, "phi_deg", "A")},
    "harmonic": lambda r, q: {"THD_U": _pick(q, "thd_u_worst_pct"), "THD_I": _pick(q, "thd_i_worst_pct")},
    "interharmonic": lambda r, q: {"TIHD_U": _pick(q, "tihd_u_worst_pct"), "TIHD_I": _pick(q, "tihd_i_worst_pct"),
                                   "IHmax_U_pct": _pick(q, "max_group_u", "pct"),
                                   "IHmax_I_pct": _pick(q, "max_group_i", "pct")},
    "dc": lambda r, q: {"Ua_dc": _pick(q, "u_dc", "A"), "Ub_dc": _pick(q, "u_dc", "B"), "Uc_dc": _pick(q, "u_dc", "C"),
                        "Ia_dc": _pick(q, "i_dc", "A"), "Ib_dc": _pick(q, "i_dc", "B"), "Ic_dc": _pick(q, "i_dc", "C"),
                        "In_dc": _pick(q, "in_dc")},
    "spectrum": lambda r, q: {"peak_hz": _pick(q, "peak", "freq_hz"),
                              "peak_amp": _pick(q, "peak", "amp_rms")},
}


_NAN = float("nan")


def curve_record(result: "MetricsResult", key: str, q: "QuantityResult") -> Optional[Dict[str, Any]]:
    """某量本次结果对应的「曲线标量记录」（History 入库与实时落盘共用同一提取规则）。

    返回 {"window_s": …, 字段: 值, …}；该量无曲线定义或 t_ref 非有限时返回 None。
    """
    ext = _EXTRACTORS.get(key)
    if ext is None:
        return None
    t = q.t_ref
    if not isinstance(t, (int, float)) or not math.isfinite(float(t)):
        return None
    rec: Dict[str, Any] = {"window_s": q.window.get("length_s_requested")}
    try:
        rec.update(ext(result, q))
    except Exception:                      # 提取失败不影响主流程
        pass
    return rec


class History:
    """各量标量历史（UI 趋势曲线用），按 quantity 分组，**按数据时间保留最近 N 小时**。

    - 只对本次**实际计算出**的量追加记录——各量窗长/步长独立（需求⑥），
      若强行对齐会在曲线上插入 None 空点。
    - 保留策略（需求「曲线＝最新 24 小时，不足则全部」）：以**最新一条记录的数据时间**为基准，
      丢弃早于 ``hours`` 小时之前的记录；``max_points`` 是内存安全阀（6400Hz、0.2s 步长的快量
      24h≈43.2 万点），超出按最旧丢弃。按「数据时间」而非墙钟计，离线文件回放同样成立。
    - 存储按列（每个字段一个 ``array('d')``，缺值存 NaN）而不是每条一个 dict：
      43 万条 dict 约占 300MB+，紧凑数组每值 8 字节（快量 8 个字段 ×50 万点 ≈ 32MB）；
      修剪用切片一次性做，均摊 O(1)。
    - ``get()`` 支持 ``max_points`` 抽稀：均匀分桶，每桶取**首点＋桶内最大值点＋最小值点**
      （保峰谷），画 24h 趋势时 1500 点足以还原形状，前端不必接收几十万点。
    """

    def __init__(self, hours: float = 24.0, max_points: int = 200000, maxlen: Optional[int] = None):
        # maxlen 为兼容旧调用（History(600)），等价于 max_points
        self.hours = float(hours)
        self.max_points = int(maxlen if maxlen is not None else max_points)
        self._t: Dict[str, array] = {k: array("d") for k in QUANTITY_KEYS}
        self._cols: Dict[str, Dict[str, array]] = {k: {} for k in QUANTITY_KEYS}
        self._dropped: Dict[str, int] = {k: 0 for k in QUANTITY_KEYS}
        # 引擎线程 push、Web 线程 get：修剪时的 del 切片与读取必须互斥
        self._lock = threading.Lock()

    # ---------- 写 ----------
    def push(self, result: "MetricsResult") -> None:
        with self._lock:
            self._push(result)

    def _push(self, result: "MetricsResult") -> None:
        for key, q in result.quantities.items():
            rec = curve_record(result, key, q)
            if rec is None:
                continue
            t = q.t_ref
            ts = self._t.setdefault(key, array("d"))
            cols = self._cols.setdefault(key, {})
            n = len(ts)
            for f, v in rec.items():
                col = cols.get(f)
                if col is None:
                    col = cols[f] = array("d", [_NAN]) * n      # 新字段：历史位置补 NaN
                col.append(float(v) if isinstance(v, (int, float)) and math.isfinite(float(v)) else _NAN)
            for f, col in cols.items():                  # 本条缺的字段补 NaN，保持等长
                if len(col) < n + 1:
                    col.append(_NAN)
            ts.append(float(t))
            self._trim(key)

    def load_records(self, key: str, records: List[Dict[str, Any]], replace: bool = True) -> int:
        """v0.18：把落盘 CSV 读回来的曲线点（[{"t":..., 字段: 值}] 按 t 升序）装入历史；replace=True 先清空该量。"""
        with self._lock:
            if replace or key not in self._t:
                self._t[key] = array("d")
                self._cols[key] = {}
                self._dropped[key] = 0
            ts = self._t[key]
            cols = self._cols[key]
            for rec in records:
                t = rec.get("t")
                if t is None:
                    continue
                n = len(ts)
                for f, v in rec.items():
                    if f == "t":
                        continue
                    col = cols.get(f)
                    if col is None:
                        col = cols[f] = array("d", [_NAN]) * n
                    col.append(float(v) if isinstance(v, (int, float)) and math.isfinite(float(v)) else _NAN)
                for f, col in cols.items():
                    if len(col) < n + 1:
                        col.append(_NAN)
                ts.append(float(t))
            self._trim(key)
            return len(ts)

    def _trim(self, key: str) -> None:
        ts = self._t[key]
        n = len(ts)
        if n == 0:
            return
        cut = 0
        if n > self.max_points:
            cut = n - self.max_points
        horizon = ts[-1] - self.hours * 3600.0
        if ts[cut] < horizon:
            # 时间按递增追加（同一数据集内 t_ref 单调），二分找到第一个 ≥ horizon 的位置；
            # 若数据时间倒退（换源未清空）就退化为线性，结果仍正确
            lo, hi = cut, n
            while lo < hi:
                mid = (lo + hi) // 2
                if ts[mid] < horizon:
                    lo = mid + 1
                else:
                    hi = mid
            cut = lo
        # 修剪只在积压超过 5% 或 1000 条时真正切片，避免每次 push 都 O(n)
        if cut and (cut >= 1000 or cut * 20 >= n):
            del ts[:cut]
            for col in self._cols[key].values():
                del col[:cut]
            self._dropped[key] += cut

    # ---------- 读 ----------
    def count(self, quantity: str) -> int:
        return len(self._t.get(quantity, ()))

    def span(self, quantity: str) -> Tuple[Optional[float], Optional[float]]:
        ts = self._t.get(quantity) or []
        return (ts[0], ts[-1]) if ts else (None, None)

    def get(self, quantity: str, n: Optional[int] = None, hours: Optional[float] = None,
            max_points: Optional[int] = None) -> List[Dict[str, Any]]:
        """取记录列表（每条 {t, window_s, 字段...}）。

        n：只取最后 n 条（兼容旧接口）；hours：只取最新记录往前 hours 小时（默认全部已保留的）；
        max_points：超出则抽稀（保首点/峰/谷）。43 万点抽到 1500 点约 10ms（numpy 分桶）。
        """
        with self._lock:
            ts_arr = self._t.get(quantity)
            if not ts_arr:
                return []
            # 复制成 numpy（单次 C 调用，持 GIL；不保留对 array 的 buffer 导出，否则引擎线程 append 会 BufferError）
            ts = np.array(ts_arr, dtype=np.float64)
            cols = {f: np.array(c, dtype=np.float64) for f, c in self._cols.get(quantity, {}).items()}
        hi = ts.size
        lo = 0
        if hours is not None and hours > 0:
            lo = int(np.searchsorted(ts, ts[-1] - float(hours) * 3600.0, side="left"))
        if n:
            lo = max(lo, hi - int(n))
        if max_points and (hi - lo) > int(max_points) > 2:
            idx = self._decimate(lo, hi, cols, int(max_points))
        else:
            idx = np.arange(lo, hi)
        out: List[Dict[str, Any]] = []
        names = list(cols)
        vals = [cols[f][idx] for f in names]
        tsel = ts[idx]
        for j in range(idx.size):
            rec: Dict[str, Any] = {"t": float(tsel[j])}
            for f, v in zip(names, vals):
                x = v[j]
                rec[f] = None if x != x else float(x)      # NaN → None（JSON 里 NaN 不合法）
            out.append(rec)
        return out

    @staticmethod
    def _decimate(lo: int, hi: int, cols: Dict[str, np.ndarray], max_points: int) -> np.ndarray:
        """均匀分桶抽稀：每桶保留首点，再按「首个数值字段」补桶内最大/最小值点；最后一点永远保留。"""
        n = hi - lo
        nb = max(1, max_points // 3)
        key_field = next((f for f in cols if f != "window_s"), None)
        edges = np.linspace(0, n, nb + 1).astype(np.int64)
        picks: List[int] = []
        col = cols[key_field][lo:hi] if key_field is not None else None
        for b in range(nb):
            a, z = int(edges[b]), int(edges[b + 1])
            if z <= a:
                continue
            picks.append(a)
            if col is not None and z - a > 2:
                seg = col[a:z]
                if not np.all(np.isnan(seg)):
                    picks.append(a + int(np.nanargmax(seg)))
                    picks.append(a + int(np.nanargmin(seg)))
        picks.append(n - 1)
        return np.unique(np.asarray(picks, dtype=np.int64)) + lo

    def stats(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return self._stats()

    def _stats(self) -> Dict[str, Dict[str, Any]]:
        return {k: {"count": len(self._t.get(k, ())), "dropped": self._dropped.get(k, 0),
                    "t_first": (self._t[k][0] if self._t.get(k) else None),
                    "t_last": (self._t[k][-1] if self._t.get(k) else None)}
                for k in QUANTITY_KEYS}

    def clear(self) -> None:
        with self._lock:
            for k in QUANTITY_KEYS:
                self._t[k] = array("d")
                self._cols[k] = {}


class MetricsCalculator:
    """按配置计算各电气量。输入必须是**已变换到一次侧**的数据块（见 scaling.scale_block）。"""

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg.validate()
        self.history = History(hours=cfg.output.history_hours, max_points=cfg.output.history_max_points)

    # ---------------- 对外入口 ----------------
    def compute(self, block: SampleBlock, f_used: Optional[float] = None,
                with_history: bool = True, keys: Optional[List[str]] = None) -> MetricsResult:
        """计算电气量。

        keys=None → 计算全部 7 个量；keys=['voltage','harmonic'] → 只算指定量
        （引擎按各量独立步长调度时用，避免重复计算）。
        """
        cfg = self.cfg
        fs = cfg.sampling.fs
        notes: List[str] = []
        if not block.scaled:
            notes.append("输入数据块未经 PT/CT 变换（scaled=False）——结果按原值计算，请确认调用方已 scale_block")
        if block.is_empty():
            return MetricsResult(t_ref=float("nan"), fs=fs, f_used=float(cfg.sampling.f_nom),
                                 f_source="nominal", quantities={},
                                 meta={"ok": False, "notes": ["数据块为空"], "source": block.source})

        # ---- 频率估计：用最长窗的电压数据估一次，全量共用（避免各量频率口径不一致） ----
        f_source = "nominal"
        if f_used is None:
            if cfg.sampling.adaptive_freq:
                ref_len = max(cfg.max_window_s, 10.0 / cfg.sampling.f_nom)
                ref = block.tail(samples_for_seconds(ref_len, fs))
                u_ref = ref.u[0] if ref.n else block.u[0]
                f_used, f_source = estimate_frequency(u_ref, fs, cfg.sampling.f_min, cfg.sampling.f_max,
                                                      cfg.sampling.f_nom)
            else:
                f_used, f_source = float(cfg.sampling.f_nom), "nominal"
        else:
            f_source = "external"

        quantities: Dict[str, QuantityResult] = {}
        want = [k for k in QUANTITY_KEYS if (keys is None or k in set(keys))]
        unknown = [k for k in (keys or []) if k not in QUANTITY_KEYS]
        if unknown:
            notes.append(f"忽略未知电气量 {unknown}（可用：{list(QUANTITY_KEYS)}）")
        for key in want:
            spec = cfg.windows.get(key) or WindowSpec(length_s=1.0)
            quantities[key] = self._compute_quantity(key, spec, block, float(f_used), f_source, fs)

        t_ref = float(block.t[-1]) if block.n else float("nan")
        meta = {
            "ok": True,
            "source": block.source,
            "scaled": bool(block.scaled),
            "pt_ratio": cfg.transform.pt_ratio if cfg.transform.enabled else 1.0,
            "ct_ratio": cfg.transform.ct_ratio if cfg.transform.enabled else 1.0,
            "voltage_input": cfg.transform.voltage_input,
            "n_available_samples": int(block.n),
            "available_duration_s": float(block.n / fs),
            "max_window_s": float(cfg.max_window_s),
            "adaptive_freq": bool(cfg.sampling.adaptive_freq),
            "harmonic_orders": [cfg.harmonic.order_min, cfg.harmonic.order_max],
            "computed_keys": want,
            "notes": notes,
        }
        res = MetricsResult(t_ref=t_ref, fs=fs, f_used=float(f_used), f_source=f_source,
                            quantities=quantities, meta=meta)
        if with_history:
            self.history.push(res)
        return res

    def compute_from_buffer(self, buf: FrameBuffer, f_used: Optional[float] = None,
                            with_history: bool = True, keys: Optional[List[str]] = None) -> MetricsResult:
        """从环形缓冲取「最长窗」长度的尾部数据，再按各量窗长二次切分。"""
        n = samples_for_seconds(self.cfg.max_window_s, self.cfg.sampling.fs)
        block = buf.snapshot(max(n, 1))
        if block is None:
            return MetricsResult(t_ref=float("nan"), fs=self.cfg.sampling.fs,
                                 f_used=self.cfg.sampling.f_nom, f_source="nominal", quantities={},
                                 meta={"ok": False, "notes": ["缓冲为空"]})
        return self.compute(block, f_used=f_used, with_history=with_history, keys=keys)

    # ---------------- 单量计算 ----------------
    def _compute_quantity(self, key: str, spec: WindowSpec, block: SampleBlock,
                          f_used: float, f_source: str, fs: float) -> QuantityResult:
        # FFT 类量强制整周期策略（否则泄漏），偏离配置时打告警而不是静默出错
        eff_spec = spec
        forced_note: List[str] = []
        if is_fft_quantity(key) and spec.policy != "integer_cycles":
            eff_spec = WindowSpec(length_s=spec.length_s, step_s=spec.step_s, policy="integer_cycles",
                                  window_fn=spec.window_fn, remove_dc=spec.remove_dc, min_cycles=spec.min_cycles)
            forced_note.append(f"{key} 为 FFT 类量，policy 由 {spec.policy} 强制为 integer_cycles（避免频谱泄漏）")

        cut = plan_window(available=block.n, spec=eff_spec, quantity=key, fs=fs, f_used=f_used,
                          f_source=f_source, t_start=block.t_start, t_end=block.t_end)
        if cut.n_samples <= 0:
            return QuantityResult(key=key, ok=False, error="可用数据不足，本窗未计算",
                                  window=cut.to_dict(), t_ref=block.t_end)
        seg = block.tail(cut.n_samples)
        cut.t_start, cut.t_end = seg.t_start, seg.t_end
        cut.length_s_actual = float(seg.n / fs)
        for n_ in forced_note:
            cut.notes.append(n_)
        wd = cut.to_dict()
        try:
            if key == "voltage":
                values, units, series = self._q_voltage(seg, f_used, eff_spec)
            elif key == "current":
                values, units, series = self._q_current(seg, f_used, eff_spec)
            elif key in ("power", "power_factor"):
                values, units, series = self._q_power(seg, f_used, cut, eff_spec, want_pf=(key == "power_factor"))
            elif key == "fundamental":
                values, units, series = self._q_fundamental(seg, f_used, cut)
            elif key == "harmonic":
                values, units, series = self._q_harmonic(seg, f_used, cut, eff_spec)
            elif key == "interharmonic":
                values, units, series = self._q_interharmonic(seg, f_used, cut, eff_spec)
            elif key == "dc":
                values, units, series = self._q_dc(seg, f_used, cut)
            elif key == "spectrum":
                values, units, series = self._q_spectrum(seg, f_used, eff_spec)
            else:
                raise ValueError(f"未知电气量 '{key}'")
        except Exception as exc:  # 单量失败不影响其他量
            return QuantityResult(key=key, ok=False, error=f"{type(exc).__name__}: {exc}",
                                  window=wd, t_ref=cut.t_end)
        if cut.leakage_risk:
            values.setdefault("notes", []).append("本窗存在频谱泄漏风险（非整周期/加窗），幅值类结果仅供参考")
        return QuantityResult(key=key, ok=True, values=values, series=series, units=units,
                              window=wd, t_ref=cut.t_end)

    # ---------------- 各量实现 ----------------
    def _q_voltage(self, seg: SampleBlock, f_used: float, spec: WindowSpec) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        u = seg.u
        if cfg.transform.voltage_input == "line":
            from .analysis.rms import phase_from_line_inst
            u_phase = phase_from_line_inst(u)
        else:
            u_phase = u
        res = three_phase_rms(u_phase, cfg.sampling.fs, f_used, spec.remove_dc, per_cycle=True)
        res["line_rms"] = line_voltages_rms(u_phase, spec.remove_dc)
        res["input_type"] = cfg.transform.voltage_input
        # 序分量与不平衡度（基于本窗**基波**相量）
        phasors = np.array([
            dft_harmonic_phasors(u_phase[k], cfg.sampling.fs, f_used, [1], "rect", spec.remove_dc)[0].get(1, 0j)
            for k in range(3)
        ], dtype=np.complex128)
        res["sequence"] = symmetrical_components(phasors)
        res["unbalance_pct"] = unbalance_ratio(phasors)
        res["fundamental_rms"] = {PHASES[k]: float(abs(phasors[k])) for k in range(3)}
        units = {"rms": "V", "line_rms": "V", "peak": "V", "dc_mean": "V", "fundamental_rms": "V",
                 "unbalance_pct": "%", "rms_unbalance_pct": "%"}
        series = {"waveform": self._waveform(seg, u_phase, 1200)}
        return res, units, series

    def _q_current(self, seg: SampleBlock, f_used: float, spec: WindowSpec) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        i = seg.i
        res = three_phase_rms(i, cfg.sampling.fs, f_used, spec.remove_dc, per_cycle=True)
        i_sum = i.sum(axis=0)                      # 三相四线：零线电流瞬时值 = ia+ib+ic
        res["neutral_rms"] = rms(i_sum, spec.remove_dc)
        res["neutral_per_cycle"] = rms_per_cycle(i_sum, cfg.sampling.fs, f_used, spec.remove_dc)
        phasors = np.array([
            dft_harmonic_phasors(i[k], cfg.sampling.fs, f_used, [1], "rect", spec.remove_dc)[0].get(1, 0j)
            for k in range(3)
        ], dtype=np.complex128)
        res["sequence"] = symmetrical_components(phasors)
        res["unbalance_pct"] = unbalance_ratio(phasors)
        res["fundamental_rms"] = {PHASES[k]: float(abs(phasors[k])) for k in range(3)}
        res["crest_factor"] = {PHASES[k]: (float(np.max(np.abs(i[k])) / res["rms"][PHASES[k]])
                                           if res["rms"][PHASES[k]] > 0 else float("nan")) for k in range(3)}
        units = {"rms": "A", "peak": "A", "dc_mean": "A", "neutral_rms": "A", "fundamental_rms": "A",
                 "unbalance_pct": "%", "rms_unbalance_pct": "%", "crest_factor": "-"}
        series = {"waveform": self._waveform(seg, i, 1200)}
        return res, units, series

    def _q_power(self, seg: SampleBlock, f_used: float, cut, spec: WindowSpec,
                 want_pf: bool) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        full = power_analysis(seg.u, seg.i, cfg.sampling.fs, f_used, cfg.power, cfg.harmonic,
                              remove_dc=spec.remove_dc, window_fn="rect", n_cycles=cut.n_cycles,
                              max_series_points=1000)
        units = {"p_total": "W", "q_total": "var", "s_total": "VA", "pf_total": "-",
                 "u_rms": "V", "i_rms": "A", "p_per_phase": "W", "q_per_phase": "var",
                 "s_per_phase": "VA", "pf_per_phase": "-"}
        if want_pf:
            fund = full.get("fundamental", {}) or {}
            values = {
                "pf_total": full["pf_total"],
                "pf_per_phase": full["pf_per_phase"],
                "dpf": fund.get("dpf"),
                "phi1_deg": fund.get("phi1_deg"),
                "displacement_vs_true_pf_diff": (float(fund["dpf"] - full["pf_total"])
                                                 if isinstance(fund.get("dpf"), float) and np.isfinite(fund.get("dpf", np.nan))
                                                 and np.isfinite(full["pf_total"]) else None),
                "q_sign": full["quadrant"].get("q_sign"),
                "quadrant": full["quadrant"],
                "modes": full["modes"],
                "p_total_for_reference": full["p_total"],
                "s_total_for_reference": full["s_total"],
                "notes": list(full.get("notes", [])),
            }
            units = {"pf_total": "-", "pf_per_phase": "-", "dpf": "-", "phi1_deg": "deg",
                     "displacement_vs_true_pf_diff": "-", "p_total_for_reference": "W",
                     "s_total_for_reference": "VA"}
            return values, units, {}
        series = {"p_total": full.get("series", {}).get("p_total", []),
                  "stride": full.get("series", {}).get("stride", 1)}
        values = {k: v for k, v in full.items() if k != "series"}
        return values, units, series

    def _q_fundamental(self, seg: SampleBlock, f_used: float, cut) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        fs = cfg.sampling.fs
        up, _ = dft_harmonic_phasors(seg.u[0], fs, f_used, [1], "rect", True)
        u_ph = np.array([dft_harmonic_phasors(seg.u[k], fs, f_used, [1], "rect", True)[0].get(1, 0j)
                         for k in range(3)], dtype=np.complex128)
        i_ph = np.array([dft_harmonic_phasors(seg.i[k], fs, f_used, [1], "rect", True)[0].get(1, 0j)
                         for k in range(3)], dtype=np.complex128)
        u_seq = symmetrical_components(u_ph)
        i_seq = symmetrical_components(i_ph)
        phi = {PHASES[k]: float(np.degrees(np.angle(u_ph[k] * np.conj(i_ph[k])))) for k in range(3)}
        values = {
            "freq_hz": float(f_used),
            "freq_source": cut.f_source,
            "u1_rms": {PHASES[k]: float(abs(u_ph[k])) for k in range(3)},
            "u1_angle_deg": {PHASES[k]: float(np.degrees(np.angle(u_ph[k]))) for k in range(3)},
            "i1_rms": {PHASES[k]: float(abs(i_ph[k])) for k in range(3)},
            "i1_angle_deg": {PHASES[k]: float(np.degrees(np.angle(i_ph[k]))) for k in range(3)},
            "u1_rms_total": float(np.mean([abs(v) for v in u_ph])) if u_ph.size else float("nan"),
            "i1_rms_total": float(np.mean([abs(v) for v in i_ph])) if i_ph.size else float("nan"),
            "phi_deg": phi,                       # 电压超前电流的角度（>0 感性）
            "unbalance_u_pct": float(u_seq["negative_seq_pct"]),
            "unbalance_i_pct": float(i_seq["negative_seq_pct"]),
            "u_sequence": u_seq,
            "i_sequence": i_seq,
            "n_cycles": cut.n_cycles,
            "integer_bins": bool(cut.n_cycles is not None),
            "notes": [],
        }
        # 相电压相位差（判断相序）
        d_ab = float(np.degrees(np.angle(u_ph[0] * np.conj(u_ph[1]))))
        d_bc = float(np.degrees(np.angle(u_ph[1] * np.conj(u_ph[2]))))
        values["phase_diff_uab_deg"] = d_ab
        values["phase_diff_ubc_deg"] = d_bc
        values["phase_sequence"] = "正序(ABC)" if (0 < d_ab < 180) else ("负序(ACB)" if -180 < d_ab < 0 else "未知")
        units = {"freq_hz": "Hz", "u1_rms": "V", "i1_rms": "A", "u1_angle_deg": "deg",
                 "i1_angle_deg": "deg", "phi_deg": "deg", "unbalance_u_pct": "%",
                 "unbalance_i_pct": "%", "u1_rms_total": "V", "i1_rms_total": "A",
                 "phase_diff_uab_deg": "deg", "phase_diff_ubc_deg": "deg"}
        return values, units, {}

    def _q_harmonic(self, seg: SampleBlock, f_used: float, cut, spec: WindowSpec) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        hu = harmonic_analysis_3phase(seg.u, cfg.sampling.fs, f_used, cfg.harmonic,
                                      "rect", spec.remove_dc, cut.n_cycles)
        hi = harmonic_analysis_3phase(seg.i, cfg.sampling.fs, f_used, cfg.harmonic,
                                      "rect", spec.remove_dc, cut.n_cycles)
        values = {
            "thd_u_pct": hu["thd_pct"], "thd_i_pct": hi["thd_pct"],
            "thd_u_worst_pct": hu["worst_thd_pct"], "thd_i_worst_pct": hi["worst_thd_pct"],
            "worst_phase_u": hu["worst_phase"], "worst_phase_i": hi["worst_phase"],
            "u": hu["per_phase"], "i": hi["per_phase"],
            "order_range": [cfg.harmonic.order_min, cfg.harmonic.order_max],
            "n_cycles": cut.n_cycles,
            "freq_resolution_hz": hu["per_phase"]["A"]["freq_resolution_hz"],
        }
        units = {"thd_u_pct": "%", "thd_i_pct": "%", "thd_u_worst_pct": "%", "thd_i_worst_pct": "%",
                 "freq_resolution_hz": "Hz"}
        # 柱状图数据：三相 2~50 次含有率（UI 直接画）
        series = {
            "orders": list(range(cfg.harmonic.order_min, cfg.harmonic.order_max + 1)),
            "hr_u_pct": {p: [hu["per_phase"][p]["hr_pct"][str(h)] for h in series_orders(cfg)] for p in PHASES},
            "hr_i_pct": {p: [hi["per_phase"][p]["hr_pct"][str(h)] for h in series_orders(cfg)] for p in PHASES},
            "rms_u": {p: [hu["per_phase"][p]["orders_rms"][str(h)] for h in series_orders(cfg)] for p in PHASES},
            "rms_i": {p: [hi["per_phase"][p]["orders_rms"][str(h)] for h in series_orders(cfg)] for p in PHASES},
        }
        return values, units, series

    def _q_interharmonic(self, seg: SampleBlock, f_used: float, cut, spec: WindowSpec) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        hmax = int(cfg.harmonic.order_max)
        iu = interharmonic_analysis_3phase(seg.u, cfg.sampling.fs, f_used, hmax, cut.n_cycles, spec.remove_dc)
        ii = interharmonic_analysis_3phase(seg.i, cfg.sampling.fs, f_used, hmax, cut.n_cycles, spec.remove_dc)
        pa = iu["per_phase"]["A"]

        def worst_group(res: Dict) -> Optional[Dict]:
            cands = [dict(res["per_phase"][p]["max_group"], phase=p) for p in PHASES if res["per_phase"][p].get("max_group")]
            return max(cands, key=lambda d: d["rms"]) if cands else None

        values = {
            "tihd_u_pct": iu["tihd_pct"], "tihd_i_pct": ii["tihd_pct"],
            "tihd_u_worst_pct": iu["worst_tihd_pct"], "tihd_i_worst_pct": ii["worst_tihd_pct"],
            "worst_phase_u": iu["worst_phase"], "worst_phase_i": ii["worst_phase"],
            "max_group_u": worst_group(iu), "max_group_i": worst_group(ii),
            "top_u": {p: iu["per_phase"][p]["top"] for p in PHASES},
            "top_i": {p: ii["per_phase"][p]["top"] for p in PHASES},
            "u1_rms": {p: iu["per_phase"][p]["fundamental_rms"] for p in PHASES},
            "i1_rms": {p: ii["per_phase"][p]["fundamental_rms"] for p in PHASES},
            "n_cycles": cut.n_cycles, "freq_resolution_hz": pa.get("freq_resolution_hz"),
            "n_bins_per_group": pa.get("n_bins_per_group"), "n_groups": pa.get("n_groups"),
            "notes": list(pa.get("notes", [])),
        }
        units = {"tihd_u_pct": "%", "tihd_i_pct": "%", "tihd_u_worst_pct": "%", "tihd_i_worst_pct": "%",
                 "freq_resolution_hz": "Hz", "u1_rms": "V", "i1_rms": "A"}
        series = {
            "groups": [g["h"] for g in pa["groups"]],
            "f_center": [0.5 * (g["f_lo"] + g["f_hi"]) for g in pa["groups"]],
            "rms_u": {p: [g["rms"] for g in iu["per_phase"][p]["groups"]] for p in PHASES},
            "rms_i": {p: [g["rms"] for g in ii["per_phase"][p]["groups"]] for p in PHASES},
            "pct_u": {p: [g["pct"] for g in iu["per_phase"][p]["groups"]] for p in PHASES},
            "pct_i": {p: [g["pct"] for g in ii["per_phase"][p]["groups"]] for p in PHASES},
            "dom_freq_u": {p: [g["dom_freq_hz"] for g in iu["per_phase"][p]["groups"]] for p in PHASES},
            "dom_freq_i": {p: [g["dom_freq_hz"] for g in ii["per_phase"][p]["groups"]] for p in PHASES},
            "dom_angle_u": {p: [g["dom_angle_deg"] for g in iu["per_phase"][p]["groups"]] for p in PHASES},
            "dom_angle_i": {p: [g["dom_angle_deg"] for g in ii["per_phase"][p]["groups"]] for p in PHASES},
        }
        return values, units, series

    def _q_dc(self, seg: SampleBlock, f_used: float, cut) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        fs = cfg.sampling.fs
        u1 = {PHASES[k]: float(abs(dft_harmonic_phasors(seg.u[k], fs, f_used, [1], "rect", True)[0].get(1, 0j))) for k in range(3)}
        i1 = {PHASES[k]: float(abs(dft_harmonic_phasors(seg.i[k], fs, f_used, [1], "rect", True)[0].get(1, 0j))) for k in range(3)}
        du = {PHASES[k]: dc_analysis(seg.u[k], fs, f_used, u1[PHASES[k]], cut.n_cycles) for k in range(3)}
        di = {PHASES[k]: dc_analysis(seg.i[k], fs, f_used, i1[PHASES[k]], cut.n_cycles) for k in range(3)}
        i_sum = seg.i[0] + seg.i[1] + seg.i[2]
        dn = dc_analysis(i_sum, fs, f_used, None, cut.n_cycles)
        u_dc = {p: du[p]["dc"] for p in PHASES}
        i_dc = {p: di[p]["dc"] for p in PHASES}
        values = {
            "u_dc": u_dc, "i_dc": i_dc, "in_dc": dn["dc"],
            "u_dc_pct": {p: du[p]["dc_pct"] for p in PHASES}, "i_dc_pct": {p: di[p]["dc_pct"] for p in PHASES},
            "u_dc_max_abs": float(max(abs(v) for v in u_dc.values())),
            "i_dc_max_abs": float(max(abs(v) for v in i_dc.values())),
            "u_dc_drift": {p: {"max": du[p]["per_cycle_max"], "min": du[p]["per_cycle_min"], "std": du[p]["per_cycle_std"]} for p in PHASES},
            "i_dc_drift": {p: {"max": di[p]["per_cycle_max"], "min": di[p]["per_cycle_min"], "std": di[p]["per_cycle_std"]} for p in PHASES},
            "u1_rms": u1, "i1_rms": i1,
            "n_cycles": cut.n_cycles,
            "notes": ["直流＝整数周期窗算术均值（整周期上交流分量均值为 0，无偏）；百分比＝DC / 基波有效值"],
        }
        units = {"u_dc": "V", "i_dc": "A", "in_dc": "A", "u_dc_pct": "%", "i_dc_pct": "%",
                 "u_dc_max_abs": "V", "i_dc_max_abs": "A", "u1_rms": "V", "i1_rms": "A"}
        series = {"cycle": list(range(int(dn["n_cycles"]))),
                  "u_per_cycle": {p: du[p]["per_cycle"] for p in PHASES},
                  "i_per_cycle": {p: di[p]["per_cycle"] for p in PHASES},
                  "in_per_cycle": dn["per_cycle"]}
        return values, units, series

    def _q_spectrum(self, seg: SampleBlock, f_used: float, spec: WindowSpec) -> Tuple[Dict, Dict, Dict]:
        cfg = self.cfg
        chans = {"Ua": seg.u[0], "Ia": seg.i[0], "Ub": seg.u[1], "Ib": seg.i[1],
                 "Uc": seg.u[2], "Ic": seg.i[2]}
        out: Dict[str, Any] = {}
        for name, x in chans.items():
            out[name] = spectrum_analysis(x, cfg.sampling.fs, f_used, spec.window_fn, spec.remove_dc,
                                          cfg.output.spectrum_max_points)
        # 概览（以 A 相电压为主）+ 峰值表
        peaks = {name: out[name].get("peak") for name in out}
        values = {"peak": peaks.get("Ua"), "peaks": peaks, "window_fn": spec.window_fn,
                  "freq_resolution_hz": out["Ua"].get("freq_resolution_hz"),
                  "nyquist_hz": out["Ua"].get("nyquist_hz"),
                  "notes": list(out["Ua"].get("notes", []))}
        units = {"freq_resolution_hz": "Hz", "nyquist_hz": "Hz"}
        series = {"channels": {name: {"freqs": out[name]["freqs"], "amp_rms": out[name]["amp_rms"],
                                      "amp_db": out[name]["amp_db"]} for name in out}}
        return values, units, series

    @staticmethod
    def _waveform(seg: SampleBlock, arr: np.ndarray, max_points: int = 1200) -> Dict[str, Any]:
        """波形抽稀（等间隔，保形显示用；不作为计算依据）。"""
        n = arr.shape[1]
        if n == 0:
            return {"t": [], "A": [], "B": [], "C": [], "stride": 1}
        step = max(1, int(math.ceil(n / max_points)))
        t0 = float(seg.t[0])
        return {
            "t": [float(v) for v in (seg.t[::step] - t0)],
            "A": [float(v) for v in arr[0][::step]],
            "B": [float(v) for v in arr[1][::step]],
            "C": [float(v) for v in arr[2][::step]],
            "stride": int(step),
            "fs_effective": float(seg.n and (arr.shape[1] / max((seg.t[-1] - seg.t[0]), 1e-9))),
        }


def series_orders(cfg: AppConfig) -> List[int]:
    return list(range(int(cfg.harmonic.order_min), int(cfg.harmonic.order_max) + 1))
