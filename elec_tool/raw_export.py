"""v0.21：从离线数据源 CSV 文件中把**指定时间段的原始采样行**重新导出到一个新的 CSV（第 28 轮；v0.21.1 两侧独立）。

- 时间段按**播放时间轴**判断（与界面上显示的数据时间一致）：文件时标 + 时区解释、无日期写法按当天、
  跨午夜展开、启用「自定义播放时间」时按自定义时间轴——复用 CsvFileSource，口径与播放完全相同。
- 行按原样写出（不做变比、不做重排），只在末尾追加 ``source_id`` 列（0＝总线侧、1＝分路侧）；
  播放器按表头/默认列序取前 7 列，多出的尾列不影响把导出文件再当数据源播放。
- **总线侧与分路侧的导出相互独立、互不关联**：Web 层每次只传一侧（`sides` 只有一个元素），各自写各自的文件
  （默认名 ``raw_<起>_<止>_src<source_id>.csv``）。``export_range`` 本身仍支持多侧合并（库调用可用），
  多侧时分路侧表头与主侧不同则按主侧列序重排 7 个标准列并提示。
"""
from __future__ import annotations

import csv
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import AppConfig, ColumnMap
from .sources.csv_file import CsvFileSource
from .sources.parsing import file_tz_offset_h, read_header
from .timefmt import fmt_local

STD_FIELDS = tuple(ColumnMap.FIELDS)          # timestamp, ua, ia, ub, ib, uc, ic


def _abs_path(p: str, root: Optional[str]) -> str:
    if p and not os.path.isabs(p) and root:
        cand = os.path.join(root, p)
        if os.path.exists(cand):
            return cand
    return p


def _export_cfg(cfg: AppConfig, t_from: Optional[float]) -> AppConfig:
    c = AppConfig.from_dict(cfg.to_dict())
    c.source.kind = "csv_file"
    c.source.file_speed = 0.0
    c.source.play_window = False
    c.source.play_end_time = ""
    # 自定义播放时间：起点定位按文件时标会与自定义时间轴错位 → 从头顺序读，靠 t 过滤
    if t_from is not None and not bool(c.source.custom_time):
        c.source.play_start_mode = "time"; c.source.play_start_value = repr(float(t_from))
    else:
        c.source.play_start_mode = "begin"; c.source.play_start_value = ""
    return c


def iter_rows_in_range(cfg: AppConfig, t_from: Optional[float], t_to: Optional[float], root: Optional[str] = None,
                       margin_s: float = 0.0):
    """逐块产出 (header, rows, t) ——rows 已按 [t_from−margin, t_to+margin] 过滤（原始字符串行），t 为对应播放时刻。"""
    c = _export_cfg(cfg, (t_from - margin_s) if t_from is not None else None)
    c.source.path = _abs_path(c.source.path, root)
    c.validate()
    src = CsvFileSource(c, tz_offset_h=file_tz_offset_h(c))
    src.keep_rows = True                          # type: ignore[attr-defined]
    lo = (t_from - margin_s) if t_from is not None else None
    hi = (t_to + margin_s) if t_to is not None else None
    from .sources.parsing import ParseError
    src.open()
    try:
        while True:
            try:
                blk = src.read()
            except ParseError as exc:
                if "播放起点超出文件范围" in str(exc):      # 起点晚于文件末尾 → 段内无数据
                    break
                raise
            if blk is None:
                break
            info = src._last_info or {}
            rows: List[List[str]] = info.get("rows") or []
            header = info.get("header")
            if blk.n == 0 or not rows:
                continue
            t = np.asarray(blk.t, dtype=np.float64)
            if hi is not None and float(t[0]) > hi:
                break
            mask = np.ones(t.shape[0], dtype=bool)
            if lo is not None:
                mask &= t >= lo
            if hi is not None:
                mask &= t <= hi
            if mask.any():
                sel = [rows[k] for k in np.nonzero(mask)[0]]
                yield header, sel, t[mask]
            if hi is not None and float(t[-1]) >= hi:
                break
    finally:
        src.close()


