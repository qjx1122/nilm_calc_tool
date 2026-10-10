"""算法层测试：全部用解析解对账（注入已知信号 → 与公式期望值比对）。"""

from __future__ import annotations

import math

import numpy as np
import pytest

from elec_tool.analysis.harmonic import (bin_spectrum, dft_harmonic_phasors, harmonic_analysis,
                                         harmonic_analysis_3phase, spectrum_analysis)
from elec_tool.analysis.power import instantaneous_power, power_analysis
from elec_tool.analysis.rms import (line_voltages_rms, phase_from_line_inst, rms, rms_per_cycle,
                                    symmetrical_components, three_phase_rms, unbalance_ratio)
from elec_tool.analysis.window import (estimate_frequency, estimate_frequency_fft,
                                       estimate_frequency_zero_crossing, plan_window,
                                       refine_frequency_baseband, samples_for_seconds)
from elec_tool.config import AppConfig, HarmonicConfig, PowerConfig, WindowSpec
from elec_tool.selftest import HarmSpec, build_signal, expected_values
from tests.conftest import CT, F_NOM, FS, PT


# ---------------------------------------------------------------- RMS

def test_rms_pure_sine():
    n = 6400
    t = np.arange(n) / FS
    x = math.sqrt(2) * 220.0 * np.cos(2 * math.pi * 50 * t)
    assert rms(x) == pytest.approx(220.0, rel=1e-9)
    assert rms(x, remove_dc=False) == pytest.approx(220.0, rel=1e-9)


def test_rms_with_dc_and_flag():
    n = 6400
    t = np.arange(n) / FS
    x = 10.0 + math.sqrt(2) * 220.0 * np.cos(2 * math.pi * 50 * t)
    assert rms(x, remove_dc=True) == pytest.approx(220.0, rel=1e-6)
    assert rms(x, remove_dc=False) == pytest.approx(math.sqrt(220.0 ** 2 + 10.0 ** 2), rel=1e-6)


def test_rms_empty_is_nan():
    assert math.isnan(rms(np.empty(0)))


def test_rms_per_cycle_stats(default_specs):
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    st = rms_per_cycle(u[0], FS, F_NOM)
    exp = math.sqrt(sum((s.U ** 2) for s in default_specs))
    assert st["n_cycles"] == 50
    assert st["mean"] == pytest.approx(exp, rel=1e-3)
    assert st["min"] <= st["mean"] <= st["max"]
    assert st["std"] < 0.01 * exp            # 稳态信号逐周期波动应极小


def test_rms_per_cycle_non_integer_spc(default_specs):
    """频率偏移时 fs/f 非整数：逐周期切分不得崩（曾踩 reshape bug）。"""
    t, u, i = build_signal(default_specs, FS, 1.0, 49.85)
    st = rms_per_cycle(u[0], FS, 49.85)
    exp = math.sqrt(sum((s.U ** 2) for s in default_specs))
    assert st["n_cycles"] >= 49
    assert st["mean"] == pytest.approx(exp, rel=5e-3)


def test_three_phase_rms_and_line_voltage(default_specs):
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    up = u * PT
    res = three_phase_rms(up, FS, F_NOM)
    exp = expected_values(default_specs, AppConfig().transform, FS, F_NOM)
    for ph in ("A", "B", "C"):
        assert res["rms"][ph] == pytest.approx(exp["u_rms_phase"], rel=1e-3)
    lv = line_voltages_rms(up)
    # 3 的整数倍次为零序 → 线电压中抵消；其余 ×√3
    assert lv["Uab"] == pytest.approx(exp["u_line"], rel=1e-3)
    assert lv["Ubc"] == pytest.approx(exp["u_line"], rel=1e-3)
    assert res["rms_unbalance_pct"] < 0.5      # 三相平衡


def test_phase_from_line_roundtrip():
    n = 6400
    t = np.arange(n) / FS
    ph = np.vstack([math.sqrt(2) * 100 * np.cos(2 * math.pi * 50 * t + b) for b in (0, -2 * math.pi / 3, 2 * math.pi / 3)])
    line = np.vstack([ph[0] - ph[1], ph[1] - ph[2], ph[2] - ph[0]])
    back = phase_from_line_inst(line)
    np.testing.assert_allclose(back, ph, atol=1e-9)


