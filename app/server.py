"""Web 服务：导航条 + 各电气量子界面 + 实时推送（需求①②③④）。

架构（物理隔离）：
    浏览器（app/static，原生 JS + Canvas，无外部 CDN 依赖）
        ↕ REST（配置/控制/历史/导出/自检） + WebSocket（结果推送）
    FastAPI 服务（本文件，只做编排与序列化，不含算法）
        ↕
    elec_tool（算法核心：引擎/数据源/分析，仅依赖 numpy）

启动：python cli.py serve --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import re
import threading
import platform
import sys
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

log = logging.getLogger("elec_tool.server")

from contextlib import asynccontextmanager

import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from elec_tool import __version__
from elec_tool.config import (AppConfig, ConfigError, parse_time_text, CURVE_KEYS, QUANTITY_KEYS, SourceConfig, WindowSpec,
                              load_or_default)
from elec_tool.engine import LiveEngine
from elec_tool.pace import PaceClock
from elec_tool.timefmt import fmt_local
from elec_tool.metrics import MetricsResult
from elec_tool.resample import METHODS as RESAMPLE_METHODS, ResampleError, ResampleJob, resample_csv
from elec_tool.resample import output_name as resample_output_name
from elec_tool.selftest import run_selftest, summarize

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATIC_DIR = os.path.join(HERE, "static")
DEFAULT_CONFIG_PATH = os.path.join(ROOT, "configs", "default.json")
# 出厂模板 configs/default.json 必须保持干净（入库、可回溯）；用户在界面里改的
# 配置与数据源选择落到 configs/runtime.json（gitignore），下次启动优先加载它。
RUNTIME_CONFIG_PATH = os.path.join(ROOT, "configs", "runtime.json")
BRANCH_CONFIG_PATH = os.path.join(ROOT, "configs", "branch.json")            # 分路侧出厂模板（可不存在）
BRANCH_RUNTIME_CONFIG_PATH = os.path.join(ROOT, "configs", "branch_runtime.json")
SIDES = ("bus", "branch")
SIDE_LABELS = {"bus": "总线侧", "branch": "分路侧设备"}
SIDE_SOURCE_ID = {"bus": 0, "branch": 1}      # v0.17：落盘/导出 CSV 的 source_id 列


def _resolve_cfg_paths() -> Tuple[str, str]:
    """返回 (加载路径, 持久化路径)。

    显式指定 ELEC_TOOL_CONFIG_PATH 时两者相同（用户自己负责这个文件）；
    否则加载 runtime.json（若存在）或 default.json，但**只往 runtime.json 写**，
    保证入库的出厂模板 configs/default.json 永远不被界面操作污染。
    """
    env_path = os.environ.get("ELEC_TOOL_CONFIG_PATH", "").strip()
    if env_path:
        return env_path, env_path
    load_path = RUNTIME_CONFIG_PATH if os.path.exists(RUNTIME_CONFIG_PATH) else DEFAULT_CONFIG_PATH
    return load_path, RUNTIME_CONFIG_PATH




# ------------------------------------------------------------------ 引擎运行器

def _safe(fn, default):
    """状态汇总里的单项失败不应拖垮整个 /api/state（F-41：界面靠它翻到终态）。"""
    try:
        return fn()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"} if isinstance(default, dict) else default


class EngineRunner:
    """在后台线程跑引擎，把结果广播给 WebSocket 客户端。"""

    def __init__(self, maxlen: int = 2000, side: str = "bus"):
        self.side = side
        self.lock = threading.RLock()
        self.engine: Optional[LiveEngine] = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()      # set＝暂停（仅离线文件源；每轮运行一个新对象）
        self._thread_done = False                 # 引擎线程已走完（终态广播时线程对象可能仍 alive）
        self.paused_at: Optional[float] = None
        self.paused_total_s = 0.0
        self.latest: Optional[MetricsResult] = None
        self.latest_merged: Optional[Dict[str, Any]] = None   # 各量最近一次结果的并集（/api/result?full=false）
        self.latest_full: Optional[MetricsResult] = None
        self.store: Deque[MetricsResult] = deque(maxlen=maxlen)
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.clients: Set[asyncio.Queue] = set()
        self.started_at: Optional[float] = None
        self.error: Optional[str] = None
        self.loaded_last: Optional[Dict[str, Any]] = None     # v0.18：最近一次「加载上次播放数据」的摘要（state 里带出）
        self.cfg_path: str = DEFAULT_CONFIG_PATH        # 启动时加载哪个文件
        self.persist_path: str = RUNTIME_CONFIG_PATH    # 界面改动写到哪个文件
        self._play_user: Optional[Tuple[str, str, str]] = None   # 本次运行用户自己的 (play_start_mode, play_start_value, play_end_time)
        self._cfg_view: Optional[AppConfig] = None               # cfg 属性的缓存视图（引擎配置 + 用户播放字段）

    # ---------- 配置 ----------
    @property
    def cfg(self) -> AppConfig:
        with self.lock:
            if self.engine is not None:
                if self._play_user is None:
                    return self.engine.cfg
                # 公共时间段联动启动时，引擎配置里的播放起点/终点是**本次运行专用**的自动值；
                # 对外（/api/config、持久化、下次启动）一律呈现用户自己的设置，自动值绝不外泄（v0.15.3）
                if self._cfg_view is None:
                    c = AppConfig.from_dict(self.engine.cfg.to_dict())
                    c.source.play_start_mode, c.source.play_start_value, c.source.play_end_time = self._play_user
                    self._cfg_view = c
                return self._cfg_view
        return load_or_default(self.cfg_path)

    def set_cfg(self, cfg: AppConfig) -> None:
        cfg.output.source_id = SIDE_SOURCE_ID[self.side]        # v0.17：数据来源号按侧别强制（0 总线 / 1 分路）
        _share_output_dirs(cfg, self.side)
        cfg.validate()
        with self.lock:
            self._cfg_view = None
            if self.engine is not None:
                if self._play_user is not None:
                    # 热更新不得把用户的播放起点/终点覆盖到正在按公共时间段播放的引擎上（这些字段只在开源时生效）
                    self._play_user = (cfg.source.play_start_mode, str(cfg.source.play_start_value), str(cfg.source.play_end_time))
                    ec = self.engine.cfg.source
                    cfg = AppConfig.from_dict(cfg.to_dict())
                    cfg.source.play_start_mode, cfg.source.play_start_value, cfg.source.play_end_time = ec.play_start_mode, ec.play_start_value, ec.play_end_time
                # 运行中或已结束（离线文件读完）都走热更新：保留趋势历史与最近结果。
                # 旧写法对「已结束」的引擎整个重建 → 勾一下「保存曲线」24h 曲线和结果全部清空。
                self.engine.update_config(cfg)
            else:
                self.engine = LiveEngine(cfg, output_root=ROOT)
                self.engine.on_event = self._on_event
                self.engine.on_nilm_event = self._on_nilm_event
                self.latest = None

        # v0.17.2：总线侧改了落盘/导出目录 → 分路侧跟着改（两侧共用同一文件）
        if self.side == "bus" and "RUNNERS" in globals():
            br = RUNNERS.get("branch")
            if br is not None and br.cfg is not None and (
                    br.cfg.output.realtime_dir != cfg.output.realtime_dir or br.cfg.events.events_dir != cfg.events.events_dir
                    or br.cfg.nilm.nilm_dir != cfg.nilm.nilm_dir or br.cfg.output.export_dir != cfg.output.export_dir):
                try:
                    br.set_cfg(AppConfig.from_dict(br.cfg.to_dict()))
                except Exception as exc:
                    log.warning("分路侧输出目录同步失败：%s", exc)

    # ---------- 事件 ----------
    def _on_event(self, changed: List[Dict[str, Any]]) -> None:
        """引擎线程回调：新开始 / 刚结束的事件 → WS 推送。"""
        self.broadcast({"type": "event", "data": changed})

    def events(self, active: bool = False, limit: int = 200, types: Optional[List[str]] = None,
               since_id: int = 0) -> Dict[str, Any]:
        with self.lock:
            eng = self.engine
        if eng is None:
            from elec_tool.events import EVENT_TYPES
            return {"ok": True, "events": [], "summary": {"enabled": True, "active": 0, "total": 0,
                                                          "counts": {k: 0 for k in EVENT_TYPES},
                                                          "types": EVENT_TYPES, "notes": ["引擎尚未启动"]}}
        return {"ok": True, "events": eng.detector.list(active_only=active, limit=limit, types=types, since_id=since_id),
                "summary": eng.detector.summary()}

    # ---------- 最后一次电气量结果落盘（v0.20）：两侧共用 output/last_result.json，按 source_id 分键 ----------
    LAST_RESULT_FILE: Optional[str] = None       # 测试可覆盖；默认 env ELEC_TOOL_LAST_RESULT_FILE 或 output/last_result.json

    def _last_result_path(self) -> str:
        return self.LAST_RESULT_FILE or os.environ.get("ELEC_TOOL_LAST_RESULT_FILE") or os.path.join(ROOT, "output", "last_result.json")

    def persist_last_result(self) -> bool:
        """把 latest_merged（各量最近一次结果的并集，含频谱等 series）写入 last_result.json 的本侧键。
        停止 / 播完 / 异常退出 / 运行中每 ≥5 s 调用一次；失败只记日志。"""
        from elec_tool.filelock import SHARED_FILE_LOCK
        with self.lock:
            d = self.latest_merged
            if not d:
                return False
            src = getattr(self.engine.cfg.source, "path", "") if self.engine is not None else ""
            kind = getattr(self.engine.cfg.source, "kind", "") if self.engine is not None else ""
        sid = str(SIDE_SOURCE_ID[self.side])
        entry = {"side": self.side, "source_id": int(sid), "saved_at": time.time(), "saved_at_local": fmt_local(time.time()),
                 "source_kind": kind, "source_path": src, "t_ref": d.get("t_ref"), "result": d}
        path = self._last_result_path()
        try:
            with SHARED_FILE_LOCK:
                data: Dict[str, Any] = {}
                if os.path.isfile(path):
                    try:
                        with open(path, "r", encoding="utf-8") as fh:
                            data = json.load(fh) or {}
                    except Exception:
                        data = {}
                if not isinstance(data, dict):
                    data = {}
                data[sid] = entry
                data["_note"] = "两侧共用：键 0＝总线侧、1＝分路侧（source_id）；由软件自动维护，重启时读回各子界面的最新电气量"
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False)
                os.replace(tmp, path)
            self._last_persist_at = time.time()
            return True
        except Exception as exc:
            log.warning("last_result.json 写入失败：%s", exc)
            return False

    def read_last_result(self) -> Optional[Dict[str, Any]]:
        from elec_tool.filelock import SHARED_FILE_LOCK
        path = self._last_result_path()
        if not os.path.isfile(path):
            return None
        try:
            with SHARED_FILE_LOCK:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh) or {}
            ent = data.get(str(SIDE_SOURCE_ID[self.side])) if isinstance(data, dict) else None
            return ent if isinstance(ent, dict) and isinstance(ent.get("result"), dict) else None
        except Exception as exc:
            log.warning("last_result.json 读取失败：%s", exc)
            return None

    def load_last(self, hours: Optional[float] = None, curves: bool = True, events: bool = True, nilm: bool = True,
                  result: bool = True) -> Dict[str, Any]:
        """v0.18：不播放时把上次播放落盘的曲线点 / 事件 / 负荷辨识事件从 CSV 读回内存（按本侧 source_id 过滤），
        界面各曲线与事件表立即可看。运行中拒绝（409）。"""
        from elec_tool import replay_load
        with self.lock:
            running = bool(self.thread and self.thread.is_alive() and not self.stop_event.is_set() and not self._thread_done)
        if running:
            raise RuntimeError("数据源正在播放，不能加载历史数据；请先停止")
        cfg = self.cfg
        if self.engine is None:
            self.set_cfg(AppConfig.from_dict(cfg.to_dict()))       # 建一个未运行的引擎承载历史/事件
        with self.lock:
            eng = self.engine
        assert eng is not None
        sid = SIDE_SOURCE_ID[self.side]
        use_hours = float(hours) if hours else float(cfg.output.history_hours)
        rt_dir = os.environ.get("ELEC_TOOL_REALTIME_DIR") or cfg.output.realtime_dir
        ev_dir = os.environ.get("ELEC_TOOL_EVENTS_DIR") or cfg.events.events_dir
        nl_dir = os.environ.get("ELEC_TOOL_NILM_DIR") or cfg.nilm.nilm_dir
        absd = lambda d: d if os.path.isabs(d) else os.path.join(ROOT, d)   # noqa: E731
        out: Dict[str, Any] = {"ok": True, "side": self.side, "source_id": sid, "hours": use_hours,
                               "curves": {}, "events": 0, "nilm_events": 0, "result": False, "notes": []}
        if result:
            ent = self.read_last_result()
            if ent:
                with self.lock:
                    self.latest_merged = ent["result"]
                    self.latest_full = None
                out["result"] = True
                out["result_saved_at_local"] = ent.get("saved_at_local")
                out["result_source"] = ent.get("source_path") or ent.get("source_kind")
        t_first = t_last = None
        if curves:
            res = replay_load.load_curves(absd(rt_dir), sid, use_hours, max_points=int(cfg.output.history_max_points))
            for k, recs in res["records"].items():
                eng.calc.history.load_records(k, recs, replace=True)
            out["curves"] = res["points"]; out["curve_files"] = [{**f, "path": _display_path(f["path"])} for f in res["files"]]
            t_first, t_last = res["t_first"], res["t_last"]
            if not res["records"]:
                out["notes"].append(f"实时落盘目录 {rt_dir} 下没有本侧（source_id={sid}）的曲线数据")
        # 事件 / 负荷辨识事件与曲线取同一时间窗：曲线最新点往前 hours；没有曲线时不按时间过滤（只受 max_log 限制）
        t_from = (t_last - use_hours * 3600.0) if t_last is not None else None
        if events:
            evs = replay_load.load_events(absd(ev_dir), sid, t_from=t_from, limit=int(cfg.events.max_log))
            out["events"] = eng.detector.load_events(evs, replace=True)
            for d in evs:
                t_first = d["start_t"] if t_first is None else min(t_first, d["start_t"])
                t_last = d["start_t"] if t_last is None else max(t_last, d["start_t"])
        if nilm:
            nevs = replay_load.load_nilm_events(absd(nl_dir), sid, t_from=t_from, limit=int(cfg.nilm.max_log))
            out["nilm_events"] = eng.nilm.load_events(nevs, replace=True)
        out["t_first"] = t_first; out["t_last"] = t_last
        out["t_first_local"] = fmt_local(t_first) if t_first is not None else None
        out["t_last_local"] = fmt_local(t_last) if t_last is not None else None
        out["loaded_at"] = time.time(); out["loaded_at_local"] = fmt_local(out["loaded_at"])
        self.loaded_last = {k: out.get(k) for k in ("source_id", "hours", "curves", "events", "nilm_events", "t_first", "t_last",
                                                     "t_first_local", "t_last_local", "loaded_at", "loaded_at_local",
                                                     "result", "result_saved_at_local", "result_source", "auto")}
        self.broadcast({"type": "state", "data": self.state()})
        if out.get("result"):
            with self.lock:
                snap = self.latest_merged
            if snap:
                self.broadcast({"type": "snapshot", "data": snap})
        self.broadcast({"type": "events_cleared", "data": {"removed": 0, "reloaded": True}})
        self.broadcast({"type": "nilm_cleared", "data": {"removed": 0, "reloaded": True}})
        return out

    def clear_events(self) -> int:
        with self.lock:
            eng = self.engine
        return eng.detector.clear() if eng is not None else 0

    # ---------- 负荷辨识（第 12 轮） ----------
    def _on_nilm_event(self, new: List[Dict[str, Any]]) -> None:
        self.broadcast({"type": "nilm_event", "data": new})

    def nilm_events(self, limit: int = 500, algos: Optional[List[str]] = None, channel: Optional[str] = None,
                    since_id: int = 0) -> Dict[str, Any]:
        with self.lock:
            eng = self.engine
        if eng is None:
            from elec_tool.config import NILM_ALGO_DEFAULTS, NILM_ALGO_NAMES
            return {"ok": True, "events": [], "summary": {"enabled": bool(self.cfg.nilm.enabled), "total": 0,
                                                          "counts": {k: 0 for k in NILM_ALGO_DEFAULTS},
                                                          "algorithm_names": NILM_ALGO_NAMES, "notes": ["引擎尚未启动"]}}
        return {"ok": True, "events": eng.nilm.list(limit=limit, algos=algos, channel=channel, since_id=since_id),
                "summary": eng.nilm.summary()}

    def nilm_cycles_between(self, t_from: Optional[float], t_to: Optional[float]) -> Optional[Dict[str, Any]]:
        """v0.21：保留区内指定时间段的原始周波数据（None＝引擎尚未建立）。"""
        with self.lock:
            eng = self.engine
        if eng is None:
            return None
        return eng.nilm.cycles_between(t_from, t_to)

    def nilm_cycles(self, n: int) -> Dict[str, Any]:
        with self.lock:
            eng = self.engine
        if eng is None:
            return {"ok": True, "t": [], "channels": {}, "note": "引擎尚未启动"}
        d = eng.nilm.cycles(n)
        d["ok"] = True
        return d

    def clear_nilm(self) -> int:
        with self.lock:
            eng = self.engine
        return eng.nilm.clear() if eng is not None else 0

    # ---------- 生命周期 ----------
    def start(self, cfg: AppConfig, duration_s: Optional[float] = None, pace_clock=None,
              play_user: Optional[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """play_user：若本次运行的播放起点/终点是自动算出来的（公共时间段），这里传用户原来的设置，对外呈现/持久化都用它。"""
        cfg.output.source_id = SIDE_SOURCE_ID[self.side]
        _share_output_dirs(cfg, self.side)
        cfg.validate()
        # 先在**锁外**回收旧线程：join 时若仍持有 self.lock，旧线程正好卡在
        # 「append 结果要拿锁」上就会互等到超时（2s），旧线程存活后继续轮询
        # 被替换的新引擎 → 同一批数据双重摄入（samples_in 虚高、窗内点数不足）。
        self.stop(quiet=True)
        with self.lock:
            # 每轮用全新的 Event：旧线程只持有旧 Event，绝不会因新一轮 clear() 复活
            self.stop_event = threading.Event()
            self.pause_event = threading.Event()
            self.paused_at = None
            self.paused_total_s = 0.0
            self._thread_done = False
            self.error = None
            self.latest = None
            self.latest_full = None
            self.latest_merged = None
            self._play_user = play_user
            self._cfg_view = None
            # 一次运行＝一个数据集：重启引擎必须清空历史，否则导出/趋势会把
            # 不同数据源、不同窗长的结果混在一张表里（误导性极强）。
            self.store.clear()
            self.engine = LiveEngine(cfg, output_root=ROOT)
            # 节拍钟：联动启动时两侧共用一只（严格同步）；单侧启动也用一只（绝对限速，误差不累积）
            src = self.engine.source
            if hasattr(src, "_pace"):
                src.pace_clock = pace_clock if pace_clock is not None else PaceClock(cfg.source.file_speed)
                src.pace_side = self.side
                src.pace_abort = self.stop_event.is_set
            self.engine.on_event = self._on_event
            self.engine.on_nilm_event = self._on_nilm_event
            self.started_at = time.time()
            # 引擎与停止事件按值传给线程：线程内绝不重读 self.engine
            self.thread = threading.Thread(target=self._run,
                                           args=(duration_s, self.engine, self.stop_event, self.pause_event),
                                           daemon=True, name="elec-engine")
            self.thread.start()
        return {"ok": True, "source_kind": cfg.source.kind}

    def _run(self, duration_s: Optional[float], engine: LiveEngine,
             stop_event: threading.Event, pause_event: Optional[threading.Event] = None) -> None:
        """引擎线程。engine/stop_event/pause_event 都是本轮私有对象，被取代后自行退场。"""
        pause_event = pause_event or threading.Event()
        try:
            engine.start()
            while not stop_event.is_set():
                with self.lock:
                    stale = self.engine is not engine
                if stale:                       # 已被新一轮取代：立刻退场，不再产出
                    return
                if pause_event.is_set():        # 暂停：不读源、不计算、不推进数据时间；缓冲与事件原地保留
                    time.sleep(0.05)
                    continue
                n_before = engine.state.samples_in
                res = engine.poll_once()
                if res is not None:
                    with self.lock:
                        if self.engine is not engine:
                            return
                        self.latest = res
                        self.store.append(res)
                        d = res.to_dict()
                        self._merge_latest(d)
                    self.broadcast({"type": "result", "data": d})
                    if time.time() - getattr(self, "_last_persist_at", 0.0) >= 5.0:
                        self.persist_last_result()
                elif engine.state.finished:
                    final = engine.flush_all()
                    if final is not None:
                        with self.lock:
                            if self.engine is not engine:
                                return
                            self.latest = final
                            self.latest_full = final
                            self.store.append(final)
                            d = final.to_dict()
                            self._merge_latest(d)
                        self.broadcast({"type": "result", "data": d})
                    break
                elif engine.state.samples_in == n_before:
                    # 本轮没读到数据（实时源空转/文件尾）才等 poll_interval；读到块但无量到期时立即继续——
                    # 离线文件的节拍由数据源/节拍钟控制，这里再睡 0.2 s 会把吞吐压到 < 实时（v0.15.1）
                    time.sleep(max(0.01, min(engine.cfg.source.poll_interval_s, 0.2)))
                if duration_s and (time.time() - (self.started_at or time.time()) - self.paused_total_s) > duration_s:
                    break
        except Exception as exc:                                # 线程内异常必须回收，不能静默
            msg = f"{type(exc).__name__}: {exc}"
            with self.lock:
                if self.engine is engine:
                    self.error = msg
            self.broadcast({"type": "error", "message": msg})
        finally:
            clk = getattr(getattr(engine, "source", None), "pace_clock", None)
            if clk is not None:
                clk.finish(self.side)   # 本侧播完/停止 → 对侧不再等本侧（v0.15.1 互锁）
            try:
                engine.stop()          # 只停自己的引擎，绝不动 self.engine
            except Exception:
                pass
            # 终态广播必须在 engine.stop() **之后**（F-41：之前在循环结束处广播时 engine.running 仍为 True、
            # 线程也还活着，界面收到的是「运行中」，播完后只能手动刷新才变「已完成」）
            with self.lock:
                mine = self.engine is engine
                if mine:
                    self._thread_done = True
            if mine:
                self.persist_last_result()      # v0.20：停止 / 播完 / 异常都把最后结果落盘，重启后读回
                self.broadcast({"type": "state", "data": self.state()})

    # ---------- 暂停 / 恢复（离线文件源） ----------
    def _pausable(self) -> Optional[str]:
        """可暂停则返回 None，否则返回原因。"""
        with self.lock:
            eng = self.engine
            running = bool(self.thread and self.thread.is_alive() and not self.stop_event.is_set())
        if eng is None or not running:
            return "数据源未在运行"
        if eng.state.finished:
            return "离线文件已播放完毕"
        if eng.cfg.source.kind != "csv_file":
            return f"暂停/恢复仅支持离线文件（csv_file）源，当前为 {eng.cfg.source.kind}"
        return None

    def pause(self) -> Dict[str, Any]:
        why = self._pausable()
        if why:
            return {"ok": False, "error": why, "paused": bool(self.pause_event.is_set())}
        with self.lock:
            if not self.pause_event.is_set():
                self.pause_event.set()
                self.paused_at = time.time()
            clk = getattr(getattr(self.engine, "source", None), "pace_clock", None)
        if clk is not None:
            clk.pause()
        self.broadcast({"type": "state", "data": self.state()})
        return {"ok": True, "paused": True}

    def resume(self) -> Dict[str, Any]:
        why = self._pausable()
        if why:
            return {"ok": False, "error": why, "paused": bool(self.pause_event.is_set())}
        with self.lock:
            if self.pause_event.is_set():
                self.pause_event.clear()
                if self.paused_at is not None:
                    self.paused_total_s += time.time() - self.paused_at
                self.paused_at = None
            clk = getattr(getattr(self.engine, "source", None), "pace_clock", None)
        if clk is not None:
            clk.resume()
        self.broadcast({"type": "state", "data": self.state()})
        return {"ok": True, "paused": False}

    def stop(self, quiet: bool = False) -> None:
        with self.lock:
            self.stop_event.set()
            self.pause_event.clear()            # 暂停中停止：线程立刻退出等待
            th = self.thread
            self.thread = None
        if th and th.is_alive() and th is not threading.current_thread():
            th.join(timeout=3.0)
        if not quiet:
            self.broadcast({"type": "state", "data": self.state()})

    # ---------- 广播 ----------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def broadcast(self, payload: Dict[str, Any]) -> None:
        loop = self.loop
        if loop is None or loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast_async(payload), loop)
        except RuntimeError:
            pass

    async def _broadcast_async(self, payload: Dict[str, Any]) -> None:
        text = json.dumps(payload, ensure_ascii=False)
        dead: List[asyncio.Queue] = []
        for q in list(self.clients):
            try:
                if q.full():
                    q.get_nowait()               # 丢最旧，保证实时性
                q.put_nowait(text)
            except Exception:
                dead.append(q)
        for q in dead:
            self.clients.discard(q)

    # ---------- 状态 ----------
    def state(self) -> Dict[str, Any]:
        # 对侧摘要必须在拿到 self.lock **之前**算：_side_summary 要拿对侧的 lock，而对侧线程此刻可能正
        # 持着自己的 lock 在算 state() 并等我们的 lock → AB/BA 死锁（v0.15.1 两侧严格同步后两线程同时
        # 播完、同时广播终态，实测复现：两条 elec-engine 线程互等，整个服务挂起）
        other_summary = (_side_summary("branch") if self.side == "bus" else _side_summary("bus"))
        with self.lock:
            eng = self.engine
            cfg = self.cfg
            st = (_safe(lambda: eng.state.to_dict(), {"error": "state.to_dict 失败"}) if eng else {})
            st["config_path"] = self.cfg_path
            st["config_persist_path"] = self.persist_path
            src = {}
            if eng:
                try:
                    src = eng.source.info()
                except Exception as exc:
                    src = {"error": f"{type(exc).__name__}: {exc}"}
            latest_keys = list(self.latest.quantities) if self.latest else []
            return {
                "version": __version__,
                "side": self.side,
                "side_label": SIDE_LABELS.get(self.side, self.side),
                "branch": (other_summary if self.side == "bus" else None),
                "bus": (other_summary if self.side == "branch" else None),       # 对侧摘要（徽标/顶栏用）
                "common_window": ({k: v for k, v in COMMON_WINDOW.items() if k not in ("bus", "branch")}
                                  if COMMON_WINDOW.get("enabled") else None),
                "running": bool(self.thread and self.thread.is_alive() and not self.stop_event.is_set() and not self._thread_done),
                "paused": bool(self.pause_event.is_set() and self.thread and self.thread.is_alive() and not self.stop_event.is_set() and not self._thread_done),
                "pausable": bool(eng is not None and eng.cfg.source.kind == "csv_file"),
                "paused_total_s": round(self.paused_total_s + ((time.time() - self.paused_at) if self.paused_at else 0.0), 3),
                "finished": bool(st.get("finished")),
                "error": self.error,
                "loaded_last": self.loaded_last,
                "engine": st,
                "source": src,
                "config": cfg.to_dict(),
                "quantities": list(QUANTITY_KEYS),
                "latest_keys": latest_keys,
                "latest_t_ref": self.latest.t_ref if self.latest else None,
                "stored_results": len(self.store),
                "history": (_safe(lambda: eng.calc.history.stats(), {}) if eng else {}),
                "clients": len(self.clients),
                "server_time": time.time(),
            }

    def _merge_latest(self, d: Dict[str, Any]) -> None:
        """持锁调用。latest_merged＝最近一次发射 + 之前各量的最新值：单次发射往往只含到期的几个量
        （如 0.2 s 一次的基波/谐波），对侧总览/徽标用 full=false 拉结果时若只拿到这几项，电压/功率卡片会闪「—」。"""
        prev = self.latest_merged
        if prev and isinstance(prev.get("quantities"), dict) and isinstance(d.get("quantities"), dict):
            merged = dict(d)
            merged["quantities"] = {**prev["quantities"], **d["quantities"]}
            merged["_merged"] = True
            self.latest_merged = merged
        else:
            self.latest_merged = d

    def snapshot(self, force: bool = True) -> Optional[Dict[str, Any]]:
        """取当前缓冲的全量结果（UI 首次加载/手动刷新）。force=False：各量最近一次结果的并集（不重算）。"""
        with self.lock:
            eng = self.engine
            if eng is None:
                return self.latest_merged or (self.latest.to_dict() if self.latest else None)
            if not force:
                return self.latest_merged or (self.latest.to_dict() if self.latest else None)
            res = eng.snapshot_full()
            if res is not None:
                self.latest_full = res
                d = res.to_dict()
                self._merge_latest(d)
                return d
            return self.latest_merged or (self.latest.to_dict() if self.latest else None)


# ------------------------------------------------------------------ 两侧数据源（第 14 轮）
# 总线侧（bus）＝原有数据源；分路侧设备（branch）＝一份完全独立的配置 + 独立引擎。
# 所有 REST/WS 接口按「当前侧」解析：`/api/branch/<同名接口>`、`/ws/branch` 由 _SideRouter 改写路径并设置
# contextvar；`RUNNER` 是按 contextvar 取对应 EngineRunner 的代理，既有接口代码一行不改即可同时服务两侧。
RUNNERS: Dict[str, EngineRunner] = {s: EngineRunner(side=s) for s in SIDES}
_SIDE: contextvars.ContextVar[str] = contextvars.ContextVar("elec_side", default="bus")


def current_side() -> str:
    return _SIDE.get()


class _RunnerProxy:
    """RUNNER.xxx → RUNNERS[当前侧].xxx（属性读写都转发）。"""

    def __getattr__(self, name: str) -> Any:
        return getattr(RUNNERS[_SIDE.get()], name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(RUNNERS[_SIDE.get()], name, value)


RUNNER: Any = _RunnerProxy()


class _SideRouter:
    """纯 ASGI 中间件：/api/branch/... → /api/...（side=branch）；/ws/branch → /ws。HTTP 与 WebSocket 都覆盖。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") in ("http", "websocket"):
            path = scope.get("path", "")
            side = "bus"
            if path.startswith("/api/branch/"):
                scope = dict(scope); scope["path"] = "/api/" + path[len("/api/branch/"):]
                scope["raw_path"] = scope["path"].encode()
                side = "branch"
            elif path == "/ws/branch":
                scope = dict(scope); scope["path"] = "/ws"; scope["raw_path"] = b"/ws"
                side = "branch"
            token = _SIDE.set(side)
            try:
                return await self.app(scope, receive, send)
            finally:
                _SIDE.reset(token)
        return await self.app(scope, receive, send)


