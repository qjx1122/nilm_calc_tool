"""第 168 轮（v0.99.25）：画像匹配的前后特征窗被相邻他负荷污染。

实录（海湾化工 bus-启动，2026-10-30 12:08 重跑，output 12:08:18/nilm/nilm_profile_candidates_20261030.csv）：
设备 15:00:05 起的 +35 A / 18 s 斜坡启动确实成了候选（scales_hit=0.25/0.5），但记下来的
特征却是 **ΔIa −39.2 A、ΔP +33502 W、ΔQ −15235 var、dur 1356 周波**——符号与真实启动相反，
被匹配成 STOP（D²/维 544、trajectory_deviates）而拒绝。这组数字正好等于
「14:59:08 他负荷 +60 A 之后的电平」→「15:00:39 他负荷 −70 A 之后的电平」之差：
前窗吃进了前一次投切、后窗跨过了后一次切除。

三处几何缺陷（都在 elec_tool/nilm_profile.py）：
  1. `_two_window_candidates` 的超限游程只看 |Δ|，先发生的启动与紧随其后的反号切除连成一段，
     只留幅值大的那个（启动被吞掉）；
  2. 多尺度合并 `abs(delta) > abs(hit["delta"])` 让粗尺度（后窗更长、已经吃进下一个反号事件）的幅值
     覆盖细尺度——候选的 Δ 符号被邻居带反；
  3. `window_bounds` 的同号豁免没有幅值上限，且后窗边界以 end 为基准；end 一旦被污染的中位数拉走，
     边界跟着失效，于是前后窗整个跨过他负荷。
本文件把三种情形钉住。"""
import numpy as np
import pytest

import elec_tool.nilm_profile as NP
from elec_tool.nilm_profile import detect_profile, event_features, fit_group, window_bounds


def _profile(pre_n=3000, post_n=3000, on=6000, ramp=600):
    L = 12000
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L))
    for k, a in enumerate((36.0, 31.0, 42.0), start=1):
        x = np.full(L, 0.3); x[on:on + ramp] = 0.3 + a * np.arange(ramp) / ramp; x[on + ramp:] = 0.3 + a
        i4[k] = x; p4[k] = -220 * x
    i4[0] = np.sqrt((i4[1:] ** 2).sum(axis=0)); p4[0] = p4[1:].sum(axis=0)
    f = event_features(p4, q4, i4, on, on + 600, pre_n, post_n)
    g = fit_group([{"vec": f["vec"], "template": f["template"]},
                   {"vec": {k: v * 1.03 for k, v in f["vec"].items()}, "template": f["template"]}])
    return {"quantity": "i", "unit": "A", "pre_cycles": pre_n, "post_cycles": post_n, "startup": g, "shutdown": None}


def _bus(ramp=600, r_on=8900, drop=9600, L=24000, seed=1, noise=1.0):
    """背景 60 A；6000 他负荷 +60 A；8900 设备 +36/31/42 A 斜坡 ramp 周波；drop 他负荷 −70 A。"""
    rng = np.random.default_rng(seed)
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L))
    for k, a in enumerate((36.0, 31.0, 42.0), start=1):
        x = np.full(L, 60.0) + rng.normal(0, noise, L)
        x[6000:] += 60.0
        x[r_on:r_on + ramp] += a * np.arange(ramp) / ramp
        x[r_on + ramp:] += a
        x[drop:] -= 70.0
        i4[k] = x; p4[k] = -220 * x
    i4[0] = np.sqrt((i4[1:] ** 2).sum(axis=0)); p4[0] = p4[1:].sum(axis=0)
    return p4, q4, i4


PRM = {"max_scale": 8, "k_sigma": 4.0, "d2_max": 9.0, "min_confidence": 0.3, "state_check": 0}


def test_opposite_sign_neighbour_does_not_flip_candidate_delta():
    """设备斜坡 2 s 后被 −70 A 切除：候选的 Δ 必须仍是正的启动方向（旧版被邻居带成 −91）。"""
    prof = _profile()
    p4, q4, i4 = _bus(drop=8900 + 600 + 100)
    res = detect_profile(p4, q4, i4, prof, PRM, use_p=False)
    ramp = [r for r in res if 8850 <= r["onset"] <= 8950]
    assert ramp, [(r["onset"], r["status"]) for r in res]
    r = ramp[0]
    assert r["delta"] > 0, r["delta"]
    assert r["feat"]["vec"]["d_ia"] > 0, r["feat"]["vec"]     # 量出来的 ΔI 也是启动方向
    assert r["post_hi"] is not None and r["post_hi"] <= 9600   # 后窗被 −70 A 变点截断


def test_same_sign_but_much_larger_step_is_not_own_transition():
    """同号但幅值远超候选自身过渡（−70 A 对 −35 A）⇒ 他负荷，必须截断。"""
    cps = [(1000, +5.0), (1500, -70.0)]
    _pre, post_hi = window_bounds(cps, 1000, 1200, 500, 3000, delta=-35.0, dur_max=1271, peak_max=1.6)
    assert post_hi == 1500 - max(10, min(150, 3000 // 20))     # 截断到反号大台阶之前
    # 幅值 ≤1.5|Δ| 的同号台阶（分级启动）仍视为自身过渡
    cps2 = [(1000, +5.0), (1500, -45.0)]
    _p2, post_hi2 = window_bounds(cps2, 1000, 1200, 500, 3000, delta=-35.0, dur_max=1271, peak_max=1.6)
    assert post_hi2 is None


def test_sign_flip_rejects_instead_of_confident_stop(monkeypatch):
    """万一窗几何还是被带偏：量出的 Δ 与搜索 Δ 反号 ⇒ 记 sign_flip 并拒绝，不许报成高置信 STOP。"""
    prof = _profile()
    p4, q4, i4 = _bus(drop=8900 + 600 + 100)
    monkeypatch.setattr(NP, "window_bounds", lambda *a, **k: (None, None))   # 强制不截断＝旧版最坏情形
    res = detect_profile(p4, q4, i4, prof, PRM, use_p=False)
    ramp = [r for r in res if 8850 <= r["onset"] <= 8950]
    assert ramp
    r = ramp[0]
    assert "sign_flip" in r["flags"], r["flags"]
    assert not r["accepted"] and r["status"] == "rejected", (r["status"], r["flags"])