def test_symmetrical_components_balanced():
    U = 100.0
    ph = np.array([U, U * np.exp(-2j * math.pi / 3), U * np.exp(2j * math.pi / 3)])
    sc = symmetrical_components(ph)
    assert sc["U1"] == pytest.approx(U, rel=1e-12)
    assert abs(sc["U2"]) < 1e-9
    assert abs(sc["U0"]) < 1e-9
    assert unbalance_ratio(ph) < 1e-6


def test_symmetrical_components_negative_sequence():
    U, neg = 100.0, 0.05
    pos = np.array([U, U * np.exp(-2j * math.pi / 3), U * np.exp(2j * math.pi / 3)])
    ng = np.array([neg * U, neg * U * np.exp(2j * math.pi / 3), neg * U * np.exp(-2j * math.pi / 3)])
    sc = symmetrical_components(pos + ng)
    assert sc["U1"] == pytest.approx(U, rel=1e-9)
    assert sc["U2"] == pytest.approx(neg * U, rel=1e-9)
    assert sc["negative_seq_pct"] == pytest.approx(5.0, rel=1e-6)


def test_symmetrical_components_zero_sequence():
    U0 = 10.0
    ph = np.array([U0, U0, U0], dtype=np.complex128) + np.array(
        [100.0, 100.0 * np.exp(-2j * math.pi / 3), 100.0 * np.exp(2j * math.pi / 3)])
    sc = symmetrical_components(ph)
    assert sc["U0"] == pytest.approx(U0, rel=1e-9)
    assert sc["zero_seq_pct"] == pytest.approx(10.0, rel=1e-6)


# ---------------------------------------------------------------- 频率估计

@pytest.mark.parametrize("f_true", [50.0, 49.85, 50.2, 48.0, 52.5])
def test_frequency_estimation_accuracy(default_specs, f_true):
    """含谐波 + 1% 噪声下，估频相对误差应 < 1e-5（整周期截断的前提）。"""
    t, u, i = build_signal(default_specs, FS, 1.0, f_true, noise_ratio=0.01)
    f_est, how = estimate_frequency(u[0], FS, 45.0, 65.0, F_NOM)
    assert f_est == pytest.approx(f_true, rel=1e-5), how


def test_frequency_estimation_coarse_methods(default_specs):
    t, u, i = build_signal(default_specs, FS, 1.0, 49.9)
    f_zc, how1 = estimate_frequency_zero_crossing(u[0], FS, 45.0, 65.0, F_NOM)
    assert f_zc == pytest.approx(49.9, rel=1e-3)
    f_fft, how2 = estimate_frequency_fft(u[0], FS, 45.0, 65.0)
    assert f_fft == pytest.approx(49.9, rel=1e-3)
    f_ref = refine_frequency_baseband(u[0], FS, f_zc)
    assert f_ref == pytest.approx(49.9, rel=1e-6)


def test_frequency_estimation_insufficient_samples():
    f, how = estimate_frequency(np.zeros(100), FS, 45.0, 65.0, F_NOM)
    assert f == F_NOM and "nominal" in how


# ---------------------------------------------------------------- 窗切分

def test_plan_window_integer_cycles():
    spec = WindowSpec(length_s=1.0)
    cut = plan_window(available=6400, spec=spec, quantity="voltage", fs=FS, f_used=50.0,
                      f_source="nominal", t_start=0.0, t_end=1.0)
    assert cut.n_samples == 6400 and cut.n_cycles == 50 and not cut.leakage_risk


def test_plan_window_off_nominal_frequency():
    spec = WindowSpec(length_s=1.0)
    cut = plan_window(available=6400, spec=spec, quantity="voltage", fs=FS, f_used=49.85,
                      f_source="estimated", t_start=0.0, t_end=1.0)
    assert cut.n_cycles == 49
    assert cut.n_samples == int(round(49 * FS / 49.85))
    assert cut.length_s_actual == pytest.approx(cut.n_samples / FS)