def _branch_summary() -> Dict[str, Any]:
    return _side_summary("branch")


def _side_summary(side: str) -> Dict[str, Any]:
    """某一侧的状态摘要（挂在对侧 /api/state 里：界面顶栏、导航徽标、数据源页用）。"""
    br = RUNNERS[side]
    bus = RUNNERS["bus"]
    if side == "branch":
        try:
            enabled = bool(bus.cfg.branch.enabled)
        except Exception:
            enabled = False
    else:
        enabled = True
    with br.lock:
        eng = br.engine
        running = bool(br.thread and br.thread.is_alive() and not br.stop_event.is_set() and not br._thread_done)
        st = eng.state if eng else None
        try:
            src = eng.cfg.source if eng else None
        except Exception:
            src = None
        try:
            c = br.cfg
            fs, pt, ct = float(c.sampling.fs), float(c.transform.pt_ratio), float(c.transform.ct_ratio)
        except Exception:
            fs = pt = ct = None
        latest = br.latest
    return {
        "fs": fs, "pt_ratio": pt, "ct_ratio": ct,
        "f_used": (getattr(latest, "f_used", None) if latest else None),
        "t_ref": (getattr(latest, "t_ref", None) if latest else None),
        "data_duration_s": (float(getattr(st, "data_duration_s", 0) or 0) if st else 0.0),
        "side": side, "enabled": enabled, "label": SIDE_LABELS[side], "config_path": br.cfg_path,
        "running": running, "paused": bool(running and br.pause_event.is_set()),
        "finished": bool(st and st.finished), "error": br.error,
        "source_kind": (src.kind if src else None), "source_path": (src.path if src else None),
        "samples_in": int(st.samples_in) if st else 0,
        "data_t_end": (st.data_t_end if st else None),
        "events_total": int(getattr(st, "events_total", 0) or 0) if st else 0,
        "events_active": int(getattr(st, "events_active", 0) or 0) if st else 0,
        "nilm_events_total": int(getattr(st, "nilm_events_total", 0) or 0) if st else 0,
    }


