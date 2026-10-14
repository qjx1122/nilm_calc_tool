"""离线文件数据源：按块读取 CSV（需求④ 之「离线文件数据」）。"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterator, Optional, Tuple

import numpy as np

from ..blocks import SampleBlock
from ..config import AppConfig, parse_play_start, parse_time_text
from .base import DataSource
from .parsing import ParseError, iter_csv_blocks, read_header


class CsvFileSource(DataSource):
    """离线 CSV 源：流式分块读取，读完置 exhausted=True。"""

    kind = "csv_file"

    def __init__(self, cfg: AppConfig, path: Optional[str] = None,
                 block_samples: Optional[int] = None, max_blocks: Optional[int] = None,
                 tz_offset_h: float = 0.0):
        self.cfg = cfg
        self.path = path or cfg.source.path
        self.block_samples = int(block_samples or cfg.source.block_samples or 6400)
        self.max_blocks = max_blocks
        self.tz_offset_h = tz_offset_h
        self._it: Optional[Iterator[Tuple[SampleBlock, Dict[str, Any]]]] = None
        self._exhausted = False
        self._n_blocks = 0
        self._n_samples = 0
        self.speed = float(getattr(cfg.source, "file_speed", 0.0) or 0.0)   # 0＝不限速
        self._last_emit_wall: Optional[float] = None
        self._header: Optional[list] = None
        self._encoding: Optional[str] = None
        self._last_info: Dict[str, Any] = {}
        self._first_t: Optional[float] = None
        self._last_t: Optional[float] = None
        # 自定义播放时间（需求：离线播放可不用文件时标）
        self.custom_time = bool(cfg.source.custom_time)
        self._custom_t0: Optional[float] = (
            parse_time_text(cfg.source.custom_time_start)
            if self.custom_time and str(cfg.source.custom_time_start).strip() else None)
        self._custom_t0_source = ("配置起始时间" if self._custom_t0 is not None else "文件第 1 条数据时间")
        self._file_first_t: Optional[float] = None     # 文件原始第 1 条时标（供界面显示）
        self._custom_notes: list = []
        # 播放起点（需求：离线文件可指定位置开始播放）
        self.play_start_mode = str(cfg.source.play_start_mode or "begin")
        self._play_start = parse_play_start(self.play_start_mode, cfg.source.play_start_value)
        self._seek_info: Dict[str, Any] = {}
        self._seek_notes: list = []

    def _apply_custom_time(self, block: SampleBlock) -> SampleBlock:
        """把块时间轴改写为 起始时间 + 全局样本序号 / fs（等间隔）。

        起始时间：配置给了就用配置；否则取文件第 1 条数据的时标（文件时标不可解析时
        parsing 层已退化为 0 起算的合成轴，此时等价于相对时间）。
        """
        if not self.custom_time or block.n == 0:
            return block
        if self._file_first_t is None:
            self._file_first_t = float(block.t[0])
            if self._custom_t0 is None:
                self._custom_t0 = self._file_first_t
            self._custom_notes = [
                f"自定义播放时间已启用：时间轴 = 起始时间({self._custom_t0_source}) + 样本序号/fs，"
                f"文件内时标仅用于推算采样率；文件中的时间缺口在此模式下**不会**被检测"]
        fs = float(self.cfg.sampling.fs)
        n0 = self._n_samples                      # 本块之前已产出的样本数（read() 在之后才累加）
        block.t = self._custom_t0 + (np.arange(block.n, dtype=np.float64) + n0) / fs
        return block

    def open(self) -> None:
        if not self.path or not os.path.isfile(self.path):
            raise ParseError(f"离线数据文件不存在：{self.path!r}（请检查 source.path 配置）")
        self._header, self._encoding = read_header(
            self.path, self.cfg.columns.encoding, self.cfg.columns.delimiter)
        seek_kw: Dict[str, Any] = {}
        mode, v = self.play_start_mode, self._play_start
        if mode == "row":
            seek_kw["skip_rows"] = int(v) - 1
        elif mode == "seconds":
            seek_kw["skip_rows"] = int(round(float(v) * float(self.cfg.sampling.fs)))
        elif mode == "percent":
            seek_kw["start_percent"] = float(v)
        elif mode == "time":
            seek_kw["start_time"] = v
        self._seek_info = {}
        self._it = iter_csv_blocks(
            self.path, self.cfg.columns, self.cfg.sampling,
            block_samples=self.block_samples, encoding=self.cfg.columns.encoding,
            delimiter=self.cfg.columns.delimiter, has_header=self.cfg.columns.has_header,
            tz_offset_h=self.tz_offset_h, max_blocks=self.max_blocks,
            seek_info=self._seek_info, **seek_kw)
        self._exhausted = False
        self._seek_notes = []
        if mode != "begin":
            # 定位发生在生成器第一次 next() 时；这里先把意图写进告警，定位结果在 read() 后补充
            if mode == "row":
                desc = f"第 {int(v)} 行"
            elif mode == "seconds":
                desc = f"跳过开头 {float(v):g} s（≈{seek_kw.get('skip_rows')} 行）"
            elif mode == "percent":
                desc = f"文件 {float(v):g}% 处"
            else:
                desc = f"时标 ≥ {self.cfg.source.play_start_value}"
            self._seek_notes = [f"播放起点：{desc}（之前的数据已跳过，不参与计算）"]

    def _pace(self, block: SampleBlock) -> None:
        """倍速限速：距上一块产出至少间隔 块时长/speed。只看相邻两块，暂停/卡顿后不追赶。"""
        if self.speed <= 0 or block.n == 0:
            return
        now = time.monotonic()
        if self._last_emit_wall is not None:
            fs = float(self.cfg.sampling.fs) or 1.0
            dur = block.n / fs
            need = dur / self.speed - (now - self._last_emit_wall)
            if need > 0:
                time.sleep(min(need, 1.0))
                now = time.monotonic()
        self._last_emit_wall = now

    def read(self) -> Optional[SampleBlock]:
        if self._it is None:
            self.open()
        assert self._it is not None
        try:
            block, info = next(self._it)
        except StopIteration:
            self._exhausted = True
            if self._n_blocks == 0 and self.play_start_mode != "begin" and self._seek_info.get("reached_eof"):
                raise ParseError(
                    f"播放起点超出文件范围：{self.play_start_mode}={self.cfg.source.play_start_value!r}，"
                    f"文件共 {self._seek_info.get('skipped_rows', '?')} 条数据行"
                    + ("" if self.play_start_mode != "time" else "（没有时标 ≥ 该时刻的数据；请核对文件时标范围，"
                       "无日期写法可只填 HH:MM:SS）"))
            return None
        block = self._apply_custom_time(block)
        self._pace(block)
        if self._n_blocks == 0 and self._seek_info and self._seek_info.get("mode") in ("row", "time"):
            sk = self._seek_info.get("skipped_rows")
            if sk is not None and self._seek_notes:
                extra = f"；实际跳过 {sk} 行"
                if self._seek_info.get("mode") == "time" and self._seek_info.get("start_t") is not None:
                    extra += f"，命中时标 t={self._seek_info['start_t']:.4f}"
                self._seek_notes = [self._seek_notes[0] + extra]
        if self._custom_notes or self._seek_notes:
            info = dict(info)
            info["notes"] = list(info.get("notes", [])) + self._seek_notes + self._custom_notes
        self._n_blocks += 1
        self._n_samples += block.n
        self._last_info = info
        if block.n:
            self._first_t = self._first_t if self._first_t is not None else block.t_start
            self._last_t = block.t_end
        return block

    def close(self) -> None:
        self._it = None
        self._exhausted = True

    @property
    def exhausted(self) -> bool:
        return self._exhausted

    def info(self) -> Dict[str, Any]:
        size = os.path.getsize(self.path) if self.path and os.path.isfile(self.path) else None
        return {
            "kind": self.kind, "path": self.path, "encoding": self._encoding,
            "header": self._header, "file_size_bytes": size,
            "block_samples": self.block_samples, "blocks_read": self._n_blocks, "file_speed": self.speed,
            "samples_read": self._n_samples, "exhausted": self._exhausted,
            "t_start": self._first_t, "t_end": self._last_t,
            "duration_s": (self._n_samples / self.cfg.sampling.fs) if self._n_samples else 0.0,
            "fs_est_from_timestamps": self._last_info.get("fs_est"),
            "ts_mode": self._last_info.get("ts_mode"),
            "custom_time": self.custom_time,
            "custom_time_start": self._custom_t0 if self.custom_time else None,
            "custom_time_start_source": self._custom_t0_source if self.custom_time else None,
            "file_first_t": self._file_first_t,
            "file_time_utc": bool(self.cfg.source.file_time_utc), "tz_offset_h": self.tz_offset_h,
            "play_start_mode": self.play_start_mode,
            "play_start_value": self.cfg.source.play_start_value if self.play_start_mode != "begin" else None,
            "play_seek": dict(self._seek_info) if self._seek_info else None,
            "notes": self._last_info.get("notes", []),
        }
