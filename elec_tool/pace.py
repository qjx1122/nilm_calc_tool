"""播放节拍钟（v0.15.1）：离线文件播放的**绝对**限速与两侧同步。

旧实现按「相邻两块间隔 ≥ 块时长/倍速」限速：每块独立 sleep，计算耗时、GIL 争用造成的误差会逐块累积，
总线侧与分路侧各自累积的误差不同 → 两侧数据时间越跑越不同步（用户实测：总线快、分路刷不出数据）。

新实现：一只节拍钟 = 共同的墙钟起点 wall0 + 每一侧自己的数据时间起点 data0 + 倍速 speed。
某一侧要产出数据时刻 t 的块，必须等到墙钟 ≥ wall0 + 暂停累计 + (t - data0)/speed。
误差不累积；两侧共用同一只钟 → 任一时刻两侧的「已播放数据时长」一致（公共时间段模式下 data0 相同 → 数据时刻也一致）。
每侧的块时长由**各自的采样率**决定（块样本数/fs），所以 fs 不同的两侧也能对齐。
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional


class PaceClock:
    LEAD_TOL_S = 0.1        # 互锁容差：块起点最多领先对侧进度 0.1 s（→ 块终点最多领先 1 块 + 0.1 s）
    STALL_GIVEUP_S = 10.0   # 对侧超过这么久没有任何进展 → 不再等它（防止异常侧卡死全局）

    def __init__(self, speed: float) -> None:
        self.speed = float(speed or 0.0)          # 0 ＝ 不限速（不等待墙钟；两侧互锁仍生效）
        self.wall0: Optional[float] = None
        self.data0: Dict[str, float] = {}
        self.progress: Dict[str, float] = {}      # side → 已产出的数据时长（相对各自 data0）
        self.progress_at: Dict[str, float] = {}   # side → 最近一次进展的墙钟
        self.done: Dict[str, bool] = {}           # side → 已播完/已停止（不再参与互锁）
        self.paused_total = 0.0
        self.paused_at: Optional[float] = None
        self._lock = threading.Lock()

    def anchor(self, side: str, t_data: float) -> None:
        with self._lock:
            if self.wall0 is None:
                self.wall0 = time.monotonic()
            if side not in self.data0:
                self.data0[side] = float(t_data)
                self.progress[side] = 0.0
                self.progress_at[side] = time.monotonic()
                self.done[side] = False

    def advance(self, side: str, t_data: float) -> None:
        """登记本侧已产出到数据时刻 t_data。"""
        with self._lock:
            if side in self.data0:
                self.progress[side] = max(self.progress.get(side, 0.0), float(t_data) - self.data0[side])
                self.progress_at[side] = time.monotonic()

    def finish(self, side: str) -> None:
        """本侧播完/停止：对侧不再等它。"""
        with self._lock:
            self.done[side] = True

    def _blocked_by_peer(self, side: str, offset: float) -> bool:
        """本侧想产出**起点**在 offset（相对 data0）的块；若某个仍在播放的对侧进度落后超过容差 → 需等待。
        用块起点而非块终点判断：第一块（offset=0）永远放行，且两侧不可能互相等待（A_start>B_prog≥B_start 与
        B_start>A_prog≥A_start 不能同时成立）→ 不会死锁。"""
        with self._lock:
            now = time.monotonic()
            for other, prog in self.progress.items():
                if other == side or self.done.get(other):
                    continue
                if now - self.progress_at.get(other, now) > self.STALL_GIVEUP_S:
                    continue
                if offset > prog + self.LEAD_TOL_S + 1e-6:
                    return True
            return False

    def target_wall(self, side: str, t_data: float) -> Optional[float]:
        with self._lock:
            if self.speed <= 0 or self.wall0 is None or side not in self.data0:
                return None
            return self.wall0 + self.paused_total + (float(t_data) - self.data0[side]) / self.speed

    def pause(self) -> None:
        with self._lock:
            if self.paused_at is None:
                self.paused_at = time.monotonic()

    def resume(self) -> None:
        with self._lock:
            if self.paused_at is not None:
                self.paused_total += time.monotonic() - self.paused_at
                self.paused_at = None

    def is_paused(self) -> bool:
        with self._lock:
            return self.paused_at is not None

    def wait_until(self, side: str, t_data: float, should_abort=None, t_block_start: Optional[float] = None) -> float:
        """阻塞到可以产出数据时刻 t_data（块终点）；返回实际等待秒数。暂停期间不计时（resume 后不追赶）。
        t_block_start：本块起点（用于两侧互锁判断；缺省＝t_data）。"""
        waited = 0.0
        t_bs = float(t_data if t_block_start is None else t_block_start)
        while True:
            tgt = self.target_wall(side, t_data)
            # 两侧互锁：领先对侧超过容差就等对侧（与倍速无关，不限速时也生效）
            if side in self.data0 and self._blocked_by_peer(side, t_bs - self.data0[side]):
                if should_abort and should_abort():
                    return waited
                time.sleep(0.02); waited += 0.02
                continue
            if tgt is None:
                return waited
            now = time.monotonic()
            if self.is_paused():
                time.sleep(0.05); waited += 0.05
                if should_abort and should_abort():
                    return waited
                continue
            need = tgt - now
            if need <= 0:
                return waited
            step = min(need, 0.2)
            time.sleep(step); waited += step
            if should_abort and should_abort():
                return waited

    def info(self) -> Dict[str, object]:
        with self._lock:
            return {"speed": self.speed, "wall0": self.wall0, "data0": dict(self.data0),
                    "progress_s": {k: round(v, 3) for k, v in self.progress.items()}, "done": dict(self.done),
                    "paused_total_s": round(self.paused_total, 3), "paused": self.paused_at is not None}
