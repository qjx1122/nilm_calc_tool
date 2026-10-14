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
import os
import threading
import platform
import sys
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from contextlib import asynccontextmanager

import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from elec_tool import __version__
from elec_tool.config import (AppConfig, ConfigError, CURVE_KEYS, QUANTITY_KEYS, SourceConfig, WindowSpec,
                              load_or_default)
from elec_tool.engine import LiveEngine
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
        self.latest_full: Optional[MetricsResult] = None
        self.store: Deque[MetricsResult] = deque(maxlen=maxlen)
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.clients: Set[asyncio.Queue] = set()
        self.started_at: Optional[float] = None
        self.error: Optional[str] = None
        self.cfg_path: str = DEFAULT_CONFIG_PATH        # 启动时加载哪个文件
        self.persist_path: str = RUNTIME_CONFIG_PATH    # 界面改动写到哪个文件

    # ---------- 配置 ----------
    @property
    def cfg(self) -> AppConfig:
        with self.lock:
            if self.engine is not None:
                return self.engine.cfg
        return load_or_default(self.cfg_path)

    def set_cfg(self, cfg: AppConfig) -> None:
        cfg.validate()
        with self.lock:
            if self.engine is not None:
                # 运行中或已结束（离线文件读完）都走热更新：保留趋势历史与最近结果。
                # 旧写法对「已结束」的引擎整个重建 → 勾一下「保存曲线」24h 曲线和结果全部清空。
                self.engine.update_config(cfg)
            else:
                self.engine = LiveEngine(cfg, output_root=ROOT)
                self.engine.on_event = self._on_event
                self.engine.on_nilm_event = self._on_nilm_event
                self.latest = None

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
    def start(self, cfg: AppConfig, duration_s: Optional[float] = None) -> Dict[str, Any]:
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
            # 一次运行＝一个数据集：重启引擎必须清空历史，否则导出/趋势会把
            # 不同数据源、不同窗长的结果混在一张表里（误导性极强）。
            self.store.clear()
            self.engine = LiveEngine(cfg, output_root=ROOT)
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
                res = engine.poll_once()
                if res is not None:
                    with self.lock:
                        if self.engine is not engine:
                            return
                        self.latest = res
                        self.store.append(res)
                    self.broadcast({"type": "result", "data": res.to_dict()})
                elif engine.state.finished:
                    final = engine.flush_all()
                    if final is not None:
                        with self.lock:
                            if self.engine is not engine:
                                return
                            self.latest = final
                            self.latest_full = final
                            self.store.append(final)
                        self.broadcast({"type": "result", "data": final.to_dict()})
                    break
                else:
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
                "branch": (_branch_summary() if self.side == "bus" else None),
                "running": bool(self.thread and self.thread.is_alive() and not self.stop_event.is_set() and not self._thread_done),
                "paused": bool(self.pause_event.is_set() and self.thread and self.thread.is_alive() and not self.stop_event.is_set() and not self._thread_done),
                "pausable": bool(eng is not None and eng.cfg.source.kind == "csv_file"),
                "paused_total_s": round(self.paused_total_s + ((time.time() - self.paused_at) if self.paused_at else 0.0), 3),
                "finished": bool(st.get("finished")),
                "error": self.error,
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

    def snapshot(self, force: bool = True) -> Optional[Dict[str, Any]]:
        """取当前缓冲的全量结果（UI 首次加载/手动刷新）。"""
        with self.lock:
            eng = self.engine
            if eng is None:
                return self.latest.to_dict() if self.latest else None
            res = eng.snapshot_full() if force else self.latest
            if res is not None:
                self.latest_full = res
                return res.to_dict()
            return self.latest.to_dict() if self.latest else None


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
    """总线侧 /api/state 里的分路侧摘要（界面顶栏与数据源页用）。"""
    br = RUNNERS["branch"]
    bus = RUNNERS["bus"]
    try:
        enabled = bool(bus.cfg.branch.enabled)
    except Exception:
        enabled = False
    with br.lock:
        eng = br.engine
        running = bool(br.thread and br.thread.is_alive() and not br.stop_event.is_set() and not br._thread_done)
        st = eng.state if eng else None
        try:
            src = eng.cfg.source if eng else None
        except Exception:
            src = None
    return {
        "enabled": enabled, "label": SIDE_LABELS["branch"], "config_path": br.cfg_path,
        "running": running, "paused": bool(running and br.pause_event.is_set()),
        "finished": bool(st and st.finished), "error": br.error,
        "source_kind": (src.kind if src else None), "source_path": (src.path if src else None),
        "samples_in": int(st.samples_in) if st else 0,
        "data_t_end": (st.data_t_end if st else None),
        "events_total": int(getattr(st, "events_total", 0) or 0) if st else 0,
        "nilm_events_total": int(getattr(st, "nilm_events_total", 0) or 0) if st else 0,
    }


