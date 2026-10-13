"""数据源工厂：按配置构造离线/实时源（需求④）。"""

from __future__ import annotations

from typing import Optional

from ..config import AppConfig, ConfigError
from .base import DataSource
from .csv_file import CsvFileSource
from .csv_tail import CsvTailSource
from .simulator import SimulatorSource
from .tcp_stream import TcpStreamSource

__all__ = ["DataSource", "CsvFileSource", "CsvTailSource", "SimulatorSource", "TcpStreamSource",
           "create_source"]


def create_source(cfg: AppConfig, kind: Optional[str] = None, path: Optional[str] = None,
                  realtime_pace: Optional[bool] = None, tz_offset_h: Optional[float] = None) -> DataSource:
    """按 source.kind 构造数据源（kind/path 可临时覆盖配置）。

    tz_offset_h=None（默认）→ 按 source.file_time_utc 决定：False＝本地时区偏移（曲线时间＝文件时间），True＝0（按 UTC）。
    """
    cfg.validate()
    if tz_offset_h is None:
        from .parsing import file_tz_offset_h
        tz_offset_h = file_tz_offset_h(cfg)
    k = kind or cfg.source.kind
    p = path if path is not None else cfg.source.path
    if k == "csv_file":
        return CsvFileSource(cfg, path=p, tz_offset_h=tz_offset_h)
    if k == "csv_tail":
        return CsvTailSource(cfg, path=p, tz_offset_h=tz_offset_h)
    if k == "tcp":
        return TcpStreamSource(cfg, tz_offset_h=tz_offset_h)
    if k == "simulator":
        return SimulatorSource(cfg, realtime_pace=(realtime_pace if realtime_pace is not None else True),
                               speed=cfg.source.sim_speed)
    raise ConfigError(f"未知数据源类型 '{k}'（支持 {('csv_file','csv_tail','simulator','tcp')}）")