def test_plan_window_estimated_freq_near_integer_keeps_all_cycles():
    """回归：估频比额定低/高一丝时，不得少算一个整周期。

    实测踩坑（Web 实时链路暴露）：f_used=49.999987Hz（过零+基带精修，相对误差 2.6e-7）
    时，旧的绝对容差 floor(cyc_req + 1e-9) → 49 周期 → 用户配 1s 实际只算 0.98s(6272 点)，
    窗长口径与需求⑥不符。改用相对容差后必须回到 50 周期 / 6400 点 / 1.000s。
    """
    spec = WindowSpec(length_s=1.0)
    for f in (49.999987, 50.000013, 49.9999, 50.0001):
        cut = plan_window(available=6400, spec=spec, quantity="voltage", fs=FS, f_used=f,
                          f_source="zero_crossing+baseband_refine", t_start=0.0, t_end=1.0)
        assert cut.n_cycles == 50, (f, cut.n_cycles)
        assert cut.n_samples == 6400, (f, cut.n_samples)
        assert cut.length_s_actual == pytest.approx(1.0, rel=1e-4)
        assert not cut.leakage_risk

    # 5s 窗同理：249.99993 周期要进位到 250（否则实际 4.98s）
    cut5 = plan_window(available=32000, spec=WindowSpec(length_s=5.0), quantity="voltage",
                       fs=FS, f_used=49.999987, f_source="estimated", t_start=0.0, t_end=5.0)
    assert cut5.n_cycles == 250 and cut5.n_samples == 32000
    assert cut5.length_s_actual == pytest.approx(5.0, rel=1e-4)

    # 真·非整数周期仍须向下取整：49.85Hz 是 49.85 个周期，不能当成 50
    cut_off = plan_window(available=6400, spec=spec, quantity="voltage", fs=FS, f_used=49.85,
                          f_source="estimated", t_start=0.0, t_end=1.0)
    assert cut_off.n_cycles == 49


def test_plan_window_insufficient_data_degrades():
    """数据不够 5s 时：降级为「可用数据内的最多整数周期」，且不得打泄漏告警。"""
    spec = WindowSpec(length_s=5.0, min_cycles=1)
    cut = plan_window(available=1000, spec=spec, quantity="voltage", fs=FS, f_used=50.0,
                      f_source="nominal", t_start=0.0, t_end=0.2)
    assert cut.n_cycles == 7                        # 1000 点 / 128 点每周期 = 7.8 → 7 个完整周期
    assert cut.n_samples == 7 * 128
    assert not cut.leakage_risk
    assert cut.length_s_actual == pytest.approx(896 / FS)


def test_plan_window_full_window_flags_leakage():
    spec = WindowSpec(length_s=1.0, policy="full_window")
    cut = plan_window(available=6400, spec=spec, quantity="voltage", fs=FS, f_used=49.85,
                      f_source="estimated", t_start=0.0, t_end=1.0)
    assert cut.n_samples == 6400 and cut.n_cycles is None and cut.leakage_risk


def test_samples_for_seconds():
    assert samples_for_seconds(1.0, 6400.0) == 6400
    assert samples_for_seconds(0.2, 6400.0) == 1280
    assert samples_for_seconds(5.0, 6400.0) == 32000


# ---------------------------------------------------------------- 谐波与频谱

def test_harmonic_amplitudes_and_thd(default_specs, base_cfg):
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    exp = expected_values(default_specs, base_cfg.transform, FS, F_NOM)
    res = harmonic_analysis(u[0] * PT, FS, F_NOM, base_cfg.harmonic)
    assert res["fundamental_rms"] == pytest.approx(exp["u1_rms"], rel=1e-6)
    for h in (3, 5, 7, 11, 13):
        assert res["orders_rms"][str(h)] == pytest.approx(exp["U_orders"][h], rel=1e-6)
        assert res["hr_pct"][str(h)] == pytest.approx(exp["hr_pct"][h], rel=1e-6)
    assert res["thd_pct"] == pytest.approx(exp["thd_u_pct"], rel=1e-6)
    assert res["integer_bins"] is True and res["leakage_risk"] is False
    # 未注入的次应为 0
    assert res["orders_rms"]["4"] == pytest.approx(0.0, abs=1e-9)
    assert res["orders_rms"]["50"] == pytest.approx(0.0, abs=1e-9)