def _default_branch_cfg() -> AppConfig:
    """分路侧没有配置文件时的出厂值：与总线侧同模板，但输出目录分开、数据源留空。"""
    cfg = AppConfig()
    cfg.name = "分路侧设备电气量"
    cfg.source.kind = "simulator"; cfg.source.path = ""        # 出厂占位：界面「数据源」页改成 csv_file + 路径
    return cfg                                   # v0.17.2：输出目录与总线侧共用（启动/保存时由 _share_output_dirs 强制同步）


def _share_output_dirs(cfg: AppConfig, side: str) -> None:
    """v0.17.2：分路侧的落盘/导出目录一律与总线侧相同——两侧数据写进同一个 CSV 文件，只用 source_id 区分。"""
    if side != "branch":
        return
    bus = RUNNERS.get("bus") if "RUNNERS" in globals() else None
    if bus is None or bus.cfg is None:
        return
    b = bus.cfg
    cfg.output.realtime_dir = b.output.realtime_dir
    cfg.output.export_dir = b.output.export_dir
    cfg.events.events_dir = b.events.events_dir
    cfg.nilm.nilm_dir = b.nilm.nilm_dir


def _resolve_branch_cfg_paths(bus_cfg: Optional[AppConfig]) -> Tuple[str, str]:
    env_path = os.environ.get("ELEC_TOOL_BRANCH_CONFIG_PATH", "").strip()
    if env_path:
        return env_path, env_path
    tmpl = BRANCH_CONFIG_PATH
    try:
        if bus_cfg is not None and bus_cfg.branch.config_path:
            p = bus_cfg.branch.config_path
            tmpl = p if os.path.isabs(p) else os.path.join(ROOT, p)
    except Exception:
        pass
    load_path = BRANCH_RUNTIME_CONFIG_PATH if os.path.exists(BRANCH_RUNTIME_CONFIG_PATH) else tmpl
    return load_path, BRANCH_RUNTIME_CONFIG_PATH


def _sanitize_leaked_play(cfg: AppConfig, side: str) -> List[str]:
    """清理 v0.15～v0.15.2 公共时间段联动启动泄漏进配置文件的自动播放字段（v0.15.3 起不再泄漏）：
    - play_end_time 非空：用户界面没有这个字段，一定是自动值 → 清空（否则下次启动可能秒播完）；
    - play_start_mode=time 且取值是裸 epoch 数字（repr 写法，人不会这么填）：是自动起点 → 回到 begin
      （否则下次播放别的文件会按时标逐行扫到文件尾才开始 / 报起点越界，表现为「启动后很久才开始」）。"""
    notes: List[str] = []
    src = cfg.source
    if str(src.play_end_time or "").strip():
        notes.append(f"{side}: 清除残留的自动播放终点 play_end_time={src.play_end_time!r}")
        src.play_end_time = ""
    v = str(src.play_start_value or "").strip()
    if src.play_start_mode == "time" and re.fullmatch(r"\d{9,}(\.\d+)?", v):
        notes.append(f"{side}: 清除残留的自动播放起点 play_start_mode=time/{v} → begin")
        src.play_start_mode = "begin"; src.play_start_value = ""
    if src.play_start_mode == "row" and v == "1":            # 分路侧自动起点（第 1 行＝从头）→ 等价 begin
        src.play_start_mode = "begin"; src.play_start_value = ""
    return notes


