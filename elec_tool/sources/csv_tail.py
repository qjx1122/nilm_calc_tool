"""实时数据源①：文件/目录追加监视（tail CSV）。

适用场景：采集程序持续把实时数据写入 CSV，本工具增量读取新增行。
优点：对现有采集链路零改动。
"""

from __future__ import annotations

import csv
import io
import os
import time
from typing import Any, Dict, List, Optional

import numpy as np

from ..blocks import SampleBlock
from ..config import AppConfig
from .base import DataSource, note_key
from .parsing import ParseError, decode_encoding, parse_rows


class CsvTailSource(DataSource):
    """监视 CSV 文件追加内容（path 可为目录 → 自动跟踪最新 .csv 文件）。"""

    kind = "csv_tail"

    def __init__(self, cfg: AppConfig, path: Optional[str] = None,
                 block_samples: Optional[int] = None, tz_offset_h: float = 0.0):
        self.cfg = cfg
        self.path = path or cfg.source.path
        self.block_samples = int(block_samples or cfg.source.block_samples or 640)
        self.watch_dir_newest = bool(cfg.source.watch_dir_newest)
        self.tail_from_end = bool(cfg.source.tail_from_end)
        self.poll_interval_s = float(cfg.source.poll_interval_s)
        self.tz_offset_h = tz_offset_h
        self._fh = None
        self._offset = 0
        self._inode: Optional[int] = None
        self._remainder = ""
        self._pending: List[List[str]] = []
        self._header: Optional[List[str]] = None
        self._encoding: Optional[str] = None
        self._active_path: Optional[str] = None
        self._n_blocks = 0
        self._n_samples = 0
        self._seq = 0
        self._opened_at: Optional[float] = None
        self._last_read_at: Optional[float] = None
        self._notes: List[str] = []

    # ---------- 生命周期 ----------
    def open(self) -> None:
        target = self._resolve_path()
        if not target:
            raise ParseError(
                f"csv_tail 找不到可监视的 CSV：path={self.path!r}"
                f"（目录模式需 watch_dir_newest=True 且目录内存在 *.csv）")
        self._active_path = target
        self._encoding = (self.cfg.columns.encoding if self.cfg.columns.encoding != "auto"
                          else decode_encoding(open(target, "rb").read(4096)))
        self._fh = open(target, "r", encoding=self._encoding, newline="")
        st = os.fstat(self._fh.fileno())
        self._inode = st.st_ino
        if self.cfg.columns.has_header:
            line = self._fh.readline()
            if line.strip():
                self._header = [h.strip() for h in next(csv.reader(io.StringIO(line),
                                                                  delimiter=self.cfg.columns.delimiter))]
        if self.tail_from_end:
            self._fh.seek(0, os.SEEK_END)
            self._note("tail_from_end=True：只读打开之后的新增内容（历史数据不计算）")
        self._offset = self._fh.tell()
        self._opened_at = time.time()

    def _resolve_path(self) -> Optional[str]:
        p = self.path
        if not p:
            return None
        if os.path.isfile(p):
            return p
        if os.path.isdir(p) and self.watch_dir_newest:
            cands = [os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith(".csv")]
            cands = [c for c in cands if os.path.isfile(c)]
            if not cands:
                return None
            return max(cands, key=os.path.getmtime)
        return None

    # ---------- 读取 ----------
    def _drain_current(self) -> int:
        """把当前文件里**已写完**的行全部读进 _pending，返回行数。

        为什么必须显式 drain：目录轮转/inode 变化时若直接 _reopen()，旧文件尚未读走的尾部
        会被静默丢弃——实测每切换一次丢正好一整块（640 点＝100ms），在结果里表现为
        「疑似丢点」的假缺口。切换前先 drain，样本一行不少地留在 _pending 里按序输出。
        """
        if self._fh is None:
            return 0
        n_rows = 0
        chunk = self._fh.read()
        if chunk:
            self._offset = self._fh.tell()
            text = self._remainder + chunk
            lines = text.splitlines()
            # 末尾若不是换行，说明最后一行还没写完 → 留到下次
            self._remainder = "" if text.endswith(("\n", "\r")) else (lines.pop() if lines else "")
            reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=self.cfg.columns.delimiter)
            for row in reader:
                if not row or all(not str(c).strip() for c in row):
                    continue
                self._pending.append(row)
                n_rows += 1
        if self._remainder.strip():
            # 旧文件最后一行没写完就轮转了：字段可能残缺，宁可显式告警也不静默算错
            self._note(f"切换文件时旧文件末行不完整，已丢弃该行：{self._remainder[:48]}…")
            self._remainder = ""
        return n_rows

    def read(self) -> Optional[SampleBlock]:
        if self._fh is None:
            self.open()
        self._last_read_at = time.time()
        self._rotate_if_needed()
        self._drain_current()
        if len(self._pending) >= self.block_samples:
            take = self._pending[:self.block_samples]
            self._pending = self._pending[self.block_samples:]
            return self._to_block(take)
        return None

    def _rotate_if_needed(self) -> None:
        """文件被截断/轮转（inode 变化或长度变小）时重新打开。"""
        if not self._active_path or self._fh is None:
            return
        try:
            st = os.stat(self._active_path)
        except FileNotFoundError:
            self._note(f"监视文件消失：{self._active_path}，等待重建")
            return
        if self._inode is not None and st.st_ino != self._inode:
            drained = self._drain_current()      # 旧 inode 的数据先读完，否则丢尾块
            self._note(f"检测到文件轮转（inode 变化），重新打开（旧文件补读 {drained} 行）")
            self._reopen()
        elif st.st_size < self._offset:
            # 截断＝原位置的数据已被覆盖，drain 无意义，直接从头重读
            self._note("检测到文件被截断（长度变小），从头重读")
            self._reopen()
        elif self.watch_dir_newest and os.path.isdir(self.path or ""):
            newest = self._resolve_path()
            if newest and newest != self._active_path:
                drained = self._drain_current()  # 切换前把旧文件读完：这是丢一整块的根因
                self._note(
                    f"目录中出现更新的文件，切换监视对象：{newest}（旧文件补读 {drained} 行）")
                self._active_path = newest
                self._reopen()

    def _reopen(self) -> None:
        try:
            if self._fh:
                self._fh.close()
        finally:
            self._fh = None
        self._remainder = ""
        self.tail_from_end = False      # 轮转后应从头读新文件
        self.open()

    def _note(self, msg: str) -> None:
        """追加告警并按中文骨架去重（同一告警每块都会重发，见 base.note_key）。"""
        key = note_key(msg)
        if any(note_key(n) == key for n in self._notes[-5:]):
            return
        self._notes.append(msg)          # 必须直接 append：调 _note 会无限递归
        if len(self._notes) > 20:
            self._notes = self._notes[-20:]

    def _to_block(self, rows: List[List[str]]) -> SampleBlock:
        block, info = parse_rows(rows, self.cfg.columns, self.cfg.sampling,
                                 source=f"csv_tail:{os.path.basename(self._active_path or '')}",
                                 seq=self._seq, tz_offset_h=self.tz_offset_h)
        self._seq += 1
        self._n_blocks += 1
        self._n_samples += block.n
        for n in info.get("notes", []):
            self._note(n)
        self._notes = self._notes[-20:]
        return block

    def close(self) -> None:
        if self._fh:
            try:
                self._fh.close()
            finally:
                self._fh = None
        self._pending = []

    @property
    def exhausted(self) -> bool:
        return False

    def info(self) -> Dict[str, Any]:
        return {
            "kind": self.kind, "path": self.path, "active_path": self._active_path,
            "encoding": self._encoding, "header": self._header,
            "offset": int(self._offset), "pending_rows": len(self._pending),
            "block_samples": self.block_samples, "blocks_read": self._n_blocks,
            "samples_read": self._n_samples, "poll_interval_s": self.poll_interval_s,
            "opened_at": self._opened_at, "last_read_at": self._last_read_at,
            "tail_from_end": self.tail_from_end, "notes": list(self._notes),
        }
