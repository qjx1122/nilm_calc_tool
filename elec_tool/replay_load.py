"""v0.18：不播放时直接加载上次播放落盘的数据（曲线点 / 事件 / 负荷辨识事件）。

数据来源就是三条落盘链路写出的 CSV（realtime/<曲线>_<日期>.csv、events/events_<日期>.csv、nilm/nilm_events_<日期>.csv），
按 ``source_id`` 列过滤本侧的数据（0 总线 / 1 分路；v0.17 之前没有该列的旧文件一律视为总线侧）。
只读、不改文件；按文件名里的数据日期从新到旧读取，直到覆盖 ``hours`` 小时或读完。
"""
from __future__ import annotations

import csv
import glob
import math
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import CURVE_KEYS

_DAY_RE = re.compile(r"_(\d{8})\.csv$")


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _files_by_day(dir_: str, prefix: str) -> List[Tuple[str, str]]:
    """[(day, path)]，新 → 旧；跳过 .v016.csv 备份。"""
    out: List[Tuple[str, str]] = []
    for p in glob.glob(os.path.join(dir_, f"{prefix}_*.csv")):
        if p.endswith(".v016.csv"):
            continue
        m = _DAY_RE.search(os.path.basename(p))
        if m:
            out.append((m.group(1), p))
    out.sort(reverse=True)
    return out


def _read_rows(path: str) -> Tuple[List[str], List[List[str]]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd, None) or []
        rows = [r for r in rd if r]
    return head, rows


def _row_sid(head: List[str], row: List[str]) -> int:
    if "source_id" in head:
        i = head.index("source_id")
        v = _num(row[i]) if i < len(row) else None
        return int(v) if v is not None else 0
    return 0                                   # 旧文件无来源号 → 总线侧


def load_curves(dir_: str, source_id: int, hours: float, keys: Iterable[str] = CURVE_KEYS,
                max_points: int = 200000) -> Dict[str, Any]:
    """返回 {"records": {key: [{"t":..., field: value, ...}, ...]}, "files": [...], "t_first":..., "t_last":...}。"""
    records: Dict[str, List[Dict[str, Any]]] = {}
    files: List[Dict[str, Any]] = []
    t_lo: Optional[float] = None
    t_hi: Optional[float] = None
    for key in keys:
        recs: List[Dict[str, Any]] = []
        latest: Optional[float] = None
        for day, path in _files_by_day(dir_, key):
            head, rows = _read_rows(path)
            if not head or head[0] != "t_epoch_s":
                continue
            skip = {"t_epoch_s", "time_local", "source_id"}
            fields = [(i, h) for i, h in enumerate(head) if h not in skip]
            n_side = 0
            for row in rows:
                if _row_sid(head, row) != int(source_id):
                    continue
                t = _num(row[0]) if row else None
                if t is None:
                    continue
                rec: Dict[str, Any] = {"t": t}
                for i, h in fields:
                    if i < len(row):
                        v = _num(row[i])
                        if v is not None:
                            rec[h] = v
                recs.append(rec)
                n_side += 1
            files.append({"quantity": key, "path": path, "day": day, "rows": len(rows), "rows_side": n_side})
            if recs:
                latest = max(latest or -math.inf, max(r["t"] for r in recs))
                oldest = min(r["t"] for r in recs)
                if hours and latest - oldest >= hours * 3600.0:
                    break                       # 已覆盖保留窗
        if not recs:
            continue
        recs.sort(key=lambda r: r["t"])
        if hours:
            horizon = recs[-1]["t"] - hours * 3600.0
            recs = [r for r in recs if r["t"] >= horizon]
        if max_points and len(recs) > max_points:
            recs = recs[-max_points:]
        # 同一时刻重复行（重复播放同一文件）只留最后一条
        dedup: Dict[float, Dict[str, Any]] = {}
        for r in recs:
            dedup[r["t"]] = r
        recs = [dedup[t] for t in sorted(dedup)]
        records[key] = recs
        t_lo = recs[0]["t"] if t_lo is None else min(t_lo, recs[0]["t"])
        t_hi = recs[-1]["t"] if t_hi is None else max(t_hi, recs[-1]["t"])
    return {"records": records, "files": files, "t_first": t_lo, "t_last": t_hi,
            "points": {k: len(v) for k, v in records.items()}}


