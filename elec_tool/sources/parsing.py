"""CSV / 时间戳解析工具（离线与实时源共用）。

用户给定格式（2026-10-10 确认）：
    时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流
采样频率 6400Hz；编码未指定 → 自适应（utf-8-sig / utf-8 / gbk / gb18030）。
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..blocks import SampleBlock
from ..config import ColumnMap, SamplingConfig

ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1")

TS_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S",
    "%Y%m%d%H%M%S%f", "%Y%m%d %H%M%S",
    "%Y-%m-%d %H:%M", "%H:%M:%S.%f", "%H:%M:%S",
)


class ParseError(ValueError):
    """解析失败（带可执行修复提示）。"""


def detect_encoding(path: str, sample_bytes: int = 65536) -> str:
    """按候选编码尝试解码文件头，返回第一个成功的编码。"""
    with open(path, "rb") as fh:
        raw = fh.read(sample_bytes)
    return decode_encoding(raw)


def decode_encoding(raw: bytes) -> str:
    for enc in ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    raise ParseError(f"无法识别文件编码（已尝试 {ENCODINGS}）；请在配置 columns.encoding 中显式指定")


@dataclass
class TimestampInfo:
    mode: str                      # datetime | epoch_s | epoch_ms | epoch_us | epoch_ns | relative_s
    t: np.ndarray                  # epoch 秒（float64）
    fs_est: float                  # 由时间戳中位差推算的采样率
    notes: List[str]


def parse_timestamps(values: Sequence[str], unit: str = "auto",
                     tz_offset_h: float = 0.0) -> TimestampInfo:
    """把时间戳列解析为 epoch 秒数组。

    unit: auto / s / ms / us / ns / datetime
    tz_offset_h: 本地时区偏移（小时）。datetime 字符串按**本地时间**解释，转 UTC epoch 时减去偏移；
                 默认 0（即把字符串当 UTC 处理）——若用户数据为北京时间需设 8，
                 但注意：**所有电气量计算只用时间差**，时区偏移不影响任何计算结果，
                 只影响界面显示的绝对时刻。
    """
    notes: List[str] = []
    vals = list(values)
    if not vals:
        return TimestampInfo("empty", np.empty(0), float("nan"), ["时间戳列为空"])

    # 1) 数值型（epoch 或相对秒）
    numeric: Optional[np.ndarray] = None
    if unit in ("auto", "s", "ms", "us", "ns"):
        try:
            numeric = np.array([float(str(v).strip()) for v in vals], dtype=np.float64)
        except (TypeError, ValueError):
            numeric = None
    if numeric is not None and unit != "datetime":
        mode = unit
        if mode == "auto":
            med = float(np.median(np.abs(numeric)))
            if med > 1e17:
                mode = "ns"
            elif med > 1e14:
                mode = "us"
            elif med > 1e11:
                mode = "ms"
            elif med > 1e8:
                mode = "s"
            else:
                mode = "relative_s"
                notes.append(f"时间戳中位值 {med:.3g} 小于 1e8，判为**相对秒**（非 epoch）；"
                             "绝对时刻以第一个样本为 0 点")
        scale = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "relative_s": 1.0}.get(mode, 1.0)
        t = numeric * scale
        if mode == "relative_s":
            t = t - t[0]
        return TimestampInfo(mode, t.astype(np.float64), _infer_fs(t), notes)

    # 2) 日期时间字符串
    parsed: List[float] = []
    used_fmt: Optional[str] = None
    offset = tz_offset_h * 3600.0
    for v in vals:
        s = str(v).strip()
        got = None
        for fmt in TS_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                got = dt.replace(tzinfo=timezone.utc).timestamp() - offset
                used_fmt = used_fmt or fmt
                break
            except ValueError:
                continue
        if got is None:
            # 兜底：ISO 解析（含 Z / +08:00 等）
            try:
                got = datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
                used_fmt = used_fmt or "fromisoformat"
            except ValueError as exc:
                raise ParseError(
                    f"时间戳 '{s}' 无法解析；已尝试格式 {TS_FORMATS} 与 ISO8601。"
                    f"请在配置中设 columns.timestamp_unit 或修正数据格式（原始错误：{exc}）"
                ) from exc
        parsed.append(float(got))
    t = np.asarray(parsed, dtype=np.float64)
    notes.append(f"时间戳格式识别为 '{used_fmt}'；tz_offset_h={tz_offset_h}（仅影响显示，不影响计算）")
    return TimestampInfo("datetime", t, _infer_fs(t), notes)


def _infer_fs(t: np.ndarray) -> float:
    """由时间戳推算采样率。

    做法：先用中位差找出断采点（>2×中位差）切段，再对**最长连续段**做线性拟合取斜率。
    为什么不用中位差直接倒数：6400Hz 的间隔是 156.25µs，若时间戳只写到 µs（ISO 常见），
    单点间隔会在 156/157µs 之间量化，中位差给出 6410Hz 的假偏差（0.16%）；
    线性拟合把量化误差在 N 个点上平均掉，偏差降到 1e-5 量级。
    """
    if t.size < 3:
        return float("nan")
    dt = np.diff(t)
    pos = dt[dt > 0]
    if pos.size == 0:
        return float("nan")
    med = float(np.median(pos))
    if med <= 0:
        return float("nan")
    breaks = np.where(dt > 2.0 * med)[0]
    segs = np.split(np.arange(t.size), breaks + 1)
    seg = max(segs, key=len) if segs else np.arange(t.size)
    if seg.size >= 3:
        slope = float(np.polyfit(seg.astype(np.float64), t[seg], 1)[0])
        if slope > 0:
            return float(1.0 / slope)
    return float(1.0 / med)


def check_fs(fs_est: float, sampling: SamplingConfig) -> Tuple[float, List[str]]:
    """用时间戳推算的 fs 校验配置 fs；不一致时返回告警（不擅自改配置）。"""
    notes: List[str] = []
    if not sampling.fs_from_timestamps or not np.isfinite(fs_est) or fs_est <= 0:
        return float(sampling.fs), notes
    rel = abs(fs_est - sampling.fs) / sampling.fs
    if rel > sampling.fs_tolerance:
        notes.append(
            f"⚠️ 时间戳推算采样率 {fs_est:.3f}Hz 与配置 fs={sampling.fs}Hz 偏差 {rel*100:.3f}% "
            f"> 容差 {sampling.fs_tolerance*100:.2f}%：谐波次数/bin 映射会错位。"
            f"请修正 sampling.fs 或检查数据是否丢点"
        )
    else:
        notes.append(f"采样率校验通过：时间戳推算 {fs_est:.3f}Hz ≈ 配置 {sampling.fs}Hz（偏差 {rel*100:.4f}%）")
    return float(sampling.fs), notes


def parse_rows(rows: Sequence[Sequence[str]], colmap: ColumnMap, sampling: SamplingConfig,
               source: str = "", seq: int = 0,
               tz_offset_h: float = 0.0) -> Tuple[SampleBlock, Dict[str, object]]:
    """把 CSV 数据行（不含表头）解析为 SampleBlock（二次侧值，未做 PT/CT 变换）。"""
    if not rows:
        return SampleBlock.empty(source), {"n_rows": 0, "notes": ["无数据行"]}
    ncols = len(rows[0])
    data = np.full((len(rows), ncols), np.nan, dtype=np.float64)
    bad_cells: List[Tuple[int, int, str]] = []
    ts_raw: List[str] = []
    for r, row in enumerate(rows):
        if len(row) < ncols:
            row = list(row) + [""] * (ncols - len(row))
        ts_raw.append(row[0] if not isinstance(row[0], (int, float)) else str(row[0]))
        for c in range(ncols):
            cell = str(row[c]).strip()
            if cell == "" or cell.lower() in ("nan", "null", "none", "-"):
                continue
            try:
                data[r, c] = float(cell)
            except ValueError:
                bad_cells.append((r, c, cell))
    # 时间戳列索引由 colmap 决定（默认第 0 列）
    return _assemble(data, ts_raw, colmap, sampling, source, seq, bad_cells, tz_offset_h)


def _assemble(data: np.ndarray, ts_raw: List[str], colmap: ColumnMap, sampling: SamplingConfig,
              source: str, seq: int, bad_cells: List[Tuple[int, int, str]],
              tz_offset_h: float) -> Tuple[SampleBlock, Dict[str, object]]:
    notes: List[str] = []
    # 表头缺失时按用户给定列序（时间戳,A相电压,A相电流,...）假定
    header = [colmap.timestamp, colmap.ua, colmap.ia, colmap.ub, colmap.ib, colmap.uc, colmap.ic]
    idx = colmap.resolve(header)
    ts_info = parse_timestamps(ts_raw, colmap.timestamp_unit, tz_offset_h)
    notes.extend(ts_info.notes)
    _, fs_notes = check_fs(ts_info.fs_est, sampling)
    notes.extend(fs_notes)

    def col(key: str) -> np.ndarray:
        c = idx[key]
        return data[:, c] if c < data.shape[1] else np.full(data.shape[0], np.nan)

    u = np.vstack([col("ua"), col("ub"), col("uc")])
    i = np.vstack([col("ia"), col("ib"), col("ic")])

    # 时间戳无效（全 nan / 非单调）时用配置 fs 合成等间隔时间轴
    t = ts_info.t
    if t.size != data.shape[0] or not np.all(np.isfinite(t)):
        notes.append("时间戳不可用，按配置 fs 合成等间隔时间轴（绝对时刻以 0 起算）")
        t = np.arange(data.shape[0], dtype=np.float64) / sampling.fs
    nan_count = int(np.sum(~np.isfinite(u)) + np.sum(~np.isfinite(i)))
    if nan_count:
        total_cells = 6 * data.shape[0]
        notes.append(
            f"存在 {nan_count} 个空值/非法采样单元（占比 {100.0*nan_count/max(total_cells,1):.3f}%）："
            "已按通道线性插值补齐后再计算（见 NILM_DATA_DICT.md Q-01 质量规则）")
        u = _nan_policy(u, notes, "电压")
        i = _nan_policy(i, notes, "电流")
    if bad_cells:
        sample = ", ".join(f"行{r}列{c}='{v}'" for r, c, v in bad_cells[:5])
        notes.append(f"{len(bad_cells)} 个单元格非数值（示例：{sample}）")
    block = SampleBlock(t=t, u=u, i=i, scaled=False, source=source, seq=seq)
    info = {"n_rows": int(data.shape[0]), "n_nan": nan_count, "n_bad_cells": len(bad_cells),
            "ts_mode": ts_info.mode, "fs_est": ts_info.fs_est, "notes": notes,
            "columns": idx, "t_start": block.t_start, "t_end": block.t_end}
    return block, info


def _nan_policy(arr: np.ndarray, notes: List[str], label: str) -> np.ndarray:
    """NaN 处理：线性插值（端点用最近有效值填充）。仅用于**少量**缺测；大面积缺测应告警。"""
    out = arr.copy()
    for k in range(out.shape[0]):
        row = out[k]
        bad = ~np.isfinite(row)
        if not bad.any():
            continue
        ratio = float(bad.mean())
        if ratio > 0.05:
            notes.append(f"⚠️ {label} 第{k}通道缺测比例 {ratio*100:.1f}% > 5%：已线性插值，"
                         "但该段结果不可用于验收（应剔除或补采）")
        good = np.where(~bad)[0]
        if good.size == 0:
            out[k] = 0.0
            continue
        out[k] = np.interp(np.arange(row.size), good, row[good])
    return out


def read_header(path: str, encoding: str, delimiter: str) -> Tuple[List[str], str]:
    """读表头；encoding='auto' 时自动探测。返回 (表头列表, 实际编码)。"""
    enc = encoding
    if enc == "auto":
        enc = detect_encoding(path)
    with open(path, "r", encoding=enc, newline="") as fh:
        first = fh.readline()
    if not first.strip():
        raise ParseError(f"{path} 首行为空，无法识别表头")
    header = next(csv.reader(io.StringIO(first), delimiter=delimiter))
    return [h.strip() for h in header], enc


def iter_csv_blocks(path: str, colmap: ColumnMap, sampling: SamplingConfig,
                    block_samples: int = 6400, encoding: str = "auto",
                    delimiter: str = ",", has_header: Optional[bool] = None,
                    tz_offset_h: float = 0.0, max_blocks: Optional[int] = None):
    """流式读取 CSV，按 block_samples 逐块产出 (SampleBlock, info)。"""
    if not os.path.isfile(path):
        raise ParseError(f"CSV 文件不存在：{path}")
    enc = encoding if encoding != "auto" else detect_encoding(path)
    with open(path, "r", encoding=enc, newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        try:
            first = next(reader)
        except StopIteration:
            raise ParseError(f"{path} 为空文件") from None
        use_header = has_header if has_header is not None else colmap.has_header
        header: Optional[List[str]] = None
        buf: List[List[str]] = []
        if use_header:
            header = [h.strip() for h in first]
            try:
                colmap.resolve(header)
            except Exception:
                # 首行不像表头（解析失败）→ 当数据行处理
                header = None
                buf.append(first)
        else:
            buf.append(first)
        idx_map = colmap.resolve(header) if header else None
        seq = 0
        produced = 0
        for row in reader:
            if not row or all(not str(c).strip() for c in row):
                continue
            buf.append(row)
            if len(buf) >= block_samples:
                blk, info = _rows_to_block(buf, colmap, sampling, idx_map, path, seq, tz_offset_h)
                buf = []
                seq += 1
                produced += 1
                yield blk, info
                if max_blocks and produced >= max_blocks:
                    return
        if buf:
            blk, info = _rows_to_block(buf, colmap, sampling, idx_map, path, seq, tz_offset_h)
            yield blk, info


def _rows_to_block(rows: List[List[str]], colmap: ColumnMap, sampling: SamplingConfig,
                   idx_map: Optional[Dict[str, int]], source: str, seq: int,
                   tz_offset_h: float) -> Tuple[SampleBlock, Dict[str, object]]:
    if idx_map is None:
        return parse_rows(rows, colmap, sampling, source, seq, tz_offset_h)
    ncols = max(idx_map.values()) + 1
    data = np.full((len(rows), ncols), np.nan, dtype=np.float64)
    ts_raw: List[str] = []
    bad: List[Tuple[int, int, str]] = []
    for r, row in enumerate(rows):
        ts_raw.append(row[idx_map["timestamp"]].strip() if idx_map["timestamp"] < len(row) else "")
        for key, c in idx_map.items():
            if key == "timestamp":
                continue
            if c >= len(row):
                continue
            cell = str(row[c]).strip()
            if cell == "" or cell.lower() in ("nan", "null", "none", "-"):
                continue
            try:
                data[r, c] = float(cell)
            except ValueError:
                bad.append((r, c, cell))
    # 重排到标准列序（0..6）供 _assemble 使用
    std = np.full((len(rows), 7), np.nan, dtype=np.float64)
    order = ["timestamp", "ua", "ia", "ub", "ib", "uc", "ic"]
    for new_c, key in enumerate(order):
        old_c = idx_map[key]
        if key == "timestamp":
            continue
        std[:, new_c] = data[:, old_c]
    return _assemble(std, ts_raw, colmap, sampling, source, seq, bad, tz_offset_h)
