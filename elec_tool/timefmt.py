"""跨平台安全的本地时间格式化（F-40）。

Windows 的 C 运行库 ``localtime()`` 对 **负 epoch** 或极小的正值（换算成本地时间落在 1970-01-01 之前）直接抛
``OSError: [Errno 22] Invalid argument``；Linux 则正常返回 1969 年。无日期时标（``0/00/00 HH:MM:SS``）按本地时间解释后
就可能出现这种值，因此所有「epoch → 本地时间文本」的出口统一走这里：先试 ``time.localtime``，失败则用
``datetime + timedelta`` 按本机时区偏移手工换算，并手工拼字符串（不依赖 strftime 对早年份的支持）。
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

__all__ = ["local_tuple", "fmt_local", "local_day", "local_tod_s"]

_EPOCH = datetime(1970, 1, 1)


def _offset_s() -> float:
    try:
        return float(time.localtime().tm_gmtoff)
    except Exception:
        return float(-time.timezone)


def local_tuple(t: float) -> Tuple[int, int, int, int, int, int]:
    """(年, 月, 日, 时, 分, 秒) 本地时间；任何平台、任何 epoch（含负值）都不抛异常。"""
    if t is None or not math.isfinite(t):
        raise ValueError("epoch 非有限数")
    try:
        lt = time.localtime(t)
        return lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec
    except (OSError, OverflowError, ValueError):
        dt = _EPOCH + timedelta(seconds=math.floor(t) + _offset_s())
        return dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second


def fmt_local(t: Optional[float], ms: bool = True, date: bool = True) -> str:
    """'YYYY-MM-DD HH:MM:SS[.mmm]'；t 为 None/NaN 返回空串。"""
    if t is None or not (isinstance(t, (int, float)) and math.isfinite(t)):
        return ""
    y, mo, d, hh, mm, ss = local_tuple(float(t))
    out = f"{hh:02d}:{mm:02d}:{ss:02d}"
    if date:
        out = f"{y:04d}-{mo:02d}-{d:02d} " + out
    if ms:
        out += f".{int((float(t) % 1.0) * 1000):03d}"
    return out


def local_day(t: Optional[float]) -> str:
    """'YYYYMMDD'（按本地日期分文件用）；非有限值返回 'unknown'。"""
    if t is None or not (isinstance(t, (int, float)) and math.isfinite(t)):
        return "unknown"
    y, mo, d, *_ = local_tuple(float(t))
    return f"{y:04d}{mo:02d}{d:02d}"


def local_tod_s(t: float) -> float:
    """本地「当天时刻」秒数（含小数）。"""
    _, _, _, hh, mm, ss = local_tuple(float(t))
    return hh * 3600.0 + mm * 60.0 + ss + (float(t) % 1.0)


def wall_day() -> str:
    """v0.58：**当前墙钟**的本地日期 'YYYYMMDD'——实时落盘 / 事件 / 负荷事件 CSV 按它分文件（不再按数据时间）：
    总线侧与分路侧即使播放的是不同日期的离线文件，同一次运行也写进同一个 <名>_<今天>.csv。"""
    import time as _time
    return local_day(_time.time())
