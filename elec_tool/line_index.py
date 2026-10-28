"""v0.91：离线 CSV 的**行号 ↔ 字节位置稀疏索引**（进程内缓存），给周波窗定位 / 文件信息复用。

背景：曲线图右键「显示周波窗」每点一次都要 ① `file_info` 数全文件行数（`_count_rows`，整文件扫一遍，且一次请求里会被调两次）、
② 时标二分定位后再数一遍「起点之前有多少行」（`_count_newlines`，从数据区起点扫到定位处）、③ 自定义时间按行号定位
（`_byte_offset_of_row`，从头数换行）。三者都是 O(文件大小)，几 GB 的录波每次右键都要读几 GB，与 n 个周波的实际数据量无关。

做法：每个文件维护一份「每 ``STEP`` 字节一个检查点」的累计换行数表（``cum[k]``＝字节 ``[0, k·STEP)`` 内的换行数），
按需**增量**构建（只扫到用得着的位置；整文件行数才扫到底），以 (路径, 大小, mtime) 校验有效性，文件被改写 / 追加自动失效重建。
有了检查点，任意「数到某字节有多少行」或「第 N 行在哪个字节」都只需再扫 ≤ STEP（1 MiB）。内存：1 GB 文件 ≈ 1024 个整数。

接口：
    count_newlines(path, lo, hi)      [lo, hi) 内换行数（等价 _count_newlines，首次调用后 O(STEP)）
    total_newlines(path)              整文件换行数（等价 _count_rows 的计数部分）
    byte_offset_of_row(path, n, lo)   从 lo 起数 n 个换行后的行首字节与实际跳过行数（等价 _byte_offset_of_row）
    invalidate(path=None)             清缓存（测试 / 文件被改写时）
"""
from __future__ import annotations

import os
import threading
from typing import Dict, List, Optional, Tuple

STEP = 1 << 20                  # 检查点间距（字节）
_READ = 8 << 20                 # 扫描块大小
MAX_FILES = 16                  # 最多缓存的文件数（LRU）