def _default_branch_cfg() -> AppConfig:
    """分路侧没有配置文件时的出厂值：与总线侧同模板，但输出目录分开、数据源留空。"""
    cfg = AppConfig()
    cfg.name = "分路侧设备电气量"
    cfg.source.kind = "simulator"; cfg.source.path = ""        # 出厂占位：界面「数据源」页改成 csv_file + 路径
    cfg.output.realtime_dir = "output/branch/realtime"; cfg.output.export_dir = "output/branch"
    cfg.events.events_dir = "output/branch/events"; cfg.nilm.nilm_dir = "output/branch/nilm"
    return cfg


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


def _init_branch_runner(bus_cfg: Optional[AppConfig]) -> None:
    br = RUNNERS["branch"]
    cfg_path, persist_path = _resolve_branch_cfg_paths(bus_cfg)
    br.cfg_path = cfg_path; br.persist_path = persist_path
    try:
        cfg = AppConfig.load(cfg_path) if os.path.isfile(cfg_path) else _default_branch_cfg().validate()
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
            bus.set_cfg(load_or_default(cfg_path))
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


def _start_branch_if_enabled(bus_cfg: AppConfig) -> Optional[Dict[str, Any]]:
    """总线侧启动后联动分路侧（仅 enabled 时）。返回分路侧启动结果；失败只记录、不影响总线侧。"""
    if not bus_cfg.branch.enabled:
        return {"ok": False, "skipped": True, "reason": "分路侧未启用"}
    br = RUNNERS["branch"]
    try:
        cfg = AppConfig.from_dict(br.cfg.to_dict())
        if cfg.source.kind in ("csv_file", "csv_tail") and cfg.source.path and not os.path.isabs(cfg.source.path):
            cand = os.path.join(ROOT, cfg.source.path)
            if os.path.exists(cand):
                cfg.source.path = cand
        br.start(cfg)
        br.error = None
        return {"ok": True, "source_kind": cfg.source.kind, "path": cfg.source.path}
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
                             "file_time_utc", "play_start_mode", "play_start_value", "file_speed")}
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
        RUNNER.start(cfg, duration_s=payload.get("duration_s"))
        out: Dict[str, Any] = {"ok": True, "side": current_side(), "config": cfg.to_dict()}
        if current_side() == "bus" and payload.get("with_branch", True):
            out["branch"] = _start_branch_if_enabled(cfg)
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


def _curve_rows(quantity: str, hours: Optional[float]) -> List[Dict[str, Any]]:
    with RUNNER.lock:
        eng = RUNNER.engine
        if not eng:
            return []
        return eng.calc.history.get(quantity, hours=hours)


def _curve_fields(rows: List[Dict[str, Any]]) -> List[str]:
    fields: List[str] = []
    for r in rows:
        for k in r:
            if k not in ("t",) and k not in fields:
                fields.append(k)
    return fields


def _curve_csv(quantity: str, rows: List[Dict[str, Any]]) -> str:
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf)
    fields = _curve_fields(rows)
    w.writerow(["t_epoch_s", "time_local", "quantity"] + fields)
    for r in rows:
        tl = fmt_local(r["t"])
        w.writerow([repr(float(r["t"])), tl, quantity] + [("" if r.get(f) is None else r.get(f)) for f in fields])
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
    for k in chosen:
        rows = _curve_rows(k, hours)
        if not rows:
            empty.append(k)
            continue
        fp = os.path.join(target, f"{k}.csv")
        with open(fp, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(_curve_csv(k, rows))
        files.append({"quantity": k, "path": _display_path(fp), "rows": len(rows),
                      "t_first": rows[0]["t"], "t_last": rows[-1]["t"]})
    if not files:
        try:
            os.rmdir(target)
        except OSError:
            pass
        return JSONResponse(status_code=409, content={
            "ok": False, "error": "已勾选的曲线暂无数据可保存（请先启动数据源并累计 ≥1 个窗）",
            "skipped": skipped, "empty": empty})
    return {"ok": True, "dir": _display_path(target), "files": files,
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
        return Response(content=_curve_csv(quantity, rows), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="curve_{quantity}_{stamp}.csv"'})
    chosen, _ = _selected_curves(None, cfg)
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["t_epoch_s", "time_local", "quantity", "field", "value"])
    n = 0
    for k in chosen:
        for r in _curve_rows(k, use_hours):
            tl = fmt_local(r["t"], ms=False)
            for f, v in r.items():
                if f in ("t", "window_s") or v is None:
                    continue
                w.writerow([repr(float(r["t"])), tl, k, f, v])
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
        w.writerow(["t_ref", "quantity", "metric", "value", "unit", "window_s"])
        for r in results:
            for row in r.scalar_table():
                if quantity and row["quantity"] != quantity:
                    continue
                w.writerow([r.t_ref, row["quantity"], row["metric"], row["value"],
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
