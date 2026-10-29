"""v0.99.15：① 自适应 min_delta 纳入秒级（Allan）漂移；② 画像候选多尺度搜索兼容慢斜坡停机。"""
import math
import numpy as np

from elec_tool.nilm_auto import window_stats, auto_algo_params
from elec_tool.nilm_profile import detect_profile, event_features, fit_group, FEATURES, TEMPLATE_POINTS


def test_white_noise_min_delta_unchanged():
    rng = np.random.default_rng(3)
    p = 90.0 + rng.normal(0, 0.3, 6000)
    st = window_stats(p, 50.0)
    assert st is not None and 0.7 < st["drift_ratio"] < 1.6
    legacy = max(st["k"] * st["sigma"] * math.sqrt(2.0 / st["min_steady"]) * 1.5, 4 * st["sigma"])
    assert st["min_delta"] <= legacy * 1.6 + 1e-9


def test_slow_drift_raises_min_delta():
    """总线背景：周波级噪声 0.3 A + 秒级漂移（随机游走，1 s 内常 2～6 A）⇒ min_delta 必须显著高于白噪声口径。"""
    rng = np.random.default_rng(5)
    L = 6000
    walk = np.cumsum(rng.normal(0, 0.4, L))               # 每周波 0.4 ⇒ 50 周波 ≈ 2.8 A
    p = 90.0 + walk + rng.normal(0, 0.3, L)
    st = window_stats(p, 50.0)
    assert st is not None
    legacy = max(st["k"] * st["sigma"] * math.sqrt(2.0 / st["min_steady"]) * 1.5, 4 * st["sigma"])
    assert st["drift_ratio"] > 2.0
    assert st["min_delta"] > 2.0 * legacy
    prm = auto_algo_params("steady_state", st)
    assert prm["tol_w"] > 4 * st["sigma"]                 # 稳态容差同样按等效 σ 放大


def _profile_from_steps(step_i, pre_n=10, post_n=50):
    """用一个理想快速停机（全幅 step_i/相）构造最小画像。"""
    L = 600
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L))
    for k, a in enumerate(step_i, start=1):
        i4[k, :300] = a; i4[k, 305:] = 0.3
        p4[k] = 220 * i4[k]
    i4[0] = np.sqrt((i4[1:] ** 2).sum(axis=0)); p4[0] = p4[1:].sum(axis=0)
    f = event_features(p4, q4, i4, 300, 305, pre_n, post_n)
    g = fit_group([{"vec": f["vec"], "template": f["template"]}, {"vec": {k: v * 1.05 for k, v in f["vec"].items()}, "template": f["template"]}])
    return {"quantity": "i", "unit": "A", "pre_cycles": pre_n, "post_cycles": post_n, "shutdown": g, "startup": None}


def _bus_slow_stop(step_i=(34.0, 35.0, 33.0), fast_s=3.0, tail_tau_s=6.0, fs_c=50, L=4000, onset=1500, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(L) / fs_c
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L))
    for k, a in enumerate(step_i, start=1):
        base = 90.0 + rng.normal(0, 0.15, L)
        shape = np.zeros(L)
        tt = t - t[onset]
        fast = np.clip(tt / fast_s, 0, 1) * 0.6                     # 3 s 线性降 60 %
        tail = np.where(tt > fast_s, 0.4 * (1 - np.exp(-(tt - fast_s) / tail_tau_s)), 0.0)
        shape[tt >= 0] = (fast + tail)[tt >= 0]
        i4[k] = base - a * shape
        p4[k] = 220 * i4[k]
    i4[0] = np.sqrt((i4[1:] ** 2).sum(axis=0)); p4[0] = p4[1:].sum(axis=0)
    return p4, q4, i4


def test_single_scale_misses_slow_ramp_multiscale_finds_it():
    prof = _profile_from_steps((37.0, 32.5, 43.6))
    p4, q4, i4 = _bus_slow_stop()
    prm1 = {"max_scale": 1, "k_sigma": 4.0, "d2_max": 1e9, "min_confidence": 0.0, "state_check": 0}
    res1 = detect_profile(p4, q4, i4, prof, prm1, use_p=False)
    prm8 = dict(prm1, max_scale=8)
    res8 = detect_profile(p4, q4, i4, prof, prm8, use_p=False)
    assert len(res1) == 0                                   # 旧单尺度：慢斜坡 1 s 内达不到画像幅值一半 ⇒ 无候选
    assert len(res8) >= 1
    r = res8[0]
    assert r["scale"] > 1 and abs(r["onset"] - 1500) <= 60
    v = r["feat"]["vec"]
    assert v["d_ia"] < -20 and r["match"]["direction"] == "STOP"   # 后窗落在过渡后，ΔIa 接近全幅
    assert r["post_wait"] == 50 * r["scale"]


def test_multiscale_merges_fast_step_into_one_candidate():
    """快速台阶在各尺度都命中，必须合并成 1 个候选（不会重复报）。"""
    prof = _profile_from_steps((37.0, 32.5, 43.6))
    p4, q4, i4 = _bus_slow_stop(fast_s=0.1, tail_tau_s=0.1)
    res = detect_profile(p4, q4, i4, prof, {"max_scale": 8, "k_sigma": 4.0, "d2_max": 1e9, "min_confidence": 0.0, "state_check": 0}, use_p=False)
    assert len(res) == 1 and abs(res[0]["onset"] - 1500) <= 15