def _init_branch_runner(bus_cfg: Optional[AppConfig]) -> None:
    br = RUNNERS["branch"]
    cfg_path, persist_path = _resolve_branch_cfg_paths(bus_cfg)
    br.cfg_path = cfg_path; br.persist_path = persist_path
    try:
        cfg = AppConfig.load(cfg_path) if os.path.isfile(cfg_path) else _default_branch_cfg().validate()
        for n in _sanitize_leaked_play(cfg, "branch"):
            log.warning("配置清理：%s", n)
        br.set_cfg(cfg)
    except Exception as exc:
        try:
            br.set_cfg(_default_branch_cfg().validate())
        except Exception:
            pass
        br.error = f"分路侧配置初始化失败：{type(exc).__name__}: {exc}"


async def _startup() -> None:
    loop = asyncio.get_running_loop()
    for r in RUNNERS.values():
        r.bind_loop(loop)
    bus = RUNNERS["bus"]
    cfg_path, persist_path = _resolve_cfg_paths()
    bus.cfg_path = cfg_path
    bus.persist_path = persist_path
    env_cfg = os.environ.get("ELEC_TOOL_CONFIG")
    try:
        if env_cfg:
            bus.set_cfg(AppConfig.from_dict(json.loads(env_cfg)))
        else:
            cfg0 = load_or_default(cfg_path)
            for n in _sanitize_leaked_play(cfg0, "bus"):
                log.warning("配置清理：%s", n)
            bus.set_cfg(cfg0)
    except Exception as exc:
        bus.error = f"配置初始化失败：{type(exc).__name__}: {exc}"
    try:
        _init_branch_runner(bus.cfg)
    except Exception as exc:
        RUNNERS["branch"].error = f"分路侧初始化失败：{type(exc).__name__}: {exc}"
    auto = os.environ.get("ELEC_TOOL_AUTOSTART", "").strip()
    if auto:
        try:
            bus.start(bus.cfg)
        except Exception as exc:
            bus.error = f"自动启动失败：{type(exc).__name__}: {exc}"
    elif os.environ.get("ELEC_TOOL_AUTOLOAD_LAST", "1").strip() not in ("0", "false", "no"):
        _autoload_last()


def _autoload_last() -> None:
    """v0.20：软件启动时自动把上次运行保存的 CSV（曲线 / 事件 / 负荷辨识事件）与 last_result.json（最新电气量）
    读回两侧内存，各子界面打开即有数据。受 output.autoload_last 控制；任何失败只记日志、不影响启动。"""
    bus = RUNNERS["bus"]
    try:
        cfg = bus.cfg
    except Exception:
        return
    if not getattr(cfg.output, "autoload_last", True):
        return
    sides = ["bus"] + (["branch"] if cfg.branch.enabled else [])
    for side in sides:
        try:
            r = RUNNERS[side].load_last()
            RUNNERS[side].loaded_last["auto"] = True
            pts = sum(int(v) for v in (r.get("curves") or {}).values())
            log.info("启动自动加载上次数据（%s）：曲线点 %d、事件 %d、负荷辨识事件 %d、最新电气量 %s",
                     side, pts, r.get("events", 0), r.get("nilm_events", 0), "有" if r.get("result") else "无")
        except Exception as exc:
            log.warning("启动自动加载上次数据失败（%s）：%s", side, exc)


# ------------------------------------------------------------------ 公共时间段（v0.15）

COMMON_WINDOW: Dict[str, Any] = {"enabled": False}      # 最近一次联动启动计算出的公共时间段（界面顶部显示）


def _abs_path(p: str) -> str:
    if p and not os.path.isabs(p):
        cand = os.path.join(ROOT, p)
        if os.path.exists(cand):
            return cand
    return p


def _count_data_rows(p: str, has_header: bool) -> int:
    """按字节数 \n 统计数据行数（空行无法剔除，但样例/现场文件没有空行；末行无换行符时补 1）。"""
    n = 0; last = b""
    with open(p, "rb") as fh:
        while True:
            chunk = fh.read(8 << 20)
            if not chunk:
                break
            n += chunk.count(b"\n"); last = chunk[-1:]
    if last and last != b"\n":
        n += 1
    return max(0, n - (1 if has_header else 0))


def _file_time_range(cfg: AppConfig, path: str) -> Dict[str, Any]:
    """离线文件的数据时间范围 [t0, t1] 与行数。custom_time 时时间轴＝起始时间 + 行号/fs。"""
    import csv as _csv
    from elec_tool.config import parse_time_text as _ptt
    from elec_tool.sources.parsing import detect_encoding, file_tz_offset_h, parse_timestamps, read_header
    p = _abs_path(path)
    if not os.path.isfile(p):
        raise ConfigError(f"文件不存在：{p}")
    header, enc = read_header(p, cfg.columns.encoding, cfg.columns.delimiter)
    has_header = cfg.columns.looks_like_header(header)
    idx = cfg.columns.layout(header if has_header else None)
    ts_c = idx.get("timestamp")
    fs = float(cfg.sampling.fs)
    # v0.15.3：不再用 csv.reader 逐行解析整文件（1 小时 6400 Hz ≈ 2300 万行，两侧要扫十几秒到几分钟，
    # 表现为「启动后很久才开始」）。行数按字节块数 \n；首/末几行分别从文件头和文件尾 64 KB 取。
    first: List[str] = []; last: List[str] = []
    n = _count_data_rows(p, has_header)
    with open(p, "rb") as fh:
        head = fh.read(65536).decode(enc, errors="replace").splitlines()
        size = fh.seek(0, os.SEEK_END)
        fh.seek(max(0, size - 65536))
        tail = fh.read().decode(enc, errors="replace").splitlines()
    if has_header and head:
        head = head[1:]
    def _cells(lines: List[str]) -> List[List[str]]:
        out: List[List[str]] = []
        for ln in lines:
            if not ln.strip():
                continue
            try:
                out.append(next(_csv.reader([ln], delimiter=cfg.columns.delimiter)))
            except Exception:
                continue
        return out
    if ts_c is not None:
        first = [r[ts_c] for r in _cells(head[:5]) if len(r) > ts_c][:3]
        tl = [r for r in _cells(tail[1:] if size > 65536 else tail) if len(r) > ts_c]   # 尾块首行可能被截断
        if has_header and size <= 65536 and tl:
            tl = [r for r in tl if r[ts_c] != header[ts_c]]
        last = [r[ts_c] for r in tl[-3:]]
    if n == 0:
        raise ConfigError(f"文件没有数据行：{p}")
    tz_h = file_tz_offset_h(cfg)
    if cfg.source.custom_time:
        txt = str(cfg.source.custom_time_start or "").strip()
        if txt:
            t0 = _ptt(txt)
        else:
            info = parse_timestamps(first, cfg.columns.timestamp_unit, tz_h)
            t0 = float(info.t[0]) if info.t.size else 0.0
        return {"path": p, "rows": n, "t0": t0, "t1": t0 + n / fs, "custom_time": True, "fs": fs}
    if ts_c is None:
        raise ConfigError(f"文件没有时间列，无法计算公共时间段（可改用自定义播放时间）：{p}")
    i0 = parse_timestamps(first, cfg.columns.timestamp_unit, tz_h)
    i1 = parse_timestamps(list(last), cfg.columns.timestamp_unit, tz_h)
    if not i0.t.size or not i1.t.size:
        raise ConfigError(f"无法解析文件时标：{p}")
    return {"path": p, "rows": n, "t0": float(i0.t[0]), "t1": float(i1.t[-1]) + 1.0 / fs, "custom_time": False, "fs": fs}


def _compute_common_window(bus_cfg: AppConfig, br_cfg: AppConfig) -> Dict[str, Any]:
    """两侧离线文件的公共时间段与播放起点。起点＝config.branch.common_start（若填且在段内）否则公共起点。"""
    from elec_tool.config import parse_time_text as _ptt
    rb = _file_time_range(bus_cfg, bus_cfg.source.path)
    rr = _file_time_range(br_cfg, br_cfg.source.path)
    t_start, t_end = max(rb["t0"], rr["t0"]), min(rb["t1"], rr["t1"])
    out = {"enabled": True, "bus": rb, "branch": rr, "t_start": t_start, "t_end": t_end,
           "duration_s": max(0.0, t_end - t_start), "play_start": t_start, "play_start_source": "公共时间段起点",
           "t_start_text": fmt_local(t_start), "t_end_text": fmt_local(t_end)}
    if t_end <= t_start:
        raise ConfigError(f"两侧文件没有公共时间段：总线侧 {fmt_local(rb['t0'])} → {fmt_local(rb['t1'])}，"
                          f"分路侧 {fmt_local(rr['t0'])} → {fmt_local(rr['t1'])}（可改用自定义播放时间让两侧时间轴对齐）")
    txt = str(bus_cfg.branch.common_start or "").strip()
    if txt:
        ps = _ptt(txt)
        if not (t_start <= ps < t_end):
            raise ConfigError(f"自定义播放起始时间 {txt} 不在公共时间段 {fmt_local(t_start)} → {fmt_local(t_end)} 内")
        out["play_start"] = ps; out["play_start_source"] = "自定义播放起始时间"
    out["play_end"] = t_end; out["play_end_source"] = "公共时间段终点"
    txe = str(getattr(bus_cfg.branch, "common_end", "") or "").strip()
    if txe:
        pe = _ptt(txe)
        if not (out["play_start"] < pe <= t_end):
            raise ConfigError(f"自定义播放结束时间 {txe} 不在 {fmt_local(out['play_start'])} → {fmt_local(t_end)} 内")
        out["play_end"] = pe; out["play_end_source"] = "自定义播放结束时间"
    out["play_start_text"] = fmt_local(out["play_start"]); out["play_end_text"] = fmt_local(out["play_end"])
    out["play_duration_s"] = out["play_end"] - out["play_start"]
    return out


def _play_fields(cfg: AppConfig) -> Tuple[str, str, str]:
    return (cfg.source.play_start_mode, str(cfg.source.play_start_value), str(cfg.source.play_end_time))


def _apply_window_to_source(cfg: AppConfig, rng: Dict[str, Any], play_start: float, t_end: float, side: str = "bus") -> None:
    """把公共时间段写进一侧的运行配置：起点按时标定位（custom_time 时换算成行号），终点＝公共终点。"""
    if rng.get("custom_time"):
        skip = int(round((play_start - rng["t0"]) * rng["fs"]))
        cfg.source.play_start_mode = "row"; cfg.source.play_start_value = str(max(1, skip + 1))
    else:
        cfg.source.play_start_mode = "time"; cfg.source.play_start_value = repr(float(play_start))
    cfg.source.play_end_time = repr(float(t_end))


def _apply_play_window(cfg: AppConfig) -> Optional[Tuple[str, str, str]]:
    """v0.17 指定时间段播放（单侧）：source.play_window 启用时把起点/终点写进本次运行配置。
    起点空＝沿用用户原播放起点设置（默认文件开头）；终点空＝播到文件尾。返回用户原字段（供对外呈现/持久化），未启用返回 None。"""
    if cfg.source.kind != "csv_file" or not bool(cfg.source.play_window):
        return None
    user = _play_fields(cfg)
    st = str(cfg.source.play_window_start or "").strip()
    en = str(cfg.source.play_window_end or "").strip()
    if st:
        cfg.source.play_start_mode = "time"; cfg.source.play_start_value = st
    cfg.source.play_end_time = en
    return user


