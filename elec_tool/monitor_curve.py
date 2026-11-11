"""读取实时监测输出的曲线 CSV，供数据处理页「波形预览」子界面显示（v0.99.51）。

这里说的“实时监测输出文件”就是实时落盘写出的曲线文件（``realtime_writer.RealtimeCurveWriter``）：
``output/realtime/<曲线>_<日期>.csv``，以及离线文件播放时写在运行目录 ``output/<时间>/realtime/`` 下的同名文件。
「保存曲线数据」写出的 ``output/curves_<时间>/<曲线>.csv`` 列名相同，也能读。

文件格式：第一行表头；``t_epoch_s`` 是数据时间（epoch 秒）；``source_id`` 是数据来源（0 总线侧 / 1 分路侧，
v0.17 之前的文件没有这一列，一律算总线侧）；``run_id`` 是写入这一行的那次运行（v0.32 起，墙钟毫秒）；
其余是各曲线的字段（电压 Ua/Ub/Uc…、电流 Ia/Ib/Ic…、功率 P/Q/…、功率因数 PF/…）。

只读，不改文件，也不依赖引擎是否在运行。同一个文件里可能混着两侧的数据和多次运行的数据（重复播放同一份
离线文件时数据时间是重叠的），所以读取时先按来源、再按运行批次筛选，然后才按时间排序。
"""

from __future__ import annotations

import csv
import io
import math
import os
import re
import warnings
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

# 界面上可选的五种量 → 文件里对应的列。有功、无功来自同一个功率文件。
QUANTITIES: Dict[str, Dict[str, Any]] = {
    "voltage": {"label": "电压", "unit": "V", "fields": ("Ua", "Ub", "Uc"), "file": "voltage"},
    "current": {"label": "电流", "unit": "A", "fields": ("Ia", "Ib", "Ic"), "file": "current"},
    "p": {"label": "有功功率", "unit": "W", "fields": ("P", "Pa", "Pb", "Pc"), "file": "power"},
    "q": {"label": "无功功率", "unit": "var", "fields": ("Q", "Qa", "Qb", "Qc"), "file": "power"},
    "pf": {"label": "功率因数", "unit": "", "fields": ("PF", "PFa", "PFb", "PFc"), "file": "power_factor"},
}
QUANTITY_ORDER: Tuple[str, ...] = ("voltage", "current", "p", "q", "pf")
SOURCE_LABELS = {0: "总线侧", 1: "分路侧"}

MAX_POINTS_DEFAULT = 5000            # 返回给界面的点数上限（超出则抽稀，保留每段的峰谷）
MAX_POINTS_CAP = 50000
MAX_BYTES_DEFAULT = 256 * 1024 * 1024  # 文件超过这个大小时只读末尾这么多字节（实时文件越靠后越新）
MAX_RUNS_LISTED = 50

# <曲线>_<yyyymmdd>.csv（实时落盘）或 <曲线>.csv（保存曲线数据）；power_factor 要排在 power 前面
_FILE_RE = re.compile(r"^(voltage|current|power_factor|power)(?:_(\d{8}))?\.csv$", re.IGNORECASE)


class MonitorCurveError(ValueError):
    """文件不存在 / 不是曲线文件 / 筛选后没有数据（消息可以直接显示给用户）。"""


def file_kind(name: str) -> Optional[str]:
    """按文件名判断是哪种曲线文件：``voltage`` / ``current`` / ``power`` / ``power_factor``；认不出返回 ``None``。"""
    m = _FILE_RE.match(os.path.basename(str(name or "")))
    return m.group(1).lower() if m else None


def quantities_of_kind(kind: Optional[str]) -> List[str]:
    """某种曲线文件能显示的量（功率文件对应有功和无功两项）。"""
    return [q for q in QUANTITY_ORDER if QUANTITIES[q]["file"] == kind]


def _num(text: Any) -> float:
    try:
        v = float(text)
    except (TypeError, ValueError):
        return math.nan
    return v if math.isfinite(v) else math.nan


def _read_text(path: str, max_bytes: int) -> Tuple[str, bool, int]:
    """返回 ``(文本, 是否只读了末尾, 文件字节数)``。只读末尾时，表头行仍然保留，被截断的那半行丢弃。"""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size <= max_bytes:
            return fh.read().decode("utf-8-sig", errors="replace"), False, size
        head = fh.readline()
        fh.seek(max(len(head), size - max_bytes))
        fh.readline()                                   # 丢掉被截断的半行
        tail = fh.read()
    return (head + tail).decode("utf-8-sig", errors="replace"), True, size