def test_harmonic_off_nominal_with_adaptive(default_specs, base_cfg):
    """频率偏移 + 估频后整周期截断：谐波幅值误差 <0.2%，且必须**如实**打上非整数 bin 标记。

    工程事实（本测试固化）：fs/f 非整数（6400/49.83=128.44）时无法做到「样本数恰好＝整数周期」，
    残余 <1 个样本的截断误差带来 ~1e-3 量级泄漏；额定 50Hz（6400/50=128 整）时为机器精度。
    """
    f_true = 49.83
    t, u, i = build_signal(default_specs, FS, 1.0, f_true)
    f_est, how = estimate_frequency(u[0], FS, 45.0, 65.0, F_NOM)
    assert f_est == pytest.approx(f_true, rel=1e-6), how
    n_cyc = int(math.floor(1.0 * f_est))
    n = int(round(n_cyc * FS / f_est))
    res = harmonic_analysis(u[0][-n:] * PT, FS, f_est, base_cfg.harmonic, n_cycles=n_cyc)
    exp = expected_values(default_specs, base_cfg.transform, FS, f_true)
    assert res["orders_rms"]["5"] == pytest.approx(exp["U_orders"][5], rel=2e-3)
    assert res["fundamental_rms"] == pytest.approx(exp["u1_rms"], rel=2e-4)
    assert res["thd_pct"] == pytest.approx(exp["thd_u_pct"], rel=2e-3)
    assert res["integer_bins"] is False and res["leakage_risk"] is True   # 如实标注，不假装精确


def test_harmonic_nominal_is_machine_precision(default_specs, base_cfg):
    """额定 50Hz + fs=6400（128 点/周期）→ 整数 bin、无泄漏、机器精度。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    res = harmonic_analysis(u[0] * PT, FS, F_NOM, base_cfg.harmonic, n_cycles=50)
    exp = expected_values(default_specs, base_cfg.transform, FS, F_NOM)
    assert res["integer_bins"] is True and res["leakage_risk"] is False
    assert res["orders_rms"]["5"] == pytest.approx(exp["U_orders"][5], rel=1e-9)


def test_harmonic_error_when_frequency_mismatch(default_specs, base_cfg):
    """反证：真值 49.5Hz 却按 50Hz 截断 → 5 次幅值误差 >1%（说明 adaptive_freq 的必要性）。"""
    f_true = 49.5
    t, u, i = build_signal(default_specs, FS, 1.0, f_true)
    exp = expected_values(default_specs, base_cfg.transform, FS, f_true)
    wrong = harmonic_analysis(u[0][-6400:] * PT, FS, F_NOM, base_cfg.harmonic, n_cycles=50)
    rel_wrong = abs(wrong["orders_rms"]["5"] - exp["U_orders"][5]) / exp["U_orders"][5]
    assert rel_wrong > 1e-2, f"按错误频率计算应显著偏差，实测 {rel_wrong:.4%}"
    f_est, _ = estimate_frequency(u[0], FS, 45.0, 65.0, F_NOM)
    n_cyc = int(math.floor(1.0 * f_est))
    n = int(round(n_cyc * FS / f_est))
    right = harmonic_analysis(u[0][-n:] * PT, FS, f_est, base_cfg.harmonic, n_cycles=n_cyc)
    rel_right = abs(right["orders_rms"]["5"] - exp["U_orders"][5]) / exp["U_orders"][5]
    assert rel_right < rel_wrong / 10


def test_harmonic_three_phase(default_specs, base_cfg):
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    res = harmonic_analysis_3phase(u * PT, FS, F_NOM, base_cfg.harmonic)
    assert set(res["per_phase"]) == {"A", "B", "C"}
    for ph in ("A", "B", "C"):
        assert res["thd_pct"][ph] == pytest.approx(res["thd_pct"]["A"], rel=1e-6)
    assert res["worst_phase"] in ("A", "B", "C")


def test_harmonic_window_functions_consistent(default_specs, base_cfg):
    """整周期条件下 rect 与 hann 的谐波幅值应接近（hann 有校正），差异 <0.5%。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    r = harmonic_analysis(u[0] * PT, FS, F_NOM, base_cfg.harmonic, window_fn="rect")
    h = harmonic_analysis(u[0] * PT, FS, F_NOM, base_cfg.harmonic, window_fn="hann")
    assert h["orders_rms"]["5"] == pytest.approx(r["orders_rms"]["5"], rel=5e-3)


