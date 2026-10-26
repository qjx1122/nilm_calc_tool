"""CSV / 时间戳解析工具（离线与实时源共用）。

用户给定格式（2026-10-10 确认）：
    时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流
采样频率 6400Hz；编码未指定 → 自适应（utf-8-sig / utf-8 / gbk / gb18030）。
"""

from __future__ import annotations

import csv
import io
import os
import time
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
_NO_DATE_BASE = 86400.0        # 1970-01-02：减去 UTC+14 以内的任何时区偏移仍为正 epoch（Windows localtime 不接受负值，F-40）


def local_utc_offset_h(t: Optional[float] = None) -> float:
    """本机本地时区相对 UTC 的偏移（小时，东八区＝8）。t 给出时按该时刻（含夏令时）计算。"""
    lt = time.localtime(t if t is not None else time.time())
    return float(lt.tm_gmtoff) / 3600.0


def file_tz_offset_h(cfg) -> float:
    """离线文件文本时标的解释偏移：source.file_time_utc=True → 0（按 UTC）；否则本地时区偏移（时间与文件一致）。"""
    return 0.0 if bool(getattr(cfg.source, "file_time_utc", False)) else local_utc_offset_h()


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
        return _NO_DATE_BASE + tod - tz_offset_h * 3600.0, True   # 与带日期写法同样按 tz_offset_h 解释（本地显示＝文件时刻）
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


def _parse_slash_clock_block(vals: Sequence[str], tz_offset_h: float) -> Optional[Tuple[List[float], int, str]]:
    """v0.82：整块 ``Y/M/D HH:MM:SS[.ffff]`` 的快速解析。返回 (epoch 秒列表, 无日期个数, 格式名) 或 None（有任一值不符合骨架）。

    与逐值 ``_parse_slash_clock`` 完全等价：整秒前缀（``Y/M/D HH:MM:SS``）走原函数并缓存，小数部分按
    ``float("0." + frac)`` 相加——带日期写法结果与逐值解析逐位相同，无日期写法只差浮点加法顺序（≤ 1 ulp，≈1e-11 s）。
    """
    s0 = str(vals[0]).strip()
    if not _RE_SLASH_CLOCK.match(s0):
        return None
    cache: Dict[str, Tuple[float, bool]] = {}
    out: List[float] = []
    no_date = 0
    for v in vals:
        s = str(v).strip()
        head, dot, frac = s.rpartition(".")
        if not dot:
            head, frac = s, ""
        hit = cache.get(head)
        if hit is None:
            r = _parse_slash_clock(head, tz_offset_h)
            if r is None or (frac and not frac.isdigit()):
                return None
            hit = cache[head] = r
        elif frac and not frac.isdigit():
            return None
        base, nd = hit
        out.append(base + (float("0." + frac) if frac else 0.0))
        no_date += int(nd)
    fmt = "Y/M/D HH:MM:SS.f(无日期=0/00/00)" if no_date else "Y/M/D HH:MM:SS.f"
    return out, no_date, fmt


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
            numeric = np.array(vals, dtype=np.float64)            # v0.82：整列交给 numpy 解析（C 级），失败再按字符串时间处理
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
    # v0.82 快路径：``Y/M/D HH:MM:SS.ffff``（现场主流写法）——同一秒内的几千行只有小数部分不同，
    # 按 "整秒前缀" 缓存一次正则解析结果，再加上小数秒；任一值不符合骨架即整体退回逐值慢路径（结果逐位一致，见测试）
    fast = _parse_slash_clock_block(vals, tz_offset_h)
    if fast is not None:
        parsed, no_date, used_fmt = fast
        vals = []
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
    notes.append(f"时间戳格式识别为 '{used_fmt}'；按{'UTC' if abs(tz_offset_h) < 1e-9 else f'本地时间（UTC{tz_offset_h:+g}）'}解释"
                 f"（source.file_time_utc 可改；只影响时间轴的绝对位置，不影响计算）")
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
        # v0.82：一元线性回归闭式解（与 polyfit 一次拟合同一最小二乘解，省 polyfit 的 Vandermonde/SVD 开销）
        xs = seg.astype(np.float64); ys = t[seg]
        xm = xs.mean(); ym = ys.mean()
        dx = xs - xm
        den = float(np.dot(dx, dx))
        slope = float(np.dot(dx, ys - ym) / den) if den > 0 else 0.0
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
    """把 CSV 数据行（不含表头）解析为 SampleBlock（二次侧值，未做 PT/CT 变换）。
    取列规则＝``colmap.layout(None)``：未启用映射＝默认列序；启用映射＝按列号。"""
    if not rows:
        return SampleBlock.empty(source), {"n_rows": 0, "notes": ["无数据行"]}
    return _rows_to_block([list(r) for r in rows], colmap, sampling, colmap.layout(None), source, seq, tz_offset_h)


