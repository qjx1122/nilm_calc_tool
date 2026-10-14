"""事件检测（第 9 轮）：由各量计算结果判定 6 类事件，带起止时刻、峰值、复归滞回与落盘。

事件类型（type → 中文名）
  fund_phasor   基波相量超限：任一相 U1 高于 u_nom×u1_high_pct% / 低于 u1_low_pct%，或 I1 高于 i1_high
  harm_phasor   谐波相量超限：任一相任一次 HR_h 超过 hr_*_limit_pct，或 THD 超过 thd_*_limit_pct
  interharm     间谐波相量超限：任一相任一间谐波组 IHG_h/X1 超过 ih_*_limit_pct
  freq          频率超限：f_used 不在 [f_low, f_high]
  rocof         频率变化率超限：|Δf/Δt|（相邻两次 fundamental 结果）超过 rocof_limit
  power_osc     功率振荡：最近 osc_window_s 内 P 总去趋势谱在 [osc_f_min, osc_f_max] 的主导分量峰峰值
                 ≥ osc_limit_pct%·|P̄| 且 ≥ osc_min_w

生命周期：同一 (type, subject) 只有一个活动事件；判据满足 → 开始（记 start_t / value_start / limit），
后续每次评估更新 value_peak；值回落到 limit×hysteresis 以内（低限事件为 limit/hysteresis 以上）→ 结束
（记 end_t / duration_s）。时间全部用**数据时间**（结果 t_ref），离线回放同样成立。
落盘：events_dir/events_<数据日期>.csv，开始与结束各写一行（status=start/end），UTF-8-BOM，每行 flush。
"""
from __future__ import annotations

import csv
import math
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

from .config import AppConfig, EventConfig
from .timefmt import fmt_local, local_day
from .metrics import MetricsResult, QuantityResult, _pick

EVENT_TYPES: Dict[str, str] = {
    "fund_phasor": "基波相量超限",
    "harm_phasor": "谐波相量超限",
    "interharm": "间谐波相量超限",
    "freq": "频率超限",
    "rocof": "频率变化率超限",
    "power_osc": "功率振荡",
}
PHASES = ("A", "B", "C")
_CSV_FIELDS = ("id", "status", "type", "type_name", "subject", "start_t", "start_time", "end_t", "end_time",
               "duration_s", "value_start", "value_peak", "limit", "unit", "direction", "detail")


@dataclass
class Event:
    id: int
    type: str
    subject: str                   # 如 "U1-A" / "HR_U-A-h5" / "IH_I-B-g6" / "f" / "rocof" / "P"
    start_t: float
    value_start: float
    limit: float
    unit: str
    direction: str                 # "high" 越上限 / "low" 越下限
    detail: str = ""
    band: float = 0.0              # 复归滞回带（绝对量）：high 事件需 value ≤ limit−band，low 事件需 value ≥ limit+band
    value_peak: float = 0.0
    peak_t: float = 0.0
    end_t: Optional[float] = None
    updates: int = 0

    @property
    def active(self) -> bool:
        return self.end_t is None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type_name"] = EVENT_TYPES.get(self.type, self.type)
        d["active"] = self.active
        d["status"] = "active" if self.active else "ended"
        d["duration_s"] = (None if self.end_t is None else float(self.end_t - self.start_t))
        return d


def _ts(t: Optional[float]) -> str:
    if t is None or not math.isfinite(t):
        return ""
    return fmt_local(t)