def _start_branch_if_enabled(bus_cfg: AppConfig, pace_clock=None) -> Optional[Dict[str, Any]]:
    """总线侧启动后联动分路侧（仅 enabled 时）。返回分路侧启动结果；失败只记录、不影响总线侧。

    v0.16：分路侧输入方式与总线侧同样有 4 种（csv_file / csv_tail / tcp / simulator），各自独立配置；
    两侧都是离线文件时共用节拍钟（倍速同步、严格同步播放）并可按公共时间段播放；其它组合各自按自身配置启动。
    """
    if not bus_cfg.branch.enabled:
        return {"ok": False, "skipped": True, "reason": "分路侧未启用"}
    br = RUNNERS["branch"]
    try:
        cfg = AppConfig.from_dict(br.cfg.to_dict())
        if cfg.source.kind in ("csv_file", "csv_tail") and not cfg.source.path:
            raise ConfigError(f"分路侧 {cfg.source.kind} 需要文件路径（source.path）")
        if cfg.source.kind in ("csv_file", "csv_tail") and cfg.source.path and not os.path.isabs(cfg.source.path):
            cand = os.path.join(ROOT, cfg.source.path)
            if os.path.exists(cand):
                cfg.source.path = cand
        both_file = bus_cfg.source.kind == "csv_file" and cfg.source.kind == "csv_file"
        clock = None
        if both_file:
            # 播放速率与总线侧保持一致（需求：两侧倍速一致），共用节拍钟
            cfg.source.file_speed = float(bus_cfg.source.file_speed or 0.0)
            clock = pace_clock
        cw = COMMON_WINDOW if (both_file and COMMON_WINDOW.get("enabled")) else None
        cfg.source.play_end_time = ""
        play_user: Optional[Tuple[str, str, str]] = None
        if cw:
            play_user = _play_fields(cfg)
            _apply_window_to_source(cfg, cw["branch"], cw["play_start"], cw["play_end"], side="branch")
        else:
            play_user = _apply_play_window(cfg)          # 分路侧自己的指定时间段（未按公共时间段联动时）
        br.start(cfg, pace_clock=clock, play_user=play_user)
        br.error = None
        return {"ok": True, "source_kind": cfg.source.kind, "path": cfg.source.path, "synced_pace": both_file}
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        br.error = f"分路侧启动失败：{msg}"
        br.broadcast({"type": "state", "data": br.state()})
        return {"ok": False, "error": msg}


@asynccontextmanager
async def lifespan(_app: "FastAPI"):
    await _startup()
    yield
    for r in RUNNERS.values():
        r.stop(quiet=True)


app = FastAPI(title="电力系统电气量计算工具", version=__version__, lifespan=lifespan)
app.add_middleware(_SideRouter)


@app.get("/api/common_window")
async def get_common_window(preview: bool = False) -> Any:
    """公共时间段：preview=1 按当前两侧配置现算（不启动）；否则返回最近一次联动启动用的结果。"""
    if not preview:
        return COMMON_WINDOW
    try:
        bus_cfg = RUNNERS["bus"].cfg; br_cfg = RUNNERS["branch"].cfg
        if bus_cfg.source.kind != "csv_file" or br_cfg.source.kind != "csv_file":
            return {"ok": False, "error": "两侧都必须是离线文件 csv_file"}
        if not bus_cfg.source.path or not br_cfg.source.path:
            return {"ok": False, "error": "两侧文件路径都要先配置"}
        w = _compute_common_window(bus_cfg, br_cfg); w["ok"] = True
        return w
    except Exception as exc:
        return {"ok": False, "error": str(exc)}



# ------------------------------------------------------------------ 跨侧对齐与差值（第 15 轮）

_RATIO_FIELDS = {"P", "Q", "S", "Ia", "Ib", "Ic", "In", "I1", "U1", "Ua", "Ub", "Uc"}


def _compare_params(quantity: str, offset_s: Optional[float], tol_s: Optional[float]) -> Tuple[float, float, float]:
    """返回 (offset, tol, step)。offset/tol 为空时取总线侧 config.branch 的设置；tol=0 → 自动。"""
    bus = RUNNERS["bus"]; br = RUNNERS["branch"]
    bcfg = bus.cfg.branch
    off = float(offset_s) if offset_s is not None else float(bcfg.time_offset_s)
    tol = float(tol_s) if tol_s is not None else float(bcfg.align_tol_s)
    steps = []
    for r in (bus, br):
        try:
            w = r.cfg.windows.get(quantity)
            if w is not None:
                steps.append(float(w.step_s if w.step_s else w.length_s))
        except Exception:
            pass
    step = max(steps) if steps else 1.0
    if tol <= 0:
        tol = max(0.05, step * 0.6)
    return off, tol, step


def _rows_of(side: str, quantity: str, hours: Optional[float]) -> List[Dict[str, Any]]:
    r = RUNNERS[side]
    with r.lock:
        eng = r.engine
        use_hours = float(hours) if hours is not None else float(r.cfg.output.history_hours)
        return eng.calc.history.get(quantity, hours=use_hours) if eng else []


def _align_rows(bus_rows: List[Dict[str, Any]], br_rows: List[Dict[str, Any]], offset: float, tol: float,
                max_points: int) -> Dict[str, Any]:
    """按时间最近邻配对：分路侧时标 + offset 与总线侧时标之差 ≤ tol 才算同一时刻。差值＝总线 − 分路；占比＝分路/总线×100。"""
    if not bus_rows or not br_rows:
        return {"points": [], "aligned_count": 0, "unmatched_bus": len(bus_rows), "unmatched_branch": len(br_rows), "fields": []}
    bt = np.array([r["t"] for r in bus_rows], dtype=np.float64)
    rt = np.array([r["t"] for r in br_rows], dtype=np.float64) + offset
    order = np.argsort(rt); rt_sorted = rt[order]
    fields = [f for f in bus_rows[-1] if f not in ("t", "window_s") and f in br_rows[-1]]
    pairs: List[Tuple[int, int, float]] = []
    used: Set[int] = set()
    for i, t in enumerate(bt):
        j = int(np.searchsorted(rt_sorted, t))
        cand = [k for k in (j - 1, j) if 0 <= k < rt_sorted.size]
        if not cand:
            continue
        k = min(cand, key=lambda k: abs(rt_sorted[k] - t))
        dt = float(rt_sorted[k] - t)
        if abs(dt) <= tol and k not in used:
            used.add(k); pairs.append((i, int(order[k]), dt))
    pts: List[Dict[str, Any]] = []
    for i, j, dt in pairs:
        b, r = bus_rows[i], br_rows[j]
        diff: Dict[str, Any] = {}; ratio: Dict[str, Any] = {}
        for f in fields:
            x, y = b.get(f), r.get(f)
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                diff[f] = x - y
                if f in _RATIO_FIELDS:
                    ratio[f] = (y / x * 100.0) if abs(x) > 1e-12 else None
            else:
                diff[f] = None
        pts.append({"t": float(b["t"]), "t_branch": float(r["t"]), "dt_s": round(dt, 6),
                    "bus": {f: b.get(f) for f in fields}, "branch": {f: r.get(f) for f in fields},
                    "diff": diff, "ratio_pct": ratio})
    n = len(pts)
    decimated = False
    if max_points and n > max_points > 2:
        idx = np.unique(np.concatenate([np.linspace(0, n - 1, max_points).astype(int), [n - 1]]))
        pts = [pts[k] for k in idx]; decimated = True
    return {"points": pts, "aligned_count": n, "decimated": decimated, "fields": fields,
            "unmatched_bus": len(bus_rows) - n, "unmatched_branch": len(br_rows) - n,
            "dt_abs_mean_s": (float(np.mean([abs(p[2]) for p in pairs])) if pairs else None)}


@app.get("/api/compare/{quantity}")
async def get_compare(quantity: str, offset_s: Optional[float] = None, tol_s: Optional[float] = None,
                      hours: Optional[float] = None, max_points: int = 1500) -> Any:
    """总线侧 vs 分路侧同一电气量的时间轴对齐与差值：diff＝总线−分路，ratio_pct＝分路/总线×100。

    offset_s：分路侧时标偏移（默认 config.branch.time_offset_s）；tol_s：配对容差（默认自动＝输出步长×0.6）。
    """
    if quantity not in QUANTITY_KEYS:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"未知电气量 '{quantity}'"})
    off, tol, step = _compare_params(quantity, offset_s, tol_s)
    bus_rows = _rows_of("bus", quantity, hours); br_rows = _rows_of("branch", quantity, hours)
    res = _align_rows(bus_rows, br_rows, off, tol, max_points)
    span = lambda rows: (rows[0]["t"], rows[-1]["t"]) if rows else (None, None)
    b0, b1 = span(bus_rows); r0, r1 = span(br_rows)
    res.update({"quantity": quantity, "offset_s": off, "tol_s": tol, "step_s": step,
                "bus_count": len(bus_rows), "branch_count": len(br_rows),
                "bus_t_first": b0, "bus_t_last": b1, "branch_t_first": r0, "branch_t_last": r1,
                "offset_suggest_s": ((b0 - r0) if (b0 is not None and r0 is not None) else None),
                "latest": (res["points"][-1] if res["points"] else None)})
    return res


@app.get("/api/compare")
async def get_compare_summary(offset_s: Optional[float] = None, tol_s: Optional[float] = None) -> Any:
    """各曲线量的最新一组对齐值（表格用）。"""
    out: Dict[str, Any] = {"quantities": {}}
    for k in CURVE_KEYS:
        off, tol, step = _compare_params(k, offset_s, tol_s)
        res = _align_rows(_rows_of("bus", k, None), _rows_of("branch", k, None), off, tol, 1)
        pts = res["points"]
        out["quantities"][k] = {"latest": (pts[-1] if pts else None), "aligned_count": res["aligned_count"],
                                "tol_s": tol, "offset_s": off}
    out["offset_s"] = float(RUNNERS["bus"].cfg.branch.time_offset_s)
    return out


@app.get("/api/sides")
async def get_sides() -> Dict[str, Any]:
    """两侧概览：标签、配置文件、运行状态（界面侧别切换器用）。"""
    out = {}
    for s, r in RUNNERS.items():
        with r.lock:
            eng = r.engine
            running = bool(r.thread and r.thread.is_alive() and not r.stop_event.is_set() and not r._thread_done)
            st = eng.state if eng else None
        out[s] = {"label": SIDE_LABELS[s], "config_path": r.cfg_path, "running": running,
                  "paused": bool(running and r.pause_event.is_set()), "finished": bool(st and st.finished),
                  "error": r.error, "api_prefix": ("/api/branch" if s == "branch" else "/api"),
                  "ws_path": ("/ws/branch" if s == "branch" else "/ws")}
    out["bus"]["branch_enabled"] = bool(RUNNERS["bus"].cfg.branch.enabled) if RUNNERS["bus"].engine else False
    return {"ok": True, "sides": out, "current": current_side()}


# ------------------------------------------------------------------ REST

@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "version": __version__, "time": time.time(),
            "running": bool(RUNNER.thread and RUNNER.thread.is_alive())}


@app.get("/api/state")
async def get_state() -> Dict[str, Any]:
    return RUNNER.state()


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    return RUNNER.cfg.to_dict()


@app.put("/api/config")
async def put_config(payload: Dict[str, Any]) -> Any:
    """局部更新配置（支持只传要改的部分），热更新到运行中的引擎。"""
    try:
        cur = RUNNER.cfg
        data = cur.to_dict()
        _deep_update(data, payload)
        cfg = AppConfig.from_dict(data)
        RUNNER.set_cfg(cfg)
        if os.environ.get("ELEC_TOOL_PERSIST_CONFIG", "1") == "1":
            try:
                _persist(cfg)
            except Exception:
                pass
        return {"ok": True, "config": cfg.to_dict()}
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _persist(cfg: AppConfig) -> None:
    """写运行时配置文件；路径尽量存成相对仓库根的形式，换机器/换目录仍可用。"""
    out = AppConfig.from_dict(cfg.to_dict())
    out.source.play_end_time = ""                 # 运行期自动字段，不落盘
    sp = out.source.path or ""
    if sp.startswith(ROOT + os.sep):
        out.source.path = os.path.relpath(sp, ROOT)
    out.validate().save(RUNNER.persist_path)


def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v