def load_events(dir_: str, source_id: int, t_from: Optional[float] = None, limit: int = 2000) -> List[Dict[str, Any]]:
    """events_<日期>.csv：同一 id 有 start/end 两行 → 合并为一条（有 end 的为准）。返回按 start_t 升序的字典列表。"""
    by_id: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for day, path in _files_by_day(dir_, "events"):
        head, rows = _read_rows(path)
        if "type" not in head or "start_t" not in head:
            continue
        idx = {h: i for i, h in enumerate(head)}
        g = lambda row, k: (row[idx[k]] if k in idx and idx[k] < len(row) else "")   # noqa: E731
        for row in rows:
            if _row_sid(head, row) != int(source_id):
                continue
            st = _num(g(row, "start_t"))
            if st is None or (t_from is not None and st < t_from):
                continue
            key = (day, g(row, "id"))
            d = {
                "id": int(_num(g(row, "id")) or 0), "type": g(row, "type"), "subject": g(row, "subject"),
                "start_t": st, "end_t": _num(g(row, "end_t")),
                "value_start": _num(g(row, "value_start")) or 0.0, "value_peak": _num(g(row, "value_peak")) or 0.0,
                "limit": _num(g(row, "limit")) or 0.0, "unit": g(row, "unit"), "direction": g(row, "direction"),
                "detail": g(row, "detail"), "status_csv": g(row, "status"),
            }
            prev = by_id.get(key)
            if prev is None or (d["end_t"] is not None) or (prev["end_t"] is None):
                by_id[key] = d if prev is None or d["end_t"] is not None else prev
        if len(by_id) >= limit:
            break
    evs = sorted(by_id.values(), key=lambda d: d["start_t"])
    return evs[-limit:]


def load_nilm_events(dir_: str, source_id: int, t_from: Optional[float] = None, limit: int = 5000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for day, path in _files_by_day(dir_, "nilm_events"):
        head, rows = _read_rows(path)
        if "algorithm" not in head or "t_start" not in head:
            continue
        idx = {h: i for i, h in enumerate(head)}
        g = lambda row, k: (row[idx[k]] if k in idx and idx[k] < len(row) else "")   # noqa: E731
        for row in rows:
            if _row_sid(head, row) != int(source_id):
                continue
            ts = _num(g(row, "t_start"))
            if ts is None or (t_from is not None and ts < t_from):
                continue
            out.append({
                "algorithm": g(row, "algorithm"), "channel": g(row, "channel") or "total",
                "t_start": ts, "t_end": _num(g(row, "t_end")) or ts, "direction": g(row, "direction"),
                "magnitude_w": _num(g(row, "magnitude_w")) or 0.0, "delta_p_w": _num(g(row, "delta_p_w")) or 0.0,
                "delta_q_var": _num(g(row, "delta_q_var")) or 0.0, "delta_i_a": _num(g(row, "delta_i_a")) or 0.0,
                "pre_p_w": _num(g(row, "pre_p_w")) or 0.0, "post_p_w": _num(g(row, "post_p_w")) or 0.0,
                "cycles": int(_num(g(row, "cycles")) or 0), "score": _num(g(row, "score")) or 0.0,
            })
        if len(out) >= limit:
            break
    out.sort(key=lambda d: d["t_start"])
    # 去重（同一文件重复播放）：算法+对象+起点
    seen = set(); uniq: List[Dict[str, Any]] = []
    for d in out:
        k = (d["algorithm"], d["channel"], round(d["t_start"], 4))
        if k in seen:
            continue
        seen.add(k); uniq.append(d)
    return uniq[-limit:]
