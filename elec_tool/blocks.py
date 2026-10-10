"""数据块与环形缓冲：实时/离线共用的内存数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

PHASES = ("A", "B", "C")
CHANNELS = ("ua", "ia", "ub", "ib", "uc", "ic")   # 与 CSV 列顺序一致


@dataclass
class SampleBlock:
    """一段连续采样。

    t : (N,) 绝对时间（epoch 秒，float64）
    u : (3,N) 三相电压（默认为**二次侧**值，经 scaling.scale_block 变换为一次侧）
    i : (3,N) 三相电流（同上）
    """

    t: np.ndarray
    u: np.ndarray
    i: np.ndarray
    scaled: bool = False
    source: str = ""
    seq: int = 0

    def __post_init__(self) -> None:
        self.t = np.ascontiguousarray(self.t, dtype=np.float64)
        self.u = np.ascontiguousarray(self.u, dtype=np.float64)
        self.i = np.ascontiguousarray(self.i, dtype=np.float64)
        if self.u.ndim != 2 or self.u.shape[0] != 3:
            raise ValueError(f"u 形状必须是 (3,N)，当前 {self.u.shape}")
        if self.i.shape != self.u.shape:
            raise ValueError(f"i 形状 {self.i.shape} 与 u 形状 {self.u.shape} 不一致")
        if self.t.shape[0] != self.u.shape[1]:
            raise ValueError(f"t 长度 {self.t.shape[0]} 与样本数 {self.u.shape[1]} 不一致")

    @property
    def n(self) -> int:
        return int(self.u.shape[1])

    def is_empty(self) -> bool:
        return self.n == 0

    @property
    def t_start(self) -> float:
        return float(self.t[0]) if self.n else float("nan")

    @property
    def t_end(self) -> float:
        return float(self.t[-1]) if self.n else float("nan")

    def duration_s(self, fs: float) -> float:
        return self.n / float(fs)

    def slice(self, start: int, stop: Optional[int] = None) -> "SampleBlock":
        stop = self.n if stop is None else stop
        return SampleBlock(t=self.t[start:stop], u=self.u[:, start:stop], i=self.i[:, start:stop],
                           scaled=self.scaled, source=self.source, seq=self.seq)

    def tail(self, n: int) -> "SampleBlock":
        n = min(int(n), self.n)
        return self.slice(self.n - n, self.n)

    def channel(self, name: str) -> np.ndarray:
        idx = CHANNELS.index(name)
        return self.u[idx // 2] if idx % 2 == 0 else self.i[idx // 2]

    @staticmethod
    def concat(blocks: List["SampleBlock"], source: str = "") -> "SampleBlock":
        blocks = [b for b in blocks if b is not None and not b.is_empty()]
        if not blocks:
            return SampleBlock(t=np.empty(0), u=np.empty((3, 0)), i=np.empty((3, 0)), source=source)
        return SampleBlock(
            t=np.concatenate([b.t for b in blocks]),
            u=np.concatenate([b.u for b in blocks], axis=1),
            i=np.concatenate([b.i for b in blocks], axis=1),
            scaled=blocks[-1].scaled,
            source=source or blocks[-1].source,
            seq=blocks[-1].seq,
        )

    @staticmethod
    def empty(source: str = "") -> "SampleBlock":
        return SampleBlock(t=np.empty(0), u=np.empty((3, 0)), i=np.empty((3, 0)), source=source)


@dataclass
class FrameBuffer:
    """环形缓冲：保留最近 capacity 个样本，供各电气量按自己的窗长取数。

    需求⑥ 要求「各电气量分别配置计算时间段」，故缓冲容量必须 ≥ 最长窗；
    各量独立按 length_s 取尾部数据计算，互不影响。
    """

    capacity: int
    _u: np.ndarray = field(init=False)
    _i: np.ndarray = field(init=False)
    _t: np.ndarray = field(init=False)
    _filled: int = field(init=False, default=0)
    _pos: int = field(init=False, default=0)
    total_in: int = field(init=False, default=0)
    dropped: int = field(init=False, default=0)
    source: str = field(init=False, default="")

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"capacity 必须 > 0（当前 {self.capacity}）")
        self._u = np.zeros((3, self.capacity), dtype=np.float64)
        self._i = np.zeros((3, self.capacity), dtype=np.float64)
        self._t = np.zeros(self.capacity, dtype=np.float64)

    def __len__(self) -> int:
        return self._filled

    def resize(self, capacity: int) -> None:
        """扩容（保留已有数据尾部）；缩容时丢弃最旧数据。"""
        old = self.snapshot()
        self.capacity = int(capacity)
        self.__post_init__()
        if old is not None and not old.is_empty():
            self.append(old.tail(self.capacity))

    def append(self, block: SampleBlock) -> int:
        """写入一块数据，返回实际写入样本数（超出容量的旧数据被覆盖）。"""
        if block.is_empty():
            return 0
        n = block.n
        if n > self.capacity:
            self.dropped += n - self.capacity
            block = block.tail(self.capacity)
            n = block.n
        self.source = block.source or self.source
        end = self._pos + n
        if end <= self.capacity:
            self._u[:, self._pos:end] = block.u
            self._i[:, self._pos:end] = block.i
            self._t[self._pos:end] = block.t
        else:
            first = self.capacity - self._pos
            self._u[:, self._pos:] = block.u[:, :first]
            self._i[:, self._pos:] = block.i[:, :first]
            self._t[self._pos:] = block.t[:first]
            rest = n - first
            self._u[:, :rest] = block.u[:, first:]
            self._i[:, :rest] = block.i[:, first:]
            self._t[:rest] = block.t[first:]
        self._pos = end % self.capacity
        self._filled = min(self._filled + n, self.capacity)
        self.total_in += n
        return n

    def snapshot(self, n: Optional[int] = None) -> Optional[SampleBlock]:
        """取最近 n 个样本（n=None 取全部已填充数据），按时间正序返回。"""
        if self._filled == 0:
            return None
        n = self._filled if n is None else min(int(n), self._filled)
        if n <= 0:
            return None
        start = (self._pos - n) % self.capacity
        if start + n <= self.capacity:
            idx = slice(start, start + n)
            u, i, t = self._u[:, idx], self._i[:, idx], self._t[idx]
        else:
            first = self.capacity - start
            u = np.concatenate([self._u[:, start:], self._u[:, : n - first]], axis=1)
            i = np.concatenate([self._i[:, start:], self._i[:, : n - first]], axis=1)
            t = np.concatenate([self._t[start:], self._t[: n - first]])
        return SampleBlock(t=t.copy(), u=u.copy(), i=i.copy(), scaled=True, source=self.source)

    def tail_duration(self, seconds: float, fs: float) -> Optional[SampleBlock]:
        """按窗长（秒）取尾部数据 —— 各电气量独立窗配置的取数入口。"""
        n = int(round(seconds * fs))
        return self.snapshot(n)

    def clear(self) -> None:
        self._filled = 0
        self._pos = 0
        self._u[:] = 0.0
        self._i[:] = 0.0
        self._t[:] = 0.0