@app.post("/api/engine/start")
async def engine_start(payload: Optional[Dict[str, Any]] = None) -> Any:
    payload = payload or {}
    try:
        cfg = RUNNER.cfg
        data = cfg.to_dict()
        src_over = {k: v for k, v in payload.items()
                    if k in ("kind", "path", "host", "port", "frame", "block_samples",
                             "poll_interval_s", "tail_from_end", "sim_speed", "watch_dir_newest",
                             "struct_fmt", "struct_fields", "custom_time", "custom_time_start",
                             "file_time_utc", "play_start_mode", "play_start_value", "file_speed",
                             "play_window", "play_window_start", "play_window_end")}
        if src_over:
            data["source"].update(src_over)
        if payload.get("windows"):
            for k, v in payload["windows"].items():
                if k in data["windows"]:
                    if isinstance(v, dict):
                        data["windows"][k].update(v)
                    else:
                        data["windows"][k]["length_s"] = float(v)
        cfg = AppConfig.from_dict(data)
        # 相对路径解析到仓库根（浏览器只传相对/绝对路径字符串）
        if cfg.source.kind in ("csv_file", "csv_tail") and cfg.source.path and not os.path.isabs(cfg.source.path):
            cand = os.path.join(ROOT, cfg.source.path)
            if os.path.exists(cand):
                cfg.source.path = cand
        coupled = (current_side() == "bus" and payload.get("with_branch", True) and cfg.branch.enabled)
        cfg.source.play_end_time = ""          # 终点只由公共时间段自动给出，用户配置里不存在这个概念
        play_user: Optional[Tuple[str, str, str]] = None
        cw_note: Optional[str] = None
        if current_side() == "bus":
            COMMON_WINDOW.clear(); COMMON_WINDOW["enabled"] = False
        if coupled and cfg.branch.common_window:
            br_cfg = RUNNERS["branch"].cfg
            if cfg.source.kind != "csv_file" or br_cfg.source.kind != "csv_file":
                # 公共时间段只对「两侧都是离线文件」有意义；其它组合按各自配置启动，不报错（v0.16）
                cw_note = (f"公共时间段仅在两侧都是离线文件时生效（总线侧 {cfg.source.kind}，分路侧 {br_cfg.source.kind}），本次按各自配置播放")
            elif not br_cfg.source.path:
                raise ConfigError("启用「只播放公共时间段」需要分路侧已配置离线文件路径")
            else:
                w = _compute_common_window(cfg, br_cfg)        # 失败 → 400，两侧都不启动
                COMMON_WINDOW.update(w)
                play_user = _play_fields(cfg)
                _apply_window_to_source(cfg, w["bus"], w["play_start"], w["play_end"], side="bus")
        if play_user is None:
            play_user = _apply_play_window(cfg)                # 本侧自己的指定时间段播放（v0.17）
        clock = PaceClock(cfg.source.file_speed) if cfg.source.kind == "csv_file" else None
        RUNNER.start(cfg, duration_s=payload.get("duration_s"), pace_clock=clock, play_user=play_user)
        out: Dict[str, Any] = {"ok": True, "side": current_side(), "config": RUNNER.cfg.to_dict()}
        if COMMON_WINDOW.get("enabled"):
            out["common_window"] = {k: v for k, v in COMMON_WINDOW.items() if k not in ("bus", "branch")}
        elif cw_note:
            out["common_window"] = {"enabled": False, "reason": cw_note}
        if current_side() == "bus" and payload.get("with_branch", True):
            out["branch"] = _start_branch_if_enabled(cfg, pace_clock=clock)
        return out
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.post("/api/engine/pause")
async def engine_pause() -> Any:
    """暂停离线文件播放：停止读文件与计算，数据时间原地不动；缓冲/历史/事件保留。非 csv_file 源或未运行 → 400。"""
    r = RUNNER.pause()
    if not r["ok"]:
        return JSONResponse(status_code=400, content=r)
    if current_side() == "bus":
        r["branch"] = RUNNERS["branch"].pause()   # 联动；分路侧不可暂停（未运行/非文件源）只记结果
    r["state"] = RUNNER.state()
    return r


@app.post("/api/engine/resume")
async def engine_resume() -> Any:
    """从暂停处继续播放（接着上次读到的位置，不重读、不跳过）。"""
    r = RUNNER.resume()
    if not r["ok"]:
        return JSONResponse(status_code=400, content=r)
    if current_side() == "bus":
        r["branch"] = RUNNERS["branch"].resume()
    r["state"] = RUNNER.state()
    return r


@app.post("/api/engine/stop")
async def engine_stop() -> Dict[str, Any]:
    RUNNER.stop()
    if current_side() == "bus":
        RUNNERS["branch"].stop()                  # 总线侧停止 → 分路侧一并停止（未运行时无副作用）
    return {"ok": True, "state": RUNNER.state()}


@app.get("/api/events")
async def get_events(active: bool = False, limit: int = 200, types: Optional[str] = None,
                     since_id: int = 0) -> Dict[str, Any]:
    """事件列表：active=1 只看活动事件；types=逗号分隔类型；since_id 增量拉取。"""
    tl = [t.strip() for t in types.split(",") if t.strip()] if types else None
    return RUNNER.events(active=active, limit=max(1, min(int(limit), 5000)), types=tl, since_id=int(since_id))


@app.post("/api/history/load_last")
async def history_load_last(payload: Optional[Dict[str, Any]] = None) -> Any:
    """v0.18：不播放时直接加载上次播放落盘的电气量曲线 / 事件 / 负荷辨识事件（按本侧 source_id 过滤）。
    body：{hours?: 小时数（默认 output.history_hours）, curves?: true, events?: true, nilm?: true, with_branch?: true}。
    总线侧调用且启用分路侧时，分路侧一并加载（结果在 branch 字段）。"""
    payload = payload or {}
    try:
        res = RUNNER.load_last(hours=payload.get("hours"), curves=payload.get("curves", True) is not False,
                               events=payload.get("events", True) is not False, nilm=payload.get("nilm", True) is not False)
    except RuntimeError as exc:
        return JSONResponse(status_code=409, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    if current_side() == "bus" and RUNNER.cfg.branch.enabled and payload.get("with_branch", True):
        try:
            res["branch"] = RUNNERS["branch"].load_last(hours=payload.get("hours"))
        except RuntimeError as exc:
            res["branch"] = {"ok": False, "error": str(exc)}
        except Exception as exc:
            res["branch"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return res


@app.post("/api/events/clear")
async def clear_events() -> Dict[str, Any]:
    n = RUNNER.clear_events()
    RUNNER.broadcast({"type": "events_cleared", "data": {"removed": n}})
    return {"ok": True, "removed": n, "summary": RUNNER.events(limit=1)["summary"]}


@app.get("/api/nilm/events")
async def get_nilm_events(limit: int = 500, algos: Optional[str] = None, channel: Optional[str] = None,
                          since_id: int = 0) -> Dict[str, Any]:
    """负荷辨识事件列表：algos=逗号分隔算法键；channel=total/A/B/C；since_id 增量拉取。"""
    al = [a.strip() for a in algos.split(",") if a.strip()] if algos else None
    return RUNNER.nilm_events(limit=max(1, min(int(limit), 5000)), algos=al, channel=(channel or None), since_id=int(since_id))


@app.get("/api/nilm/cycles")
async def get_nilm_cycles(n: int = 300) -> Dict[str, Any]:
    """最近 n 个周波的 P/Q/I 序列（total/A/B/C），供负荷辨识界面画图。"""
    return RUNNER.nilm_cycles(max(1, min(int(n), 20000)))


NILM_CYCLE_HEADER = ["source_id", "cycle_idx", "t_epoch_s", "time_local",
                     "P_total", "P_A", "P_B", "P_C", "Q_total", "Q_A", "Q_B", "Q_C", "I_total", "I_A", "I_B", "I_C"]


def _cycle_rows(side: str, d: Dict[str, Any]) -> List[List[Any]]:
    sid = SIDE_SOURCE_ID[side]
    t = d["t"]; p = d["p"]; q = d["q"]; i = d["i"]; idx = d["idx"]
    rows: List[List[Any]] = []
    for k in range(int(t.shape[0])):
        rows.append([sid, int(idx[k]), repr(float(t[k])), fmt_local(float(t[k]))]
                    + [f"{float(p[c, k]):.10g}" for c in range(4)] + [f"{float(q[c, k]):.10g}" for c in range(4)]
                    + [f"{float(i[c, k]):.10g}" for c in range(4)])
    return rows


def _parse_range(payload: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    t_from = payload.get("t_from"); t_to = payload.get("t_to")
    tf = parse_time_text(str(t_from)) if t_from not in (None, "") else None
    tt = parse_time_text(str(t_to)) if t_to not in (None, "") else None
    if tf is not None and tt is not None and tt < tf:
        raise ConfigError("结束时间早于开始时间")
    return tf, tt


@app.post("/api/nilm/cycles/export")
async def nilm_cycles_export(payload: Optional[Dict[str, Any]] = None) -> Any:
    """v0.21：导出指定时间段的**原始周波数据**（每周波 P/Q/I × total/A/B/C）到 CSV。

    body：{t_from?: 时间文本或 epoch 秒, t_to?: 同, with_branch?: true}（两者都空＝保留区全部）。
    总线侧调用且启用分路侧时，分路侧同一时间段的周波写进**同一个文件**（source_id=1），按时间排序。
    文件：output/cycles_<起>_<止>.csv。数据来自内存保留区（nilm.cycle_keep_cycles，默认 ≈1 h@50 Hz）。
    """
    payload = payload or {}
    try:
        tf, tt = _parse_range(payload)
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    side = current_side()
    sides = [side] + (["branch"] if side == "bus" and RUNNER.cfg.branch.enabled and payload.get("with_branch", True) else [])
    rows: List[List[Any]] = []
    per: Dict[str, Any] = {}
    for sd in sides:
        d = RUNNERS[sd].nilm_cycles_between(tf, tt)
        info = RUNNERS[sd].engine.nilm.keep_info() if RUNNERS[sd].engine is not None else {"cycles": 0}
        n = int(d["t"].shape[0]) if d is not None else 0
        per[sd] = {"rows": n, "keep": info,
                   "t_first": (float(d["t"][0]) if n else None), "t_last": (float(d["t"][-1]) if n else None)}
        if n:
            rows.extend(_cycle_rows(sd, d))
    if not rows:
        return JSONResponse(status_code=409, content={
            "ok": False, "error": "指定时间段内没有原始周波数据（保留区范围见 sides[*].keep.t_first~t_last；保留区长度由 nilm.cycle_keep_cycles 决定）",
            "sides": per, "t_from": tf, "t_to": tt})
    rows.sort(key=lambda r: (float(r[2]), int(r[0])))
    out_dir = RUNNER.cfg.output.export_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(ROOT, out_dir)
    os.makedirs(out_dir, exist_ok=True)
    t0 = float(rows[0][2]); t1 = float(rows[-1][2])
    name = f"cycles_{fmt_local(t0, ms=False).replace('-', '').replace(':', '').replace(' ', '_')}_{fmt_local(t1, ms=False).replace('-', '').replace(':', '').replace(' ', '_')}.csv"
    fp = os.path.join(out_dir, name)
    import csv as _csv
    with open(fp, "w", encoding="utf-8-sig", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(NILM_CYCLE_HEADER)
        w.writerows(rows)
    return {"ok": True, "path": _display_path(fp), "rows": len(rows), "sides": per, "source_ids": sorted({int(r[0]) for r in rows}),
            "t_from": tf, "t_to": tt, "t_first": t0, "t_last": t1, "t_first_local": fmt_local(t0), "t_last_local": fmt_local(t1),
            "columns": NILM_CYCLE_HEADER}


@app.get("/api/nilm/cycles/export")
async def nilm_cycles_download(t_from: Optional[str] = None, t_to: Optional[str] = None, with_branch: bool = True) -> Any:
    """同上，但直接以 CSV 下载（不落盘）。"""
    try:
        tf, tt = _parse_range({"t_from": t_from, "t_to": t_to})
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    side = current_side()
    sides = [side] + (["branch"] if side == "bus" and RUNNER.cfg.branch.enabled and with_branch else [])
    rows: List[List[Any]] = []
    for sd in sides:
        d = RUNNERS[sd].nilm_cycles_between(tf, tt)
        if d is not None and d["t"].shape[0]:
            rows.extend(_cycle_rows(sd, d))
    rows.sort(key=lambda r: (float(r[2]), int(r[0])))
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf); w.writerow(NILM_CYCLE_HEADER); w.writerows(rows)
    fname = "cycles.csv" if not rows else f"cycles_{fmt_local(float(rows[0][2]), ms=False).replace('-', '').replace(':', '').replace(' ', '_')}.csv"
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})


@app.post("/api/nilm/clear")
async def clear_nilm() -> Dict[str, Any]:
    n = RUNNER.clear_nilm()
    RUNNER.broadcast({"type": "nilm_cleared", "data": {"removed": n}})
    return {"ok": True, "removed": n, "summary": RUNNER.nilm_events(limit=1)["summary"]}


@app.get("/api/result")
async def get_result(full: bool = True) -> Any:
    data = RUNNER.snapshot(force=full)
    if data is None:
        return JSONResponse(status_code=409, content={
            "ok": False, "error": "尚无计算结果：请先在「数据源与控制」启动数据源"})
    return data


@app.get("/api/history/{quantity}")
async def get_history(quantity: str, n: Optional[int] = None, hours: Optional[float] = None,
                      max_points: int = 1500) -> Any:
    """趋势曲线数据。默认＝最近 output.history_hours（24h）内全部记录，超过 max_points 则抽稀（保峰谷）。

    n：兼容旧调用，只取最后 n 条；hours：覆盖默认时间窗；max_points≤0 表示不抽稀。
    返回 count＝本次返回点数、count_total＝该曲线内存中保留的总点数、span_s＝保留区间长度。
    """
    if quantity not in QUANTITY_KEYS:
        return JSONResponse(status_code=400, content={
            "ok": False, "error": f"未知电气量 '{quantity}'，可用：{list(QUANTITY_KEYS)}"})
    with RUNNER.lock:
        eng = RUNNER.engine
        cfg = RUNNER.cfg
        use_hours = float(hours) if hours is not None else float(cfg.output.history_hours)
        if eng:
            h = eng.calc.history
            hist = h.get(quantity, n=n, hours=use_hours, max_points=(max_points if max_points > 0 else None))
            total = h.count(quantity)
            t0, t1 = h.span(quantity)
        else:
            hist, total, t0, t1 = [], 0, None, None
    return {"quantity": quantity, "points": hist, "count": len(hist), "count_total": total,
            "hours": use_hours, "decimated": bool(total and len(hist) < min(total, 10**9) and max_points > 0 and total > max_points),
            "t_first": t0, "t_last": t1, "span_s": ((t1 - t0) if (t0 is not None and t1 is not None) else 0.0)}


# ------------------------------------------------------------------ 曲线数据保存

def _display_path(p: str) -> str:
    """仓库内路径显示为相对路径，仓库外（如自定义 export_dir）保持绝对路径。"""
    ap = os.path.abspath(p)
    root = os.path.abspath(ROOT)
    return os.path.relpath(ap, root) if ap.startswith(root + os.sep) else ap


def _curve_rows(quantity: str, hours: Optional[float], side: Optional[str] = None) -> List[Dict[str, Any]]:
    r = RUNNERS[side] if side else RUNNER
    with r.lock:
        eng = r.engine
        if not eng:
            return []
        return eng.calc.history.get(quantity, hours=hours)


def _curve_fields(rows: List[Dict[str, Any]]) -> List[str]:
    fields: List[str] = []
    for r in rows:
        for k in r:
            if k not in ("t", "_sid") and k not in fields:
                fields.append(k)
    return fields


def _curve_csv(quantity: str, rows: List[Dict[str, Any]], source_id: int = 0) -> str:
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf)
    fields = _curve_fields(rows)
    w.writerow(["t_epoch_s", "time_local", "source_id", "quantity"] + fields)     # v0.17：source_id 0 总线 / 1 分路
    for r in rows:
        tl = fmt_local(r["t"])
        w.writerow([repr(float(r["t"])), tl, int(r.get("_sid", source_id)), quantity] + [("" if r.get(f) is None else r.get(f)) for f in fields])
    return buf.getvalue()