def _assemble(data: np.ndarray, ts_raw: List[str], colmap: ColumnMap, sampling: SamplingConfig,
              source: str, seq: int, bad_cells: List[Tuple[int, int, str]],
              tz_offset_h: float, unmapped: Optional[List[str]] = None,
              layout: Optional[Dict[str, Optional[int]]] = None) -> Tuple[SampleBlock, Dict[str, object]]:
    """data 已是标准列序（0=时间戳占位，1..6=ua,ia,ub,ib,uc,ic）。unmapped 列出未映射字段：
    通道按 0 播放（不参与插值），时间戳未映射则合成时间轴。"""
    notes: List[str] = []
    idx = {k: i for i, k in enumerate(ColumnMap.FIELDS)}
    unmapped = list(unmapped or [])
    for k in unmapped:
        if k != "timestamp":
            data[:, idx[k]] = 0.0
    if unmapped:
        names = "、".join(ColumnMap.FIELD_NAMES[k] for k in unmapped)
        notes.append(f"列映射：未映射字段 {names} 不播放（通道按 0 处理"
                     + ("，时间轴按配置 fs 合成" if "timestamp" in unmapped else "") + "）")
    if "timestamp" in unmapped or not ts_raw:
        ts_raw = []
    if ts_raw:
        ts_info = parse_timestamps(ts_raw, colmap.timestamp_unit, tz_offset_h)
        notes.extend(ts_info.notes)
        _, fs_notes = check_fs(ts_info.fs_est, sampling)
        notes.extend(fs_notes)
    else:
        ts_info = parse_timestamps([], colmap.timestamp_unit, tz_offset_h)

    def col(key: str) -> np.ndarray:
        c = idx[key]
        return data[:, c] if c < data.shape[1] else np.full(data.shape[0], np.nan)

    u = np.vstack([col("ua"), col("ub"), col("uc")])
    i = np.vstack([col("ia"), col("ib"), col("ic")])

    # 时间戳无效（全 nan / 非单调）时用配置 fs 合成等间隔时间轴
    t = ts_info.t
    if t.size != data.shape[0] or not np.all(np.isfinite(t)):
        if "timestamp" not in unmapped:
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
            "columns": (layout if layout is not None else idx), "unmapped": unmapped,
            "t_start": block.t_start, "t_end": block.t_end}
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


def _tod_of(t: float, mode: str, tz_offset_h: float = 0.0) -> float:
    """时标的「当天时刻」秒数：无日期写法（clock_time）按解释偏移还原文件时刻；带日期的按本地时间取时刻（与界面显示一致）。"""
    if mode == "clock_time":
        return (float(t) + tz_offset_h * 3600.0) % 86400.0
    from ..timefmt import local_tod_s
    return local_tod_s(t)


def _seek_rows(reader, first_rows: List[List[str]], n_skip: int) -> Tuple[List[List[str]], int]:
    """跳过 n_skip 条非空数据行（含 first_rows 里已经读到的）。返回 (剩余待处理的行, 实际跳过行数)。"""
    skipped = 0
    pending = list(first_rows)
    while skipped < n_skip:
        if pending:
            pending.pop(0)
            skipped += 1
            continue
        try:
            row = next(reader)
        except StopIteration:
            break
        if not row or all(not str(c).strip() for c in row):
            continue
        skipped += 1
    return pending, skipped