class _Index:
    def __init__(self, path: str, size: int, mtime_ns: int):
        self.path = path; self.size = size; self.mtime_ns = mtime_ns
        self.cum: List[int] = [0]       # cum[k] = newlines in [0, k*STEP)，只收录完整的 STEP 边界
        self.done_to = 0                # 已扫描到的字节位置（STEP 边界或文件尾）
        self.total: Optional[int] = None  # 扫到文件尾后的整文件换行数
        self.lock = threading.Lock()

    def ensure(self, upto: int) -> None:
        """保证已扫描到 ≥ upto 的 STEP 边界（或文件尾）。"""
        upto = min(int(upto), self.size)
        if self.done_to >= upto:
            return
        with self.lock:
            if self.done_to >= upto:
                return
            with open(self.path, "rb") as fh:
                pos = self.done_to
                fh.seek(pos)
                n = self.cum[-1]
                while pos < upto and pos < self.size:
                    nxt = min((pos // STEP + 1) * STEP, self.size)
                    while pos < nxt:
                        chunk = fh.read(min(_READ, nxt - pos))
                        if not chunk:
                            nxt = pos; self.size = pos; break          # 文件比 stat 时短（被截断）
                        n += chunk.count(b"\n"); pos += len(chunk)
                    if pos % STEP == 0 and pos // STEP == len(self.cum):
                        self.cum.append(n)
                    if pos >= self.size:
                        self.total = n
                        break
                self.done_to = pos

    def count_to(self, hi: int) -> int:
        """[0, hi) 内换行数。"""
        hi = max(0, min(int(hi), self.size))
        if hi >= self.size:
            if self.total is None:
                self.ensure(self.size)
            return int(self.total or 0)
        self.ensure(hi)
        k = min(hi // STEP, len(self.cum) - 1)
        start = k * STEP
        return self.cum[k] + (_count_range(self.path, start, hi) if hi > start else 0)


def _count_range(path: str, lo: int, hi: int) -> int:
    n = 0
    with open(path, "rb") as fh:
        fh.seek(lo); left = hi - lo
        while left > 0:
            chunk = fh.read(min(_READ, left))
            if not chunk:
                break
            n += chunk.count(b"\n"); left -= len(chunk)
    return n


_CACHE: Dict[str, _Index] = {}
_ORDER: List[str] = []
_CACHE_LOCK = threading.Lock()


def _get(path: str) -> _Index:
    ap = os.path.abspath(path)
    st = os.stat(ap)
    with _CACHE_LOCK:
        ix = _CACHE.get(ap)
        if ix is None or ix.size != st.st_size or ix.mtime_ns != st.st_mtime_ns:
            ix = _Index(ap, st.st_size, st.st_mtime_ns)
            _CACHE[ap] = ix
            if ap in _ORDER:
                _ORDER.remove(ap)
            _ORDER.append(ap)
            while len(_ORDER) > MAX_FILES:
                old = _ORDER.pop(0); _CACHE.pop(old, None)
        else:
            if _ORDER and _ORDER[-1] != ap:
                _ORDER.remove(ap); _ORDER.append(ap)
        return ix


def invalidate(path: Optional[str] = None) -> None:
    with _CACHE_LOCK:
        if path is None:
            _CACHE.clear(); _ORDER.clear()
        else:
            ap = os.path.abspath(path); _CACHE.pop(ap, None)
            if ap in _ORDER:
                _ORDER.remove(ap)


_WARMING: Dict[str, threading.Thread] = {}


def warm(path: Optional[str], background: bool = True) -> None:
    """预建整文件索引（后台线程）：配置 / 启动离线文件源时调用，让首次右键周波窗也不用等整文件扫描。
    已索引到底 / 正在构建 / 文件不存在 → 直接返回。"""
    if not path:
        return
    ap = os.path.abspath(path)
    try:
        if not os.path.isfile(ap):
            return
        ix = _get(ap)
    except OSError:
        return
    if ix.total is not None:
        return
    if not background:
        ix.count_to(ix.size); return
    with _CACHE_LOCK:
        th = _WARMING.get(ap)
        if th is not None and th.is_alive():
            return
        th = threading.Thread(target=lambda: ix.count_to(ix.size), name=f"line-index:{os.path.basename(ap)}", daemon=True)
        _WARMING[ap] = th
    th.start()


def count_newlines(path: str, lo: int, hi: int) -> int:
    """[lo, hi) 内的换行数。"""
    ix = _get(path)
    lo = max(0, int(lo)); hi = max(lo, min(int(hi), ix.size))
    if hi - lo <= STEP:                       # 短区间直接数，不动索引
        return _count_range(ix.path, lo, hi)
    return ix.count_to(hi) - ix.count_to(lo)


def total_newlines(path: str) -> int:
    ix = _get(path)
    return ix.count_to(ix.size)


def byte_offset_of_row(path: str, n_skip: int, lo: int = 0) -> Tuple[int, int]:
    """从 lo 起数 n_skip 个换行，返回 (第 n_skip 行的行首字节, 实际跳过行数)；行不够时 (size, 实际行数)。"""
    ix = _get(path)
    n_skip = int(n_skip); lo = max(0, int(lo))
    if n_skip <= 0:
        return lo, 0
    base_lo = ix.count_to(lo) if lo > 0 else 0
    target = base_lo + n_skip                 # 需要的累计换行数（相对文件头）
    # 找最后一个 cum[k] < target 的检查点（按需扩展索引）。必须严格小于：cum[k]==target 时第 target 个换行在边界之前，
    # 目标行首可能在边界前（行跨边界），要从上一个检查点扫过来
    k = 0
    while True:
        if k + 1 < len(ix.cum) and ix.cum[k + 1] < target:
            k += 1; continue
        if (k + 1) * STEP < ix.size and ix.done_to < min((k + 1) * STEP, ix.size):
            ix.ensure(min((k + 2) * STEP, ix.size))
            continue
        break
    start = max(lo, k * STEP)
    remaining = target - (ix.cum[k] if start == k * STEP else base_lo)
    pos = start
    with open(ix.path, "rb") as fh:
        fh.seek(pos)
        while remaining > 0 and pos < ix.size:
            chunk = fh.read(min(_READ, ix.size - pos))
            if not chunk:
                break
            c = chunk.count(b"\n")
            if c < remaining:
                remaining -= c; pos += len(chunk); continue
            idx = -1
            for _ in range(remaining):
                idx = chunk.find(b"\n", idx + 1)
            pos += idx + 1; remaining = 0
    if remaining > 0:
        return ix.size, n_skip - remaining
    return pos, n_skip
