"""计算结果实时落盘：每算出一次曲线点就追加到 output/realtime/<曲线>_<日期>.csv。

设计要点：
- 与趋势曲线/「保存曲线数据」共用同一提取规则（``metrics.curve_record``），文件内容与界面曲线一致；
- 受 ``output.curve_save`` 勾选控制：未勾选的曲线不落盘（与手工保存口径一致）；
- 按**墙钟（写入时刻）**的本地日期分文件（``voltage_20261012.csv``），跨午夜自动换文件（v0.58 起不再按数据时间：
  总线侧与分路侧播放不同日期的离线文件时也写进同一个文件，只用 source_id 区分；行内 ``t_epoch_s/time_local`` 仍是数据时间）；
- 追加写、每次写后 flush：进程被杀最多丢最后一行；文件已存在且非空时沿用其表头字段顺序，不重复写表头；
- 表头字段顺序由该曲线第一条记录决定，后续记录只按表头列输出（新增字段不会破坏列对齐）；
- UTF-8-BOM，Excel 直接双击可开。
"""

from __future__ import annotations

import csv
import io
import os
import threading

from .filelock import SHARED_FILE_LOCK
import time
from typing import Any, Dict, List, Optional

from .config import AppConfig, CURVE_KEYS
from .timefmt import fmt_local, wall_day
from .metrics import MetricsResult, curve_record


def _time_local(t: float) -> str:
    return fmt_local(t)


class RealtimeCurveWriter:
    FIXED = ("t_epoch_s", "time_local", "source_id")      # v0.17：第 3 列数据来源号 0＝总线 / 1＝分路
    FIXED_LEGACY = ("t_epoch_s", "time_local")           # v0.17 之前的文件：追加时保持原列结构

    def __init__(self, cfg: AppConfig, root: Optional[str] = None, run_id: int = 0):
        self.cfg = cfg
        self.run_id = int(run_id or 0)          # v0.32：本次运行标识，作为末列 run_id 写入
        self.enabled = bool(cfg.output.realtime_save)
        self.source_id = int(getattr(cfg.output, "source_id", 0) or 0)
        # 环境变量 ELEC_TOOL_REALTIME_DIR 可整体改写目录（测试隔离 / 现场把落盘指到数据盘）
        d = os.environ.get("ELEC_TOOL_REALTIME_DIR") or cfg.output.realtime_dir or "output/realtime"
        if not os.path.isabs(d) and root:
            d = os.path.join(root, d)
        self.dir = d
        self._files: Dict[str, Dict[str, Any]] = {}      # key -> {fh, path, fields, day, rows}
        self._lock = threading.Lock()
        self.rows_written: Dict[str, int] = {k: 0 for k in CURVE_KEYS}
        self.errors: List[str] = []

    # ---------- 对外 ----------
    def write(self, result: MetricsResult) -> int:
        """把 result 中本次计算出的各曲线点追加到对应文件；返回写入行数。"""
        if not self.enabled:
            return 0
        n = 0
        with self._lock:
            for key, q in result.quantities.items():
                if key not in CURVE_KEYS or not self.cfg.output.curve_save.get(key, True):
                    continue
                rec = curve_record(result, key, q)
                if rec is not None and self.run_id:
                    rec = dict(rec); rec["run_id"] = self.run_id
                if rec is None:
                    continue
                try:
                    self._append(key, float(q.t_ref), rec)
                    n += 1
                except OSError as exc:
                    msg = f"实时落盘失败（{key}）：{type(exc).__name__}: {exc}"
                    if msg not in self.errors:
                        self.errors.append(msg)
        return n

    def close(self) -> None:
        with self._lock:
            for f in self._files.values():
                try:
                    f["fh"].close()
                except Exception:
                    pass
            self._files.clear()

    def info(self) -> Dict[str, Any]:
        with self._lock:
            files = [{"quantity": k, "path": f["path"], "rows_this_session": f["rows"], "day": f["day"]}
                     for k, f in self._files.items()]
        return {"enabled": self.enabled, "dir": self.dir, "files": files,
                "rows_written": dict(self.rows_written), "errors": list(self.errors[-5:])}

    # ---------- 内部 ----------
    def _append(self, key: str, t: float, rec: Dict[str, Any]) -> None:
        day = wall_day()                            # v0.58：按墙钟本地日期分文件（不按数据时间），两侧同一运行日同一文件
        with SHARED_FILE_LOCK:                      # v0.17.2：两侧共用同一文件，表头/整行写入互斥
            f = self._files.get(key)
            if f is None or f["day"] != day:
                if f is not None:
                    f["fh"].close()
                f = self._open(key, day, list(rec.keys()))
                self._files[key] = f
            row = [repr(t), _time_local(t)] + ([] if f.get("legacy") else [self.source_id])
            for name in f["fields"]:
                v = rec.get(name)
                row.append("" if v is None else v)
            f["writer"].writerow(row)
            f["fh"].flush()
            f["rows"] += 1
        self.rows_written[key] = self.rows_written.get(key, 0) + 1

    def _open(self, key: str, day: str, fields: List[str]) -> Dict[str, Any]:
        os.makedirs(self.dir, exist_ok=True)
        path = os.path.join(self.dir, f"{key}_{day}.csv")
        existing_fields: Optional[List[str]] = None
        legacy = False
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                head = next(csv.reader(fh), None)
            if head and head[:3] == list(self.FIXED):
                existing_fields = head[3:]
                # v0.27：字段扩充（如新增分相列）后，旧表头缺列 → 把当天旧文件改名为 <名>.pre-v032.csv 保留，新建完整表头
                if set(fields) - set(existing_fields):
                    bak = path[:-4] + ".pre-v032.csv"
                    try:
                        if not os.path.exists(bak):
                            os.replace(path, bak)
                            existing_fields = None
                    except OSError:
                        pass
            elif head and head[:2] == list(self.FIXED_LEGACY):
                # v0.17.2：旧版（无 source_id 列）文件不再续写——两侧共用一个文件后没有来源号就无法区分，
                # 把旧文件改名为 <名>.v016.csv 保留，新建带 source_id 的文件
                bak = path[:-4] + ".v016.csv"
                try:
                    if not os.path.exists(bak):
                        os.replace(path, bak)
                    else:
                        legacy = True; existing_fields = head[2:]      # 备份名已占用：退回续写旧结构
                except OSError:
                    legacy = True; existing_fields = head[2:]
        fh = open(path, "a", encoding="utf-8-sig" if existing_fields is None else "utf-8", newline="")
        w = csv.writer(fh)
        if existing_fields is None:
            w.writerow(list(self.FIXED) + fields)
            fh.flush()
            use = fields
        else:
            use = existing_fields
        return {"fh": fh, "writer": w, "path": path, "fields": use, "day": day, "rows": 0, "legacy": legacy}
