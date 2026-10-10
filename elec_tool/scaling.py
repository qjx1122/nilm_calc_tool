"""PT/CT 变比变换：二次侧 → 一次侧。

口径（用户确认，2026-10-10）：PT=100（如 10000V/100V）、CT=15（如 75A/5A），均可配置。
- 电压一次值 = 二次值 × PT
- 电流一次值 = 二次值 × CT
- 功率一次值 = 二次功率 × PT × CT
注：PT 变比对相电压与线电压同为 100（如 10000/√3 : 100/√3 = 100），故 voltage_input
    为 phase 或 line 时变换系数一致；差别只在于是否需要对相/线电压做 √3 换算（见 analysis/rms.py）。
"""

from __future__ import annotations

import numpy as np

from .blocks import SampleBlock
from .config import TransformConfig


def scale_voltage(u: np.ndarray, tr: TransformConfig) -> np.ndarray:
    if not tr.enabled:
        return np.asarray(u, dtype=np.float64)
    return np.asarray(u, dtype=np.float64) * float(tr.pt_ratio)


def scale_current(i: np.ndarray, tr: TransformConfig) -> np.ndarray:
    if not tr.enabled:
        return np.asarray(i, dtype=np.float64)
    return np.asarray(i, dtype=np.float64) * float(tr.ct_ratio)


def scale_block(block: SampleBlock, tr: TransformConfig) -> SampleBlock:
    """返回一次侧数据块（不修改原对象；已变换过则原样返回）。"""
    if block.scaled or tr.pt_ratio == 1.0 and tr.ct_ratio == 1.0 and not tr.enabled:
        return block
    if block.scaled:
        return block
    return SampleBlock(
        t=block.t,
        u=scale_voltage(block.u, tr),
        i=scale_current(block.i, tr),
        scaled=True,
        source=block.source,
        seq=block.seq,
    )


def unscale_power(value: float, tr: TransformConfig) -> float:
    """一次功率 → 二次功率（对账/调试用）。"""
    return float(value) / float(tr.power_ratio)