def _layout(cfg: AppConfig, header: Optional[List[str]]) -> Dict[str, Optional[int]]:
    return cfg.columns.layout(header)


def export_range(sides: List[Tuple[AppConfig, int]], t_from: Optional[float], t_to: Optional[float], out_path: str,
                 root: Optional[str] = None) -> Dict[str, Any]:
    """把若干侧（(cfg, source_id) 列表，第 1 个为主侧，决定输出表头）在 [t_from, t_to] 内的原始行写到 out_path。

    返回 {"rows", "sides": {sid: {rows, t_first, t_last, path, header_same}}, "header", "notes", "t_first", "t_last"}。
    """
    notes: List[str] = []
    main_cfg = sides[0][0]
    main_path = _abs_path(main_cfg.source.path, root)
    main_header, _enc = read_header(main_path, main_cfg.columns.encoding, main_cfg.columns.delimiter)
    use_header = bool(main_header) and main_cfg.columns.looks_like_header(main_header)
    out_header: Optional[List[str]] = ([h.strip() for h in main_header] if use_header else None)
    main_layout = _layout(main_cfg, out_header)
    per: Dict[int, Dict[str, Any]] = {}
    buf: List[Tuple[float, int, List[str]]] = []        # (t, sid, row) —— 两侧合并后按时间排序
    for cfg, sid in sides:
        path = _abs_path(cfg.source.path, root)
        n = 0; t0 = None; t1 = None
        hdr, _e = read_header(path, cfg.columns.encoding, cfg.columns.delimiter)
        side_header = [h.strip() for h in hdr] if hdr and cfg.columns.looks_like_header(hdr) else None
        same = (side_header == out_header)
        lay = _layout(cfg, side_header)
        if not same:
            notes.append(f"source_id={sid} 的文件表头/列序与主侧不同，已按主侧列序只保留 7 个标准列重排写出")
        for header, rows, t in iter_rows_in_range(cfg, t_from, t_to, root=root):
            for k, row in enumerate(rows):
                if same:
                    out_row = list(row)
                else:
                    # 按主侧列序重排：主侧每一列若是标准字段 → 取本侧对应列；主侧无表头 → 标准 7 列顺序
                    if out_header is not None:
                        inv = {v: f for f, v in main_layout.items() if v is not None}
                        out_row = []
                        for ci in range(len(out_header)):
                            f = inv.get(ci)
                            src_ci = lay.get(f) if f else None
                            out_row.append(row[src_ci] if (src_ci is not None and src_ci < len(row)) else "")
                    else:
                        out_row = [(row[lay[f]] if (lay.get(f) is not None and lay[f] < len(row)) else "") for f in STD_FIELDS]
                out_row.append(str(sid))
                tt = float(t[k])
                buf.append((tt, sid, out_row))
                n += 1
                t0 = tt if t0 is None else min(t0, tt); t1 = tt if t1 is None else max(t1, tt)
        per[sid] = {"rows": n, "t_first": t0, "t_last": t1, "path": path, "header_same": same,
                    "t_first_local": fmt_local(t0) if t0 is not None else None, "t_last_local": fmt_local(t1) if t1 is not None else None}
    if not buf:
        return {"rows": 0, "sides": per, "header": out_header, "notes": notes, "t_first": None, "t_last": None}
    buf.sort(key=lambda x: (x[0], x[1]))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=main_cfg.columns.delimiter)
        if out_header is not None:
            w.writerow(list(out_header) + ["source_id"])
        for _t, _sid, row in buf:
            w.writerow(row)
    return {"rows": len(buf), "sides": per, "header": (list(out_header) + ["source_id"]) if out_header is not None else None,
            "notes": notes, "t_first": buf[0][0], "t_last": buf[-1][0],
            "t_first_local": fmt_local(buf[0][0]), "t_last_local": fmt_local(buf[-1][0])}