def _ts_values(raw: List[str], kind: str, colmap: ColumnMap, tz_offset_h: float) -> Tuple[np.ndarray, np.ndarray]:
    """把一批时标文本变成可与播放起点比较的数值：abs → epoch；tod → 当天秒。返回 (比较值, epoch)。"""
    info = parse_timestamps(raw, colmap.timestamp_unit, tz_offset_h)
    t = info.t
    if kind == "abs" or not t.size:
        return t, t
    if info.mode == "clock_time":
        return (t + tz_offset_h * 3600.0) % 86400.0, t
    return np.array([_tod_of(float(x), info.mode) for x in t]), t


# v0.15.4：大文件快速定位。此前按时标/按行定位都是 csv 逐行顺序扫（6400 Hz 一小时 ≈ 2300 万行，几十秒到几分钟），
# 用户体感＝「启动后很久才开始」。现在：按行 → 字节块数 \n 直接算出目标行的字节偏移；按时标 → 字节二分（每次探测只读一行），
# 再顺序扫最后 ≤64 KB 精确到行。两者都假定文件里没有带引号换行的字段（本工具的 CSV 格式不含），
# 按行定位还假定没有空行（有则 skipped_rows 会把空行也算进去；旧实现剔除空行，差异只在这种畸形文件上）。
SEEK_FAST_MIN_BYTES = 4 << 20          # 小于 4 MB 的文件仍走旧的顺序扫（够快，且行为与旧版完全一致）


def _line_starts_after(raw, pos: int, lo: int) -> int:
    """pos 处若在行中间则跳到下一行行首（pos==lo 视为已在行首）。"""
    if pos <= lo:
        return lo
    raw.seek(pos - 1)
    if raw.read(1) == b"\n":
        return pos
    raw.readline()
    return raw.tell()


def _byte_offset_of_row(raw, n_skip: int, lo: int, size: int) -> Tuple[int, int]:
    """从数据起点 lo 开始数 n_skip 个换行，返回 (第 n_skip 行的行首字节, 实际跳过行数)。"""
    raw.seek(lo)
    remaining = n_skip
    pos = lo
    while remaining > 0 and pos < size:
        chunk = raw.read(min(8 << 20, size - pos))
        if not chunk:
            break
        c = chunk.count(b"\n")
        if c < remaining:
            remaining -= c; pos += len(chunk)
            continue
        # 目标行首就在这一块里：找第 remaining 个 \n
        idx = -1
        for _ in range(remaining):
            idx = chunk.find(b"\n", idx + 1)
        pos += idx + 1; remaining = 0
    if remaining > 0:                                  # 文件没那么多行
        return size, n_skip - remaining
    return pos, n_skip


def _count_newlines(raw, lo: int, hi: int) -> int:
    raw.seek(lo); n = 0; left = hi - lo
    while left > 0:
        chunk = raw.read(min(8 << 20, left))
        if not chunk:
            break
        n += chunk.count(b"\n"); left -= len(chunk)
    return n


def _bisect_time(raw, lo: int, size: int, enc: str, delimiter: str, ts_col: int, colmap: ColumnMap,
                 target: Tuple[str, float], tz_offset_h: float, window: int = 65536) -> Optional[int]:
    """字节二分：返回一个行首字节位置 p，保证 [p, p+window) 内含「第一条时标 ≥ 目标」的行（或 p 之前全部 < 目标）。
    探测行解析失败 / 时标非单调（探测到的值比前一个探测点小）→ 返回 None，调用方退回顺序扫。"""
    kind, tv = target

    def probe(pos: int) -> Tuple[int, Optional[float]]:
        p0 = _line_starts_after(raw, pos, lo)
        if p0 >= size:
            return p0, None
        raw.seek(p0)
        line = raw.readline()
        try:
            cells = next(csv.reader([line.decode(enc, errors="replace")], delimiter=delimiter))
            v, _ = _ts_values([cells[ts_col].strip()], kind, colmap, tz_offset_h)
        except Exception:
            return p0, float("nan")
        return p0, (float(v[0]) if v.size and np.isfinite(v[0]) else float("nan"))

    a, b = lo, size
    _, va = probe(a)
    if va is None or not np.isfinite(va):
        return None
    if va >= tv:
        return lo
    while b - a > window:
        mid = (a + b) // 2
        pm, vm = probe(mid)
        if vm is None:                      # mid 已到文件尾
            b = mid; continue
        if not np.isfinite(vm) or vm < va:  # 解析不了 / 非单调 → 放弃快速路径
            return None
        if vm >= tv:
            b = pm
        else:
            a, va = pm, vm
    return a