class EventWriter:
    """events_<数据日期>.csv 追加写（每行 flush）。"""

    def __init__(self, cfg: EventConfig, root: Optional[str] = None):
        self.cfg = cfg
        env_dir = os.environ.get("ELEC_TOOL_EVENTS_DIR")
        d = env_dir or cfg.events_dir
        self.dir = d if os.path.isabs(d) else os.path.join(root or os.getcwd(), d)
        self._fh = None
        self._path: Optional[str] = None
        self.rows_written = 0
        self.errors: List[str] = []

    def _open_for(self, t: float) -> None:
        day = local_day(t)
        path = os.path.join(self.dir, f"events_{day}.csv")
        if self._fh is not None and self._path == path:
            return
        self.close()
        os.makedirs(self.dir, exist_ok=True)
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self._fh = open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="")
        self._path = path
        if new:
            csv.writer(self._fh).writerow(_CSV_FIELDS)
            self._fh.flush()

    def write(self, ev: Event, status: str) -> None:
        if not self.cfg.save:
            return
        try:
            self._open_for(ev.start_t)
            d = ev.to_dict()
            row = [d["id"], status, d["type"], d["type_name"], d["subject"],
                   f"{d['start_t']:.3f}", _ts(d["start_t"]),
                   ("" if d["end_t"] is None else f"{d['end_t']:.3f}"), _ts(d["end_t"]),
                   ("" if d["duration_s"] is None else f"{d['duration_s']:.3f}"),
                   f"{d['value_start']:.6g}", f"{d['value_peak']:.6g}", f"{d['limit']:.6g}", d["unit"], d["direction"], d["detail"]]
            csv.writer(self._fh).writerow(row)
            self._fh.flush()
            self.rows_written += 1
        except Exception as exc:                     # 落盘失败不影响检测
            msg = f"事件落盘失败：{type(exc).__name__}: {exc}"
            if msg not in self.errors:
                self.errors.append(msg)

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None
        self._path = None

    def info(self) -> Dict[str, Any]:
        return {"enabled": bool(self.cfg.save), "dir": self.dir, "current_file": self._path,
                "rows_written": self.rows_written, "errors": list(self.errors)}