def test_spectrum_peak_and_resolution(default_specs, base_cfg):
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    sp = spectrum_analysis(u[0] * PT, FS, F_NOM, "rect", True, max_points=1600)
    assert sp["peak"]["freq_hz"] == pytest.approx(F_NOM, rel=1e-3)
    assert sp["peak"]["amp_rms"] == pytest.approx(expected_values(default_specs, base_cfg.transform, FS, F_NOM)["u1_rms"], rel=1e-3)
    assert sp["freq_resolution_hz"] == pytest.approx(1.0, rel=1e-9)     # 1s 窗 → 1Hz
    assert sp["nyquist_hz"] == pytest.approx(FS / 2, rel=1e-12)
    assert len(sp["freqs"]) == len(sp["amp_rms"]) <= 1600
    assert sp["decimated"] is True


def test_spectrum_max_hold_preserves_harmonic_peaks(default_specs, base_cfg):
    """抽稀后仍应能看到 3/5/7 次谐波峰（max-hold 的作用）。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    sp = spectrum_analysis(u[0] * PT, FS, F_NOM, "rect", True, max_points=400)
    f = np.asarray(sp["freqs"]); a = np.asarray(sp["amp_rms"])
    for h, ratio in ((3, 0.08), (5, 0.06), (7, 0.03)):
        k = int(np.argmin(np.abs(f - h * F_NOM)))
        expected = ratio * 100.0 / math.sqrt(3) * PT
        # 抽稀桶内取最大 → 邻近 bin 即为峰值
        win = a[max(0, k - 2):k + 3]
        assert win.max() == pytest.approx(expected, rel=2e-2)


def test_parseval_total_rms_consistency(default_specs):
    """Parseval 对账：bin 能量之和 == 时域有效值。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    freqs, amp, phasor, meta = bin_spectrum(u[0], FS, "rect", True)
    assert meta["total_ac_rms"] == pytest.approx(rms(u[0], True), rel=1e-9)


def test_harmonic_out_of_range_orders_flagged(base_cfg):
    """次数超出可用 bin（如短窗）时不能静默给 0，要标 out_of_range。"""
    n = 64                                     # 0.01s @6400Hz
    x = np.sqrt(2) * 100 * np.cos(2 * np.pi * 50 * np.arange(n) / FS)
    ph, meta = dft_harmonic_phasors(x, FS, F_NOM, [1, 20, 50], "rect", True)
    assert meta["out_of_range"], meta


# ---------------------------------------------------------------- 功率

def test_power_analytic(default_specs, base_cfg):
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    exp = expected_values(default_specs, base_cfg.transform, FS, F_NOM)
    res = power_analysis(u * PT, i * CT, FS, F_NOM, base_cfg.power, base_cfg.harmonic, n_cycles=50)
    assert res["p_total"] == pytest.approx(exp["p_total"], rel=1e-6)
    assert res["q_total"] == pytest.approx(exp["q_total"], rel=1e-6)
    assert res["s_total"] == pytest.approx(exp["s_arith_total"], rel=1e-6)
    assert res["pf_total"] == pytest.approx(exp["pf_arith"], rel=1e-6)
    assert res["fundamental"]["dpf"] == pytest.approx(math.cos(math.radians(30)), rel=1e-6)
    assert res["fundamental"]["p1_total"] == pytest.approx(exp["p1_total"], rel=1e-6)
    assert res["quadrant"]["index"] == 1                 # P>0, Q>0 → 感性吸收
    assert abs(res["p_residual_pct"]) < 1e-6             # 时域 P 与 Σ_h P_h 完全对账


def test_power_vector_apparent_with_harmonic_reactive(default_specs, base_cfg):
    """几何视在 S=√(P²+Q²)（Q 用严格谐波口径）→ 与解析解一致。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    exp = expected_values(default_specs, base_cfg.transform, FS, F_NOM)
    cfg_v = PowerConfig(apparent="vector", reactive="harmonic_sum")
    res = power_analysis(u * PT, i * CT, FS, F_NOM, cfg_v, base_cfg.harmonic, n_cycles=50)
    assert res["s_total"] == pytest.approx(exp["s_vec_total"], rel=1e-6)
    assert res["q_total"] == pytest.approx(exp["q_total"], rel=1e-6)
    assert res["modes"]["apparent"] == "vector"
    assert res["s_total"] < res["s_total_arithmetic"]        # 非正弦工况：几何视在 < 算术视在


def test_power_quadrature_reactive_approximates(default_specs, base_cfg):
    """Q=√(S²−P²) 等效口径应与严格谐波口径接近（本例差 <1%），且符号取自谐波口径。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    exp = expected_values(default_specs, base_cfg.transform, FS, F_NOM)
    res = power_analysis(u * PT, i * CT, FS, F_NOM, PowerConfig(reactive="quadrature"),
                         base_cfg.harmonic, n_cycles=50)
    assert res["q_total"] == pytest.approx(exp["q_total"], rel=1e-2)
    assert res["q_total"] > 0                                 # 感性 → 正号保持