def _selected_curves(payload: Optional[Dict[str, Any]], cfg: AppConfig) -> Tuple[List[str], List[str]]:
    """返回 (要保存的曲线, 因未勾选而跳过的曲线)。payload.quantities 显式给出时仍受勾选过滤。"""
    want = payload.get("quantities") if payload else None
    keys = [k for k in CURVE_KEYS if (not want or k in want)]
    enabled = cfg.output.curve_save
    return [k for k in keys if enabled.get(k, True)], [k for k in keys if not enabled.get(k, True)]


@app.post("/api/curves/save")
async def curves_save(payload: Optional[Dict[str, Any]] = None) -> Any:
    """把已勾选「保存」的曲线数据写到 output/curves_<时间>/<曲线>.csv（未勾选的曲线不写）。

    payload 可选：{"quantities": [...], "hours": 24}
    """
    payload = payload or {}
    cfg = RUNNER.cfg
    hours = payload.get("hours")
    hours = float(hours) if hours is not None else float(cfg.output.history_hours)
    chosen, skipped = _selected_curves(payload, cfg)
    if not chosen:
        return JSONResponse(status_code=400, content={
            "ok": False, "error": "没有勾选任何要保存的曲线：请在曲线面板或「导出与日志」勾选后再保存",
            "skipped": skipped})
    out_dir = cfg.output.export_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(ROOT, out_dir)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = os.path.join(out_dir, f"curves_{stamp}")
    os.makedirs(target, exist_ok=True)
    files: List[Dict[str, Any]] = []
    empty: List[str] = []
    sid = SIDE_SOURCE_ID[current_side()]
    # v0.17.1：总线侧保存且启用分路侧 → 分路侧曲线写进**同一个** <曲线>.csv（按 source_id 区分 0/1，按时间排序），
    # 不另建目录/文件；分路侧按自己的「保存曲线」勾选过滤。
    branch_rows: Dict[str, List[Dict[str, Any]]] = {}
    branch_skipped: List[str] = []
    with_branch = current_side() == "bus" and cfg.branch.enabled and payload.get("with_branch", True)
    if with_branch:
        br_chosen, branch_skipped = _selected_curves(payload, RUNNERS["branch"].cfg)
        for k in br_chosen:
            rows_b = _curve_rows(k, hours, side="branch")
            if rows_b:
                branch_rows[k] = rows_b
    for k in list(chosen) + [k for k in branch_rows if k not in chosen]:
        rows = _curve_rows(k, hours) if k in chosen else []
        tagged = [dict(r, _sid=sid) for r in rows] + [dict(r, _sid=1) for r in branch_rows.get(k, [])]
        if not tagged:
            empty.append(k)
            continue
        tagged.sort(key=lambda r: float(r["t"]))        # 稳定排序：同一时刻总线行在前
        fp = os.path.join(target, f"{k}.csv")
        with open(fp, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(_curve_csv(k, tagged, sid))
        nb = len(branch_rows.get(k, []))
        files.append({"quantity": k, "path": _display_path(fp), "rows": len(tagged), "rows_bus": len(rows), "rows_branch": nb,
                      "source_ids": sorted({int(r["_sid"]) for r in tagged}),
                      "t_first": tagged[0]["t"], "t_last": tagged[-1]["t"]})
    if not files:
        try:
            os.rmdir(target)
        except OSError:
            pass
        return JSONResponse(status_code=409, content={
            "ok": False, "error": "已勾选的曲线暂无数据可保存（请先启动数据源并累计 ≥1 个窗）",
            "skipped": skipped, "empty": empty})
    return {"ok": True, "dir": _display_path(target), "files": files, "with_branch": bool(with_branch),
            "branch_quantities": sorted(branch_rows), "branch_skipped": branch_skipped,
            "skipped": skipped, "empty": empty, "hours": hours}


@app.get("/api/realtime")
async def realtime_status() -> Dict[str, Any]:
    """实时落盘状态：开关、目录、本次会话各曲线写入行数、目录下现有文件清单（含大小/行数估计）。"""
    cfg = RUNNER.cfg
    with RUNNER.lock:
        eng = RUNNER.engine
        info = eng.writer.info() if eng else {"enabled": bool(cfg.output.realtime_save), "dir": cfg.output.realtime_dir,
                                               "files": [], "rows_written": {}, "errors": []}
    d = os.environ.get("ELEC_TOOL_REALTIME_DIR") or cfg.output.realtime_dir
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    listing: List[Dict[str, Any]] = []
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            fp = os.path.join(d, name)
            if name.endswith(".csv") and os.path.isfile(fp):
                listing.append({"name": name, "path": _display_path(fp), "size_bytes": os.path.getsize(fp),
                                "mtime": os.path.getmtime(fp)})
    info["dir_display"] = _display_path(d)
    info["dir_files"] = listing
    info["curve_save"] = dict(cfg.output.curve_save)
    return info


@app.get("/api/curves/export")
async def curves_export(quantity: Optional[str] = None, hours: Optional[float] = None) -> Response:
    """下载曲线数据 CSV：quantity 给出＝单曲线；不给＝所有**已勾选**曲线合并（长表）。未勾选的曲线不输出。"""
    cfg = RUNNER.cfg
    use_hours = float(hours) if hours is not None else float(cfg.output.history_hours)
    if quantity:
        if quantity not in CURVE_KEYS:
            return JSONResponse(status_code=400, content={
                "ok": False, "error": f"未知曲线 '{quantity}'，可用：{list(CURVE_KEYS)}"})
        if not cfg.output.curve_save.get(quantity, True):
            return JSONResponse(status_code=403, content={
                "ok": False, "error": f"曲线 '{quantity}' 未勾选「保存曲线数据」，已按配置跳过；需要请先勾选"})
        rows = _curve_rows(quantity, use_hours)
        if not rows:
            return JSONResponse(status_code=409, content={"ok": False, "error": f"曲线 '{quantity}' 暂无数据"})
        stamp = time.strftime("%Y%m%d_%H%M%S")
        return Response(content=_curve_csv(quantity, rows, SIDE_SOURCE_ID[current_side()]), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="curve_{quantity}_{stamp}.csv"'})
    chosen, _ = _selected_curves(None, cfg)
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["t_epoch_s", "time_local", "source_id", "quantity", "field", "value"])
    n = 0
    sides = [(current_side(), SIDE_SOURCE_ID[current_side()])]
    if current_side() == "bus" and cfg.branch.enabled:
        sides.append(("branch", 1))                    # v0.17：启用分路侧时合并下载也含分路数据（source_id=1）
    for side, sid in sides:
        side_chosen = chosen if side == current_side() else _selected_curves(None, RUNNERS[side].cfg)[0]
        for k in side_chosen:
            for r in _curve_rows(k, use_hours, side=side):
                tl = fmt_local(r["t"], ms=False)
                for f, v in r.items():
                    if f in ("t", "window_s") or v is None:
                        continue
                    w.writerow([repr(float(r["t"])), tl, sid, k, f, v])
                    n += 1
    if n == 0:
        return JSONResponse(status_code=409, content={"ok": False, "error": "已勾选的曲线暂无数据可导出"})
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="curves_{stamp}.csv"'})


@app.get("/api/export")
async def export(fmt: str = "json", quantity: Optional[str] = None) -> Response:
    """导出已累计的结果（JSON 全量 / CSV 扁平表）。"""
    if fmt not in ("json", "csv"):
        return JSONResponse(status_code=400, content={
            "ok": False, "error": f"未知导出格式 '{fmt}'（支持 csv / json）"})
    with RUNNER.lock:
        results = list(RUNNER.store)
    if not results:
        return JSONResponse(status_code=409, content={"ok": False, "error": "暂无结果可导出"})
    ts = time.strftime("%Y%m%d_%H%M%S")
    if fmt == "csv":
        import csv
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        sid = SIDE_SOURCE_ID[current_side()]
        w.writerow(["source_id", "t_ref", "quantity", "metric", "value", "unit", "window_s"])
        for r in results:
            for row in r.scalar_table():
                if quantity and row["quantity"] != quantity:
                    continue
                w.writerow([sid, r.t_ref, row["quantity"], row["metric"], row["value"],
                            row["unit"], row["window_s"]])
        return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="elec_result_{ts}.csv"'})
    payload = [r.to_dict() for r in results]
    if quantity:
        payload = [{**r, "quantities": {quantity: v for k, v in r["quantities"].items() if k == quantity}}
                   for r in payload]
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    return Response(content=body, media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="elec_result_{ts}.json"'})


@app.get("/api/selftest")
async def selftest(fs: float = 6400.0, freq: float = 50.0, pt: float = 100.0, ct: float = 15.0,
                   window: float = 1.0) -> Dict[str, Any]:
    """一键算法自检：在**当前运行环境**用解析解对账（模式 B 验收用）。"""
    t0 = time.time()
    checks = run_selftest(fs=fs, f=freq, pt=pt, ct=ct, duration_s=window)
    s = summarize(checks)
    s["duration_s"] = round(time.time() - t0, 3)
    # 运行环境必须如实显示：本地部署排障（Python 版本 / 操作系统）第一眼看这里。
    # 旧写法靠 os.popen("python -V") 且需要 PY_CMD，未设时留空；os.uname() 在 Windows 不存在。
    s["conditions"] = {"fs": fs, "f_nom": freq, "pt": pt, "ct": ct, "window_s": window,
                       "python": sys.version.split()[0],
                       "python_impl": platform.python_implementation(),
                       "platform": f"{platform.system()} {platform.release()} ({sys.platform})",
                       "numpy": np.__version__}
    s["checks"] = [c.to_dict() for c in checks]
    return s


@app.get("/api/probe")
async def probe(path: str) -> Dict[str, Any]:
    """探查 CSV（表头/编码/行数/推算采样率），供 UI 在启动前检查数据。"""
    try:
        import csv as _csv
        from elec_tool.sources.parsing import detect_encoding, parse_timestamps, read_header
        cfg = RUNNER.cfg
        p = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if os.path.isdir(p):
            files = sorted(f for f in os.listdir(p) if f.lower().endswith(".csv"))
            if not files:
                return {"ok": False, "error": f"目录 {p} 下没有 CSV 文件"}
            p = os.path.join(p, files[-1])
        if not os.path.isfile(p):
            return {"ok": False, "error": f"文件不存在：{p}"}
        enc = detect_encoding(p)
        header, enc2 = read_header(p, cfg.columns.encoding, cfg.columns.delimiter)
        # 首行解析不出表头 → 视为**无表头**数据行（与 iter_csv_blocks 同一规则）：
        # 采集器直写的 CSV（如 ``0/00/00 00:12:40.0000,290.17,...``）第一行就是数据。
        has_header = cfg.columns.looks_like_header(header)
        idx = cfg.columns.layout(header if has_header else None)      # 启用映射时只按 mapping；可能抛 ConfigError
        ts_c = idx.get("timestamp")
        ts: List[str] = []
        n_rows = 0
        with open(p, "r", encoding=enc2, newline="") as fh:
            rdr = _csv.reader(fh, delimiter=cfg.columns.delimiter)
            if has_header:
                next(rdr, None)
            for row in rdr:
                n_rows += 1
                if ts_c is not None and row and len(row) > ts_c and n_rows <= 5000:
                    ts.append(row[ts_c])
        from elec_tool.sources.parsing import file_tz_offset_h
        tz_h = file_tz_offset_h(cfg)
        info = parse_timestamps(ts[:3000], cfg.columns.timestamp_unit, tz_h)
        return {"ok": True, "path": p, "size_mb": round(os.path.getsize(p) / 1024 / 1024, 3),
                "encoding": enc, "header": header if has_header else None, "has_header": has_header,
                "first_row": None if has_header else header,
                "columns": idx, "rows": n_rows, "ncols": len(header),
                "mapping_enabled": cfg.columns.mapping_enabled,
                "unmapped": [cfg.columns.FIELD_NAMES[k] for k in cfg.columns.unmapped(idx)],
                "t_first": (float(info.t[0]) if info.t.size else None),
                "t_first_text": (ts[0] if ts else None),
                "file_time_utc": bool(cfg.source.file_time_utc), "tz_offset_h": tz_h,
                "t_first_local": (fmt_local(float(info.t[0]), ms=False) if len(info.t) else None),
                "ts_mode": info.mode, "fs_est": info.fs_est, "fs_configured": cfg.sampling.fs,
                "fs_deviation_pct": (abs(info.fs_est - cfg.sampling.fs) / cfg.sampling.fs * 100
                                     if info.fs_est == info.fs_est else None),
                "duration_s": n_rows / cfg.sampling.fs, "notes": info.notes}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


@app.get("/api/files")
async def list_files(sub: str = "data") -> Dict[str, Any]:
    """列出仓库内可选数据文件（仅列名与大小，不读内容）。"""
    base = sub if os.path.isabs(sub) else os.path.join(ROOT, sub)
    base = os.path.normpath(base)
    if not base.startswith(os.path.normpath(ROOT)):
        return {"ok": False, "error": "路径越界：只允许访问仓库内文件"}
    out = []
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            fp = os.path.join(base, name)
            if os.path.isfile(fp) and name.lower().endswith((".csv", ".txt")):
                out.append({"name": os.path.relpath(fp, ROOT), "size_mb": round(os.path.getsize(fp) / 1024 / 1024, 3),
                            "mtime": os.path.getmtime(fp)})
            elif os.path.isdir(fp):
                out.append({"name": os.path.relpath(fp, ROOT) + "/", "dir": True})
    return {"ok": True, "base": os.path.relpath(base, ROOT), "files": out}


# ------------------------------------------------------------------ 数据处理：离线 CSV 重采样

class _ResampleJobs:
    """单任务后台重采样：POST 启动（线程），GET 轮询进度/结果，POST cancel 取消。"""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.job: Optional[ResampleJob] = None
        self.thread: Optional[threading.Thread] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.params: Dict[str, Any] = {}
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None

    def running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            if self.running():
                return {"ok": False, "error": "已有重采样任务在运行，请等待完成或先取消"}
            self.job = ResampleJob()
            self.result, self.error = None, None
            self.params = dict(params)
            self.started_at, self.finished_at = time.time(), None
            job = self.job

            def run() -> None:
                try:
                    res = resample_csv(params["path"], params["fs_new"], params.get("out_dir") or "data",
                                       cfg=RUNNER.cfg, fs_src=params.get("fs_src") or None,
                                       method=params.get("method") or "linear",
                                       overwrite=bool(params.get("overwrite")), job=job, root=ROOT)
                    with self.lock:
                        self.result = res
                except Exception as exc:                    # 线程内异常必须回收给界面
                    with self.lock:
                        self.error = f"{type(exc).__name__}: {exc}" if not isinstance(exc, ResampleError) else str(exc)
                finally:
                    with self.lock:
                        self.finished_at = time.time()

            self.thread = threading.Thread(target=run, daemon=True, name="elec-resample")
            self.thread.start()
        return {"ok": True, "status": self.status()}

    def cancel(self) -> Dict[str, Any]:
        with self.lock:
            if self.job and self.running():
                self.job.cancel.set()
                return {"ok": True, "cancelling": True}
        return {"ok": True, "cancelling": False}

    def status(self) -> Dict[str, Any]:
        with self.lock:
            j = self.job
            return {
                "running": self.running(), "params": self.params,
                "progress": (j.progress if j else 0.0), "stage": (j.stage if j else "idle"),
                "rows_in": (j.rows_in if j else 0), "rows_out": (j.rows_out if j else 0),
                "result": self.result, "error": self.error,
                "started_at": self.started_at, "finished_at": self.finished_at,
                "elapsed_s": (round((self.finished_at or time.time()) - self.started_at, 2) if self.started_at else None),
            }


RESAMPLE = _ResampleJobs()


@app.post("/api/process/resample")
async def process_resample(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = payload or {}
    """启动离线 CSV 重采样后台任务。payload：path, fs_new, [fs_src], [method=linear|nearest|fft],
    [overwrite], [out_dir=data]。输出文件名 = 原名_re_<fs_new>.csv。"""
    path = str(payload.get("path") or "").strip()
    if not path:
        return {"ok": False, "error": "请填写源文件路径"}
    try:
        fs_new = float(payload.get("fs_new"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "目标采样率必须是数字"}
    if not fs_new > 0:
        return {"ok": False, "error": "目标采样率必须 > 0"}
    method = str(payload.get("method") or "linear")
    if method not in RESAMPLE_METHODS:
        return {"ok": False, "error": f"method 必须是 {RESAMPLE_METHODS} 之一"}
    fs_src = payload.get("fs_src")
    try:
        fs_src = float(fs_src) if fs_src not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        return {"ok": False, "error": "原采样率必须是数字或留空（自动推算）"}
    out_dir = str(payload.get("out_dir") or "data")
    out_abs = os.path.normpath(out_dir if os.path.isabs(out_dir) else os.path.join(ROOT, out_dir))
    if not out_abs.startswith(os.path.normpath(ROOT)):
        return {"ok": False, "error": "输出目录越界：只允许仓库内目录（默认 data）"}
    src_abs = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if not os.path.isfile(src_abs):
        return {"ok": False, "error": f"文件不存在：{path}"}
    return RESAMPLE.start({"path": path, "fs_new": fs_new, "fs_src": fs_src, "method": method,
                           "overwrite": bool(payload.get("overwrite")), "out_dir": out_dir})


@app.get("/api/process/resample")
async def process_resample_status() -> Dict[str, Any]:
    return {"ok": True, **RESAMPLE.status()}


@app.post("/api/process/resample/cancel")
async def process_resample_cancel() -> Dict[str, Any]:
    return RESAMPLE.cancel()


@app.get("/api/process/resample/preview")
async def process_resample_preview(path: str, fs_new: float) -> Dict[str, Any]:
    """只算输出文件名与是否已存在（界面即时提示用），不读数据。"""
    src_abs = path if os.path.isabs(path) else os.path.join(ROOT, path)
    name = resample_output_name(src_abs, fs_new)
    out = os.path.join(ROOT, "data", name)
    return {"ok": True, "out_name": name, "out_path": os.path.relpath(out, ROOT), "exists": os.path.exists(out),
            "src_exists": os.path.isfile(src_abs)}


# ------------------------------------------------------------------ WebSocket

WS_STATE_INTERVAL_S = 1.0   # state 定期推送周期（秒）；与 result 流量无关


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    RUNNER.clients.add(q)
    try:
        await ws.send_text(json.dumps({"type": "hello", "data": RUNNER.state()}, ensure_ascii=False))
        snap = RUNNER.snapshot(force=False)
        if snap:
            await ws.send_text(json.dumps({"type": "snapshot", "data": snap}, ensure_ascii=False))
        # F-23：state（samples_in / 数据时长 / 缓冲 / 输出次数…）必须**按时间**定期推送，
        # 不能只在队列空闲 1s 时才发——离线文件播放时 result 连续不断、队列永不空闲，
        # 顶栏「样本」与「数据源状态」汇总会一直停在启动瞬间，只能手动刷新。
        last_state = time.monotonic()
        while True:
            try:
                text = await asyncio.wait_for(q.get(), timeout=WS_STATE_INTERVAL_S)
                await ws.send_text(text)
            except asyncio.TimeoutError:
                pass
            now = time.monotonic()
            if now - last_state >= WS_STATE_INTERVAL_S:
                last_state = now
                try:
                    payload = json.dumps({"type": "state", "data": RUNNER.state()}, ensure_ascii=False)
                except Exception as exc:          # state() 出错不能让推送通道静默断掉（界面会停在旧状态）
                    payload = json.dumps({"type": "error", "message": f"state: {type(exc).__name__}: {exc}"}, ensure_ascii=False)
                await ws.send_text(payload)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception:
        pass
    finally:
        RUNNER.clients.discard(q)


# ------------------------------------------------------------------ 静态页面

def _asset_version() -> str:
    """前端资源版本号＝app.js/style.css/index.html 内容哈希前 10 位；文件一改 URL 就变，浏览器不可能再用旧缓存（F-42）。"""
    import hashlib
    h = hashlib.sha1()
    for name in ("app.js", "style.css", "index.html"):
        try:
            with open(os.path.join(STATIC_DIR, name), "rb") as fh:
                h.update(fh.read())
        except OSError:
            pass
    return h.hexdigest()[:10]


@app.get("/")
async def index() -> Response:
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as fh:
        html = fh.read()
    v = _asset_version()
    html = html.replace('href="/static/style.css"', f'href="/static/style.css?v={v}"') \
               .replace('src="/static/app.js"', f'src="/static/app.js?v={v}"')
    return Response(content=html, media_type="text/html",
                    headers={"Cache-Control": "no-store, max-age=0", "X-Asset-Version": v})


@app.middleware("http")
async def _no_stale_static(request, call_next):
    """静态资源一律 no-cache（每次向服务端校验 ETag）：F-42 用户浏览器拿着旧 app.js 点新按钮没有反应。"""
    resp = await call_next(request)
    p = request.url.path
    if p.startswith("/static/") or p in ("/", "/index.html"):
        resp.headers.setdefault("Cache-Control", "no-cache, max-age=0, must-revalidate")
    return resp


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="root")
