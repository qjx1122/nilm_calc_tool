"""v0.83（第 107 轮）：调参「量噪声」对周波复制文件（每秒一个模板复制 50 周波）的保护。

用户现场：`波形_农业排灌_大水泵_80_1.csv` 调参得 σ=3.3e-7 A，推出的容差比真实秒间抖动（1e-2 A）小 4 个量级，
负荷辨识 0 事件。本测试用秒级 Ia 展开成逐周波序列复现，并断言修正后：σ 量到秒间抖动量级、暂态长度量到 ~45 s、
suggest 出的 steady_state 参数能检出起动 / 停机。
"""
import numpy as np
import pytest

from elec_tool.config import NILM_ALGO_DEFAULTS
from elec_tool.nilm import detect_steps, effective_params, params_for_current
from elec_tool.nilm_tuning import estimate_min_load, longest_transient, measure, suggest


def _pump_seconds() -> np.ndarray:
    rng = np.random.default_rng(7)
    idle = 0.0025 + rng.normal(0, 4e-4, 60)
    ramp_up = np.concatenate([np.linspace(0.024, 0.39, 25), [0.31, 0.33, 0.37, 0.39, 0.40], np.linspace(0.46, 1.57, 16)])
    steady = 1.40 + rng.normal(0, 0.01, 300)
    ramp_down = np.linspace(1.41, 0.005, 45)
    idle2 = 0.0025 + rng.normal(0, 4e-4, 40)
    return np.concatenate([idle, ramp_up, steady, ramp_down, idle2])


@pytest.fixture(scope="module")
def x_rep() -> np.ndarray:
    return np.repeat(_pump_seconds(), 50)        # 每秒 50 个逐位相同的周波


def test_measure_detects_repeated_cycles_and_rescales_sigma(x_rep):
    m = measure(x_rep, "A")
    assert m["repeated_cycles"] is True
    assert m["sigma_method"] == "block"
    assert m["repeat_frac"] > 0.95
    assert m["repeat_run_cycles"] == 50
    assert m["sigma_raw"] < 1e-6                       # 老口径：差分 MAD 落在 0
    assert 0.003 < m["sigma_cycle"] < 0.02             # 新口径：秒间抖动 0.01 A 量级
    assert 0.005 < m["range10_p95"] < 0.06
    assert 0.003 < m["sigma_mean10"] < 0.03


def test_measure_unchanged_for_real_noise():
    rng = np.random.default_rng(3)
    x = 1.4 + rng.normal(0, 0.01, 20000)
    m = measure(x, "A")
    assert m["repeated_cycles"] is False and m["sigma_method"] == "diff_mad"
    assert m["sigma_cycle"] == pytest.approx(m["sigma_raw"])
    assert m["sigma_cycle"] == pytest.approx(0.01, rel=0.1)


def test_longest_transient_sees_whole_ramp(x_rep):
    m = measure(x_rep, "A")
    tr = longest_transient(x_rep, m["sigma_cycle"], 0.7, tol=0.03, run_cycles=m["repeat_run_cycles"])
    assert 1800 <= tr["longest"] <= 2600                 # ≈46 s 斜坡，而不是被切碎成 ~8 s
    assert tr["min_steady_cycles_used"] >= 100
    tr_old = longest_transient(x_rep, m["sigma_cycle"], 0.7, tol=0.03)
    assert tr_old["longest"] < tr["longest"]             # 不折算时斜坡上每段同值周波都成锚点


def test_suggest_params_detect_start_and_stop(x_rep):
    m = measure(x_rep, "A")
    sg = suggest(m, 1.4, x_rep)
    ss = sg["algorithms"]["steady_state"]
    assert ss["max_transient_cycles"] >= 2500 and sg["window_cycles"] >= ss["max_transient_cycles"] + 2 * ss["min_steady_cycles"]
    assert ss["tol_a"] >= 0.02
    lvl = float(np.median(np.abs(x_rep)))
    full = dict(NILM_ALGO_DEFAULTS["steady_state"]); full.update(ss)
    prm = effective_params(params_for_current(full), lvl, sg["rel_tol_pct"], sg["min_delta_pct"])
    steps = detect_steps("steady_state", x_rep, prm)
    deltas = sorted(round(s[3] - s[2], 1) for s in steps)
    assert any(d >= 1.2 for d in deltas) and any(d <= -1.2 for d in deltas)


def test_estimate_min_load_uses_run_cycles(x_rep):
    m = measure(x_rep, "A")
    est = estimate_min_load(x_rep, m["sigma_cycle"], "A", run_cycles=m["repeat_run_cycles"])
    assert est["n_steady"] <= 12                          # 不是每秒一个"台阶"
    assert est["max_step"] == pytest.approx(1.4, abs=0.15)


def test_measure_blocky_with_in_second_jitter(x_rep):
    """v0.83.1：用户实测形态——秒内周波不是逐位相同，而是带 1e-6 量级舍入抖动（只有 35% 逐位相等）。
    同值段压缩法失效（run=1），改用多滞后 σ：σ_1≈4e-7 而 σ_50≈7e-3 ⇒ 判分段恒定、段长 50、σ 取段间跳变尺度。"""
    rng = np.random.default_rng(11)
    j = rng.normal(0, 6e-7, x_rep.size)
    j[rng.random(x_rep.size) < 0.35] = 0.0
    xb = x_rep + j
    m = measure(xb, "A")
    assert m["repeat_frac"] < 0.5                       # 逐位相等比例不足以触发压缩法
    assert m["repeated_cycles"] is True and m["sigma_method"] == "block"
    assert m["repeat_run_cycles"] == 50
    assert m["sigma_raw"] < 2e-6 and 0.003 < m["sigma_cycle"] < 0.02
    assert m["sigma_lags"][1] < 2e-6 and m["sigma_lags"][50] > 0.003
    sg = suggest(m, 1.4, xb)
    ss = sg["algorithms"]["steady_state"]
    assert ss["max_transient_cycles"] >= 2500 and ss["tol_a"] >= 0.02
    lvl = float(np.median(np.abs(xb)))
    full = dict(NILM_ALGO_DEFAULTS["steady_state"]); full.update(ss)
    prm = effective_params(params_for_current(full), lvl, sg["rel_tol_pct"], sg["min_delta_pct"])
    deltas = [round(s[3] - s[2], 1) for s in detect_steps("steady_state", xb, prm)]
    assert any(d >= 1.2 for d in deltas) and any(d <= -1.2 for d in deltas)
    est = estimate_min_load(xb, m["sigma_cycle"], "A", run_cycles=m["repeat_run_cycles"])
    assert est["n_steady"] <= 12
