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
from elec_tool.config import (AppConfig, ConfigError, QUANTITY_KEYS, SourceConfig, WindowSpec,
                              load_or_default)
from elec_tool.engine import LiveEngine
from elec_tool.metrics import MetricsResult
from elec_tool.selftest import run_selftest, summarize

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATIC_DIR = os.path.join(HERE, "static")
DEFAULT_CONFIG_PATH = os.path.join(ROOT, "configs", "default.json")
# 出厂模板 configs/default.json 必须保持干净（入库、可回溯）；用户在界面里改的
# 配置与数据源选择落到 configs/runtime.json（gitignore），下次启动优先加载它。
RUNTIME_CONFIG_PATH = os.path.join(ROOT, "configs", "runtime.json")


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

class EngineRunner:
    """在后台线程跑引擎，把结果广播给 WebSocket 客户端。"""

    def __init__(self, maxlen: int = 2000):
        self.lock = threading.RLock()
        self.engine: Optional[LiveEngine] = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
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
            if self.engine is not None and self.thread and self.thread.is_alive():
                self.engine.update_config(cfg)
            else:
                self.engine = LiveEngine(cfg)
                self.latest = None

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
            self.error = None
            self.latest = None
            self.latest_full = None
            # 一次运行＝一个数据集：重启引擎必须清空历史，否则导出/趋势会把
            # 不同数据源、不同窗长的结果混在一张表里（误导性极强）。
            self.store.clear()
            self.engine = LiveEngine(cfg)
            self.started_at = time.time()
            # 引擎与停止事件按值传给线程：线程内绝不重读 self.engine
            self.thread = threading.Thread(target=self._run,
                                           args=(duration_s, self.engine, self.stop_event),
                                           daemon=True, name="elec-engine")
            self.thread.start()
        return {"ok": True, "source_kind": cfg.source.kind}

    def _run(self, duration_s: Optional[float], engine: LiveEngine,
             stop_event: threading.Event) -> None:
        """引擎线程。engine/stop_event 都是本轮私有对象，被取代后自行退场。"""
        try:
            engine.start()
            while not stop_event.is_set():
                with self.lock:
                    stale = self.engine is not engine
                if stale:                       # 已被新一轮取代：立刻退场，不再产出
                    return
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
                if duration_s and (time.time() - (self.started_at or time.time())) > duration_s:
                    break
            self.broadcast({"type": "state", "data": self.state()})
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

    def stop(self, quiet: bool = False) -> None:
        with self.lock:
            self.stop_event.set()
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
            st = eng.state.to_dict() if eng else {}
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
                "running": bool(self.thread and self.thread.is_alive() and not self.stop_event.is_set()),
                "finished": bool(st.get("finished")),
                "error": self.error,
                "engine": st,
                "source": src,
                "config": cfg.to_dict(),
                "quantities": list(QUANTITY_KEYS),
                "latest_keys": latest_keys,
                "latest_t_ref": self.latest.t_ref if self.latest else None,
                "stored_results": len(self.store),
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


RUNNER = EngineRunner()


async def _startup() -> None:
    RUNNER.bind_loop(asyncio.get_running_loop())
    cfg_path, persist_path = _resolve_cfg_paths()
    RUNNER.cfg_path = cfg_path
    RUNNER.persist_path = persist_path
    env_cfg = os.environ.get("ELEC_TOOL_CONFIG")
    try:
        if env_cfg:
            RUNNER.set_cfg(AppConfig.from_dict(json.loads(env_cfg)))
        else:
            RUNNER.set_cfg(load_or_default(cfg_path))
    except Exception as exc:
        RUNNER.error = f"配置初始化失败：{type(exc).__name__}: {exc}"
    auto = os.environ.get("ELEC_TOOL_AUTOSTART", "").strip()
    if auto:
        try:
            RUNNER.start(RUNNER.cfg)
        except Exception as exc:
            RUNNER.error = f"自动启动失败：{type(exc).__name__}: {exc}"


@asynccontextmanager
async def lifespan(_app: "FastAPI"):
    await _startup()
    yield
    RUNNER.stop(quiet=True)


app = FastAPI(title="电力系统电气量计算工具", version=__version__, lifespan=lifespan)


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
                             "struct_fmt", "struct_fields")}
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
        return {"ok": True, "config": cfg.to_dict()}
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.post("/api/engine/stop")
async def engine_stop() -> Dict[str, Any]:
    RUNNER.stop()
    return {"ok": True, "state": RUNNER.state()}


@app.get("/api/result")
async def get_result(full: bool = True) -> Any:
    data = RUNNER.snapshot(force=full)
    if data is None:
        return JSONResponse(status_code=409, content={
            "ok": False, "error": "尚无计算结果：请先在「数据源与控制」启动数据源"})
    return data


@app.get("/api/history/{quantity}")
async def get_history(quantity: str, n: int = 300) -> Any:
    if quantity not in QUANTITY_KEYS:
        return JSONResponse(status_code=400, content={
            "ok": False, "error": f"未知电气量 '{quantity}'，可用：{list(QUANTITY_KEYS)}"})
    with RUNNER.lock:
        eng = RUNNER.engine
        hist = eng.calc.history.get(quantity, n) if eng else []
    return {"quantity": quantity, "points": hist, "count": len(hist)}


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
        idx = cfg.columns.resolve(header)
        ts: List[str] = []
        n_rows = 0
        with open(p, "r", encoding=enc2, newline="") as fh:
            rdr = _csv.reader(fh, delimiter=cfg.columns.delimiter)
            next(rdr, None)
            for row in rdr:
                n_rows += 1
                if row and len(row) > idx["timestamp"] and n_rows <= 5000:
                    ts.append(row[idx["timestamp"]])
        info = parse_timestamps(ts[:3000], cfg.columns.timestamp_unit)
        return {"ok": True, "path": p, "size_mb": round(os.path.getsize(p) / 1024 / 1024, 3),
                "encoding": enc, "header": header, "columns": idx, "rows": n_rows,
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


# ------------------------------------------------------------------ WebSocket

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
        while True:
            try:
                text = await asyncio.wait_for(q.get(), timeout=1.0)
                await ws.send_text(text)
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "state", "data": RUNNER.state()}, ensure_ascii=False))
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception:
        pass
    finally:
        RUNNER.clients.discard(q)


# ------------------------------------------------------------------ 静态页面

@app.get("/")
async def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="root")
