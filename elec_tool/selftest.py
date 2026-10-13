"""算法自检：用**解析解**对账（不依赖真实数据即可验证实现正确性）。

原理：构造已知幅值/相位的三相谐波信号 → 用公式算出理论期望值 → 与本工具计算结果比对。
信号模型（三相平衡，h 次谐波相序随 h 旋转，符合真实电网）：
    u_k(t) = Σ_h √2·U_h·cos(2πh·f·t + h·β_k + α_h)
    i_k(t) = Σ_h √2·I_h·cos(2πh·f·t + h·β_k + α_h − φ_h)
    β_k = 0, −2π/3, +2π/3（A/B/C 正序）
由此可直接推出期望值：
    U_rms,相 = √(Σ_h U_h²)；P_相 = Σ_h U_h I_h cosφ_h；Q_相 = Σ_h U_h I_h sinφ_h
    线电压：非零序谐波 ×√3，3 的整数倍次（零序）在线电压中抵消 → U_line = √3·√(Σ_{h∉3n} U_h²)
    零线电流：仅零序（3n 次）叠加 → I_n = 3·√(Σ_{h∈3n} I_h²)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .blocks import SampleBlock
from .config import (QUANTITY_KEYS, AppConfig, HarmonicConfig, PowerConfig, SamplingConfig, TransformConfig,
                     WindowSpec)
from .metrics import MetricsCalculator

BETA = (0.0, -2 * math.pi / 3, 2 * math.pi / 3)


@dataclass
class HarmSpec:
    """一次谐波的注入规格：U/I 为**二次侧** RMS，phi_deg＝该次电压超前电流的角度。"""
    order: int
    U: float
    I: float
    phi_deg: float = 0.0
    alpha_deg: float = 0.0


@dataclass
class CheckResult:
    id: str
    name: str
    expected: float
    actual: float
    tol_rel: float
    rel_err: float
    ok: bool
    unit: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "expected": self.expected, "actual": self.actual,
                "tol_rel": self.tol_rel, "rel_err": self.rel_err, "ok": self.ok,
                "unit": self.unit, "note": self.note}


def build_signal(specs: Sequence[HarmSpec], fs: float, duration_s: float, f: float = 50.0,
                 neg_seq_ratio: float = 0.0, noise_ratio: float = 0.0,
                 seed: int = 7, t0: float = 1_760_000_000.0,
                 u_dc: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """构造解析信号，返回 (t, u(3,N), i(3,N))，均为二次侧值。"""
    n = int(round(duration_s * fs))
    t = t0 + np.arange(n, dtype=np.float64) / fs
    tt = np.arange(n, dtype=np.float64) / fs
    u = np.zeros((3, n), dtype=np.float64)
    i = np.zeros((3, n), dtype=np.float64)
    for k in range(3):
        for sp in specs:
            h = int(sp.order)
            a = math.radians(sp.alpha_deg)
            phi = math.radians(sp.phi_deg)
            u[k] += math.sqrt(2) * sp.U * np.cos(2 * math.pi * h * f * tt + h * BETA[k] + a)
            i[k] += math.sqrt(2) * sp.I * np.cos(2 * math.pi * h * f * tt + h * BETA[k] + a - phi)
        if neg_seq_ratio > 0:      # 基波负序分量（反转相序），三相均注入
            base = [s for s in specs if s.order == 1]
            if base:
                sp = base[0]
                phi = math.radians(sp.phi_deg)
                u[k] += math.sqrt(2) * (neg_seq_ratio * sp.U) * np.cos(2 * math.pi * f * tt - BETA[k] + math.radians(sp.alpha_deg))
                i[k] += math.sqrt(2) * (neg_seq_ratio * sp.I) * np.cos(2 * math.pi * f * tt - BETA[k] + math.radians(sp.alpha_deg) - phi)
    if u_dc:
        u += u_dc
    if noise_ratio > 0:
        rng = np.random.default_rng(seed)
        u1 = max((s.U for s in specs), default=1.0)
        i1 = max((s.I for s in specs), default=1.0)
        u += noise_ratio * math.sqrt(2) * u1 * rng.standard_normal((3, n))
        i += noise_ratio * math.sqrt(2) * i1 * rng.standard_normal((3, n))
    return t, u, i


def expected_values(specs: Sequence[HarmSpec], tr: TransformConfig, fs: float, f: float,
                    order_max: int = 50) -> Dict[str, Any]:
    """按公式算出全部期望值（一次侧）。"""
    pt = tr.pt_ratio if tr.enabled else 1.0
    ct = tr.ct_ratio if tr.enabled else 1.0
    U = {int(s.order): float(s.U) * pt for s in specs if int(s.order) <= order_max}
    I = {int(s.order): float(s.I) * ct for s in specs if int(s.order) <= order_max}
    PHI = {int(s.order): math.radians(float(s.phi_deg)) for s in specs if int(s.order) <= order_max}
    u_rms_phase = math.sqrt(sum(v * v for v in U.values()))
    i_rms_phase = math.sqrt(sum(v * v for v in I.values()))
    p_phase = sum(U[h] * I[h] * math.cos(PHI[h]) for h in U if h in I)
    q_phase = sum(U[h] * I[h] * math.sin(PHI[h]) for h in U if h in I)
    triplen = [h for h in U if h % 3 == 0 and h != 0]
    non_triplen = [h for h in U if h % 3 != 0]
    u_line = math.sqrt(3.0) * math.sqrt(sum(U[h] ** 2 for h in non_triplen))
    i_neutral = 3.0 * math.sqrt(sum(I[h] ** 2 for h in triplen)) if triplen else 0.0
    s_arith_total = 3.0 * u_rms_phase * i_rms_phase
    p_total = 3.0 * p_phase
    q_total = 3.0 * q_phase
    s_vec_total = math.sqrt(p_total ** 2 + q_total ** 2)
    thd_u = math.sqrt(sum(U[h] ** 2 for h in U if h >= 2)) / U.get(1, float("nan")) * 100.0 if U.get(1) else float("nan")
    thd_i = math.sqrt(sum(I[h] ** 2 for h in I if h >= 2)) / I.get(1, float("nan")) * 100.0 if I.get(1) else float("nan")
    return {
        "u_rms_phase": u_rms_phase, "i_rms_phase": i_rms_phase,
        "u_line": u_line, "i_neutral": i_neutral,
        "p_total": p_total, "q_total": q_total,
        "s_arith_total": s_arith_total, "s_vec_total": s_vec_total,
        "pf_arith": p_total / s_arith_total if s_arith_total else float("nan"),
        "pf_vec": p_total / s_vec_total if s_vec_total else float("nan"),
        "thd_u_pct": thd_u, "thd_i_pct": thd_i,
        "U_orders": U, "I_orders": I, "phi_rad": PHI,
        "p1_total": 3 * U.get(1, 0) * I.get(1, 0) * math.cos(PHI.get(1, 0)),
        "q1_total": 3 * U.get(1, 0) * I.get(1, 0) * math.sin(PHI.get(1, 0)),
        "dpf": math.cos(PHI.get(1, 0.0)),
        "u1_rms": U.get(1, float("nan")), "i1_rms": I.get(1, float("nan")),
        "hr_pct": {h: (100.0 * U[h] / U[1]) for h in U if U.get(1)},
    }


def _rel(actual: float, expected: float) -> float:
    if expected is None or not np.isfinite(expected):
        return float("inf") if not (actual is not None and np.isfinite(actual or np.nan)) else 0.0
    if abs(expected) < 1e-12:
        return abs(float(actual)) if np.isfinite(actual) else float("inf")
    if actual is None or not np.isfinite(actual):
        return float("inf")
    return abs(float(actual) - float(expected)) / abs(float(expected))


def _mk(cid: str, name: str, expected: float, actual: Optional[float], tol_rel: float,
        unit: str = "", note: str = "") -> CheckResult:
    a = float("nan") if actual is None else float(actual)
    rel = _rel(a, expected)
    ok = bool(np.isfinite(rel) and rel <= tol_rel)
    return CheckResult(id=cid, name=name, expected=float(expected), actual=a, tol_rel=tol_rel,
                       rel_err=float(rel), ok=ok, unit=unit, note=note)


def run_selftest(fs: float = 6400.0, f: float = 50.0, pt: float = 100.0, ct: float = 15.0,
                 duration_s: float = 1.0, verbose: bool = False) -> List[CheckResult]:
    """全套自检（默认参数＝用户给定工况：fs=6400、PT=100、CT=15、50Hz）。"""
    checks: List[CheckResult] = []
    specs = [
        HarmSpec(1, 100.0 / math.sqrt(3), 5.0, phi_deg=30.0),     # 基波：57.735V/5A，φ=30°（感性）
        HarmSpec(3, 0.08 * 100.0 / math.sqrt(3), 0.10 * 5.0, phi_deg=45.0),
        HarmSpec(5, 0.06 * 100.0 / math.sqrt(3), 0.08 * 5.0, phi_deg=60.0),
        HarmSpec(7, 0.03 * 100.0 / math.sqrt(3), 0.05 * 5.0, phi_deg=20.0),
        HarmSpec(11, 0.015 * 100.0 / math.sqrt(3), 0.02 * 5.0, phi_deg=10.0),
        HarmSpec(13, 0.010 * 100.0 / math.sqrt(3), 0.015 * 5.0, phi_deg=80.0),
    ]
    cfg = AppConfig(
        sampling=SamplingConfig(fs=fs, f_nom=f, adaptive_freq=False),
        transform=TransformConfig(pt_ratio=pt, ct_ratio=ct),
        harmonic=HarmonicConfig(order_min=2, order_max=50),
        power=PowerConfig(apparent="arithmetic", reactive="harmonic_sum"),
        windows={k: WindowSpec(length_s=duration_s) for k in QUANTITY_KEYS},
    ).validate()
    exp = expected_values(specs, cfg.transform, fs, f, cfg.harmonic.order_max)

    t, u, i = build_signal(specs, fs, duration_s + 0.2, f)          # 多给 0.2s 余量
    block = SampleBlock(t=t, u=u * pt, i=i * ct, scaled=True, source="selftest")
    res = MetricsCalculator(cfg).compute(block, with_history=False)
    q = res.quantities

    def val(key: str, *path: str) -> Optional[float]:
        cur: Any = q[key].values if key in q and q[key].ok else None
        for p in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(p)
        return None if cur is None else float(cur)

    tol = 2e-3      # 0.2%：整周期截断 + 有限字长的合理容差
    # --- S1 有效值 / 线电压 / 零线电流 ---
    for k, ph in enumerate(("A", "B", "C")):
        checks.append(_mk(f"S1-U{ph}", f"{ph}相电压有效值", exp["u_rms_phase"], val("voltage", "rms", ph), tol, "V"))
        checks.append(_mk(f"S1-I{ph}", f"{ph}相电流有效值", exp["i_rms_phase"], val("current", "rms", ph), tol, "A"))
    checks.append(_mk("S1-Uab", "线电压 Uab 有效值", exp["u_line"], val("voltage", "line_rms", "Uab"), tol, "V",
                      "3 的整数倍次（零序）在线电压中抵消"))
    checks.append(_mk("S1-In", "零线电流有效值", exp["i_neutral"], val("current", "neutral_rms"), 5e-3, "A",
                      "零序（3n 次）电流在零线叠加为 3 倍"))
    # --- S2 功率与功率因数 ---
    checks.append(_mk("S2-P", "三相总有功 P", exp["p_total"], val("power", "p_total"), tol, "W"))
    checks.append(_mk("S2-Q", "三相总无功 Q", exp["q_total"], val("power", "q_total"), 5e-3, "var"))
    checks.append(_mk("S2-S", "三相视在 S（算术）", exp["s_arith_total"], val("power", "s_total"), tol, "VA"))
    checks.append(_mk("S2-PF", "功率因数 PF", exp["pf_arith"], val("power_factor", "pf_total"), tol, ""))
    checks.append(_mk("S2-DPF", "基波位移因数 DPF=cosφ1", exp["dpf"], val("power_factor", "dpf"), tol, ""))
    checks.append(_mk("S2-P1", "基波有功 P1", exp["p1_total"], val("power", "fundamental", "p1_total"), tol, "W"))
    checks.append(_mk("S2-Q1", "基波无功 Q1", exp["q1_total"], val("power", "fundamental", "q1_total"), 5e-3, "var"))
    # --- S3 基波与谐波 ---
    checks.append(_mk("S3-U1", "基波电压 U1", exp["u1_rms"], val("fundamental", "u1_rms", "A"), tol, "V"))
    checks.append(_mk("S3-I1", "基波电流 I1", exp["i1_rms"], val("fundamental", "i1_rms", "A"), tol, "A"))
    checks.append(_mk("S3-THDu", "电压总谐波畸变率 THD_U", exp["thd_u_pct"], val("harmonic", "thd_u_pct", "A"), 5e-3, "%"))
    checks.append(_mk("S3-THDi", "电流总谐波畸变率 THD_I", exp["thd_i_pct"], val("harmonic", "thd_i_pct", "A"), 5e-3, "%"))
    for h in (3, 5, 7, 11, 13):
        exp_u = exp["U_orders"][h]
        act_u = val("harmonic", "u", "A", "orders_rms", str(h))
        checks.append(_mk(f"S3-U{h}", f"{h} 次谐波电压幅值", exp_u, act_u, 5e-3, "V"))
        checks.append(_mk(f"S3-HR{h}", f"{h} 次电压含有率", exp["hr_pct"][h], val("harmonic", "u", "A", "hr_pct", str(h)),
                          5e-3, "%"))
    # --- S4 频谱峰值位置 ---
    peak = q["spectrum"].values.get("peak") if q["spectrum"].ok else None
    peak_hz = float(peak.get("freq_hz", float("nan"))) if isinstance(peak, dict) else float("nan")
    checks.append(_mk("S4-peak", "频谱主峰频率（应为基波 50Hz）", f, peak_hz, 1e-3, "Hz"))
    checks.append(_mk("S4-res", "频谱分辨率（=1/窗长）", 1.0 / duration_s,
                      val("spectrum", "freq_resolution_hz"), 1e-6, "Hz"))
    # --- S5 窗长独立性（需求⑥）：1s 与 5s 对稳态信号结果应一致 ---
    if duration_s >= 1.0:
        cfg5 = _cfg_with_windows(cfg, 5.0)
        t5, u5, i5 = build_signal(specs, fs, 5.2, f)
        blk5 = SampleBlock(t=t5, u=u5 * pt, i=i5 * ct, scaled=True, source="selftest5s")
        r5 = MetricsCalculator(cfg5).compute(blk5, with_history=False)
        u5a = float(r5.quantities["voltage"].values["rms"]["A"])
        p5 = float(r5.quantities["power"].values["p_total"])
        checks.append(_mk("S5-U5s", "5s 窗 vs 1s 窗：电压有效值一致性", exp["u_rms_phase"], u5a, tol, "V"))
        checks.append(_mk("S5-P5s", "5s 窗 vs 1s 窗：有功一致性", exp["p_total"], p5, tol, "W"))
    # --- S6 PT/CT 可配置：变比缩放线性 ---
    cfg1 = _cfg_with_transform(cfg, 1.0, 1.0)
    exp1 = expected_values(specs, cfg1.transform, fs, f, cfg1.harmonic.order_max)
    blk1 = SampleBlock(t=t, u=u, i=i, scaled=True, source="selftest_ratio")
    r1 = MetricsCalculator(cfg1).compute(blk1, with_history=False)
    checks.append(_mk("S6-U", "PT=1 时电压有效值（对账 PT 可配置）", exp1["u_rms_phase"],
                      float(r1.quantities["voltage"].values["rms"]["A"]), tol, "V"))
    ratio_u = (float(q["voltage"].values["rms"]["A"]) /
               float(r1.quantities["voltage"].values["rms"]["A"]))
    checks.append(_mk("S6-ratioU", "PT 缩放比（应等于 PT）", pt, ratio_u, tol, ""))
    ratio_p = float(q["power"].values["p_total"]) / float(r1.quantities["power"].values["p_total"])
    checks.append(_mk("S6-ratioP", "功率缩放比（应等于 PT×CT）", pt * ct, ratio_p, tol, ""))
    # --- S7 频率自适应（f=49.85Hz，adaptive 开启）---
    f_off = 49.85
    cfg_ad = _cfg_with_adaptive(cfg, True)
    t7, u7, i7 = build_signal(specs, fs, 1.2, f_off)
    blk7 = SampleBlock(t=t7, u=u7 * pt, i=i7 * ct, scaled=True, source="selftest_adaptive")
    r7 = MetricsCalculator(cfg_ad).compute(blk7, with_history=False)
    checks.append(_mk("S7-f", "频率估计（真值 49.85Hz）", f_off, float(r7.f_used), 2e-4, "Hz"))
    exp7 = expected_values(specs, cfg.transform, fs, f_off, cfg.harmonic.order_max)
    checks.append(_mk("S7-U", "频率偏移下电压有效值", exp7["u_rms_phase"],
                      float(r7.quantities["voltage"].values["rms"]["A"]), tol, "V"))
    checks.append(_mk("S7-U5", "频率偏移下 5 次谐波幅值（抗泄漏）", exp7["U_orders"][5],
                      float(r7.quantities["harmonic"].values["u"]["A"]["orders_rms"]["5"]), 1e-2, "V"))
    checks.append(_mk("S7-P", "频率偏移下有功", exp7["p_total"],
                      float(r7.quantities["power"].values["p_total"]), tol, "W"))
    # --- S8 不平衡度：注入 5% 基波负序 ---
    t8, u8, i8 = build_signal([specs[0]], fs, 1.2, f, neg_seq_ratio=0.05)
    blk8 = SampleBlock(t=t8, u=u8 * pt, i=i8 * ct, scaled=True, source="selftest_unbalance")
    r8 = MetricsCalculator(cfg).compute(blk8, with_history=False)
    checks.append(_mk("S8-unb", "电压不平衡度（注入 5% 负序）", 5.0,
                      float(r8.quantities["fundamental"].values["unbalance_u_pct"]), 2e-2, "%"))
    checks.append(_mk("S8-U1", "正序基波电压（应≈U1）", specs[0].U * pt,
                      float(r8.quantities["fundamental"].values["u_sequence"]["U1"]), tol, "V"))
    # --- S9 直流分量与 remove_dc 口径 ---
    t9, u9, i9 = build_signal([specs[0]], fs, 1.2, f, u_dc=2.0)
    blk9 = SampleBlock(t=t9, u=u9 * pt, i=i9 * ct, scaled=True, source="selftest_dc")
    r9 = MetricsCalculator(cfg).compute(blk9, with_history=False)
    checks.append(_mk("S9-dc", "直流分量识别（注入 2V×PT）", 2.0 * pt,
                      float(r9.quantities["voltage"].values["dc_mean"]["A"]), 1e-2, "V"))
    checks.append(_mk("S9-rms", "去直流后有效值不受直流影响", specs[0].U * pt,
                      float(r9.quantities["voltage"].values["rms"]["A"]), tol, "V"))

    if verbose:
        for c in checks:
            flag = "PASS" if c.ok else "FAIL"
            print(f"[{flag}] {c.id:<10} {c.name:<38} 期望={c.expected:14.6g} 实际={c.actual:14.6g} "
                  f"相对误差={c.rel_err*100:8.4f}% (容差 {c.tol_rel*100:.3f}%) {c.unit}")
    return checks


def _cfg_with_windows(cfg: AppConfig, length_s: float) -> AppConfig:
    import copy
    c = copy.deepcopy(cfg)
    for k in c.windows:
        c.windows[k].length_s = float(length_s)
    return c.validate()


def _cfg_with_transform(cfg: AppConfig, pt: float, ct: float) -> AppConfig:
    import copy
    c = copy.deepcopy(cfg)
    c.transform.pt_ratio = float(pt)
    c.transform.ct_ratio = float(ct)
    return c.validate()


def _cfg_with_adaptive(cfg: AppConfig, adaptive: bool) -> AppConfig:
    import copy
    c = copy.deepcopy(cfg)
    c.sampling.adaptive_freq = bool(adaptive)
    return c.validate()


def summarize(checks: Sequence[CheckResult]) -> Dict[str, Any]:
    n = len(checks)
    passed = sum(1 for c in checks if c.ok)
    fails = [c.to_dict() for c in checks if not c.ok]
    worst = max((c.rel_err for c in checks if np.isfinite(c.rel_err)), default=float("nan"))
    return {"total": n, "passed": passed, "failed": n - passed,
            "pass_rate_pct": (100.0 * passed / n) if n else float("nan"),
            "worst_rel_err": worst, "failures": fails,
            "all_ok": passed == n}