def _seek_time(reader, first_rows: List[List[str]], colmap: ColumnMap, idx_map: Optional[Dict[str, int]],
               target: Tuple[str, float], tz_offset_h: float, chunk: int = 8192) -> Tuple[List[List[str]], int, Optional[float]]:
    """按时标定位：返回 (从目标时刻起的剩余行, 跳过行数, 命中行时标)。target=("abs", epoch) | ("tod", 当天秒)。"""
    kind, tv = target
    ts_col = (idx_map or {}).get("timestamp")
    if ts_col is None:
        if idx_map is not None and idx_map.get("timestamp") is None and getattr(colmap, "mapping_enabled", False):
            raise ParseError("播放起点按时刻定位需要时间戳列，但列映射未映射时间戳")
        ts_col = 0                                           # 无表头：第 0 列为时间戳
    skipped = 0
    pending = list(first_rows)
    exhausted = False
    while True:
        rows = pending
        pending = []
        while len(rows) < chunk and not exhausted:
            try:
                row = next(reader)
            except StopIteration:
                exhausted = True
                break
            if not row or all(not str(c).strip() for c in row):
                continue
            rows.append(row)
        if not rows:
            return [], skipped, None
        raw = [(r[ts_col].strip() if ts_col < len(r) else "") for r in rows]
        cmp, t = _ts_values(raw, kind, colmap, tz_offset_h)
        hit = np.nonzero(cmp >= (tv if kind == "abs" else tv - 1e-6))[0]
        if hit.size:
            i = int(hit[0])
            return rows[i:], skipped + i, float(t[i])
        skipped += len(rows)
        if exhausted:
            return [], skipped, None


