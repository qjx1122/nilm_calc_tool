"""CSV / 时间戳解析工具（离线与实时源共用）。

用户给定格式（2026-10-10 确认）：
    时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流
采样频率 6400Hz；编码未指定 → 自适应（utf-8-sig / utf-8 / gbk / gb18030）。
"""

from __future__ import annotations

import csv
import io
import os
import re
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


# 「日期/日期/日期 时:分:秒[.小数]」通用骨架：日期段三个整数、任意位数小数秒。
# 覆盖用户 2026-10-12 给出的采集器写法 ``0/00/00 00:12:40.0000``（日期段全 0 ＝无日期，
# 小数 4 位＝0.1ms 分辨率），也顺手覆盖 ``2026/1/5 8:03:07.5`` 这类非补零写法——
# strptime 对这两类都解析失败。
_RE_SLASH_CLOCK = re.compile(
    r"^\s*(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})[ T](\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?\s*$")

# 无日期（日期段全 0）时的时间基准：epoch 日 0（1970-01-01 00:00:00 UTC）。
# 这样 t 仍是「epoch 秒」语义（界面按 时:分:秒 显示正确），而绝对日期由
# source.custom_time_start 指定（离线播放自定义时间功能）。
_NO_DATE_BASE = 0.0


def _parse_slash_clock(s: str, tz_offset_h: float) -> Optional[Tuple[float, bool]]:
    """解析 ``Y/M/D HH:MM:SS.ffff`` 骨架。返回 (epoch 秒, 是否无日期) 或 None（不匹配）。

    日期段为 0/00/00（或任一段为 0）→ 判为**无日期**，只取当天时刻（秒数自 00:00:00 起）。
    小数秒按十进制位数换算（4 位 = 0.1ms，不受 %f 的 6 位限制）。
    """
    m = _RE_SLASH_CLOCK.match(s)
    if not m:
        return None
    a, b, c, hh, mm, ss, frac = m.groups()
    frac_s = (float("0." + frac) if frac else 0.0)
    tod = int(hh) * 3600.0 + int(mm) * 60.0 + int(ss) + frac_s
    if int(hh) > 23 or int(mm) > 59 or int(ss) > 60:
        return None
    y, mo, d = int(a), int(b), int(c)
    if y == 0 or mo == 0 or d == 0:
        return _NO_DATE_BASE + tod, True
    # 日/月/年 或 年/月/日：第一段 >31 视为年；两位年补 2000
    if y <= 31 and d > 31:
        y, d = d, y
    if y < 100:
        y += 2000
    try:
        base = datetime(y, mo, d, tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None
    return base + tod - tz_offset_h * 3600.0, False


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


def _flag_degenerate_clock(t: np.ndarray, notes: List[str]) -> None:
    """时间轴退化必须显式告警：否则 t「看着有值」，缺口检测与时段对齐全失真。

    两类退化：① 整块无递增对（时标精度远粗于采样间隔，典型是用 float32 存 epoch 秒——
    float32 在 1.7e9 秒处量化步长约 128s，一整块 0.1s 的样本时标完全相同）；
    ② 存在回退（字节序/字段顺序解析错、多通道交错、设备时标回绕）。
    注意：ms 级时标配 6400Hz 会出现**局部重复**但仍有递增对，属正常，不告警。
    """
    if t.size < 2:
        return
    dt = np.diff(t)
    if not np.any(dt > 0):
        notes.append(
            "时间戳整块无递增（全部相同）：时标精度远粗于采样间隔，或用 float32 存 epoch 秒"
            "导致量化（float32 在 1.7e9 秒处步长约 128s）。电气量仍按样本序与配置 fs 计算，"
            "但时间轴与缺口检测不可信；建议协议改用 double 或整数毫秒时标")
    elif np.any(dt < 0):
        notes.append(
            f"时间戳存在 {int(np.count_nonzero(dt < 0))} 处回退（非单调递增）："
            "可能是字节序/字段顺序解析错误、多通道交错或设备时标回绕；"
            "请核对 source.struct_fmt 与 columns 映射")


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
        # 合理性闸门：换算后应是 epoch 秒（~1e9）或相对秒（~0 起）。
        # 超出 1e11（≈公元 5138 年）或非有限值，说明**时间戳根本没被正确取到**——
        # TCP 二进制帧最常见于 struct_fmt/struct_fields 与真实协议不一致（字节序/字段顺序/类型），
        # CSV 则常见于列映射错位或时间戳单位判断失误。此处必须显式报错，
        # 否则坏值会一路传到显示层（time.localtime 抛 OverflowError）或产出错误时间轴。
        t = t.astype(np.float64)
        if t.size and (not np.all(np.isfinite(t)) or float(np.max(np.abs(t))) > 1e11):
            bad = float(np.max(np.abs(t[np.isfinite(t)]))) if np.any(np.isfinite(t)) else float("nan")
            raise ParseError(
                f"时间戳换算后不合理（模式={mode}，最大绝对值 {bad:.6g} 秒，超过 1e11 或含 inf/nan）。"
                f"排查：① TCP 二进制帧请核对 source.struct_fmt（字节序/类型，如 '<7d' 小端 double、"
                f"'>7f' 大端 float）与 struct_fields 字段顺序是否与真实协议一致；"
                f"② CSV 请核对 columns 列映射与 timestamp_unit（原始中位值 "
                f"{float(np.median(np.abs(numeric))):.6g}）；"
                f"③ 若协议用 float32 存 epoch 秒，精度只有 ~1e2 秒级，必须改用 double 或整数毫秒")
        _flag_degenerate_clock(t, notes)
        return TimestampInfo(mode, t, _infer_fs(t), notes)

    # 2) 日期时间字符串
    parsed: List[float] = []
    used_fmt: Optional[str] = None
    offset = tz_offset_h * 3600.0
    no_date = 0
    for v in vals:
        s = str(v).strip()
        got = None
        sc = _parse_slash_clock(s, tz_offset_h)
        if sc is not None:
            got, nd = sc
            no_date += int(nd)
            used_fmt = used_fmt or ("Y/M/D HH:MM:SS.f(无日期=0/00/00)" if nd else "Y/M/D HH:MM:SS.f")
            parsed.append(float(got))
            continue
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
    mode = "datetime"
    if no_date:
        # 只有当天时刻：跨午夜会回绕（23:59:59.9 → 00:00:00.0），按「回退超过半天即跨日」展开，
        # 否则 diff<0 会被判为时标回退、缺口检测把整段数据当成倒流。
        t = _unwrap_midnight(t)
        mode = "clock_time"
        notes.append(
            "时间戳只有时刻、无日期（日期段为 0/00/00）：绝对时刻按 1970-01-01 + 当天时刻处理，"
            "跨午夜自动展开；需要真实日期请在数据源启用「自定义播放时间」并填写起始时间")
    _flag_degenerate_clock(t, notes)
    return TimestampInfo(mode, t, _infer_fs(t), notes)


def _unwrap_midnight(t: np.ndarray) -> np.ndarray:
    """当天时刻序列跨午夜展开：相邻差 < -12h 视为跨日，其后整体 +86400。"""
    if t.size < 2:
        return t
    dt = np.diff(t)
    wraps = np.where(dt < -43200.0)[0]
    if wraps.size == 0:
        return t
    out = t.copy()
    for w in wraps:
        out[w + 1:] += 86400.0
    return out


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
        for c in range(1, ncols):          # 第 0 列是时间戳（字符串），不按数值解析，否则每行都记一次「非数值」
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
