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
import shutil
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
from elec_tool.wave_preview import WaveError
from elec_tool.nilm_tuning import TuneError, build_cli_command, export_tuned_config, run_tune, tune_result_path
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

# ---------- v0.59：离线文件播放 → 每次运行一个输出目录 output/<yyyyMMdd_HHmmss>/ ----------
# 实时曲线 / 事件 / 负荷事件 CSV 与两侧当前配置（config_bus.json / config_branch.json）都写在里面；
# 总线侧与分路侧共用同一目录：一侧启动时若另一侧正在运行（含联动启动）就沿用它的目录，否则新建。
# 环境变量 ELEC_TOOL_RUN_DIRS=0 关闭（回到 output/realtime 等固定目录；测试隔离用），ELEC_TOOL_OUTPUT_DIR 改根目录。
_RUN_DIR_LOCK = threading.Lock()


def _run_dirs_enabled() -> bool:
    return os.environ.get("ELEC_TOOL_RUN_DIRS", "1").strip() not in ("0", "false", "off", "")


def _output_base() -> str:
    d = os.environ.get("ELEC_TOOL_OUTPUT_DIR", "").strip() or os.path.join(ROOT, "output")
    return d if os.path.isabs(d) else os.path.join(ROOT, d)


def _alloc_run_dir(side: str) -> str:
    """本侧启动离线文件播放时的输出目录：另一侧正在运行 → 沿用其目录；否则新建 output/<本地时间 yyyyMMdd_HHmmss>/。"""
    with _RUN_DIR_LOCK:
        other = RUNNERS.get("branch" if side == "bus" else "bus") if "RUNNERS" in globals() else None
        if other is not None:
            with other.lock:
                eng = other.engine
                alive = bool(other.thread and other.thread.is_alive() and not other.stop_event.is_set() and not other._thread_done)
            if alive and eng is not None and getattr(eng, "run_dir", None):
                return eng.run_dir
        base = _output_base()
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())   # v0.60：yyyyMMdd_HHmmss
        path = os.path.join(base, stamp)
        k = 1
        while os.path.exists(path):                      # 同一秒内再次启动：加序号
            path = os.path.join(base, f"{stamp}_{k}"); k += 1
        os.makedirs(path, exist_ok=True)
        return path