def test_power_degenerate_mode_is_flagged(default_specs, base_cfg):
    """vector + quadrature 组合会口径退化（S≡S_arith），必须显式告警而不是静默给数。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    exp = expected_values(default_specs, base_cfg.transform, FS, F_NOM)
    res = power_analysis(u * PT, i * CT, FS, F_NOM, PowerConfig(apparent="vector", reactive="quadrature"),
                         base_cfg.harmonic, n_cycles=50)
    assert res["s_total"] == pytest.approx(exp["s_arith_total"], rel=1e-9)
    assert any("口径退化" in n for n in res["notes"])


def test_power_capacitive_sign():
    """容性（电流超前）→ Q 应为负，象限＝第四象限。"""
    n = 6400
    t = np.arange(n) / FS
    u1, i1 = 100.0, 5.0
    ph_u = np.vstack([math.sqrt(2) * u1 * np.cos(2 * math.pi * 50 * t + b) for b in (0, -2 * math.pi / 3, 2 * math.pi / 3)])
    ph_i = np.vstack([math.sqrt(2) * i1 * np.cos(2 * math.pi * 50 * t + b + math.radians(40))
                      for b in (0, -2 * math.pi / 3, 2 * math.pi / 3)])
    res = power_analysis(ph_u * PT, ph_i * CT, FS, F_NOM, PowerConfig(), HarmonicConfig(), n_cycles=50)
    assert res["q_total"] < 0
    assert res["quadrant"]["index"] == 4
    assert res["pf_total"] == pytest.approx(math.cos(math.radians(40)), rel=1e-6)
    assert res["p_total"] == pytest.approx(3 * u1 * PT * i1 * CT * math.cos(math.radians(40)), rel=1e-6)


def test_power_reverse_active():
    """反向有功（P<0，如光伏反送）→ 第二象限。"""
    n = 6400
    t = np.arange(n) / FS
    u1, i1 = 100.0, 5.0
    ph_u = np.vstack([math.sqrt(2) * u1 * np.cos(2 * math.pi * 50 * t + b) for b in (0, -2 * math.pi / 3, 2 * math.pi / 3)])
    ph_i = np.vstack([math.sqrt(2) * i1 * np.cos(2 * math.pi * 50 * t + b + math.radians(150))
                      for b in (0, -2 * math.pi / 3, 2 * math.pi / 3)])
    res = power_analysis(ph_u * PT, ph_i * CT, FS, F_NOM, PowerConfig(), HarmonicConfig(), n_cycles=50)
    assert res["p_total"] < 0
    assert res["quadrant"]["index"] in (2, 3)


def test_power_zero_signal_no_crash():
    z = np.zeros((3, 6400))
    res = power_analysis(z, z, FS, F_NOM, PowerConfig(), HarmonicConfig(), n_cycles=50)
    assert res["p_total"] == pytest.approx(0.0, abs=1e-12)
    assert math.isnan(res["pf_total"])
    assert math.isnan(res["fundamental"]["dpf"])


def test_instantaneous_power_sum():
    n = 1280
    u = np.ones((3, n)); i = np.ones((3, n)) * 2
    p = instantaneous_power(u, i)
    assert p.shape == (n,)
    np.testing.assert_allclose(p, 6.0)


def test_power_neutral_current_triplen(default_specs, base_cfg):
    """3 次（零序）电流在零线叠加为 3 倍——三相四线系统的典型现象。"""
    t, u, i = build_signal(default_specs, FS, 1.0, F_NOM)
    exp = expected_values(default_specs, base_cfg.transform, FS, F_NOM)
    i_sum = (i * CT).sum(axis=0)
    assert rms(i_sum) == pytest.approx(exp["i_neutral"], rel=1e-6)
    assert exp["i_neutral"] == pytest.approx(3 * 0.10 * 5.0 * CT, rel=1e-9)
