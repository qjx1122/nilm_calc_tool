"""计算结果实时落盘：每算出一次曲线点就追加到 output/realtime/<曲线>_<日期>.csv。

设计要点：
- 与趋势曲线/「保存曲线数据」共用同一提取规则（``metrics.curve_record``），文件内容与界面曲线一致；
- 受 ``output.curve_save`` 勾选控制：未勾选的曲线不落盘（与手工保存口径一致）；
- 按**数据时间**的本地日期分文件（``voltage_20261012.csv``），跨午夜自动换文件；离线回放同样成立；
- 追加写、每次写后 flush：进程被杀最多丢最后一行；文件已存在且非空时沿用其表头字段顺序，不重复写表头；
- 表头字段顺序由该曲线第一条记录决定，后续记录只按表头列输出（新增字段不会破坏列对齐）；
- UTF-8-BOM，Excel 直接双击可开。
"""

from __future__ import annotations

import csv
import io
import os
import threading
import time
from typing import Any, Dict, List, Optional

from .config import AppConfig, CURVE_KEYS
from .timefmt import fmt_local, local_day
from .metrics import MetricsResult, curve_record


def _time_local(t: float) -> str:
    return fmt_local(t)


class RealtimeCurveWriter:
    FIXED = ("t_epoch_s", "time_local")

    def __init__(self, cfg: AppConfig, root: Optional[str] = None):
        self.cfg = cfg
        self.enabled = bool(cfg.output.realtime_save)
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
        day = local_day(t)
        f = self._files.get(key)
        if f is None or f["day"] != day:
            if f is not None:
                f["fh"].close()
            f = self._open(key, day, list(rec.keys()))
            self._files[key] = f
        row = [repr(t), _time_local(t)]
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
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                head = next(csv.reader(fh), None)
            if head and head[:2] == list(self.FIXED):
                existing_fields = head[2:]
        fh = open(path, "a", encoding="utf-8-sig" if existing_fields is None else "utf-8", newline="")
        w = csv.writer(fh)
        if existing_fields is None:
            w.writerow(list(self.FIXED) + fields)
            fh.flush()
            use = fields
        else:
            use = existing_fields
        return {"fh": fh, "writer": w, "path": path, "fields": use, "day": day, "rows": 0}