def _parse_columns(body: str, ncol: int, used: Sequence[int]) -> Dict[int, np.ndarray]:
    """把表头之后的正文解析成 ``{列号: float64 数组}``（只解析用到的列；空格子、非数字、无穷大都记为 NaN）。

    先走快路径：numpy 的 C 解析器只转换用到的列，43 万行约 1 秒。实时落盘文件没有引号，空格子先替换成 nan。
    快路径遇到任何它处理不了的内容（引号、列数不齐的行、非数字）就整体退回 ``csv`` 模块逐行解析，
    比表头短的行用空格子补齐。两条路径的结果相同（有用例对照）。
    """
    used = sorted(set(int(i) for i in used))
    out: Optional[np.ndarray] = None
    if '"' not in body:
        text = body
        if ",," in text or ",\n" in text or ",\r" in text:
            text = text.replace(",,", ",nan,").replace(",,", ",nan,").replace(",\r\n", ",nan\r\n").replace(",\n", ",nan\n")
            if text.endswith(","):
                text += "nan"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")                 # 正文为空时 loadtxt 只给一个警告
                out = np.loadtxt(io.StringIO(text), delimiter=",", usecols=used, dtype=np.float64, ndmin=2, comments=None)
        except Exception:                                        # noqa: BLE001 —— 任何解析问题都交给慢路径
            out = None
        if out is not None and (out.ndim != 2 or out.shape[1] != len(used)):
            out = np.zeros((0, len(used))) if out.size == 0 else None      # 正文为空时各版本 numpy 给的形状不一样
    if out is None:
        rows = [r if len(r) >= ncol else r + [""] * (ncol - len(r)) for r in csv.reader(io.StringIO(body, newline="")) if r]
        out = np.array([[_num(r[i]) for i in used] for r in rows], dtype=np.float64).reshape(len(rows), len(used))
    out[~np.isfinite(out)] = np.nan
    return {i: out[:, k] for k, i in enumerate(used)}