def iter_csv_blocks(path: str, colmap: ColumnMap, sampling: SamplingConfig,
                    block_samples: int = 6400, encoding: str = "auto",
                    delimiter: str = ",", has_header: Optional[bool] = None,
                    tz_offset_h: float = 0.0, max_blocks: Optional[int] = None,
                    skip_rows: int = 0, start_percent: Optional[float] = None,
                    start_time: Optional[Tuple[str, float]] = None,
                    seek_info: Optional[Dict[str, Any]] = None,
                    keep_rows: bool = False):
    """流式读取 CSV，按 block_samples 逐块产出 (SampleBlock, info)。

    播放起点（三选一，优先级 start_time > start_percent > skip_rows）：
      skip_rows      跳过开头 N 条数据行（不含表头、不含空行）
      start_percent  按字节位置跳到文件 N% 处并对齐到下一行行首（大文件 O(1) 定位，跳过行数未知）
      start_time     ("abs", epoch 秒) / ("tod", 当天秒)：顺序扫描时标列直到 ≥ 目标的第一条
    定位结果写入 seek_info（skipped_rows / start_byte / start_t / reached_eof）。
    """
    if not os.path.isfile(path):
        raise ParseError(f"CSV 文件不存在：{path}")
    enc = encoding if encoding != "auto" else detect_encoding(path)
    with open(path, "rb") as _rb:
        first_line_bytes = _rb.readline()
    with open(path, "r", encoding=enc, newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        try:
            first = next(reader)
        except StopIteration:
            raise ParseError(f"{path} 为空文件") from None
        use_header = has_header if has_header is not None else colmap.has_header
        header: Optional[List[str]] = None
        buf: List[List[str]] = []
        if use_header and colmap.looks_like_header(first):
            header = [h.strip() for h in first]
        else:
            # 首行不像表头 → 当数据行处理
            buf.append(first)
        idx_map = colmap.layout(header)            # 未启用映射＝表头/默认列序；启用＝只按 mapping
        size = os.path.getsize(path)
        data_lo = len(first_line_bytes) if header is not None else 0    # 数据区起始字节（表头行之后）

        def _rewrap(byte_pos: int):
            """把读取位置切到 byte_pos（必须是行首），返回新的 csv.reader。"""
            import io as _io
            fh.seek(0)
            raw_fh = fh.buffer
            raw_fh.seek(byte_pos)
            fh2 = _io.TextIOWrapper(raw_fh, encoding=enc, newline="")
            return csv.reader(fh2, delimiter=delimiter)

        fast = size >= SEEK_FAST_MIN_BYTES and not buf     # 首行是数据（无表头）时 buf 非空，保持旧路径
        # ---- 播放起点定位 ----
        if start_time is not None:
            fast_pos = None
            if fast:
                ts_col = (idx_map or {}).get("timestamp")
                if ts_col is None and not getattr(colmap, "mapping_enabled", False):
                    ts_col = 0
                if ts_col is not None:
                    try:
                        fast_pos = _bisect_time(fh.buffer, data_lo, size, enc, delimiter, ts_col, colmap, start_time, tz_offset_h)
                    except Exception:
                        fast_pos = None
            if fast_pos is not None and fast_pos > data_lo:
                pre_rows = _count_newlines(fh.buffer, data_lo, fast_pos)
                reader = _rewrap(fast_pos)
                buf, skipped, hit_t = _seek_time(reader, [], colmap, idx_map, start_time, tz_offset_h)
                skipped += pre_rows
                seek_mode = "time(bisect)"
            else:
                if fast:
                    reader = _rewrap(data_lo)          # 探测移动过底层文件位置，顺序扫前必须回到数据区起点
                buf, skipped, hit_t = _seek_time(reader, buf, colmap, idx_map, start_time, tz_offset_h)
                seek_mode = "time"
            if seek_info is not None:
                seek_info.update({"mode": "time", "skipped_rows": skipped, "start_t": hit_t,
                                  "reached_eof": hit_t is None, "method": seek_mode})
        elif start_percent is not None and start_percent > 0:
            size = os.path.getsize(path)
            pos = int(size * float(start_percent) / 100.0)
            # 文本模式下 seek 只接受 tell() 的值；这里改用二进制定位后重新包装
            fh.seek(0)
            raw_fh = fh.buffer
            raw_fh.seek(pos)
            if pos > 0:
                raw_fh.readline()                       # 丢弃半行，对齐到下一行行首
            start_byte = raw_fh.tell()
            import io as _io
            fh2 = _io.TextIOWrapper(raw_fh, encoding=enc, newline="")
            reader = csv.reader(fh2, delimiter=delimiter)
            buf = []
            if seek_info is not None:
                seek_info.update({"mode": "percent", "start_byte": start_byte, "file_size": size,
                                  "skipped_rows": None, "reached_eof": start_byte >= size})
        elif skip_rows and skip_rows > 0:
            if fast:
                pos, skipped = _byte_offset_of_row(fh.buffer, int(skip_rows), data_lo, size)
                reader = _rewrap(pos)
                buf = []
                if seek_info is not None:
                    seek_info.update({"mode": "row", "skipped_rows": skipped, "reached_eof": skipped < skip_rows, "method": "row(bytes)"})
            else:
                buf, skipped = _seek_rows(reader, buf, int(skip_rows))
                if seek_info is not None:
                    seek_info.update({"mode": "row", "skipped_rows": skipped, "reached_eof": skipped < skip_rows, "method": "row"})
        seq = 0
        produced = 0
        row_offset = 0
        # v0.15.1：定位后 buf 里可能残留一大段已读行（按块预读）→ 先按正常块大小切出，
        # 否则第一块会异常大（之前实测 2014～8000 行），两侧同步/倍速节拍都会被它打乱
        while len(buf) >= block_samples:
            head, buf = buf[:block_samples], buf[block_samples:]
            blk, info = _rows_to_block(head, colmap, sampling, idx_map, path, seq, tz_offset_h, row_offset)
            if keep_rows:
                info["rows"] = head; info["header"] = header
            row_offset += len(head)
            seq += 1
            produced += 1
            yield blk, info
            if max_blocks and produced >= max_blocks:
                return
        for row in reader:
            # v0.82：首格非空白即正常数据行（绝大多数），只有首格为空时才逐格判断整行是否为空行（省每行一次 Python 级 all()）
            if not row or ((not row[0] or row[0].isspace()) and all(not str(c).strip() for c in row)):
                continue
            buf.append(row)
            if len(buf) >= block_samples:
                blk, info = _rows_to_block(buf, colmap, sampling, idx_map, path, seq, tz_offset_h, row_offset)
                if keep_rows:
                    info["rows"] = buf; info["header"] = header
                row_offset += len(buf)
                buf = []
                seq += 1
                produced += 1
                yield blk, info
                if max_blocks and produced >= max_blocks:
                    return
        if buf:
            blk, info = _rows_to_block(buf, colmap, sampling, idx_map, path, seq, tz_offset_h, row_offset)
            if keep_rows:
                info["rows"] = buf; info["header"] = header
            yield blk, info


def _rows_to_block(rows: List[List[str]], colmap: ColumnMap, sampling: SamplingConfig,
                   idx_map: Optional[Dict[str, Optional[int]]], source: str, seq: int,
                   tz_offset_h: float, row_offset: int = 0) -> Tuple[SampleBlock, Dict[str, object]]:
    """row_offset：本块首行在文件中的数据行序号——时间戳未映射时用它合成连续时间轴（t = 行号 / fs）。"""
    if idx_map is None:
        idx_map = colmap.layout(None)
    unmapped = colmap.unmapped(idx_map)
    std = np.full((len(rows), 7), np.nan, dtype=np.float64)
    ts_raw: List[str] = []
    bad: List[Tuple[int, int, str]] = []
    ts_c = idx_map.get("timestamp")
    chan = [(new_c, idx_map[key]) for new_c, key in enumerate(ColumnMap.FIELDS)
            if key != "timestamp" and idx_map.get(key) is not None]
    if ts_c is not None:
        ts_raw = [str(row[ts_c]).strip() if ts_c < len(row) else "" for row in rows]
    # v0.82 快路径：整块按列一次性交给 numpy 解析（C 级 str→float，比逐单元 strip/lower/float 快约 10 倍）。
    # 任一单元为空 / 非数值（含 null / none / -）→ numpy 抛 ValueError → 退回逐单元慢路径，保证空值策略与坏单元报告与原来完全一致。
    need = max((c for _, c in chan), default=-1)
    fast_ok = bool(chan) and rows and min(len(r) for r in rows) > need
    if fast_ok:
        try:
            for new_c, c in chan:
                std[:, new_c] = np.array([row[c] for row in rows], dtype=np.float64)
        except (ValueError, TypeError):
            fast_ok = False
            std[:] = np.nan
    if not fast_ok:
        for r, row in enumerate(rows):
            for new_c, c in chan:
                if c >= len(row):
                    continue
                cell = str(row[c]).strip()
                if cell == "" or cell.lower() in ("nan", "null", "none", "-"):
                    continue
                try:
                    std[r, new_c] = float(cell)
                except ValueError:
                    bad.append((r, c, cell))
    blk, info = _assemble(std, ts_raw, colmap, sampling, source, seq, bad, tz_offset_h, unmapped, idx_map)
    if ts_c is None and row_offset and blk.n:
        blk = SampleBlock(t=(row_offset + np.arange(blk.n, dtype=np.float64)) / sampling.fs, u=blk.u, i=blk.i,
                          scaled=blk.scaled, source=blk.source, seq=blk.seq)
        info["t_start"], info["t_end"] = blk.t_start, blk.t_end
    return blk, info
