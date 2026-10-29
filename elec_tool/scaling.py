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


def _needs_sign(tr: TransformConfig) -> bool:
    return bool(getattr(tr, "invert_current", False)) or bool(str(getattr(tr, "invert_phases", "") or "").strip())


def scale_current(i: np.ndarray, tr: TransformConfig) -> np.ndarray:
    """电流二次→一次，并按全局/分相极性取反（v0.93：invert_phases 如 "A" 只反转 A 相；i 形状 (3,N) 或 (N,)）。"""
    arr = np.asarray(i, dtype=np.float64)
    k = float(tr.ct_ratio) if tr.enabled else 1.0
    if _needs_sign(tr):
        sg = np.asarray(tr.phase_signs(), dtype=np.float64) if hasattr(tr, "phase_signs") else np.full(3, -1.0)
        if arr.ndim == 2 and arr.shape[0] == 3:
            return arr * (k * sg)[:, None]
        return arr * (k * (-1.0 if bool(getattr(tr, "invert_current", False)) else 1.0))
    return arr if k == 1.0 else arr * k


def reconstruct_three_wire(u: np.ndarray, i: np.ndarray):
    """v0.94：三相三线两表法 → 伪三相四线。

    * 电流：无中性线 ⇒ ia+ib+ic≡0，ib = −(ia+ic)（严格成立）。
    * 电压：CSV A/C 列＝Uab、Ucb（B 为公共端）。Uca = Ucb − Uab、Ubc = −Ucb；按虚拟中性点
      Ua=(Uab−Uca)/3、Ub=(Ubc−Uab)/3、Uc=(Uca−Ubc)/3（假设电压三相对称，近似；电流可不对称）。
    返回 (u3, i3)，形状同输入 (3,N)。
    """
    u = np.asarray(u, dtype=np.float64); i = np.asarray(i, dtype=np.float64)
    if u.ndim != 2 or u.shape[0] != 3 or i.ndim != 2 or i.shape[0] != 3:
        return u, i
    uab, ucb = u[0], u[2]
    uca = ucb - uab; ubc = -ucb
    u3 = np.vstack([(uab - uca) / 3.0, (ubc - uab) / 3.0, (uca - ubc) / 3.0])
    i3 = np.vstack([i[0], -(i[0] + i[2]), i[2]])
    return u3, i3


def scale_block(block: SampleBlock, tr: TransformConfig) -> SampleBlock:
    """返回一次侧数据块（不修改原对象；已变换过则原样返回）。v0.94：3p3w+reconstruct_3w 时先取反/变比再重构。"""
    if block.scaled:
        return block
    recon = bool(getattr(tr, "reconstructing", False))
    if not tr.enabled and not _needs_sign(tr) and not recon:
        return block
    u = scale_voltage(block.u, tr); i = scale_current(block.i, tr)
    if recon:
        u, i = reconstruct_three_wire(u, i)
    return SampleBlock(
        t=block.t,
        u=u,
        i=i,
        scaled=True,
        source=block.source,
        seq=block.seq,
    )


def unscale_power(value: float, tr: TransformConfig) -> float:
    """一次功率 → 二次功率（对账/调试用）。"""
    return float(value) / float(tr.power_ratio)