def _dump_run_configs(run_dir: str, started_side: str) -> List[str]:
    """把两侧**当前的配置文件原封不动复制**进运行目录（v0.60）：config_bus.json / config_branch.json＝本侧持久化文件
    （configs/runtime.json / branch_runtime.json；尚不存在时取启动加载的文件，如 default.json / branch.json）的逐字节副本，
    不重新序列化、不补默认键；两个文件都不存在时才退回写运行配置的 to_dict() 并在 run_info 标明。
    覆盖写，始终是最新一次启动时的文件；另写 run_info.json（启动时刻、启动侧、两侧数据源、配置来源文件）。失败只记日志。"""
    written: List[str] = []
    info_path = os.path.join(run_dir, "run_info.json")
    info: Dict[str, Any] = {}
    if os.path.isfile(info_path):                         # 另一侧已建目录：保留首次信息，只追加本次启动记录
        try:
            with open(info_path, "r", encoding="utf-8") as fh:
                info = json.load(fh) or {}
        except Exception:
            info = {}
    info.setdefault("created_local", fmt_local(time.time()))
    info.setdefault("started_side", started_side)
    info.setdefault("starts", []).append({"side": started_side, "at_local": fmt_local(time.time())})
    info["sides"] = {}
    for s in ("bus", "branch"):
        r = RUNNERS.get(s) if "RUNNERS" in globals() else None
        if r is None:
            continue
        try:
            c = r.cfg
            p = os.path.join(run_dir, f"config_{s}.json")
            src_file = next((x for x in (r.persist_path, r.cfg_path) if x and os.path.isfile(x)), None)
            if src_file:
                shutil.copyfile(src_file, p)                 # 原封不动（字节级复制）
                how = "verbatim_copy"
            else:
                with open(p, "w", encoding="utf-8") as fh:
                    json.dump(c.to_dict(), fh, ensure_ascii=False, indent=2)
                how = "runtime_dump"
            written.append(p)
            info["sides"][s] = {"source_kind": c.source.kind, "source_path": c.source.path, "source_id": SIDE_SOURCE_ID[s],
                                "config_file": os.path.basename(p), "config_copied_from": _display_path(src_file) if src_file else None,
                                "config_mode": how}
        except Exception as exc:
            log.warning("运行目录写配置失败（%s）：%s", s, exc)
    try:
        with open(info_path, "w", encoding="utf-8") as fh:
            json.dump(info, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.warning("运行目录写 run_info.json 失败：%s", exc)
    return written



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
        _warm_line_index(cfg)

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
            run_id = int(getattr(self.engine, "run_id", 0) or 0) if self.engine is not None else 0
            run_dir = getattr(self.engine, "run_dir", None) if self.engine is not None else None
        sid = str(SIDE_SOURCE_ID[self.side])
        entry = {"side": self.side, "source_id": int(sid), "saved_at": time.time(), "saved_at_local": fmt_local(time.time()),
                 "source_kind": kind, "source_path": src, "t_ref": d.get("t_ref"), "run_id": run_id, "run_dir": run_dir, "result": d}
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
                text = json.dumps(data, ensure_ascii=False)       # v0.82：dumps 走 C 编码器；json.dump 逐块 iterencode 慢约 5 倍
                with open(tmp, "w", encoding="utf-8") as fh:
                    fh.write(text)
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
        # v0.30：以 last_result.json 记录的「上次播放结束时的数据时刻」t_ref 为锚点，曲线 / 事件 / 负荷辨识事件统一取
        # [t_ref - hours, t_ref]。没有快照（或快照无 t_ref）时退回旧行为（目录中最新时标）。
        ent = self.read_last_result()
        t_anchor: Optional[float] = None
        run_id: Optional[int] = None
        if ent and isinstance(ent.get("t_ref"), (int, float)):
            t_anchor = float(ent["t_ref"])
            out["t_anchor"] = t_anchor; out["t_anchor_local"] = fmt_local(t_anchor)
        if ent and ent.get("run_id"):
            run_id = int(ent["run_id"])                    # v0.32：只取上次那一次运行写的行（旧文件无 run_id 列仍按时间窗）
            out["run_id"] = run_id
        if ent and ent.get("run_dir") and os.path.isdir(str(ent["run_dir"])):
            rdir = str(ent["run_dir"])                        # v0.59：上次是离线文件播放 → 都在运行目录里；v0.60：三个子目录
            rt_dir, ev_dir, nl_dir = os.path.join(rdir, "realtime"), os.path.join(rdir, "events"), os.path.join(rdir, "nilm")
            out["run_dir"] = _display_path(rdir)
        if result and ent:
            with self.lock:
                self.latest_merged = ent["result"]
                self.latest_full = None
            out["result"] = True
            out["result_saved_at_local"] = ent.get("saved_at_local")
            out["result_source"] = ent.get("source_path") or ent.get("source_kind")
        t_first = t_last = None
        if curves:
            res = replay_load.load_curves(absd(rt_dir), sid, use_hours, max_points=int(cfg.output.history_max_points), t_anchor=t_anchor, run_id=run_id)
            for k, recs in res["records"].items():
                eng.calc.history.load_records(k, recs, replace=True)
            out["curves"] = res["points"]; out["curve_files"] = [{**f, "path": _display_path(f["path"])} for f in res["files"]]
            t_first, t_last = res["t_first"], res["t_last"]
            if not res["records"]:
                out["notes"].append(f"实时落盘目录 {rt_dir} 下没有本侧（source_id={sid}）的曲线数据")
        # 事件 / 负荷辨识事件与曲线取同一时间窗：曲线最新点往前 hours；没有曲线时不按时间过滤（只受 max_log 限制）
        t_ref_win = t_anchor if t_anchor is not None else t_last
        t_from = (t_ref_win - use_hours * 3600.0) if t_ref_win is not None else None
        t_to = t_anchor                                           # 有锚点时锚点之后的事件（属于别的播放）不取
        if events:
            evs = replay_load.load_events(absd(ev_dir), sid, t_from=t_from, limit=int(cfg.events.max_log), t_to=t_to, run_id=run_id)
            out["events"] = eng.detector.load_events(evs, replace=True)
            for d in evs:
                t_first = d["start_t"] if t_first is None else min(t_first, d["start_t"])
                t_last = d["start_t"] if t_last is None else max(t_last, d["start_t"])
        if nilm:
            nevs = replay_load.load_nilm_events(absd(nl_dir), sid, t_from=t_from, limit=int(cfg.nilm.max_log), t_to=t_to, run_id=run_id)
            out["nilm_events"] = eng.nilm.load_events(nevs, replace=True)
        out["t_first"] = t_first; out["t_last"] = t_last
        out["t_first_local"] = fmt_local(t_first) if t_first is not None else None
        out["t_last_local"] = fmt_local(t_last) if t_last is not None else None
        out["loaded_at"] = time.time(); out["loaded_at_local"] = fmt_local(out["loaded_at"])
        self.loaded_last = {k: out.get(k) for k in ("source_id", "hours", "curves", "events", "nilm_events", "t_first", "t_last", "t_anchor", "t_anchor_local", "run_id",
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
        _warm_line_index(cfg)
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
            run_dir = _alloc_run_dir(self.side) if (cfg.source.kind == "csv_file" and _run_dirs_enabled()) else None
            self.engine = LiveEngine(cfg, output_root=ROOT, run_dir=run_dir)
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
        if run_dir:
            _dump_run_configs(run_dir, self.side)
        return {"ok": True, "source_kind": cfg.source.kind, "run_dir": (_display_path(run_dir) if run_dir else None)}

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
        if not self.clients:                      # v0.82：没有 WebSocket 客户端时不做 json.dumps（省事件循环线程 CPU / GIL）
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
                "run_dir": (_display_path(eng.run_dir) if eng is not None and getattr(eng, "run_dir", None) else None),
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
    hide_ui = False
    if side == "branch":
        try:
            enabled = bool(bus.cfg.branch.enabled)
            hide_ui = bool(getattr(bus.cfg.branch, "hide_ui", False))      # v0.33：隐藏分路侧界面
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
        "side": side, "enabled": enabled, "hide_ui": hide_ui, "label": SIDE_LABELS[side], "config_path": br.cfg_path,
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


def _warm_line_index(cfg: AppConfig) -> None:
    """v0.91：本侧为离线文件源时，后台预建该文件的行索引（周波窗右键定位 / 文件信息共用），首次右键不必等整文件扫描。"""
    try:
        if cfg.source.kind == "csv_file" and str(cfg.source.path or "").strip():
            from elec_tool.line_index import warm
            warm(_abs_path(cfg.source.path))
    except Exception as exc:                      # 预热失败不影响任何功能
        log.debug("行索引预热跳过：%s", exc)


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
    def _in_window(txt: str) -> float:
        # v0.70：与数据源页其它时间输入一致：完整日期时间 / epoch 秒 / 只写 HH:MM:SS（＝公共时间段起点当天的该时刻）
        from elec_tool.config import parse_play_start as _pps
        from elec_tool.timefmt import local_tod_s
        kind, v = _pps("time", txt)
        return float(v) if kind == "abs" else t_start - local_tod_s(t_start) + float(v)
    txt = str(bus_cfg.branch.common_start or "").strip()
    if txt:
        ps = _in_window(txt)
        if not (t_start <= ps < t_end):
            raise ConfigError(f"自定义播放起始时间 {txt} 不在公共时间段 {fmt_local(t_start)} → {fmt_local(t_end)} 内")
        out["play_start"] = ps; out["play_start_source"] = "自定义播放起始时间"
    out["play_end"] = t_end; out["play_end_source"] = "公共时间段终点"
    txe = str(getattr(bus_cfg.branch, "common_end", "") or "").strip()
    if txe:
        pe = _in_window(txe)
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


def _start_branch_if_enabled(bus_cfg: AppConfig, pace_clock=None, br_cfg: Optional[AppConfig] = None) -> Optional[Dict[str, Any]]:
    """总线侧启动后联动分路侧（仅 enabled 时）。返回分路侧启动结果；失败只记录、不影响总线侧。

    v0.16：分路侧输入方式与总线侧同样有 4 种（csv_file / csv_tail / tcp / simulator），各自独立配置；
    两侧都是离线文件时共用节拍钟（倍速同步、严格同步播放）并可按公共时间段播放；其它组合各自按自身配置启动。
    """
    if not bus_cfg.branch.enabled:
        return {"ok": False, "skipped": True, "reason": "分路侧未启用"}
    br = RUNNERS["branch"]
    try:
        cfg = AppConfig.from_dict((br_cfg or br.cfg).to_dict())
        if cfg.source.kind in ("csv_file", "csv_tail") and not cfg.source.path:
            raise ConfigError(f"分路侧 {cfg.source.kind} 需要文件路径（source.path）")
        if cfg.source.kind in ("csv_file", "csv_tail") and cfg.source.path and not os.path.isabs(cfg.source.path):
            cand = os.path.join(ROOT, cfg.source.path)
            if os.path.exists(cand):
                cfg.source.path = cand
        both_file = bus_cfg.source.kind == "csv_file" and cfg.source.kind == "csv_file"
        clock = None
        follow = bool(both_file and cfg.source.file_speed_follow)
        own_speed = float(cfg.source.file_speed or 0.0)
        if follow:
            # v0.85：默认随总线侧倍速——共用节拍钟（倍速一致、严格同步）；source.file_speed_follow=false 时
            # 按分路侧自己的 file_speed 独立限速（Runner.start 自建节拍钟，不与总线侧互锁）
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
        sr = br.start(cfg, pace_clock=clock, play_user=play_user)
        eff_speed = float(cfg.source.file_speed or 0.0)
        if follow:
            # 源对象已按总线侧倍速建好；运行配置里仍保留分路侧自己的 file_speed（随总线侧只是本次生效，不改分路侧配置）
            cfg.source.file_speed = own_speed
        br.error = None
        return {"ok": True, "source_kind": cfg.source.kind, "path": cfg.source.path, "synced_pace": follow,
                "file_speed": eff_speed, "run_dir": sr.get("run_dir")}
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
    return _preview_common_window({})


@app.post("/api/common_window/preview")
async def post_common_window_preview(payload: Optional[Dict[str, Any]] = None) -> Any:
    """v0.70：按**界面当前值**预览公共时间段（不启动、不写配置）。body 与 /api/engine/start 同形：
    总线侧 source 字段 + ``branch``（联动参数）+ ``branch_source``（分路侧数据源字段）。"""
    return _preview_common_window(payload or {})


def _preview_common_window(payload: Dict[str, Any]) -> Any:
    try:
        d = RUNNERS["bus"].cfg.to_dict()
        d["source"].update({k: v for k, v in payload.items() if k in _START_SRC_KEYS})
        if isinstance(payload.get("branch"), dict):
            d.setdefault("branch", {}).update({k: v for k, v in payload["branch"].items() if k in _START_BRANCH_KEYS})
        bus_cfg = AppConfig.from_dict(d)
        if bus_cfg.source.kind in ("csv_file", "csv_tail") and bus_cfg.source.path and not os.path.isabs(bus_cfg.source.path):
            cand = os.path.join(ROOT, bus_cfg.source.path)
            if os.path.exists(cand):
                bus_cfg.source.path = cand
        bso = payload.get("branch_source") if isinstance(payload.get("branch_source"), dict) else None
        br_cfg = _branch_cfg_for_start({k: v for k, v in (bso or {}).items() if k in _START_SRC_KEYS})
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
        persisted = False
        _LAST_PERSIST_CHANGES[current_side()] = []
        if os.environ.get("ELEC_TOOL_PERSIST_CONFIG", "1") == "1":
            try:
                _persist(cfg, payload); persisted = True
            except Exception:
                pass
        changed = list(_LAST_PERSIST_CHANGES.get(current_side(), []))
        return {"ok": True, "config": cfg.to_dict(), "config_file_updated": persisted,
                "config_file": _display_path(RUNNER.persist_path),
                # v0.75：本次实际写入文件的键（原文件基础上只改这些；空＝文件内容未变）
                "config_file_changes": changed}
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _side_default_cfg_file() -> Optional[str]:
    """本侧「现有路径」的配置文件：持久化文件（runtime.json / branch_runtime.json）存在则取它，否则取启动时加载的文件。"""
    for pth in (RUNNER.persist_path, RUNNER.cfg_path):
        if pth and os.path.isfile(pth):
            return pth
    return RUNNER.persist_path or RUNNER.cfg_path or None


@app.get("/api/config/file")
async def get_config_file() -> Dict[str, Any]:
    """v0.81：本侧配置文件路径（界面「从文件加载配置」输入框的默认值）。分路侧经 ``/api/branch/config/file``。"""
    d = _side_default_cfg_file()
    return {"ok": True, "side": current_side(), "path": _display_path(d) if d else "", "exists": bool(d and os.path.isfile(d)),
            "persist_path": _display_path(RUNNER.persist_path) if RUNNER.persist_path else "",
            "load_path": _display_path(RUNNER.cfg_path) if RUNNER.cfg_path else ""}


@app.post("/api/config/load_file")
async def load_config_file(payload: Optional[Dict[str, Any]] = None) -> Any:
    """v0.81：从指定路径的 JSON 配置文件加载**本侧**配置并热更新到运行中的引擎（分路侧经 ``/api/branch/config/load_file``）。

    body：``{path?: str, persist?: bool}``。``path`` 空＝本侧现有路径（持久化文件存在则取它，否则取启动时加载的文件）；
    相对路径相对仓库根解释。文件须是合法的 AppConfig JSON（``AppConfig.from_dict`` 规范化 + ``validate``；
    侧别强制项 output.source_id 与共享输出目录由 ``set_cfg`` 统一处理）。默认**只加载到运行配置、不写配置文件**；
    ``persist=true`` 时再以本侧配置文件为基准只写入与其不同的项（同「保存本侧配置」规则）。"""
    payload = payload or {}
    raw = str(payload.get("path") or "").strip()
    path = os.path.abspath(raw if os.path.isabs(raw) else os.path.join(ROOT, raw)) if raw else _side_default_cfg_file()
    if not path:
        return JSONResponse(status_code=400, content={"ok": False, "error": "未指定配置文件路径，且本侧没有现有配置文件"})
    if not os.path.isfile(path):
        return JSONResponse(status_code=400, content={"ok": False, "error": f"配置文件不存在：{_display_path(path)}"})
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if not isinstance(doc, dict):
            raise ConfigError("配置文件顶层必须是 JSON 对象")
        cfg = AppConfig.from_dict(doc)
        RUNNER.set_cfg(cfg)
    except json.JSONDecodeError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"配置文件不是合法 JSON：{exc}"})
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    persisted = False
    warning = ""
    _LAST_PERSIST_CHANGES[current_side()] = []
    if bool(payload.get("persist")) and os.environ.get("ELEC_TOOL_PERSIST_CONFIG", "1") == "1":
        try:
            _persist(RUNNER.cfg, RUNNER.cfg.to_dict()); persisted = True
        except Exception as exc:
            warning = f"已加载到运行配置，但写入配置文件失败：{exc}"
    return {"ok": True, "config": RUNNER.cfg.to_dict(), "loaded_from": _display_path(path), "side": current_side(),
            "same_as_config_file": os.path.abspath(path) == os.path.abspath(RUNNER.persist_path or ""),
            "config_file_updated": persisted, "config_file": _display_path(RUNNER.persist_path),
            "config_file_changes": list(_LAST_PERSIST_CHANGES.get(current_side(), [])), "warning": warning}


def _persist_base_doc() -> Dict[str, Any]:
    """「保存配置」的落盘基准：本侧持久化文件（runtime.json / branch_runtime.json）的**原始 JSON 文本**；
    文件尚不存在时退回本侧启动时的加载文件（出厂 default.json / 分路模板），再不存在才是空字典（写出完整默认配置）。"""
    for pth in (RUNNER.persist_path, RUNNER.cfg_path):
        if pth and os.path.isfile(pth):
            with open(pth, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            if isinstance(doc, dict):
                return doc
    return {}


_DEL = object()     # patch 里有、规范化配置里没有的键 ⇒ 从文件中删除（如 series_hidden 送空列表＝取消该项）


def _patch_pick(patch: Any, norm: Any) -> Any:
    """按 patch 的键形状，从 norm（AppConfig.to_dict() 规范化结果）取值：
    * 字典递归；叶子取规范化后的值（类型/取整与内存配置一致）；
    * patch 里有而 norm 里没有的键 → ``_DEL``（AppConfig 不认识的垃圾键不写入；已被规范化删除的映射项从文件里同步删掉）。"""
    if isinstance(patch, dict) and isinstance(norm, dict):
        out: Dict[str, Any] = {}
        for k, v in patch.items():
            out[k] = _patch_pick(v, norm[k]) if k in norm else _DEL
        return out
    return norm


def _apply_patch(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if v is _DEL:
            dst.pop(k, None)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            _apply_patch(dst[k], v)
        elif isinstance(v, dict):
            dst[k] = {}
            _apply_patch(dst[k], v)
        else:
            dst[k] = v


def _dict_diff(old: Any, new: Any) -> Any:
    """new 相对 old 变化的叶子（嵌套字典形状）；无变化返回 {}。"""
    if isinstance(old, dict) and isinstance(new, dict):
        out: Dict[str, Any] = {}
        for k, v in new.items():
            if k not in old:
                out[k] = v
            else:
                d = _dict_diff(old[k], v)
                if d != {} or not isinstance(d, dict):
                    out[k] = d
        return out
    return {} if old == new else new


def _detect_indent(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                n = len(line) - len(line.lstrip(" "))
                if n > 0:
                    return n
    except Exception:
        pass
    return 2


def _persist(cfg: AppConfig, patch: Optional[Dict[str, Any]] = None) -> None:
    """把**本次改动**写进运行时配置文件（v0.63）：读原文件 → 只深合并 patch 对应的键 → 写回。

    * 原文件里其它键（含 AppConfig 不认识的自定义键）与键顺序、缩进原样保留；
    * 启动参数 / 负荷辨识「套用」等**未经保存**的运行期改动不随本次保存落盘；
    * 服务启动后用户在外部手改的内容不会被内存配置覆盖；
    * patch 为 None ＝ 显式要求整份落盘（兼容旧调用）。
    路径尽量存成相对仓库根的形式，换机器/换目录仍可用。"""
    out = AppConfig.from_dict(cfg.to_dict())
    out.source.play_end_time = ""                 # 运行期自动字段，不落盘
    sp = out.source.path or ""
    if sp.startswith(ROOT + os.sep):
        out.source.path = os.path.relpath(sp, ROOT)
    out.validate()
    norm = out.to_dict()
    path = RUNNER.persist_path
    if patch is None:
        doc = _persist_base_doc()
        _deep_update(doc, norm)
    else:
        doc = _persist_base_doc()
        sel = _patch_pick(patch, norm)
        if isinstance(sel, dict) and "source" in sel and isinstance(sel["source"], dict):
            sel["source"].pop("play_end_time", None)
        if not doc:                                # 无任何基准文件：写完整当前配置（其中已含本次改动）
            doc = norm
        else:
            # v0.75：只落盘**与原文件不同**的叶子——patch 里值未变的键不碰（文件里原有写法 / 顺序原样），
            # 整份送回（导出页「保存配置」）时也只写真正变化的项
            sel = _drop_unchanged(sel, doc, _BUILTIN_DEFAULTS)
            # output.source_id 由侧别在运行期强制（0 总线 / 1 分路），文件里没写就不补写
            o = sel.get("output") if isinstance(sel, dict) else None
            if isinstance(o, dict) and "source_id" not in (doc.get("output") or {}) and o.get("source_id") == SIDE_SOURCE_ID.get(current_side()):
                o.pop("source_id", None)
                if not o:
                    sel.pop("output", None)
            _LAST_PERSIST_CHANGES[current_side()] = _flat_keys(sel)
            if not sel:
                return
            _apply_patch(doc, sel)
    AppConfig.from_dict(json.loads(json.dumps(doc))).validate()   # 合并结果必须仍是合法配置
    indent = _detect_indent(path) if os.path.isfile(path) else 2
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=indent) + "\n")
    os.replace(tmp, path)


_LAST_PERSIST_CHANGES: Dict[str, List[str]] = {}     # v0.75：最近一次保存实际写入文件的键（按侧），供 PUT /api/config 回显


def _drop_unchanged(sel: Any, doc: Any, dflt: Any = None) -> Any:
    """去掉 sel（_patch_pick 结果）里与原文件 doc 取值相同的叶子；_DEL 只在文件里确有该键时保留。
    v0.75.1：文件里**没有**该键、而取值又等于程序内置默认值（dflt）的叶子也不写——文件原本靠默认值生效，
    「不改任何值直接点保存」时文件一字不动；只有真正改成非默认值才把该键补进文件。"""
    if isinstance(sel, dict) and isinstance(doc, dict):
        out: Dict[str, Any] = {}
        dd = dflt if isinstance(dflt, dict) else {}
        for k, v in sel.items():
            if v is _DEL:
                if k in doc:
                    out[k] = v
            elif isinstance(v, dict) and isinstance(doc.get(k), dict):
                d = _drop_unchanged(v, doc[k], dd.get(k))
                if d:
                    out[k] = d
            elif isinstance(v, dict) and k not in doc and isinstance(dd.get(k), dict):
                d = _drop_unchanged(v, {}, dd.get(k))
                if d:
                    out[k] = d
            elif k in doc and doc[k] == v:
                continue
            elif k not in doc and k in dd and dd[k] == v:
                continue
            else:
                out[k] = v
        return out
    return sel


_BUILTIN_DEFAULTS: Dict[str, Any] = AppConfig.from_dict({}).to_dict()   # 程序内置默认值（不依赖任何文件）


def _flat_keys(sel: Any, prefix: str = "") -> List[str]:
    if isinstance(sel, dict):
        out: List[str] = []
        for k, v in sel.items():
            out += _flat_keys(v, f"{prefix}{k}.")
        return out
    return [prefix[:-1] + ("(删除)" if sel is _DEL else "")]


def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v


_START_SRC_KEYS = ("kind", "path", "host", "port", "frame", "block_samples",
                   "poll_interval_s", "tail_from_end", "sim_speed", "watch_dir_newest",
                   "struct_fmt", "struct_fields", "custom_time", "custom_time_start",
                   "file_time_utc", "play_start_mode", "play_start_value", "file_speed", "file_speed_follow",
                   "play_window", "play_window_start", "play_window_end")
# v0.70：总线侧启动时可随请求覆盖的分路侧联动字段（只影响本次运行，不写配置文件）
_START_BRANCH_KEYS = ("enabled", "common_window", "common_start", "common_end", "time_offset_s", "align_tol_s")


def _branch_cfg_for_start(src_over: Optional[Dict[str, Any]]) -> AppConfig:
    """本次联动启动用的分路侧配置：已保存配置 + 界面当前的分路侧数据源字段（v0.70），相对路径解析到仓库根。"""
    d = RUNNERS["branch"].cfg.to_dict()
    if src_over:
        d["source"].update(src_over)
    cfg = AppConfig.from_dict(d)
    if cfg.source.kind in ("csv_file", "csv_tail") and cfg.source.path and not os.path.isabs(cfg.source.path):
        cand = os.path.join(ROOT, cfg.source.path)
        if os.path.exists(cand):
            cfg.source.path = cand
    return cfg


@app.post("/api/engine/start")
async def engine_start(payload: Optional[Dict[str, Any]] = None) -> Any:
    payload = payload or {}
    try:
        cfg = RUNNER.cfg
        data = cfg.to_dict()
        src_over = {k: v for k, v in payload.items() if k in _START_SRC_KEYS}
        if src_over:
            data["source"].update(src_over)
        # v0.70：总线侧「启动」同时带上界面当前的分路侧联动参数（启用 / 公共时间段 / 自定义起止 / 偏移 / 容差）与
        # 分路侧数据源字段——与总线侧 source 一样「按界面当前值启动、不写配置文件」。此前这些只从已保存配置读取：
        # 界面取消勾选「只播放公共时间段」但没点「保存分路侧配置」→ 启动仍按旧配置算公共时间段并报错。
        br_over_top = payload.get("branch") if isinstance(payload.get("branch"), dict) else None
        if br_over_top and current_side() == "bus":
            data.setdefault("branch", {}).update({k: v for k, v in br_over_top.items() if k in _START_BRANCH_KEYS})
        br_src_over = payload.get("branch_source") if isinstance(payload.get("branch_source"), dict) else None
        br_src_over = {k: v for k, v in (br_src_over or {}).items() if k in _START_SRC_KEYS} if current_side() == "bus" else None
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
        br_cfg = _branch_cfg_for_start(br_src_over) if coupled else None
        if coupled and cfg.branch.common_window:
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
        sr = RUNNER.start(cfg, duration_s=payload.get("duration_s"), pace_clock=clock, play_user=play_user)
        out: Dict[str, Any] = {"ok": True, "side": current_side(), "config": RUNNER.cfg.to_dict(), "run_dir": sr.get("run_dir")}
        if COMMON_WINDOW.get("enabled"):
            out["common_window"] = {k: v for k, v in COMMON_WINDOW.items() if k not in ("bus", "branch")}
        elif cw_note:
            out["common_window"] = {"enabled": False, "reason": cw_note}
        if current_side() == "bus" and payload.get("with_branch", True):
            out["branch"] = _start_branch_if_enabled(cfg, pace_clock=clock, br_cfg=br_cfg)
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
    """负荷辨识事件列表：algos=逗号分隔算法键；channel=total/A/B/C；since_id 增量拉取；limit=0 ＝ 全部（v0.89）。"""
    al = [a.strip() for a in algos.split(",") if a.strip()] if algos else None
    lim = int(limit)
    lim = 10 ** 9 if lim <= 0 else max(1, min(lim, 5000))          # v0.89：limit=0 ＝ 全部（内存保留上限 nilm.max_log）
    return RUNNER.nilm_events(limit=lim, algos=al, channel=(channel or None), since_id=int(since_id))


@app.post("/api/nilm/tune/apply")
async def nilm_tune_apply(payload: Dict[str, Any]) -> Any:
    """v0.50：把 nilm_tune.py --json 的结果叠加到**当前侧正在运行的配置**上。

    payload：``{"params": <nilm_tune --json 整份 / 其 suggest 片段 / {"nilm": {...}}>, "hot": true, "persist": false, "out": null}``
    * 总是在 ``nilm.nilm_dir``（默认 output/nilm）写出更新后的完整配置 ``nilm_tuned_config_<side>_<时间戳>.json``；
    * ``hot``（默认 true）：热更新到运行中的引擎（与界面「保存参数」同一路径），但**不写配置文件**；
    * ``persist``（默认 false）：显式要求时才把配置回写 runtime 配置文件（受 ELEC_TOOL_PERSIST_CONFIG 约束）。
    """
    params = payload.get("params") if isinstance(payload, dict) else None
    if not isinstance(params, dict):
        return JSONResponse(status_code=400, content={"ok": False, "error": "缺少 params（nilm_tune.py --json 的输出）"})
    try:
        side = current_side()
        nl_dir = os.environ.get("ELEC_TOOL_NILM_DIR") or RUNNER.cfg.nilm.nilm_dir      # 与事件 CSV 同一目录
        cfg, path, notes = export_tuned_config(RUNNER.cfg, params, out_path=(payload.get("out") or None), out_dir=nl_dir,
                                               tag=side, meta={"side": side, "base_config": "running"})
        if not notes:
            return JSONResponse(status_code=400, content={"ok": False, "error": "params 里没有可套用的 nilm 参数（需 quantity / rel_tol_pct / min_delta_pct / algorithms）"})
        hot = bool(payload.get("hot", True))
        persisted = False
        if hot:
            before = RUNNER.cfg.to_dict()
            RUNNER.set_cfg(cfg)
            if bool(payload.get("persist", False)) and os.environ.get("ELEC_TOOL_PERSIST_CONFIG", "1") == "1":
                _persist(cfg, {"nilm": _dict_diff(before.get("nilm", {}), cfg.to_dict().get("nilm", {}))}); persisted = True
        # v0.99.13：目标侧启用自适应算法参数时，套用的 6 种算法数值参数在检测时不参与（被窗内推导覆盖），明确告知
        auto_on = bool(getattr(cfg.nilm, "auto_params", False))
        warn = ("目标侧已启用「自适应算法参数」：本次套用的算法数值参数（min_delta / settle_tol / drift / threshold / noise / k_sigma 等）"
                "已写入配置但检测时不参与——运行时每个周波窗由数据自身推导并覆盖；要让调参结果生效，请在负荷辨识页取消勾选「是否启用自适应算法参数」"
                ) if auto_on else ""
        return {"ok": True, "side": side, "saved_to": _display_path(path), "changes": notes, "hot": hot, "auto_params": auto_on, "warning": warn,
                "config_file_updated": persisted, "config": (RUNNER.cfg if hot else cfg).to_dict()}
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.get("/api/nilm/cycles")
async def get_nilm_cycles(n: int = 300) -> Dict[str, Any]:
    """最近 n 个周波的 P/Q/I 序列（total/A/B/C），供负荷辨识界面画图。"""
    return RUNNER.nilm_cycles(max(1, min(int(n), 20000)))


@app.get("/api/nilm/cycles_file")
async def get_nilm_cycles_file(t: Optional[str] = None, n: int = 300):
    """v0.46：**非运行状态下**从当前侧配置的离线文件装载一段周波窗：t 为空＝数据起点起 n 个周波；
    t＝epoch 秒或 'YYYY-MM-DD HH:MM:SS[.fff]'（本机时区）＝以该时刻为中心的 n 个周波。引擎运行中返回 409。"""
    from elec_tool.config import ConfigError, parse_time_text
    from elec_tool.nilm import load_cycles_from_file
    if RUNNER.state().get("running"):
        return JSONResponse(status_code=409, content={"ok": False, "error": "引擎运行中：请先停止数据源，再手动装载周波窗（运行中周波窗显示实时数据）"})
    cfg = AppConfig.from_dict(RUNNER.cfg.to_dict())
    tc: Optional[float] = None
    if t is not None and str(t).strip():
        try:
            tc = float(parse_time_text(str(t).strip()))
        except ConfigError as exc:
            return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    try:
        if cfg.source.path:
            cfg.source.path = _abs_path(cfg.source.path)
        return await asyncio.to_thread(load_cycles_from_file, cfg, tc, max(1, min(int(n), 20000)))
    except (ValueError, ConfigError) as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _wave_window_from_file(cfg: AppConfig, tc: Optional[float], n: int, channels: Optional[List[str]] = None) -> Dict[str, Any]:
    """v0.65/v0.71：从本侧配置的离线文件读取以 tc 为中心（None＝数据起点起）n 个周波的原始采样瞬时值（同步函数，放线程里跑）。
    按本侧运行配置的 fs / f_nom / PT·CT / 时标 UTC / 自定义时间解释；靠近文件两端时整体平移仍取 n 个周波。"""
    from elec_tool.wave_preview import file_info, load_waveform, relax_harmonic_limits
    p = _abs_path(cfg.source.path)
    cfg.source.play_window = False; cfg.source.play_end_time = ""
    cfg.source.play_start_mode = "begin"; cfg.source.play_start_value = ""
    relax_harmonic_limits(cfg)
    info = file_info(cfg, p)
    fnom = float(info["f_nom"]); dur = n / fnom
    t0f, t1f = float(info["t_start"]), float(info["t_end"])
    if tc is None:
        a = t0f; mode = "begin"
    else:
        a = tc - dur / 2.0; mode = "center"
        if a < t0f:
            a = t0f
        if a + dur > t1f:                       # 靠近文件末尾：整体左移，仍取 n 个周波
            a = max(t0f, t1f - dur)
    d = load_waveform(cfg, p, t_start=repr(a), n_cycles=n, channels=channels or None)
    d["source"] = {"path": _display_path(p), "mode": mode, "t_center": tc, "n_cycles": n, "t_start": d.get("t_first"), "t_end": d.get("t_last"),
                   "custom_time": bool(cfg.source.custom_time), "side": current_side(), "n_loaded": d.get("n")}
    return d


def _file_window_args(t: Optional[str], n: int) -> Tuple[Optional[AppConfig], Optional[float], int, Optional[JSONResponse]]:
    """周波窗（瞬时值 / 有效值）端点共用的参数校验：本侧须为离线文件源；t 可为空 / epoch / 'YYYY-MM-DD HH:MM:SS[.fff]'。"""
    from elec_tool.config import ConfigError, parse_time_text
    cfg = AppConfig.from_dict(RUNNER.cfg.to_dict())
    if cfg.source.kind != "csv_file" or not str(cfg.source.path or "").strip():
        return None, None, 0, JSONResponse(status_code=400, content={"ok": False, "error": f"当前侧数据源不是离线文件（{cfg.source.kind}）或未配置文件路径；周波窗只能从离线文件读取"})
    tc: Optional[float] = None
    if t is not None and str(t).strip():
        try:
            tc = float(parse_time_text(str(t).strip()))
        except ConfigError as exc:
            return None, None, 0, JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    return cfg, tc, max(1, min(int(n), 20000)), None


@app.get("/api/nilm/wave_file")
async def get_nilm_wave_file(t: Optional[str] = None, n: int = 300, channels: str = ""):
    """v0.65：「周波窗 2（瞬时值）」——从当前侧配置的离线文件读取以 t 为中心的 n 个周波**原始采样瞬时值**
    （Ua/Ub/Uc/Ia/Ib/Ic，按本侧运行配置的 fs / f_nom / PT·CT / 时标 UTC / 自定义时间解释；口径同本侧计算）。
    t 为空＝数据起点起 n 个周波。只读文件、不改运行配置；引擎运行与否都可用（读的是文件，不是实时缓冲）。"""
    from elec_tool.config import ConfigError
    from elec_tool.wave_preview import WaveError
    cfg, tc, n, err = _file_window_args(t, n)
    if err is not None:
        return err
    try:
        chans = [c for c in channels.split(",") if c.strip()] or None
        return await asyncio.to_thread(_wave_window_from_file, cfg, tc, n, chans)
    except (WaveError, ValueError, ConfigError) as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.get("/api/elec/cycles_file")
async def get_elec_cycles_file(t: Optional[str] = None, n: int = 300):
    """v0.71：实时监测（三相电压 / 三相电流 / 有功无功视在）子界面的「周波窗（有效值）」——从当前侧配置的离线文件读取
    以 t 为中心（空＝数据起点起）的 n 个周波，输出每周波的 U 有效值（A/B/C）、I 有效值（A/B/C/total）、P/Q/S（total/A/B/C）。
    口径同负荷辨识周波窗（P=mean(u·i)，Q=基波 DFT 无功，S=Urms·Irms）；只读文件、不改运行配置、运行与否都可用。"""
    from elec_tool.config import ConfigError
    from elec_tool.wave_preview import WaveError, cycle_values
    cfg, tc, n, err = _file_window_args(t, n)
    if err is not None:
        return err
    try:
        def _work() -> Dict[str, Any]:
            d = _wave_window_from_file(cfg, tc, n, None)
            out = cycle_values(d, float(cfg.sampling.f_nom))
            out["source"] = d["source"]; out["channels_loaded"] = d.get("channels_loaded"); out["path"] = d.get("path")
            out["source"]["n_loaded"] = out["n_cycles"]
            if out["t"]:
                out["source"]["t_start"] = out["t"][0]; out["source"]["t_end"] = out["t"][-1]
            return out
        return await asyncio.to_thread(_work)
    except (WaveError, ValueError, ConfigError) as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


# ------------------------------------------------------------------ v0.21：离线文件指定时间段原始数据重新导出
def _raw_export_sides(payload: Dict[str, Any]) -> Tuple[List[Tuple[AppConfig, int]], List[str], Dict[str, Any]]:
    """**只取当前侧**的离线文件配置（总线侧与分路侧的导出相互独立、互不关联）；非 csv_file 时给出说明。"""
    side = current_side()
    notes: List[str] = []
    ranges: Dict[str, Any] = {}
    out: List[Tuple[AppConfig, int]] = []
    for sd in [side]:
        cfg = AppConfig.from_dict(RUNNERS[sd].cfg.to_dict())
        label = "总线侧" if sd == "bus" else "分路侧"
        if cfg.source.kind != "csv_file":
            notes.append(f"{label}数据源不是离线文件（当前 {cfg.source.kind}），已跳过"); continue
        if not str(cfg.source.path or "").strip():
            notes.append(f"{label}未配置离线文件路径，已跳过"); continue
        p = _abs_path(cfg.source.path)
        if not os.path.isfile(p):
            notes.append(f"{label}离线文件不存在：{cfg.source.path}，已跳过"); continue
        try:
            ranges[sd] = _file_time_range(cfg, cfg.source.path)
            ranges[sd]["t0_local"] = fmt_local(ranges[sd]["t0"]); ranges[sd]["t1_local"] = fmt_local(ranges[sd]["t1"])
        except Exception as exc:
            ranges[sd] = {"error": str(exc)}
        out.append((cfg, SIDE_SOURCE_ID[sd]))
    return out, notes, ranges


@app.get("/api/source/raw_range")
async def raw_range_info() -> Dict[str, Any]:
    """当前侧离线文件的时间范围，供导出界面填默认值（分路侧用 /api/branch/source/raw_range）。"""
    sides, notes, ranges = _raw_export_sides({})
    return {"ok": True, "sides": {("bus" if sid == 0 else "branch"): {"path": _display_path(_abs_path(c.source.path)), "custom_time": bool(c.source.custom_time)}
                                  for c, sid in sides}, "ranges": ranges, "notes": notes}


@app.post("/api/source/export_range")
async def raw_export_range(payload: Optional[Dict[str, Any]] = None) -> Any:
    """v0.21：从离线数据源 CSV 中把**指定时间段的原始采样行**重新导出到一个新的 CSV 文件。

    body：{t_from, t_to（时间文本 "2026-10-15 14:14:20.5" / "14:14:20.5000" 或 epoch 秒；可留一端为空）, name?: 文件名}。
    时间按播放时间轴判断（与界面显示一致，含自定义播放时间）。**只导出当前侧自己的文件**（总线侧 `/api/source/export_range`、
    分路侧 `/api/branch/source/export_range`，两者相互独立、互不关联）；行按原样写出，末尾追加 source_id 列（0 总线 / 1 分路）；
    导出文件可直接再作为离线数据源播放。文件：output/raw_<起>_<止>_src<source_id>.csv。
    """
    payload = payload or {}
    from elec_tool import raw_export
    from elec_tool.config import parse_play_start
    try:
        tf = parse_play_start("time", payload.get("t_from")) if payload.get("t_from") not in (None, "") else None
        tt = parse_play_start("time", payload.get("t_to")) if payload.get("t_to") not in (None, "") else None
    except ConfigError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    if tf is None and tt is None:
        return JSONResponse(status_code=400, content={"ok": False, "error": "请至少填写开始或结束时间（都留空＝整个文件，请改用复制文件）"})
    sides, notes, ranges = _raw_export_sides(payload)
    if not sides:
        return JSONResponse(status_code=409, content={"ok": False, "error": "没有可导出的离线文件数据源：" + "；".join(notes), "notes": notes})
    # 只填时刻（HH:MM:SS.ffff，与文件时标写法一致）→ 以主侧文件首行所在日期（播放时间轴）补齐
    def _resolve(v: Any) -> Optional[float]:
        if v is None:
            return None
        kind, val = v
        if kind == "abs":
            return float(val)
        from elec_tool.timefmt import local_tod_s   # v0.68.1：跨平台安全（无日期时标 epoch 极小时 fromtimestamp 在 Windows 抛 Errno 22）
        r0 = next((r for r in ranges.values() if isinstance(r, dict) and r.get("t0") is not None), {})
        base = float(r0.get("t0") or 0.0)
        return base - local_tod_s(base) + float(val)
    tf = _resolve(tf); tt = _resolve(tt)
    if tf is not None and tt is not None and tt <= tf:
        return JSONResponse(status_code=400, content={"ok": False, "error": "结束时间必须晚于开始时间"})
    out_dir = RUNNER.cfg.output.export_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(ROOT, out_dir)
    stamp = lambda t: fmt_local(t, ms=False).replace("-", "").replace(":", "").replace(" ", "_")   # noqa: E731
    name = (str(payload.get("name") or "").strip()
            or f"raw_{stamp(tf) if tf is not None else 'begin'}_{stamp(tt) if tt is not None else 'end'}_src{sides[0][1]}.csv")
    if not name.lower().endswith(".csv"):
        name += ".csv"
    name = os.path.basename(name)
    fp = os.path.join(out_dir, name)
    try:
        res = await asyncio.get_event_loop().run_in_executor(None, lambda: raw_export.export_range(sides, tf, tt, fp, root=ROOT))
    except Exception as exc:
        return JSONResponse(status_code=500, content={"ok": False, "error": f"{type(exc).__name__}: {exc}", "notes": notes})
    notes += res.get("notes", [])
    if not res["rows"]:
        return JSONResponse(status_code=409, content={"ok": False, "error": "指定时间段内没有数据行（请对照各文件的时间范围）",
                                                      "ranges": ranges, "notes": notes, "t_from": tf, "t_to": tt})
    per = {("bus" if sid == 0 else "branch"): v for sid, v in res["sides"].items()}
    for v in per.values():
        v["path"] = _display_path(v["path"])
    return {"ok": True, "path": _display_path(fp), "rows": res["rows"], "sides": per, "source_ids": sorted(res["sides"]),
            "header": res["header"], "t_from": tf, "t_to": tt, "t_first": res["t_first"], "t_last": res["t_last"],
            "t_first_local": res.get("t_first_local"), "t_last_local": res.get("t_last_local"), "ranges": ranges, "notes": notes,
            "size_bytes": os.path.getsize(fp)}


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

    def start(self, params: Dict[str, Any], cfg: Optional[AppConfig] = None) -> Dict[str, Any]:
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
                                       cfg=cfg or RUNNER.cfg, fs_src=params.get("fs_src") or None,
                                       method=params.get("method") or "linear",
                                       overwrite=bool(params.get("overwrite")), job=job, root=ROOT,
                                       error_window_s=params.get("err_window_s"))
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
                "progress": (j.overall if j else 0.0), "stage": (j.stage if j else "idle"),
                # v0.35：两步进度
                "step": (j.step if j else 1), "steps": (j.steps if j else 1), "step_progress": (j.progress if j else 0.0),
                "step_status": (dict(j.step_status) if j else {}),
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
    [overwrite], [out_dir=data], [err_report], [err_window_s]。输出文件名 = 原名_re_<fs_new>.csv。
    v0.34：err_report（默认取配置 processing.error_report）为真时按 err_window_s 秒（默认取配置
    processing.error_window_s）逐窗计算重采样前后相对误差，写 原名_re_<fs_new>_err.csv。"""
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
    pc = RUNNER.cfg.processing
    err_report = bool(payload.get("err_report")) if "err_report" in payload else bool(pc.error_report)
    err_window_s: Optional[float] = None
    if err_report:
        try:
            err_window_s = float(payload.get("err_window_s")) if payload.get("err_window_s") not in (None, "") \
                else float(pc.error_window_s)
        except (TypeError, ValueError):
            return {"ok": False, "error": "误差统计时间窗必须是数字（秒）"}
        if not (err_window_s > 0) or err_window_s > 3600:
            return {"ok": False, "error": "误差统计时间窗必须在 (0, 3600] 秒之间"}
    # v0.86：离线文件列映射（默认不启用＝各列依次为 时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流）
    rs_cfg = AppConfig.from_dict(RUNNER.cfg.to_dict())
    try:
        from elec_tool.wave_preview import apply_col_map
        apply_col_map(rs_cfg, payload.get("col_map_enabled", False), payload.get("col_map"))
        rs_cfg.columns.validate()
    except ConfigError as exc:
        return {"ok": False, "error": f"列映射无效：{exc}"}
    return RESAMPLE.start({"path": path, "fs_new": fs_new, "fs_src": fs_src, "method": method,
                           "overwrite": bool(payload.get("overwrite")), "out_dir": out_dir,
                           "err_report": err_report, "err_window_s": err_window_s,
                           "col_map_enabled": bool(rs_cfg.columns.mapping_enabled), "col_map": dict(rs_cfg.columns.mapping)},
                          cfg=rs_cfg)


@app.get("/api/process/resample")
async def process_resample_status() -> Dict[str, Any]:
    pc = RUNNER.cfg.processing
    return {"ok": True, **RESAMPLE.status(),
            "defaults": {"err_report": bool(pc.error_report), "err_window_s": float(pc.error_window_s)}}


@app.post("/api/process/resample/cancel")
async def process_resample_cancel() -> Dict[str, Any]:
    return RESAMPLE.cancel()


# v0.72：负荷辨识调参的「独立基准配置」——出厂配置 configs/default.json + 界面给的几项，不关联两侧运行配置
NT_BASE_KEYS = ("fs", "f_nom", "pt_ct_enabled", "pt_ratio", "ct_ratio", "file_time_utc",
                "wiring", "reconstruct_3w", "invert_current", "invert_phases")   # v0.95：接线 / 极性进入基准配置
NT_BASE_FILE = "nilm_tune_base.json"      # 独立基准配置落盘文件名（nilm_dir 下；每次调参覆盖，供等价命令 --config 复现）


def _nt_base_fields(cfg: AppConfig) -> Dict[str, Any]:
    return {"fs": float(cfg.sampling.fs), "f_nom": float(cfg.sampling.f_nom), "pt_ct_enabled": bool(cfg.transform.enabled),
            "pt_ratio": float(cfg.transform.pt_ratio), "ct_ratio": float(cfg.transform.ct_ratio),
            "file_time_utc": bool(cfg.source.file_time_utc), "quantity": str(cfg.nilm.quantity),
            "channel": str((cfg.nilm.channels or ["total"])[0]),
            "wiring": str(cfg.transform.wiring), "reconstruct_3w": bool(cfg.transform.reconstruct_3w),
            "invert_current": bool(cfg.transform.invert_current), "invert_phases": str(cfg.transform.invert_phases or "")}


def _nt_make_base(payload: Dict[str, Any]) -> Tuple[AppConfig, str, Optional[str]]:
    """按 payload 决定基准配置：``base_mode``＝``custom``（默认，独立基准配置：出厂配置 + ``base{...}`` 各项）/
    ``running``（本侧当前运行配置，旧行为）。返回 (cfg, mode, 标签)。"""
    from elec_tool.wave_preview import make_base
    mode = str(payload.get("base_mode") or "").strip().lower()
    if not mode:
        # 未显式给 base_mode：带 base ⇒ custom；都不带 ⇒ legacy（本侧运行配置，但 quantity / channel 仍按请求，兼容 v0.52 调用方）
        mode = "custom" if isinstance(payload.get("base"), dict) else "legacy"
    if mode in ("running", "legacy"):
        return AppConfig.from_dict(RUNNER.cfg.to_dict()), mode, None
    if mode != "custom":
        raise TuneError(f"base_mode 必须是 custom / running（当前 {mode!r}）")
    b = payload.get("base") or {}
    if not isinstance(b, dict):
        raise TuneError("base 必须是 {fs, f_nom, pt_ct_enabled, pt_ratio, ct_ratio, file_time_utc} 字典")
    cfg = make_base(AppConfig.load(DEFAULT_CONFIG_PATH), **{k: b.get(k) for k in NT_BASE_KEYS})
    q = str(b.get("quantity") or "").strip()
    if q:
        if q not in ("auto", "p", "i"):
            raise TuneError(f"基准配置 quantity 必须是 auto / p / i（当前 {q!r}）")
        cfg.nilm.quantity = q
    cfg.validate()
    f = _nt_base_fields(cfg)
    label = (f"独立基准配置（出厂配置 + fs={f['fs']:g} f_nom={f['f_nom']:g} PT/CT={'启用' if f['pt_ct_enabled'] else '关闭'} "
             f"PT={f['pt_ratio']:g} CT={f['ct_ratio']:g} UTC={'是' if f['file_time_utc'] else '否'} quantity={f['quantity']} "
             f"接线={f['wiring']}{'+重构' if f['reconstruct_3w'] else ''} 极性反转={'全部' if f['invert_current'] else (f['invert_phases'] or '无')}）")
    return cfg, mode, label


@app.get("/api/process/nilm_tune/base")
async def process_nilm_tune_base(source: str = "default") -> Any:
    """v0.72：独立基准配置的取值来源：``default``＝出厂配置 configs/default.json；``running``＝本侧当前运行配置
    （经 ``/api/branch/...`` 为分路侧）。只读，供界面「恢复出厂 / 填入总线侧 / 填入分路侧」按钮用。"""
    src = (source or "default").strip().lower()
    if src == "running":
        cfg = AppConfig.from_dict(RUNNER.cfg.to_dict()); side = current_side()
    elif src == "default":
        cfg = AppConfig.load(DEFAULT_CONFIG_PATH); side = None
    else:
        return JSONResponse(status_code=400, content={"ok": False, "error": "source 必须是 default / running"})
    return {"ok": True, "source": src, "side": side, "base": _nt_base_fields(cfg), "keys": list(NT_BASE_KEYS) + ["quantity"]}


@app.post("/api/process/nilm_tune")
async def process_nilm_tune(payload: Dict[str, Any]) -> Any:
    """v0.52：数据处理子界面「负荷辨识调参」——对指定波形文件（可选时间段）量噪声、给出 6 种算法参数建议
    （与 ``tools/nilm_tune.py`` 同一实现）。基准配置（PT/CT、列映射、缺省 nilm.quantity）＝当前侧运行配置
    （``/api/branch/process/nilm_tune`` 为分路侧）；不改运行配置、不启动引擎。

    body：{path, channel?, quantity?, min_load_w?, min_load_a?, min_load_auto?: false, max_cycles?, t_start?, t_end?, duration_s?,
           custom_time?: false, custom_time_start?, custom_time_end?,
           save?: false, name?: "tune_{时间}.json",
           base_mode?: "custom"|"running", base?: {fs, f_nom, pt_ct_enabled, pt_ratio, ct_ratio, file_time_utc, quantity}}
    * v0.72.2：``base_mode=running`` 时 quantity / channel 沿用该侧运行配置（``nilm.quantity`` / ``nilm.channels[0]``），请求中的同名项忽略；
      ``custom`` 时才可单独指定。
    * v0.72：基准配置默认**独立于两侧运行配置**（``base_mode=custom``：出厂配置 + ``base`` 各项，空项＝出厂值；
      界面上可单独修改，并会写到 ``nilm_dir/nilm_tune_base.json`` 供等价命令 ``--config`` 复现）；``base_mode=running``
      保留旧行为（本侧当前运行配置；``/api/branch/...`` 为分路侧）。保存（save）时以该基准配置为底只更新算法参数。
    * min_load_auto（v0.55）：未手填最小关心负荷时从文件投切台阶估计（``min_load_estimate``，仅分路侧含启停录波有效）；
      v0.80：投切幅值分两簇（主负荷 + 二级波动，相差 >10 倍）时 ``split=True``、``reliable=False``、附 ``primary_step``，
      不自动采用，由界面「取值方式」三选一；另附 ``repetition``（模板拼接文件检测，疑似时 notes 告警）；
    * t_start / t_end 都空且 duration_s 空＝整个文件；
    * save=true（默认 false）：以本侧**原配置文件**（runtime.json / branch_runtime.json）为基准，只更新算法参数、其它参数不变，
      把更新后的**完整配置**写到 ``nilm.nilm_dir``（默认 output/nilm）下的 name（空＝``tune_<YYYYmmdd_HHMMSS>.json``；
      ``{时间}`` 占位符替换为时间戳），并在 ``_tuning`` 里附带 measure/suggest；原配置文件本身不改动（v0.53）。
    * 返回与保存文件的 ``_tuning`` 都含 ``command``：与本次等价的 ``tools/nilm_tune.py`` 命令行（v0.54）。
    """
    path = str(payload.get("path") or "").strip()
    if not path:
        return JSONResponse(status_code=400, content={"ok": False, "error": "请填写波形文件路径"})
    src_abs = _abs_path(path)
    if not os.path.isfile(src_abs):
        return JSONResponse(status_code=400, content={"ok": False, "error": f"文件不存在：{path}"})

    def _num(k: str) -> Optional[float]:
        v = payload.get(k)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            raise TuneError(f"{k} 必须是数字（当前 {v!r}）")

    try:
        base, base_mode, base_label = _nt_make_base(payload)
        # v0.86：离线文件列映射（两种基准模式都按本次请求：默认不启用＝各列依次为 时间,Ua,Ia,Ub,Ib,Uc,Ic）
        from elec_tool.wave_preview import apply_col_map
        apply_col_map(base, payload.get("col_map_enabled", False), payload.get("col_map"), err=TuneError)
        try:
            base.columns.validate()
        except ConfigError as exc:
            raise TuneError(f"列映射无效：{exc}")
        kw = dict(channel=(str(payload.get("channel") or "").strip() or None),
                  quantity=(str(payload.get("quantity") or "").strip() or None),
                  min_load_w=_num("min_load_w"), min_load_a=_num("min_load_a"),
                  max_cycles=int(_num("max_cycles") or 30000),
                  t_start=str(payload.get("t_start") or ""), t_end=str(payload.get("t_end") or ""),
                  duration_s=_num("duration_s"), min_load_auto=bool(payload.get("min_load_auto", False)),
                  # v0.73：自定义时间（与波形预览同一套写法 / 语义；文件时长＝点数 / 采样率，起止都空＝整个文件）
                  custom_time=bool(payload.get("custom_time", False)),
                  custom_time_start=str(payload.get("custom_time_start") or ""), custom_time_end=str(payload.get("custom_time_end") or ""))
        if kw["quantity"] not in (None, "auto", "p", "i"):
            raise TuneError(f"quantity 必须是 auto / p / i（当前 {kw['quantity']!r}）")
        if base_mode == "running":
            # v0.72.2：显式沿用某侧运行配置时，检测量 / 检测对象也沿用该侧 nilm.quantity / nilm.channels[0]，不可单独指定
            # （请求里的 quantity / channel 忽略）；I 口径不支持三相总 → 退回默认（A 相）
            kw["quantity"] = None
            ch0 = str((base.nilm.channels or ["total"])[0])
            q_eff = base.nilm.quantity
            kw["channel"] = None if (q_eff == "i" and ch0 == "total") else ch0
        out = await asyncio.to_thread(run_tune, base, src_abs, **kw)
        out["file"] = _display_path(src_abs)
        out["side"] = current_side()
        out["saved_to"] = None
        out["base_config"] = None
        out["base_mode"] = "running" if base_mode == "legacy" else base_mode
        out["base"] = _nt_base_fields(base)
        out["col_map_enabled"] = bool(base.columns.mapping_enabled)          # v0.86
        out["col_map"] = dict(base.columns.mapping) if base.columns.mapping_enabled else None
        nl_dir = os.environ.get("ELEC_TOOL_NILM_DIR") or base.nilm.nilm_dir
        if base_mode == "custom":
            # v0.72：独立基准配置落盘（固定文件名、每次覆盖），等价命令用 --config 指向它即可复现
            bdir = nl_dir if os.path.isabs(nl_dir) else os.path.join(ROOT, nl_dir)
            os.makedirs(bdir, exist_ok=True)
            bpath = os.path.join(bdir, NT_BASE_FILE)
            base.source.path = out["file"]                   # v0.74：独立基准的 source.path 写本次波形文件（原为 make_base 占位 x.csv）
            bdoc = base.to_dict(); bdoc["_note"] = "v0.72 负荷辨识调参独立基准配置（出厂配置 + 界面项），由界面每次调参覆盖写出"
            with open(bpath, "w", encoding="utf-8") as fh:
                json.dump(bdoc, fh, ensure_ascii=False, indent=2); fh.write("\n")
            out["base_file"] = _display_path(bpath)
            cfg_arg = out["base_file"]
        else:
            out["base_file"] = None
            # v0.54：等价的 nilm_tune.py 命令（--config 取本侧原配置文件；保存时追加 --apply --out <保存路径>）
            pp0 = RUNNER.persist_path
            cfg_arg = _display_path(pp0) if (pp0 and os.path.isfile(pp0)) else None
        cmd_kw = dict(config=cfg_arg, channel=kw["channel"], quantity=kw["quantity"], min_load_w=kw["min_load_w"],
                      min_load_a=kw["min_load_a"], max_cycles=kw["max_cycles"], t_start=kw["t_start"], t_end=kw["t_end"],
                      duration_s=kw["duration_s"], min_load_auto=kw["min_load_auto"],
                      custom_time=kw["custom_time"], custom_time_start=kw["custom_time_start"], custom_time_end=kw["custom_time_end"])
        out["command"] = build_cli_command(out["file"], **cmd_kw)
        if bool(payload.get("save", False)):
            # v0.53：保存的是**完整配置**——以本侧原配置文件（runtime.json / branch_runtime.json，即界面改动的持久化文件）
            # 为基准，只更新 nilm.quantity / rel_tol_pct / min_delta_pct 与各算法建议参数，其它参数原样保留；
            # 原配置文件本身不改动，写到 output/nilm/<name>（默认 tune_<时间>.json）。
            # 原配置文件尚不存在（界面从未保存过）时退回本侧当前运行配置，并在 base_config 中注明。
            if base_mode == "custom":
                base_file = base                                  # v0.72：独立基准配置为底（base_label 已含各项）
            else:
                pp = RUNNER.persist_path
                if pp and os.path.isfile(pp):
                    base_file = AppConfig.load(pp); base_label = _display_path(pp)
                else:
                    base_file = base; base_label = f"(运行配置；{_display_path(pp) if pp else '持久化文件'} 尚不存在)"
            fp = tune_result_path(base, str(payload.get("name") or ""), out_dir=nl_dir)
            if not os.path.isabs(fp):
                fp = os.path.join(ROOT, fp)
            # v0.74：把本次调参的**全部配置项**写进保存文件（此前只写算法参数，检测对象 / 自定义时间 / 文件路径 / 最小关心负荷等遗漏）：
            #   export_tuned_config 负责 nilm.channels / source.custom_time* / source.path；其余输入项记入 _tuning.params
            params_meta = {"quantity_requested": out["quantity_requested"], "channel": out["channel"],
                           "t_start": kw["t_start"], "t_end": kw["t_end"], "duration_s": kw["duration_s"], "max_cycles": kw["max_cycles"],
                           "min_load_w": kw["min_load_w"], "min_load_a": kw["min_load_a"], "min_load_auto": kw["min_load_auto"],
                           "min_load_used": out.get("min_load_used"), "min_load_source": out.get("min_load_source"),
                           "custom_time": kw["custom_time"], "custom_time_start": kw["custom_time_start"], "custom_time_end": kw["custom_time_end"],
                           "base": out["base"], "base_file": out.get("base_file"),
                           "col_map_enabled": bool(base.columns.mapping_enabled), "col_map": dict(base.columns.mapping)}
            _cfg, fp, changes = export_tuned_config(base_file, out, out_path=fp,
                                                    source_path=(out["file"] if base_mode == "custom" else None),
                                                    meta={"side": current_side(), "base_mode": out["base_mode"], "base_config": base_label,
                                                          "measure": out["measure"], "suggest": out["suggest"],
                                                          "t_range": out["t_range"], "params": params_meta})
            out["saved_to"] = _display_path(fp); out["base_config"] = base_label; out["changes"] = changes
            out["command"] = build_cli_command(out["file"], apply=True, out=out["saved_to"], **cmd_kw)
            # 写入文件的 _tuning 也带上命令（export 时 command 尚未定稿，这里补写）
            try:
                with open(fp, encoding="utf-8") as fh:
                    data = json.load(fh)
                data.setdefault("_tuning", {})["command"] = out["command"]
                data["_tuning"]["changes"] = changes
                with open(fp, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False, indent=2); fh.write("\n")
            except Exception:
                pass
        return {"ok": True, **out}
    except (TuneError, ConfigError, ValueError, WaveError) as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.post("/api/process/ct_estimate")
async def process_ct_estimate(payload: Dict[str, Any]) -> Any:
    """v0.96 / v0.97：数据处理子界面「估计 CT」——两侧分别指定文件、同一次动作的事件类型（启动 / 停机）与事件时间段、单相电流、
    接线方式、CT 极性、「本侧 CT 已知」与 CT 变比，量两侧二次侧电流台阶估计未知一侧 CT（与 ``tools/ct_estimate.py`` 同一实现）。不改运行配置。

    body：{bus: {path, event: start|stop, t_begin, t_end, phase, win_cycles?: 50, known?: 0/1, ct?, wiring?, reconstruct_3w?, invert_current?,
                invert_phases?, col_map_enabled?, col_map?, file_time_utc?}, branch: {同上}, win_cycles?: 50}
    """
    from elec_tool.ct_estimate import CtEstimateError, estimate_ct
    from tools.ct_estimate import build_cli_command as _ct_cmd
    try:
        bus = dict(payload.get("bus") or {}); br = dict(payload.get("branch") or {})
        for d in (bus, br):
            if str(d.get("path") or "").strip():
                d["path"] = _abs_path(str(d["path"]).strip())
        wc = payload.get("win_cycles")
        try:
            wc = int(float(wc)) if wc not in (None, "") else 50
        except (TypeError, ValueError):
            raise CtEstimateError(f"win_cycles 必须是整数（当前 {wc!r}）")
        out = estimate_ct(AppConfig.load(DEFAULT_CONFIG_PATH), bus, br, win_cycles=wc)
        for k in ("bus", "branch"):
            m = out[k]; m["path"] = _display_path(m["path"])
            for tk in ("t_begin", "t_end", "t_step"):
                m[tk + "_local"] = fmt_local(m[tk])
        out["command"] = _ct_cmd(payload, out)
        return out
    except (CtEstimateError, ConfigError, ValueError) as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.post("/api/process/nilm_profile")
async def process_nilm_profile(payload: Dict[str, Any]) -> Any:
    """v0.90：数据处理子界面「设备画像提取」——对设备侧（分路侧）含启停过程的波形文件构建设备画像 JSON
    （与 ``tools/nilm_profile.py`` 同一实现），写到 ``nilm.nilm_dir``；总线侧把路径填入 nilm.profile_path 并勾选「设备画像匹配」后即可使用。

    body：{path, device_id?, labels?: "时间,动作\n…", label_tol_s?: 2, pre_cycles?: 10, post_cycles?: 50, quantity?, max_cycles?,
           t_start?, t_end?, custom_time?, custom_time_start?, custom_time_end?, name?: "profile_<设备>_{时间}.json",
           base_mode?/base?/col_map_enabled?/col_map? 同 /api/process/nilm_tune}
    labels 空＝自动定位（稳态分段 + 自适应参数；幅值为正＝启动、为负＝停止）。返回 {ok, saved_to, profile(summary), events, notes, command}。
    """
    from elec_tool.nilm_profile import ProfileError, build_profile, profile_summary, save_profile
    from tools.nilm_profile import build_cli_command as _profile_cmd
    path = str(payload.get("path") or "").strip()
    if not path:
        return JSONResponse(status_code=400, content={"ok": False, "error": "请填写设备侧波形文件路径"})
    src_abs = _abs_path(path)
    if not os.path.isfile(src_abs):
        return JSONResponse(status_code=400, content={"ok": False, "error": f"文件不存在：{path}"})

    def _num(k: str, default: float) -> float:
        v = payload.get(k)
        if v in (None, ""):
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ProfileError(f"{k} 必须是数字（当前 {v!r}）")

    try:
        base, base_mode, base_label = _nt_make_base(payload)
        from elec_tool.wave_preview import apply_col_map
        apply_col_map(base, payload.get("col_map_enabled", False), payload.get("col_map"), err=ProfileError)
        try:
            base.columns.validate()
        except ConfigError as exc:
            raise ProfileError(f"列映射无效：{exc}")
        device_id = str(payload.get("device_id") or "").strip() or "device"
        labels = str(payload.get("labels") or "").strip() or None
        quantity = (str(payload.get("quantity") or "").strip() or None)
        if quantity not in (None, "auto", "p", "i"):
            raise ProfileError(f"quantity 必须是 auto / p / i（当前 {quantity!r}）")
        if base_mode == "running":
            quantity = None
        kw = dict(device_id=device_id, labels=labels, label_tol_s=_num("label_tol_s", 2.0), pre_cycles=int(_num("pre_cycles", 10)),
                  post_cycles=int(_num("post_cycles", 50)), max_cycles=int(_num("max_cycles", 400000)), quantity=quantity,
                  merge_gap_s=_num("merge_gap_s", 10.0),
                  t_start=str(payload.get("t_start") or ""), t_end=str(payload.get("t_end") or ""),
                  custom_time=bool(payload.get("custom_time", False)),
                  custom_time_start=str(payload.get("custom_time_start") or ""), custom_time_end=str(payload.get("custom_time_end") or ""))
        doc = await asyncio.to_thread(build_profile, base, src_abs, **kw)
        nl_dir = os.environ.get("ELEC_TOOL_NILM_DIR") or base.nilm.nilm_dir
        d_abs = nl_dir if os.path.isabs(nl_dir) else os.path.join(ROOT, nl_dir)
        os.makedirs(d_abs, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe_dev = re.sub(r"[^\w\-.]+", "_", device_id) or "device"
        name = os.path.basename(str(payload.get("name") or "").strip()) or f"profile_{safe_dev}_{stamp}.json"
        name = name.replace("{时间}", stamp).replace("{time}", stamp).replace("{设备}", safe_dev).replace("{device}", safe_dev)
        if not name.lower().endswith(".json"):
            name += ".json"
        fp = os.path.join(d_abs, name)
        cfg_arg = None
        if base_mode == "custom":
            bpath = os.path.join(d_abs, NT_BASE_FILE)
            base.source.path = _display_path(src_abs)
            bdoc = base.to_dict(); bdoc["_note"] = "v0.72 负荷辨识调参 / v0.90 设备画像提取 独立基准配置（出厂配置 + 界面项），由界面每次覆盖写出"
            with open(bpath, "w", encoding="utf-8") as fh:
                json.dump(bdoc, fh, ensure_ascii=False, indent=2); fh.write("\n")
            cfg_arg = _display_path(bpath)
        else:
            pp0 = RUNNER.persist_path
            cfg_arg = _display_path(pp0) if (pp0 and os.path.isfile(pp0)) else None
        doc["side"] = current_side(); doc["base_mode"] = "running" if base_mode == "legacy" else base_mode
        doc["base"] = _nt_base_fields(base); doc["base_config"] = base_label
        doc["col_map_enabled"] = bool(base.columns.mapping_enabled)
        doc["col_map"] = dict(base.columns.mapping) if base.columns.mapping_enabled else None
        doc["command"] = _profile_cmd(_display_path(src_abs), device=device_id, config=cfg_arg, labels=("<标签文本>" if labels else None),
                                      label_tol=kw["label_tol_s"], pre=kw["pre_cycles"], post=kw["post_cycles"], quantity=quantity, merge_gap=kw["merge_gap_s"],
                                      t_start=kw["t_start"], t_end=kw["t_end"], custom_time=kw["custom_time"],
                                      custom_time_start=kw["custom_time_start"], custom_time_end=kw["custom_time_end"], out=_display_path(fp))
        save_profile(doc, fp)
        summ = profile_summary(doc); summ["path"] = _display_path(fp)
        events = [e for g in ("startup", "shutdown") if doc.get(g) for e in doc[g]["events"]]
        return {"ok": True, "saved_to": _display_path(fp), "profile": summ, "events": events, "notes": doc.get("notes", []),
                "command": doc["command"], "file": _display_path(src_abs), "side": doc["side"], "base_config": base_label,
                "startup": doc.get("startup"), "shutdown": doc.get("shutdown"), "features": doc.get("features")}
    except (ProfileError, ConfigError, ValueError, WaveError, TuneError) as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.get("/api/process/resample/preview")
async def process_resample_preview(path: str, fs_new: float) -> Dict[str, Any]:
    """只算输出文件名与是否已存在（界面即时提示用），不读数据。"""
    src_abs = path if os.path.isabs(path) else os.path.join(ROOT, path)
    name = resample_output_name(src_abs, fs_new)
    out = os.path.join(ROOT, "data", name)
    return {"ok": True, "out_name": name, "out_path": os.path.relpath(out, ROOT), "exists": os.path.exists(out),
            "src_exists": os.path.isfile(src_abs)}


# ------------------------------------------------------------------ v0.61：数据处理页「波形预览」
def _wave_base_cfg(fs: Optional[str] = None, f_nom: Optional[str] = None, pt_ct_enabled: Optional[str] = None,
                   pt_ratio: Optional[str] = None, ct_ratio: Optional[str] = None, file_time_utc: Optional[str] = None,
                   custom_time: Optional[str] = None, custom_time_start: Optional[str] = None,
                   custom_time_end: Optional[str] = None, col_map_enabled: Optional[str] = None,
                   col_map: Optional[str] = None, wiring: Optional[str] = None, reconstruct_3w: Optional[str] = None,
                   invert_current: Optional[str] = None, invert_phases: Optional[str] = None) -> AppConfig:
    """v0.62：预览用基准配置**独立**于总线 / 分路侧运行配置：出厂配置 configs/default.json 副本 + 界面给的几项
    （采样率 / 额定频率 / PT·CT 启用与变比 / 时标 UTC；v0.64 + 自定义时间 开关 / 起始 / 结束）。不读、不改任何运行配置。
    v0.64：谐波次数限制按 fs 自动放宽（预览不算谐波）。"""
    from elec_tool.wave_preview import make_base
    return make_base(AppConfig.load(DEFAULT_CONFIG_PATH), fs=fs, f_nom=f_nom, pt_ct_enabled=pt_ct_enabled,
                     pt_ratio=pt_ratio, ct_ratio=ct_ratio, file_time_utc=file_time_utc,
                     custom_time=custom_time, custom_time_start=custom_time_start, custom_time_end=custom_time_end,
                     col_map_enabled=col_map_enabled, col_map=col_map,   # v0.86：离线文件列映射（默认不启用）
                     wiring=wiring, reconstruct_3w=reconstruct_3w, invert_current=invert_current, invert_phases=invert_phases)   # v0.95


WAVE_MAX_POINTS_CAP = 100_000_000      # v0.64：界面可配的「最多加载点数」硬上限（默认 20_000_000）


def _wave_path(path: str) -> str:
    p = str(path or "").strip()
    if not p:
        raise ConfigError("未填写波形文件路径")
    return _abs_path(p)


def _wave_err(exc: Exception):
    from elec_tool.wave_preview import WaveError
    if isinstance(exc, (WaveError, ConfigError, ValueError)):
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    return JSONResponse(status_code=400, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@app.get("/api/process/wave/defaults")
async def process_wave_defaults() -> Any:
    """v0.62：界面「基准配置」初始值（出厂配置）、重采样方式列表、默认周波数。"""
    from elec_tool.wave_preview import DEFAULT_CYCLES, MAX_POINTS_DEFAULT, RESAMPLE_METHODS, base_defaults
    return {"ok": True, "base": base_defaults(AppConfig.load(DEFAULT_CONFIG_PATH)), "methods": list(RESAMPLE_METHODS),
            "default_cycles": DEFAULT_CYCLES, "max_points_default": MAX_POINTS_DEFAULT, "max_points_cap": WAVE_MAX_POINTS_CAP}


@app.get("/api/process/wave/info")
async def process_wave_info(path: str, fs: Optional[str] = None, f_nom: Optional[str] = None, pt_ct_enabled: Optional[str] = None,
                            pt_ratio: Optional[str] = None, ct_ratio: Optional[str] = None, file_time_utc: Optional[str] = None,
                            wiring: Optional[str] = None, reconstruct_3w: Optional[str] = None, invert_current: Optional[str] = None, invert_phases: Optional[str] = None,
                            custom_time: Optional[str] = None, custom_time_start: Optional[str] = None, custom_time_end: Optional[str] = None,
                            col_map_enabled: Optional[str] = None, col_map: Optional[str] = None) -> Any:
    """波形文件信息：通道数 / 通道 / 采样率（时标推算，<0.5% 偏差按基准配置值）/ 行数 / 时长（＝行数 / 采样率）/ 起止时间
    （结束＝起始 + (行数−1)/采样率）。基准配置项（fs/f_nom/pt_ct_enabled/pt_ratio/ct_ratio/file_time_utc）独立于运行配置。"""
    from elec_tool.wave_preview import file_info
    try:
        cfg = _wave_base_cfg(fs, f_nom, pt_ct_enabled, pt_ratio, ct_ratio, file_time_utc, custom_time, custom_time_start, custom_time_end, col_map_enabled, col_map, wiring, reconstruct_3w, invert_current, invert_phases); p = _wave_path(path)
        d = await asyncio.to_thread(file_info, cfg, p)
        d["path_display"] = _display_path(p)
        d["t_start_local"] = fmt_local(d["t_start"]) if d.get("t_start") is not None else None
        d["t_end_local"] = fmt_local(d["t_end"]) if d.get("t_end") is not None else None
        d["t_end_custom_local"] = fmt_local(d["t_end_custom"]) if d.get("t_end_custom") is not None else None
        return d
    except Exception as exc:
        return _wave_err(exc)


@app.get("/api/process/wave/load")
async def process_wave_load(path: str, t_start: str = "", t_end: str = "", n: Optional[str] = None, n_cycles: Optional[str] = None,
                            fs_out: Optional[float] = None, method: str = "linear", channels: str = "", max_points: Optional[str] = None,
                            fs: Optional[str] = None, f_nom: Optional[str] = None, pt_ct_enabled: Optional[str] = None,
                            pt_ratio: Optional[str] = None, ct_ratio: Optional[str] = None, file_time_utc: Optional[str] = None,
                            wiring: Optional[str] = None, reconstruct_3w: Optional[str] = None, invert_current: Optional[str] = None, invert_phases: Optional[str] = None,
                            custom_time: Optional[str] = None, custom_time_start: Optional[str] = None, custom_time_end: Optional[str] = None,
                            col_map_enabled: Optional[str] = None, col_map: Optional[str] = None) -> Any:
    """按 起止时刻、点数 n 或周波数 n_cycles（都空＝整段；v0.62 界面默认 300 周波）、重采样率 fs_out + 方式 method
    （linear/nearest/fft）、通道 加载一段原始波形（一次侧口径）。fs_out 空＝原采样率；channels 空＝全部。"""
    from elec_tool.wave_preview import load_waveform
    try:
        cfg = _wave_base_cfg(fs, f_nom, pt_ct_enabled, pt_ratio, ct_ratio, file_time_utc, custom_time, custom_time_start, custom_time_end, col_map_enabled, col_map, wiring, reconstruct_3w, invert_current, invert_phases); p = _wave_path(path)
        n_pts: Optional[int] = None; n_cyc: Optional[int] = None
        if n is not None and str(n).strip() != "":
            n_pts = int(float(str(n).strip()))
        elif n_cycles is not None and str(n_cycles).strip() != "":
            n_cyc = int(float(str(n_cycles).strip()))
        chans = [c for c in str(channels or "").split(",") if c.strip()] or None
        from elec_tool.wave_preview import MAX_POINTS_DEFAULT
        mp = MAX_POINTS_DEFAULT
        if max_points is not None and str(max_points).strip() != "":
            mp = int(float(str(max_points).strip()))
            if mp <= 0:
                raise ConfigError(f"最多加载点数必须 > 0（当前 {max_points}）")
        mp = min(mp, WAVE_MAX_POINTS_CAP)
        d = await asyncio.to_thread(load_waveform, cfg, p, t_start=t_start, t_end=t_end, n_points=n_pts, n_cycles=n_cyc,
                                    fs_out=fs_out, method=method, channels=chans, max_points=mp)
        d["path_display"] = _display_path(p)
        return d
    except Exception as exc:
        return _wave_err(exc)


@app.get("/api/process/wave/rms")
async def process_wave_rms(path: str, t_start: str = "", t_end: str = "", duration_s: Optional[float] = None, channels: str = "",
                           agg_cycles: int = 1, max_points: int = 200_000,
                           fs: Optional[str] = None, f_nom: Optional[str] = None, pt_ct_enabled: Optional[str] = None,
                           pt_ratio: Optional[str] = None, ct_ratio: Optional[str] = None, file_time_utc: Optional[str] = None,
                            wiring: Optional[str] = None, reconstruct_3w: Optional[str] = None, invert_current: Optional[str] = None, invert_phases: Optional[str] = None,
                            custom_time: Optional[str] = None, custom_time_start: Optional[str] = None, custom_time_end: Optional[str] = None,
                            col_map_enabled: Optional[str] = None, col_map: Optional[str] = None) -> Any:
    """指定时间段的逐周波有效值曲线（Ua/Ub/Uc/Ia/Ib/Ic）；点数过多时自动合并相邻周波。"""
    from elec_tool.wave_preview import rms_curve
    try:
        cfg = _wave_base_cfg(fs, f_nom, pt_ct_enabled, pt_ratio, ct_ratio, file_time_utc, custom_time, custom_time_start, custom_time_end, col_map_enabled, col_map, wiring, reconstruct_3w, invert_current, invert_phases); p = _wave_path(path)
        chans = [c for c in str(channels or "").split(",") if c.strip()] or None
        d = await asyncio.to_thread(rms_curve, cfg, p, t_start=t_start, t_end=t_end, duration_s=duration_s, channels=chans,
                                    agg_cycles=max(1, int(agg_cycles or 1)), max_points=max(10, min(int(max_points), 2_000_000)))
        d["path_display"] = _display_path(p)
        return d
    except Exception as exc:
        return _wave_err(exc)


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
