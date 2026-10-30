"""第 167 轮（v0.99.24）：目标设备慢斜坡启动被相邻他负荷"夹住"时仍能成为候选并正确量特征。

实录（海湾化工 bus-启动）：14:59:07 他负荷 +60 A 台阶 → 58 s 后设备 +35 A / 18 s 斜坡启动 → 16 s 后他负荷 −70 A。
画像 pre/post=3000（60 s）：旧版只有 ×1…×8 尺度，三个事件落进同一个 60 s 双滑窗超限游程，只留幅值最大的 +60 A；
且即便成候选，60 s 后窗会吃进 −70 A 台阶。v0.99.24：细尺度（÷2、÷4）找候选 + 相邻变点截断前后窗 + 细尺度候选按画像几何重算终点。"""
import numpy as np
from elec_tool.nilm_profile import detect_profile, event_features, fit_group, change_points, window_bounds


def _profile(pre_n=3000, post_n=3000):
    L = 12000; on = 6000; ramp = 900
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L))
    for k, a in enumerate((36.0, 31.0, 42.0), start=1):
        x = np.full(L, 0.3); x[on:on + ramp] = 0.3 + a * np.arange(ramp) / ramp; x[on + ramp:] = 0.3 + a
        i4[k] = x; p4[k] = -220 * x
    i4[0] = np.sqrt((i4[1:] ** 2).sum(axis=0)); p4[0] = p4[1:].sum(axis=0)
    f = event_features(p4, q4, i4, on, on + 600, pre_n, post_n)
    g = fit_group([{"vec": f["vec"], "template": f["template"]}, {"vec": {k: v * 1.03 for k, v in f["vec"].items()}, "template": f["template"]}])
    return {"quantity": "i", "unit": "A", "pre_cycles": pre_n, "post_cycles": post_n, "startup": g, "shutdown": None}


def _bus(L=20000, seed=1, noise=1.0):
    """背景 60 A；t=6000 他负荷 +60 A；t=8900 设备 +36/31/42 A 斜坡 900 周波；t=10600 他负荷 −70 A。"""
    rng = np.random.default_rng(seed)
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L))
    for k, a in enumerate((36.0, 31.0, 42.0), start=1):
        x = np.full(L, 60.0) + rng.normal(0, noise, L)
        x[6000:] += 60.0
        r = np.arange(900); x[8900:9800] += a * r / 900; x[9800:] += a
        x[10600:] -= 70.0
        i4[k] = x; p4[k] = -220 * x
    i4[0] = np.sqrt((i4[1:] ** 2).sum(axis=0)); p4[0] = p4[1:].sum(axis=0)
    return p4, q4, i4


def test_sandwiched_ramp_start_is_candidate_and_confirmed():
    prof = _profile(); p4, q4, i4 = _bus()
    prm = {"max_scale": 8, "k_sigma": 4.0, "d2_max": 9.0, "min_confidence": 0.3, "state_check": 0}
    res = detect_profile(p4, q4, i4, prof, prm, use_p=False)
    starts = [r for r in res if 8800 <= r["onset"] <= 9400]
    assert starts, [(r["onset"], r["status"]) for r in res]
    r = starts[0]
    assert r["accepted"] and r["match"]["direction"] == "START", (r["status"], r["flags"], r["match"]["contrib"])
    v = r["feat"]["vec"]
    assert 30 < v["d_ia"] < 42 and 36 < v["d_ic"] < 48          # 后窗被 −70 A 变点截断，量到的是设备全幅而不是负值
    assert r["post_hi"] is not None and r["post_hi"] <= 10600
    assert any(s < 1 for s in r["scales_hit"])                   # 由细尺度发现
    # 他负荷的两个台阶必须被拒
    others = [r_ for r_ in res if r_ is not r]
    assert others and all(not r_["accepted"] for r_ in others), [(r_["onset"], r_["status"]) for r_ in others]


def test_old_single_direction_scales_would_miss_it():
    prof = _profile(); p4, q4, i4 = _bus()
    prm = {"max_scale": 8, "min_scale": 1, "k_sigma": 4.0, "d2_max": 9.0, "min_confidence": 0.3, "state_check": 0}
    res = detect_profile(p4, q4, i4, prof, prm, use_p=False)
    assert not any(r["accepted"] and 8800 <= r["onset"] <= 9400 for r in res)


def test_window_bounds_same_sign_within_dur_not_truncating():
    cps = [(100, +5.0), (1300, +5.0), (1700, -8.0)]
    pre_lo, post_hi = window_bounds(cps, 1000, 1100, 500, 2000, delta=+10.0, dur_max=600)
    assert pre_lo == 100 + 100 and post_hi == 1700 - 100        # 同号 1300 在 1.5×dur 内 ⇒ 属自身过渡；反号 1700 截断
    _, post_hi2 = window_bounds(cps, 1000, 1100, 500, 2000, delta=+10.0, dur_max=50)
    assert post_hi2 == 1300 - 100                                # dur 很短 ⇒ 1300 视为他负荷
