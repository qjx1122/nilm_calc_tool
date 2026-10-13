"""计算引擎：数据源 → PT/CT 变换 → 环形缓冲 → 按各量独立步长调度计算 → 结果回调。

需求⑥ 的落地方式：调度以**数据时间**（而非墙钟）为基准，每个电气量维护自己的
「上次输出时刻」，当 数据时间 − 上次输出时刻 ≥ step_s 且缓冲已满足 length_s 时触发计算。
效果：谐波窗 0.2s → 每秒出 5 次；电压窗 5s → 每 5 秒出 1 次；两者共用同一份缓冲，互不干扰。
离线回放同理（数据时间快进，输出节奏按数据时间等比）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional

import numpy as np

from .blocks import FrameBuffer, SampleBlock
from .config import AppConfig, QUANTITY_KEYS
from .metrics import MetricsCalculator, MetricsResult
from .realtime_writer import RealtimeCurveWriter
from .events import EventDetector
from .nilm import NilmDetector
from .scaling import scale_block
from .sources import create_source
from .sources.base import DataSource


@dataclass
class EngineState:
    running: bool = False
    finished: bool = False
    source_kind: str = ""
    samples_in: int = 0
    blocks_in: int = 0
    buffer_capacity: int = 0
    buffer_fill: int = 0
    data_t_start: Optional[float] = None
    data_t_end: Optional[float] = None
    data_duration_s: float = 0.0
    ticks: int = 0
    emits: Dict[str, int] = field(default_factory=dict)
    gaps: List[Dict[str, float]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: Optional[float] = None
    last_poll_at: Optional[float] = None
    rate_samples_per_s: float = 0.0
    events_total: int = 0
    events_active: int = 0
    nilm_events_total: int = 0
    nilm_cycles: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self.running, "finished": self.finished, "source_kind": self.source_kind,
            "samples_in": self.samples_in, "blocks_in": self.blocks_in,
            "buffer_capacity": self.buffer_capacity, "buffer_fill": self.buffer_fill,
            "buffer_fill_pct": (100.0 * self.buffer_fill / self.buffer_capacity) if self.buffer_capacity else 0.0,
            "data_t_start": self.data_t_start, "data_t_end": self.data_t_end,
            "data_duration_s": self.data_duration_s, "ticks": self.ticks,
            "emits": dict(self.emits), "gaps": list(self.gaps[-10:]),
            "n_gaps": len(self.gaps), "notes": list(self.notes[-20:]),
            "errors": list(self.errors[-10:]), "started_at": self.started_at,
            "last_poll_at": self.last_poll_at, "rate_samples_per_s": self.rate_samples_per_s,
            "events_total": self.events_total, "events_active": self.events_active,
            "nilm_events_total": self.nilm_events_total, "nilm_cycles": self.nilm_cycles,
        }


class LiveEngine:
    def __init__(self, cfg: AppConfig, source: Optional[DataSource] = None,
                 on_result: Optional[Callable[[MetricsResult], None]] = None,
                 tz_offset_h: Optional[float] = None, output_root: Optional[str] = None):
        self.cfg = cfg.validate()
        fs = self.cfg.sampling.fs
        cap = int(np.ceil(self.cfg.max_window_s * fs * 1.5)) + max(int(self.cfg.source.block_samples), 64)
        self.buffer = FrameBuffer(capacity=max(cap, int(fs)))
        self.calc = MetricsCalculator(self.cfg)
        self.source = source or create_source(self.cfg, tz_offset_h=tz_offset_h)
        self.on_result = on_result
        self.state = EngineState(buffer_capacity=self.buffer.capacity,
                                 source_kind=getattr(self.source, "kind", "unknown"))
        self._last_emit: Dict[str, Optional[float]] = {k: None for k in QUANTITY_KEYS}
        self._last_t: Optional[float] = None
        self._ready: Dict[str, bool] = {k: False for k in QUANTITY_KEYS}
        # 曲线点实时落盘（output.realtime_save）：与趋势历史共用同一提取规则
        self.writer = RealtimeCurveWriter(self.cfg, root=output_root)
        self._output_root = output_root
        # 事件检测（第 9 轮）：每次 compute 后评估；on_event 供 Web 层推送
        self.detector = EventDetector(self.cfg, root=output_root)
        self.on_event: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        # 负荷辨识事件检测（第 12 轮）：逐块摄入时按周波评估；on_nilm_event 供 Web 层推送
        self.nilm = NilmDetector(self.cfg, root=output_root)
        self.on_nilm_event: Optional[Callable[[List[Dict[str, Any]]], None]] = None

    # ---------------- 生命周期 ----------------
    def start(self) -> EngineState:
        self.source.open()
        self.state.running = True
        self.state.started_at = time.time()
        info = self.source.info()
        self.state.notes.append(f"数据源已打开：{info.get('kind')}")
        for n in info.get("notes", []) or []:
            if n not in self.state.notes:
                self.state.notes.append(str(n))
        return self.state

    def stop(self) -> EngineState:
        self.state.running = False
        try:
            self.writer.close()
            self.detector.close()
            self.nilm.close()
        except Exception:
            pass
        try:
            self.source.close()
        except Exception as exc:                       # 关闭失败不影响状态回收
            self.state.errors.append(f"关闭数据源异常：{type(exc).__name__}: {exc}")
        return self.state

    def update_config(self, cfg: AppConfig) -> None:
        """热更新配置（改窗长/PT-CT/谐波口径）：重建计算器与缓冲，保留已入缓冲数据尾部。"""
        new_cfg = cfg.validate()
        keep = self.buffer.snapshot()
        self.cfg = new_cfg
        old_hist = self.calc.history
        self.calc = MetricsCalculator(new_cfg)
        # 趋势历史跨热更新保留：否则勾一下「保存曲线」或改一次窗长，24h 曲线就被清空。
        # 保留参数按新配置生效（history_hours / history_max_points）。
        old_hist.hours = float(new_cfg.output.history_hours)
        old_hist.max_points = int(new_cfg.output.history_max_points)
        self.calc.history = old_hist
        # 实时落盘开关/目录/勾选热更新：关旧句柄，按新配置重建（同一天同一曲线会续写同一文件）
        try:
            self.writer.close()
        except Exception:
            pass
        self.writer = RealtimeCurveWriter(new_cfg, root=self._output_root)
        self.detector.update_config(new_cfg)
        self.nilm.update_config(new_cfg)
        fs = new_cfg.sampling.fs
        cap = int(np.ceil(new_cfg.max_window_s * fs * 1.5)) + max(int(new_cfg.source.block_samples), 64)
        self.buffer = FrameBuffer(capacity=max(cap, int(fs)))
        if keep is not None:
            self.buffer.append(keep.tail(self.buffer.capacity))
        self._last_emit = {k: None for k in QUANTITY_KEYS}
        self._ready = {k: False for k in QUANTITY_KEYS}
        self.state.buffer_capacity = self.buffer.capacity
        self.state.buffer_fill = len(self.buffer)
        self.state.notes.append(f"配置已热更新（{time.strftime('%H:%M:%S')}）：窗长/口径变化后各量重新起算")

    # ---------------- 主循环 ----------------
    def poll_once(self, read_blocks: int = 1) -> Optional[MetricsResult]:
        """读入数据并按调度计算一次；返回本次触发的结果（无量到期则 None）。"""
        if not self.state.running:
            self.start()
        got = False
        for _ in range(max(1, read_blocks)):
            block = self.source.read()
            if block is None:
                if self.source.exhausted:
                    self.state.finished = True
                break
            if block.is_empty():
                continue
            self._ingest(block)
            got = True
        self.state.last_poll_at = time.time()
        self.state.ticks += 1
        if self.state.started_at and time.time() > self.state.started_at:
            self.state.rate_samples_per_s = self.state.samples_in / max(time.time() - self.state.started_at, 1e-6)
        due = self._due_keys()
        if not due:
            return None
        snap_n = int(np.ceil(self.cfg.max_window_s * self.cfg.sampling.fs))
        block = self.buffer.snapshot(max(snap_n, 1))
        if block is None:
            return None
        result = self.calc.compute(block, keys=due, with_history=True)
        for k in due:
            self._last_emit[k] = result.t_ref if np.isfinite(result.t_ref) else self._last_emit[k]
            self.state.emits[k] = self.state.emits.get(k, 0) + 1
        self._write_realtime(result)
        if self.on_result:
            try:
                self.on_result(result)
            except Exception as exc:
                self.state.errors.append(f"结果回调异常：{type(exc).__name__}: {exc}")
        return result

    def run(self, duration_s: Optional[float] = None, max_ticks: Optional[int] = None,
            poll_interval_s: Optional[float] = None) -> Iterator[MetricsResult]:
        """迭代产出结果（离线回放：duration_s=None 直到源读完；实时：按时长/次数限制）。"""
        if not self.state.running:
            self.start()
        interval = poll_interval_s if poll_interval_s is not None else self.cfg.source.poll_interval_s
        t0 = time.time()
        ticks = 0
        idle = 0
        while True:
            if duration_s is not None and (time.time() - t0) >= duration_s:
                break
            if max_ticks is not None and ticks >= max_ticks:
                break
            res = self.poll_once()
            ticks += 1
            if res is not None:
                idle = 0
                yield res
            else:
                idle += 1
                if self.state.finished and not self._due_keys(force=False):
                    # 源已读完且无待触发量 → 收尾前把剩余各量强制算一次
                    final = self.flush_all()
                    if final is not None:
                        yield final
                    break
                if idle > 0 and interval > 0 and not self.source.exhausted:
                    time.sleep(min(interval, 0.5))
        self.stop()

    def flush_all(self) -> Optional[MetricsResult]:
        """强制计算全部量一次（离线文件读完收尾 / UI 首次加载）。"""
        snap_n = int(np.ceil(self.cfg.max_window_s * self.cfg.sampling.fs))
        block = self.buffer.snapshot(max(snap_n, 1))
        if block is None:
            return None
        result = self.calc.compute(block, keys=list(QUANTITY_KEYS), with_history=True)
        for k in QUANTITY_KEYS:
            self._last_emit[k] = result.t_ref
            self.state.emits[k] = self.state.emits.get(k, 0) + 1
        self._write_realtime(result)
        if self.on_result:
            self.on_result(result)
        return result

    def snapshot_full(self) -> Optional[MetricsResult]:
        """不推进数据、只按当前缓冲算全部量（UI 刷新用；不写 emits 计数）。"""
        snap_n = int(np.ceil(self.cfg.max_window_s * self.cfg.sampling.fs))
        block = self.buffer.snapshot(max(snap_n, 1))
        if block is None:
            return None
        return self.calc.compute(block, keys=list(QUANTITY_KEYS), with_history=False)

    # ---------------- 内部 ----------------
    def _write_realtime(self, result: MetricsResult) -> None:
        try:
            self.writer.write(result)
        except Exception as exc:                       # 落盘失败只记错误，不中断计算
            msg = f"实时落盘异常：{type(exc).__name__}: {exc}"
            if msg not in self.state.errors:
                self.state.errors.append(msg)
        self._detect_events(result)

    def _detect_events(self, result: MetricsResult) -> None:
        try:
            changed = self.detector.process(result)
            summ = self.detector.summary()
            self.state.events_total = int(summ["total"])
            self.state.events_active = int(summ["active"])
            if changed and self.on_event is not None:
                self.on_event(changed)
        except Exception as exc:
            msg = f"事件检测异常：{type(exc).__name__}: {exc}"
            if msg not in self.state.errors:
                self.state.errors.append(msg)

    def _detect_nilm(self, scaled: SampleBlock) -> None:
        try:
            new = self.nilm.ingest(scaled)
            self.state.nilm_events_total = len(self.nilm._log)
            self.state.nilm_cycles = int(self.nilm.cycles_total)
            if new and self.on_nilm_event is not None:
                self.on_nilm_event(new)
        except Exception as exc:
            msg = f"负荷辨识检测异常：{type(exc).__name__}: {exc}"
            if msg not in self.state.errors:
                self.state.errors.append(msg)

    def _ingest(self, block: SampleBlock) -> None:
        scaled = scale_block(block, self.cfg.transform)
        # 数据连续性检查（时间跳变 → 记为 gap，对应数据质量规则 Q-01/Q-02）
        if self._last_t is not None and scaled.n:
            dt = scaled.t_start - self._last_t
            expected = 1.0 / self.cfg.sampling.fs
            if dt > 1.5 * expected:
                self.state.gaps.append({"t": float(self._last_t), "gap_s": float(dt),
                                        "missing_samples": float(dt / expected - 1)})
                self.state.notes.append(
                    f"⚠️ 数据时间跳变 {dt*1000:.1f}ms（>1.5 个采样间隔）@ t={self._last_t:.3f}："
                    f"疑似丢点/断采，跨该点的窗结果需复核")
                self.state.gaps = self.state.gaps[-50:]
                self.state.notes = self.state.notes[-20:]
        self.buffer.append(scaled)
        self._detect_nilm(scaled)
        if scaled.n:
            self._last_t = float(scaled.t[-1])
            self.state.data_t_start = self.state.data_t_start or float(scaled.t[0])
            self.state.data_t_end = float(scaled.t[-1])
        self.state.samples_in += scaled.n
        self.state.blocks_in += 1
        self.state.buffer_fill = len(self.buffer)
        self.state.data_duration_s = self.state.samples_in / self.cfg.sampling.fs

    def _due_keys(self, force: bool = False) -> List[str]:
        """哪些电气量到期该算了（需求⑥：各量独立窗长与步长）。"""
        fs = self.cfg.sampling.fs
        t_now = self.state.data_t_end
        if t_now is None:
            return []
        due: List[str] = []
        filled = len(self.buffer)
        for key in QUANTITY_KEYS:
            spec = self.cfg.windows.get(key)
            if spec is None:
                continue
            need = int(np.ceil(spec.length_s * fs))
            if filled < need:                       # 缓冲还没攒够这个量的窗长
                continue
            last = self._last_emit.get(key)
            if last is None:                        # 首次：攒够即算
                self._ready[key] = True
                due.append(key)
                continue
            # 容差取 1/4 个采样间隔：时间戳是 epoch 秒量级（~1.8e9），double 在该量级的
            # 绝对精度约 2.4e-7s，若用 1e-9 硬比较会因浮点抖动漏拍（实测 5s 数据少出 3 次）
            tol = max(1e-9, 0.25 / fs)
            if (t_now - last) >= (spec.effective_step_s() - tol):
                due.append(key)
        return due

    # ---------------- 诊断 ----------------
    def info(self) -> Dict[str, Any]:
        src_info: Dict[str, Any] = {}
        try:
            src_info = self.source.info()
        except Exception as exc:
            src_info = {"error": f"{type(exc).__name__}: {exc}"}
        return {
            "state": self.state.to_dict(),
            "source": src_info,
            "config": self.cfg.to_dict(),
            "windows": {k: {"length_s": w.length_s, "step_s": w.effective_step_s(), "policy": w.policy,
                            "window_fn": w.window_fn, "remove_dc": w.remove_dc}
                        for k, w in self.cfg.windows.items()},
            "last_emit": dict(self._last_emit),
            "realtime": self.writer.info(),
            "events": self.detector.summary(),
            "nilm": self.nilm.summary(),
        }