def _decimate(cols: Sequence[np.ndarray], n: int, max_points: int) -> np.ndarray:
    """均匀分段抽稀：每段保留首点，再为每条曲线各保留段内的最大值点和最小值点；最后一点总是保留。"""
    per_bucket = 1 + 2 * max(1, len(cols))
    nb = max(1, (max_points - 1) // per_bucket)          # 每段至多 per_bucket 个点，再加末点，总数不超过 max_points
    edges = np.linspace(0, n, nb + 1).astype(np.int64)
    picks: List[int] = [n - 1]
    for b in range(nb):
        a, z = int(edges[b]), int(edges[b + 1])
        if z <= a:
            continue
        picks.append(a)
        if z - a > 2:
            for col in cols:
                seg = col[a:z]
                if not np.all(np.isnan(seg)):
                    picks.append(a + int(np.nanargmax(seg)))
                    picks.append(a + int(np.nanargmin(seg)))
    return np.unique(np.asarray(picks, dtype=np.int64))


def read_curve_file(path: str, *, quantity: str = "", source_id: Optional[int] = None, run: Any = "latest",
                    t_start: Optional[float] = None, t_end: Optional[float] = None, last_s: Optional[float] = None,
                    max_points: int = MAX_POINTS_DEFAULT, max_bytes: int = MAX_BYTES_DEFAULT) -> Dict[str, Any]:
    """读一个曲线 CSV，返回某一种量的曲线。

    quantity   ``voltage`` / ``current`` / ``p`` / ``q`` / ``pf``；空＝文件里有的第一种。
    source_id  0 总线侧 / 1 分路侧；``None``＝文件里只有一侧时取那一侧，两侧都有时取总线侧（并在 notes 里说明）。
    run        ``"latest"``（默认，最近一次运行）/ ``"all"``（不按运行筛选）/ 具体的 run_id。文件没有 run_id 列时不筛选。
    t_start / t_end / last_s  按数据时间筛选：起止时刻（epoch 秒），或只保留最后 last_s 秒。
    max_points 返回的点数上限；超出时抽稀，每段保留各条曲线的峰谷。
    """
    if not path or not os.path.isfile(path):
        raise MonitorCurveError(f"文件不存在：{path}")
    quantity = str(quantity or "").strip().lower()
    if quantity and quantity not in QUANTITIES:
        raise MonitorCurveError(f"不认识的量 '{quantity}'；可选：{'、'.join(QUANTITY_ORDER)}")
    max_points = max(10, min(int(max_points or MAX_POINTS_DEFAULT), MAX_POINTS_CAP))
    text, truncated, size = _read_text(path, max(1024, int(max_bytes)))
    first, _, body = text.partition("\n")
    head = [str(h).strip() for h in (next(csv.reader([first.rstrip("\r")]), None) or [])]
    if "t_epoch_s" not in head:
        raise MonitorCurveError("这不是实时监测输出的曲线文件：表头里没有 t_epoch_s 列"
                                f"（表头前几列：{', '.join(head[:6]) or '空'}）")
    available = [q for q in QUANTITY_ORDER if any(f in head for f in QUANTITIES[q]["fields"])]
    if not available:
        raise MonitorCurveError("这个文件里没有可以显示的量：需要电压（Ua/Ub/Uc）、电流（Ia/Ib/Ic）、"
                                f"功率（P/Q）、功率因数（PF）中的至少一组列（表头：{', '.join(head[:12])}）")
    if not quantity:
        quantity = available[0]
    elif quantity not in available:
        have = "、".join(QUANTITIES[q]["label"] for q in available)
        raise MonitorCurveError(f"这个文件里没有「{QUANTITIES[quantity]['label']}」的列；它可以显示：{have}")
    spec = QUANTITIES[quantity]
    names = [f for f in spec["fields"] if f in head]
    i_t = head.index("t_epoch_s")
    i_sid = head.index("source_id") if "source_id" in head else -1
    i_rid = head.index("run_id") if "run_id" in head else -1
    i_win = head.index("window_s") if "window_s" in head else -1
    idx = [head.index(f) for f in names]

    parsed = _parse_columns(body, len(head), [i for i in (i_t, i_sid, i_rid, i_win, *idx) if i >= 0])
    t_arr = parsed[i_t]
    valid_t = ~np.isnan(t_arr)
    rows_total = int(valid_t.sum())
    if not rows_total:
        raise MonitorCurveError("文件里只有表头，没有数据行")
    t_arr = t_arr[valid_t]
    if i_sid >= 0:
        raw_sid = parsed[i_sid][valid_t]
        sid_arr = np.where(np.isnan(raw_sid), 0, raw_sid).astype(np.int64)      # 来源号为空的行算总线侧
    else:
        sid_arr = np.zeros(rows_total, dtype=np.int64)
    rid_arr = parsed[i_rid][valid_t] if i_rid >= 0 else np.full(rows_total, np.nan)
    cols = [parsed[i][valid_t] for i in idx]
    window_s: Optional[float] = None
    if i_win >= 0:
        win = parsed[i_win][valid_t]
        win = win[~np.isnan(win)]
        if win.size:
            window_s = float(win[-1])
    notes: List[str] = []
    if truncated:
        notes.append(f"文件有 {size / 1024 / 1024:.0f} MB，只读取了末尾 {max_bytes / 1024 / 1024:.0f} MB")

    # ---- 数据来源（总线侧 / 分路侧）
    source_ids = sorted(int(x) for x in np.unique(sid_arr))
    if source_id is None:
        sid = source_ids[0]
        if len(source_ids) > 1:
            both = "、".join(SOURCE_LABELS.get(s, f"来源 {s}") for s in source_ids)
            notes.append(f"文件里有{both}的数据，当前显示{SOURCE_LABELS.get(sid, f'来源 {sid}')}；可在「数据来源」里切换")
    else:
        sid = int(source_id)
        if sid not in source_ids:
            have = "、".join(SOURCE_LABELS.get(s, f"来源 {s}") for s in source_ids)
            raise MonitorCurveError(f"文件里没有{SOURCE_LABELS.get(sid, f'来源 {sid}')}的数据；文件里有：{have}")
    keep = sid_arr == sid

    # ---- 运行批次
    run_ids: List[Dict[str, Any]] = []
    run_id: Optional[int] = None
    run_mode = "none"
    has_run = i_rid >= 0 and bool(np.any(~np.isnan(rid_arr[keep])))
    if has_run:
        side_rids = rid_arr[keep]; side_t = t_arr[keep]
        valid = side_rids[~np.isnan(side_rids)]
        uniq, first = np.unique(valid, return_index=True)
        order = [int(r) for r in uniq[np.argsort(first)]]         # 各次运行，按在文件里首次出现的先后
        seen = set(order)
        for r in order[-MAX_RUNS_LISTED:]:
            m = side_rids == r
            run_ids.append({"id": r, "rows": int(m.sum()), "t_first": float(side_t[m].min()), "t_last": float(side_t[m].max())})
        want = str(run if run is not None else "latest").strip().lower() or "latest"
        if want == "all":
            run_mode = "all"
            if len(order) > 1:
                notes.append(f"文件里有 {len(order)} 次运行的数据，已按时间合在一起显示；同一时刻有多行时取最后写入的一行")
        else:
            if want == "latest":
                run_id = int(valid[-1]); run_mode = "latest"       # 文件里最后写入的那次运行
                if len(order) > 1:
                    notes.append(f"文件里有 {len(order)} 次运行的数据，当前只显示最近一次；可在「运行批次」里切换")
            else:
                try:
                    run_id = int(float(want))
                except ValueError:
                    raise MonitorCurveError(f"运行批次写法不对：'{run}'；可写 latest、all 或文件里的 run_id") from None
                run_mode = "one"
                if run_id not in seen:
                    raise MonitorCurveError(f"文件里没有 run_id={run_id} 的数据（该来源共有 {len(order)} 次运行）")
            keep = keep & (rid_arr == run_id)

    # ---- 时间
    if not np.any(keep):
        raise MonitorCurveError("按当前的数据来源 / 运行批次筛选后没有数据")
    lo_all, hi_all = float(t_arr[keep].min()), float(t_arr[keep].max())
    if t_start is not None:
        keep = keep & (t_arr >= float(t_start))
    if t_end is not None:
        keep = keep & (t_arr <= float(t_end))
    if last_s is not None:
        if not float(last_s) > 0:
            raise MonitorCurveError(f"「只看最近」的时长必须大于 0（当前 {last_s}）")
        if np.any(keep):
            keep = keep & (t_arr >= float(t_arr[keep].max()) - float(last_s))
    if not np.any(keep):
        from .timefmt import fmt_local
        raise MonitorCurveError(f"所选时间段内没有数据（文件里这部分数据的时间范围是 {fmt_local(lo_all)} → {fmt_local(hi_all)}）")
    sel = np.flatnonzero(keep)
    order_idx = sel[np.argsort(t_arr[sel], kind="stable")]
    t_sel = t_arr[order_idx]
    if t_sel.size > 1:                                   # 同一时刻的重复行只留最后写入的一条
        last_of_run = np.append(t_sel[1:] != t_sel[:-1], True)
        order_idx = order_idx[last_of_run]; t_sel = t_sel[last_of_run]
    series = [c[order_idx] for c in cols]
    empty = [n for n, c in zip(names, series) if np.all(np.isnan(c))]
    if empty and len(empty) < len(names):
        notes.append(f"{'、'.join(empty)} 没有数值，未显示")
    kept = [(n, c) for n, c in zip(names, series) if not np.all(np.isnan(c))]
    if not kept:
        raise MonitorCurveError(f"所选范围内「{spec['label']}」的各列（{'、'.join(names)}）都没有数值")
    n_sel = int(t_sel.size)
    decimated = n_sel > max_points
    if decimated:
        pick = _decimate([c for _, c in kept], n_sel, max_points)
        t_sel = t_sel[pick]; kept = [(n, c[pick]) for n, c in kept]
        notes.append(f"共 {n_sel} 个点，超过显示上限 {max_points}，已抽稀为 {int(t_sel.size)} 个点（保留每段的最大值和最小值）")
    return {
        "ok": True, "path": path, "quantity": quantity, "label": spec["label"], "unit": spec["unit"],
        "quantities": [{"id": q, "label": QUANTITIES[q]["label"], "unit": QUANTITIES[q]["unit"]} for q in available],
        "fields": [n for n, _ in kept],
        "t": [float(x) for x in t_sel],
        "series": {n: [None if v != v else float(round(float(v), 6)) for v in c] for n, c in kept},
        "n": int(t_sel.size), "rows_total": rows_total, "rows_selected": n_sel, "decimated": decimated,
        "source_ids": source_ids, "source_id": sid, "run_ids": run_ids, "run_id": run_id, "run_mode": run_mode,
        "t_first": float(t_sel[0]), "t_last": float(t_sel[-1]), "window_s": window_s,
        "size_bytes": size, "mtime": os.path.getmtime(path), "truncated": truncated, "notes": notes,
    }


def list_curve_files(dirs: Iterable[Tuple[str, str]], limit: int = 200) -> List[Dict[str, Any]]:
    """列出若干目录下能在「波形预览」里显示的实时监测输出文件（电压 / 电流 / 功率 / 功率因数），新的在前。

    dirs：``[(说明, 目录), …]``；同一个目录出现多次只列一次。不读文件内容。
    """
    out: List[Dict[str, Any]] = []
    seen = set()
    for label, d in dirs:
        if not d:
            continue
        real = os.path.realpath(d)
        if real in seen or not os.path.isdir(real):
            continue
        seen.add(real)
        try:
            names = sorted(os.listdir(real))
        except OSError:
            continue
        for name in names:
            m = _FILE_RE.match(name)
            fp = os.path.join(d, name)
            if not m or not os.path.isfile(fp):
                continue
            kind = m.group(1).lower()
            try:
                st = os.stat(fp)
            except OSError:
                continue
            out.append({"path": fp, "name": name, "dir": d, "dir_label": label, "kind": kind, "day": m.group(2),
                        "quantities": quantities_of_kind(kind), "size_bytes": int(st.st_size), "mtime": float(st.st_mtime)})
    out.sort(key=lambda f: (-f["mtime"], f["name"]))
    return out[: max(1, int(limit))]
