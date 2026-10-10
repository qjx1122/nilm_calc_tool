"""实时数据源②：内置合成模拟器。

用途（工程实现纪律：产物必须能真实运行验证）：
1. 无真实采集链路时联调全链路（源 → 缓冲 → 计算 → UI）
2. **算法自验证**：注入已知幅值的基波与 2~50 次谐波，用解析解校验 RMS/P/Q/PF/THD
3. UI 演示

信号模型（二次侧值，未乘 PT/CT）：
    u_k(t) = √2·U1_sec·(1+ε_k)·[ cos(2πf t + φ_k) + Σ_h a_h·cos(2πh f t + ψ_h,k) ] + 噪声
    i_k(t) = √2·I1_sec·(1+ε'_k)·[ cos(2πf t + φ_k − θ_k) + Σ_h b_h·cos(2πh f t + ψ'_h,k − θ_h,k) ] + 噪声
默认二次侧额定：相电压 57.735V（=100/√3，对应 PT=100 的 10kV 系统）、相电流 5A（对应 CT=15 的 75A）。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from ..blocks import SampleBlock
from ..config import AppConfig
from .base import DataSource


class SimulatorSource(DataSource):
    kind = "simulator"

    def __init__(self, cfg: AppConfig, u1_sec: float = 100.0 / np.sqrt(3.0), i1_sec: float = 5.0,
                 f: Optional[float] = None, pf_angle_deg: float = 30.0,
                 harmonics_u: Optional[Dict[int, float]] = None,
                 harmonics_i: Optional[Dict[int, float]] = None,
                 noise_ratio: Optional[float] = None, unbalance: Optional[float] = None,
                 seed: int = 20261010, t0: Optional[float] = None,
                 block_samples: Optional[int] = None, realtime_pace: bool = True,
                 speed: Optional[float] = None, u_dc_sec: float = 0.0):
        self.cfg = cfg
        self.fs = float(cfg.sampling.fs)
        self.f = float(f if f is not None else cfg.source.sim_f)
        self.u1_sec = float(u1_sec)
        self.i1_sec = float(i1_sec)
        self.pf_angle = float(np.radians(pf_angle_deg))     # 电流滞后电压的角度（感性 → Q>0）
        self.harmonics_u = dict(harmonics_u if harmonics_u is not None else cfg.source.sim_harmonics)
        self.harmonics_i = dict(harmonics_i if harmonics_i is not None else cfg.source.sim_harmonics)
        self.noise_ratio = float(noise_ratio if noise_ratio is not None else cfg.source.sim_noise_ratio)
        self.unbalance = float(unbalance if unbalance is not None else cfg.source.sim_unbalance)
        self.u_dc_sec = float(u_dc_sec)
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.block_samples = int(block_samples or cfg.source.block_samples or 640)
        self.realtime_pace = bool(realtime_pace)
        self.speed = float(speed if speed is not None else cfg.source.sim_speed)
        self._t0 = float(t0 if t0 is not None else time.time())
        self._sample_index = 0
        self._n_blocks = 0
        self._wall_start: Optional[float] = None
        self._phase_offsets = (0.0, -2 * np.pi / 3, 2 * np.pi / 3)   # 正序 ABC
        self._unb = (1.0, 1.0 + self.unbalance, 1.0 - self.unbalance)

    # ---------- 生命周期 ----------
    def open(self) -> None:
        self._wall_start = time.time()
        self._sample_index = 0

    def close(self) -> None:
        pass

    @property
    def exhausted(self) -> bool:
        return False

    # ---------- 信号生成 ----------
    def _harmonic_sum(self, t: np.ndarray, amps: Dict[int, float], phase_base: float,
                      seed_shift: int) -> np.ndarray:
        out = np.zeros_like(t)
        for idx, (h, a) in enumerate(sorted(amps.items())):
            h = int(h)
            if h < 1:
                continue
            # 各次谐波相位：确定性伪随机（保证可复现，且三相相位互不相同）
            psi = ((h * 37 + seed_shift * 13 + idx * 7) % 360) * np.pi / 180.0
            out += float(a) * np.cos(2 * np.pi * h * self.f * t + phase_base * h + psi)
        return out

    def generate(self, n: int) -> SampleBlock:
        """生成 n 个样本（二次侧值）。t 为绝对时间（epoch 秒）。"""
        idx0 = self._sample_index
        idx = np.arange(idx0, idx0 + n, dtype=np.float64)
        t = self._t0 + idx / self.fs
        t_rel = idx / self.fs
        u = np.zeros((3, n), dtype=np.float64)
        i = np.zeros((3, n), dtype=np.float64)
        for k in range(3):
            ph = self._phase_offsets[k]
            amp_u = np.sqrt(2.0) * self.u1_sec * self._unb[k]
            amp_i = np.sqrt(2.0) * self.i1_sec * (1.0 + (self.unbalance * 0.5 if k == 1 else
                                                        -self.unbalance * 0.5 if k == 2 else 0.0))
            u[k] = amp_u * (np.cos(2 * np.pi * self.f * t_rel + ph)
                            + self._harmonic_sum(t_rel, self.harmonics_u, ph, k))
            i[k] = amp_i * (np.cos(2 * np.pi * self.f * t_rel + ph - self.pf_angle)
                            + self._harmonic_sum(t_rel, self.harmonics_i, ph - self.pf_angle, k + 3))
            if self.noise_ratio > 0:
                u[k] += self.noise_ratio * amp_u * self.rng.standard_normal(n)
                i[k] += self.noise_ratio * amp_i * self.rng.standard_normal(n)
        if self.u_dc_sec:
            u += self.u_dc_sec
        self._sample_index += n
        return SampleBlock(t=t, u=u, i=i, scaled=False, source="simulator", seq=self._n_blocks)

    # ---------- 读取 ----------
    def read(self) -> Optional[SampleBlock]:
        if self._wall_start is None:
            self.open()
        if self.realtime_pace and self.speed > 0:
            # 按真实时间速率产出（联调用）；不足一块则等待
            elapsed = (time.time() - self._wall_start) * self.speed
            target = int(elapsed * self.fs)
            if target - self._sample_index < self.block_samples:
                wait = (self.block_samples - (target - self._sample_index)) / self.fs / max(self.speed, 1e-6)
                time.sleep(min(max(wait, 0.0), 1.0))
                elapsed = (time.time() - self._wall_start) * self.speed
                target = int(elapsed * self.fs)
                if target - self._sample_index < 1:
                    return None
            n = min(self.block_samples, max(1, target - self._sample_index))
        else:
            n = self.block_samples
        block = self.generate(n)
        self._n_blocks += 1
        return block

    def info(self) -> Dict[str, Any]:
        return {
            "kind": self.kind, "fs": self.fs, "f_hz": self.f,
            "u1_sec_rms": self.u1_sec, "i1_sec_rms": self.i1_sec,
            "u1_primary_rms": self.u1_sec * (self.cfg.transform.pt_ratio if self.cfg.transform.enabled else 1.0),
            "i1_primary_rms": self.i1_sec * (self.cfg.transform.ct_ratio if self.cfg.transform.enabled else 1.0),
            "pf_angle_deg": float(np.degrees(self.pf_angle)),
            "harmonics_u": {str(k): v for k, v in sorted(self.harmonics_u.items())},
            "harmonics_i": {str(k): v for k, v in sorted(self.harmonics_i.items())},
            "noise_ratio": self.noise_ratio, "unbalance": self.unbalance,
            "block_samples": self.block_samples, "blocks_read": self._n_blocks,
            "samples_generated": self._sample_index,
            "realtime_pace": self.realtime_pace, "speed": self.speed, "seed": self.seed,
            "duration_s": self._sample_index / self.fs,
            "notes": ["合成数据：用于联调与算法自验证，**不代表真实电网**"],
        }