class EventDetector:
    """把 MetricsResult 流转换为事件流。线程安全（引擎线程 process / Web 线程 list）。"""

    def __init__(self, cfg: AppConfig, root: Optional[str] = None):
        self.cfg = cfg
        self.ecfg: EventConfig = cfg.events
        self._lock = threading.Lock()
        self._active: Dict[Tuple[str, str], Event] = {}
        self._log: Deque[Event] = deque(maxlen=int(self.ecfg.max_log))
        self._next_id = 1
        self._freq_hist: Deque[Tuple[float, float]] = deque(maxlen=8)
        self._p_hist: Deque[Tuple[float, float]] = deque(maxlen=4096)
        self._root_dir = root
        self.writer = EventWriter(self.ecfg, root=root)
        self.counts: Dict[str, int] = {k: 0 for k in EVENT_TYPES}
        self.last_eval: Dict[str, Any] = {}
        self.osc_info: Dict[str, Any] = {}

    # ---------- 对外 ----------
    def update_config(self, cfg: AppConfig) -> None:
        with self._lock:
            self.cfg = cfg
            self.ecfg = cfg.events
            self.writer.close()
            self.writer = EventWriter(self.ecfg, root=self._root_dir)
            if self._log.maxlen != int(self.ecfg.max_log):
                self._log = deque(self._log, maxlen=int(self.ecfg.max_log))

    def list(self, active_only: bool = False, limit: int = 200, types: Optional[List[str]] = None,
             since_id: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            evs = list(self._active.values()) if active_only else list(self._log)
        if types:
            evs = [e for e in evs if e.type in types]
        if since_id:
            evs = [e for e in evs if e.id > since_id]
        evs.sort(key=lambda e: (e.active, e.start_t), reverse=True)
        return [e.to_dict() for e in evs[: max(1, int(limit))]]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            active = list(self._active.values())
            total = len(self._log)
            counts = dict(self.counts)
        notes: List[str] = []
        if not self.cfg.sampling.adaptive_freq:
            notes.append("sampling.adaptive_freq=false：频率恒按额定值，频率/频率变化率事件不会触发，"
                         "且频率偏移时谐波/间谐波会因泄漏虚高——请在「数据源与控制」开启频率自适应")
        ku, ki = self.limit_scale()
        return {"enabled": bool(self.ecfg.enabled), "active": len(active), "total": total, "counts": counts,
                "notes": notes, "limit_scale": {"u": ku, "i": ki},
                "effective_limits": {"u1_high_v": self.ecfg.u_nom * ku * self.ecfg.u1_high_pct / 100.0,
                                     "u1_low_v": self.ecfg.u_nom * ku * self.ecfg.u1_low_pct / 100.0,
                                     "i1_high_a": self.ecfg.i1_high * ki},
                "active_by_type": {k: sum(1 for e in active if e.type == k) for k in EVENT_TYPES},
                "types": EVENT_TYPES, "writer": self.writer.info(), "osc": dict(self.osc_info),
                "last_eval": dict(self.last_eval)}

    def clear(self) -> int:
        with self._lock:
            n = len(self._log)
            self._log.clear()
            self._active.clear()
            self.counts = {k: 0 for k in EVENT_TYPES}
            self._freq_hist.clear()
            self._p_hist.clear()
        return n

    def close(self) -> None:
        self.writer.close()

    def process(self, result: MetricsResult) -> List[Dict[str, Any]]:
        """评估一次结果；返回本次**新开始或刚结束**的事件（供推送）。"""
        if not self.ecfg.enabled:
            return []
        t = result.t_ref
        if not isinstance(t, (int, float)) or not math.isfinite(float(t)):
            return []
        changed: List[Event] = []
        with self._lock:
            qs = result.quantities
            if "fundamental" in qs and qs["fundamental"].ok:
                self._eval_fundamental(qs["fundamental"], float(result.f_used), t, changed)
            if "harmonic" in qs and qs["harmonic"].ok:
                self._eval_harmonic(qs["harmonic"], t, changed)
            if "interharmonic" in qs and qs["interharmonic"].ok:
                self._eval_interharmonic(qs["interharmonic"], t, changed)
            if "power" in qs and qs["power"].ok:
                self._eval_power_osc(qs["power"], t, changed)
            self.last_eval = {"t": float(t), "keys": list(qs.keys())}
        return [e.to_dict() for e in changed]

    def limit_scale(self) -> Tuple[float, float]:
        """基波阈值的折算系数 (k_u, k_i)：limits_secondary 且启用 PT/CT 变换 → (PT, CT)，否则 (1, 1)。"""
        tr = self.cfg.transform
        if self.ecfg.limits_secondary and tr.enabled:
            return float(tr.pt_ratio), float(tr.ct_ratio)
        return 1.0, 1.0

    # ---------- 生命周期 ----------
    def _hit(self, typ: str, subject: str, value: float, limit: float, unit: str, direction: str,
             t: float, changed: List[Event], detail: str = "", band: Optional[float] = None) -> None:
        key = (typ, subject)
        ev = self._active.get(key)
        if ev is None:
            if band is None:
                band = (1.0 - float(self.ecfg.hysteresis)) * abs(float(limit))
            ev = Event(id=self._next_id, type=typ, subject=subject, start_t=float(t), value_start=float(value),
                       limit=float(limit), unit=unit, direction=direction, detail=detail, band=float(band),
                       value_peak=float(value), peak_t=float(t))
            self._next_id += 1
            self._active[key] = ev
            self._log.append(ev)
            self.counts[typ] = self.counts.get(typ, 0) + 1
            self.writer.write(ev, "start")
            changed.append(ev)
        else:
            ev.updates += 1
            if (direction == "high" and value > ev.value_peak) or (direction == "low" and value < ev.value_peak):
                ev.value_peak = float(value)
                ev.peak_t = float(t)
            if detail:
                ev.detail = detail

    def _release(self, typ: str, subject: str, value: Optional[float], t: float, changed: List[Event],
                 limit: Optional[float] = None) -> None:
        """判据未满足：若活动事件存在且已回到滞回带以内则结束。

        limit＝**当前**阈值（用户热改阈值后以新阈值判复归，否则旧事件永远挂着）；None 时沿用事件记录的阈值。"""
        key = (typ, subject)
        ev = self._active.get(key)
        if ev is None:
            return
        lim = ev.limit if limit is None else float(limit)
        if value is None:
            back = True
        elif ev.direction == "high":
            back = value <= lim - ev.band
        else:
            back = value >= lim + ev.band
        if back:
            ev.end_t = float(t)
            del self._active[key]
            self.writer.write(ev, "end")
            changed.append(ev)

    def _check(self, typ: str, subject: str, value: Optional[float], limit: float, unit: str,
               direction: str, t: float, changed: List[Event], detail: str = "",
               band: Optional[float] = None) -> None:
        if value is None or not math.isfinite(value):
            return
        over = value > limit if direction == "high" else value < limit
        if over:
            self._hit(typ, subject, value, limit, unit, direction, t, changed, detail, band)
        else:
            self._release(typ, subject, value, t, changed, limit)

    def _release_missing(self, typ: str, present: set, t: float, changed: List[Event]) -> None:
        """本轮评估过的类型里，未再出现的 subject 视为复归。"""
        for key in [k for k in self._active if k[0] == typ and k[1] not in present]:
            self._release(typ, key[1], None, t, changed)

    # ---------- 各类判据 ----------
    def _eval_fundamental(self, q: QuantityResult, f_used: float, t: float, changed: List[Event]) -> None:
        c = self.ecfg
        present = set()
        ku, ki = self.limit_scale()
        u_nom = c.u_nom * ku
        i_hi = c.i1_high * ki
        u_hi = u_nom * c.u1_high_pct / 100.0
        u_lo = u_nom * c.u1_low_pct / 100.0
        side = "（二次值×PT/CT 折算）" if ku != 1.0 or ki != 1.0 else ""
        for p in PHASES:
            u1 = _pick(q, "u1_rms", p)
            i1 = _pick(q, "i1_rms", p)
            if u1 is not None:
                present.update({f"U1-{p}-high", f"U1-{p}-low"})
                self._check("fund_phasor", f"U1-{p}-high", u1, u_hi, "V", "high", t, changed,
                            f"{p} 相基波电压 {u1:.3f} V > {c.u1_high_pct:g}%×{u_nom:.4g} V{side}")
                self._check("fund_phasor", f"U1-{p}-low", u1, u_lo, "V", "low", t, changed,
                            f"{p} 相基波电压 {u1:.3f} V < {c.u1_low_pct:g}%×{u_nom:.4g} V{side}")
            if i1 is not None:
                present.add(f"I1-{p}-high")
                self._check("fund_phasor", f"I1-{p}-high", i1, i_hi, "A", "high", t, changed,
                            f"{p} 相基波电流 {i1:.3f} A > {i_hi:.4g} A{side}")
        # 频率 / ROCOF
        f = _pick(q, "freq_hz")
        if f is None:
            f = f_used
        if f is not None and math.isfinite(f):
            # 频率的滞回带按「上下限带宽」而不是按 50 Hz 的百分比（否则 50.5×0.95=47.98 永不复归）
            fband = (1.0 - float(c.hysteresis)) * (c.f_high - c.f_low)
            self._check("freq", "f-high", f, c.f_high, "Hz", "high", t, changed, f"频率 {f:.4f} Hz > {c.f_high:g} Hz", fband)
            self._check("freq", "f-low", f, c.f_low, "Hz", "low", t, changed, f"频率 {f:.4f} Hz < {c.f_low:g} Hz", fband)
            if self._freq_hist and t > self._freq_hist[-1][0]:
                t0, f0 = self._freq_hist[-1]
                dt = t - t0
                if dt > 0:
                    rocof = (f - f0) / dt
                    self._check("rocof", "rocof", abs(rocof), c.rocof_limit, "Hz/s", "high", t, changed,
                                f"df/dt = {rocof:+.4f} Hz/s（{f0:.4f}→{f:.4f} Hz / {dt:.3f} s）")
                    self.last_eval["rocof"] = rocof
            if not self._freq_hist or t != self._freq_hist[-1][0]:
                self._freq_hist.append((float(t), float(f)))

    def _eval_harmonic(self, q: QuantityResult, t: float, changed: List[Event]) -> None:
        c = self.ecfg
        present = set()
        for kind, lim_hr, lim_thd, unit_key in (("U", c.hr_u_limit_pct, c.thd_u_limit_pct, "u"),
                                                 ("I", c.hr_i_limit_pct, c.thd_i_limit_pct, "i")):
            per = (q.values.get(unit_key) or {}) if q.ok else {}
            for p in PHASES:
                thd = _pick(q, f"thd_{unit_key}_pct", p)
                subj = f"THD_{kind}-{p}"
                present.add(subj)
                self._check("harm_phasor", subj, thd, lim_thd, "%", "high", t, changed,
                            f"{p} 相 THD_{kind} {thd if thd is None else round(thd, 3)}% > {lim_thd:g}%")
                hr = ((per.get(p) or {}).get("hr_pct") or {}) if isinstance(per, dict) else {}
                for h, v in hr.items():
                    if isinstance(v, (int, float)) and math.isfinite(float(v)):
                        subj = f"HR_{kind}-{p}-h{h}"
                        present.add(subj)
                        self._check("harm_phasor", subj, float(v), lim_hr, "%", "high", t, changed,
                                    f"{p} 相 {h} 次谐波 {kind} 含有率 {float(v):.3f}% > {lim_hr:g}%")
        self._release_missing("harm_phasor", present, t, changed)

    def _eval_interharmonic(self, q: QuantityResult, t: float, changed: List[Event]) -> None:
        c = self.ecfg
        present = set()
        for kind, lim, key in (("U", c.ih_u_limit_pct, "top_u"), ("I", c.ih_i_limit_pct, "top_i")):
            top = (q.values.get(key) or {}) if q.ok else {}
            for p in PHASES:
                for g in (top.get(p) or []):
                    v = g.get("pct")
                    if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
                        continue
                    subj = f"IH_{kind}-{p}-g{g.get('h')}"
                    present.add(subj)
                    self._check("interharm", subj, float(v), lim, "%", "high", t, changed,
                                f"{p} 相第 {g.get('h')} 间谐波组（{g.get('f_lo'):.0f}~{g.get('f_hi'):.0f} Hz，主导 "
                                f"{(g.get('dom_freq_hz') or 0):.1f} Hz）{float(v):.3f}% > {lim:g}%")
        self._release_missing("interharm", present, t, changed)

    def _eval_power_osc(self, q: QuantityResult, t: float, changed: List[Event]) -> None:
        c = self.ecfg
        p = _pick(q, "p_total")
        if p is None:
            return
        if self._p_hist and t <= self._p_hist[-1][0]:
            return
        self._p_hist.append((float(t), float(p)))
        horizon = t - c.osc_window_s
        while self._p_hist and self._p_hist[0][0] < horizon:
            self._p_hist.popleft()
        n = len(self._p_hist)
        info: Dict[str, Any] = {"points": n, "window_s": c.osc_window_s}
        if n < c.osc_min_points:
            info["note"] = f"点数 {n} < {c.osc_min_points}，暂不评估"
            self.osc_info = info
            return
        ts = np.array([x[0] for x in self._p_hist]); ps = np.array([x[1] for x in self._p_hist])
        span = float(ts[-1] - ts[0])
        if span < 0.5 * c.osc_window_s:
            info["note"] = f"时间跨度 {span:.1f}s 不足窗长一半"
            self.osc_info = info
            return
        dt = float(np.median(np.diff(ts)))
        if dt <= 0:
            return
        m = int(span / dt) + 1
        tu = ts[0] + np.arange(m) * dt
        pu = np.interp(tu, ts, ps)
        mean_p = float(np.mean(pu))
        # 去线性趋势 + hann 窗 → 单边幅值谱（相干增益校正）
        x = pu - np.polyval(np.polyfit(np.arange(m), pu, 1), np.arange(m))
        w = np.hanning(m)
        X = np.fft.rfft(x * w)
        amp = 2.0 * np.abs(X) / max(float(w.sum()), 1e-12)          # 正弦幅值（峰值）
        fr = np.fft.rfftfreq(m, d=dt)
        f_nyq = 0.5 / dt
        f_hi = min(c.osc_f_max, f_nyq)
        band = (fr >= c.osc_f_min) & (fr <= f_hi) & (fr > 0)
        info.update({"dt_s": dt, "f_nyquist": f_nyq, "mean_p": mean_p})
        if not np.any(band):
            info["note"] = f"评估频带 [{c.osc_f_min},{f_hi:.3f}] Hz 内无谱线（P 步长 {dt:.2f}s → Nyquist {f_nyq:.3f} Hz）"
            self.osc_info = info
            return
        k = int(np.argmax(np.where(band, amp, 0.0)))
        a_pp = float(2.0 * amp[k])                                      # 峰峰值
        pct = float(100.0 * a_pp / abs(mean_p)) if abs(mean_p) > 1e-9 else float("inf")
        info.update({"dom_freq_hz": float(fr[k]), "amp_pp": a_pp, "amp_pp_pct": pct})
        self.osc_info = info
        over = (pct >= c.osc_limit_pct) and (a_pp >= c.osc_min_w)
        detail = f"P 振荡 {fr[k]:.3f} Hz，峰峰 {a_pp:.4g} W（{pct:.2f}% of |P̄|={abs(mean_p):.4g} W）"
        if over:
            self._hit("power_osc", "P", pct, c.osc_limit_pct, "%", "high", t, changed, detail)
        else:
            self._release("power_osc", "P", pct, t, changed, c.osc_limit_pct)
