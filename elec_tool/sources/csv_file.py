"""离线文件数据源：按块读取 CSV（需求④ 之「离线文件数据」）。"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterator, Optional, Tuple

from ..blocks import SampleBlock
from ..config import AppConfig
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
        self._header: Optional[list] = None
        self._encoding: Optional[str] = None
        self._last_info: Dict[str, Any] = {}
        self._first_t: Optional[float] = None
        self._last_t: Optional[float] = None

    def open(self) -> None:
        if not self.path or not os.path.isfile(self.path):
            raise ParseError(f"离线数据文件不存在：{self.path!r}（请检查 source.path 配置）")
        self._header, self._encoding = read_header(
            self.path, self.cfg.columns.encoding, self.cfg.columns.delimiter)
        self._it = iter_csv_blocks(
            self.path, self.cfg.columns, self.cfg.sampling,
            block_samples=self.block_samples, encoding=self.cfg.columns.encoding,
            delimiter=self.cfg.columns.delimiter, has_header=self.cfg.columns.has_header,
            tz_offset_h=self.tz_offset_h, max_blocks=self.max_blocks)
        self._exhausted = False

    def read(self) -> Optional[SampleBlock]:
        if self._it is None:
            self.open()
        assert self._it is not None
        try:
            block, info = next(self._it)
        except StopIteration:
            self._exhausted = True
            return None
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
            "block_samples": self.block_samples, "blocks_read": self._n_blocks,
            "samples_read": self._n_samples, "exhausted": self._exhausted,
            "t_start": self._first_t, "t_end": self._last_t,
            "duration_s": (self._n_samples / self.cfg.sampling.fs) if self._n_samples else 0.0,
            "fs_est_from_timestamps": self._last_info.get("fs_est"),
            "ts_mode": self._last_info.get("ts_mode"),
            "notes": self._last_info.get("notes", []),
        }
