"""v0.99.27（第 174 轮）：`quantity='i'` 下**纯无功阶跃**（电容组投切 / SVG 动作）要参与"相邻变点截断"。

背景（第 172 轮实录）：总线侧播 `bus-2-启停.csv`，12:41:15 有一次 45 kW 负荷投入，前后还夹着电容组投切。
候选的 ΔQ 在干净窗里是 −0.33 kvar，实际取到 **−25.8 kvar** ⇒ 画像的 d_q（+902 var ± 225）彻底对不上。
根因：候选搜索与 `change_points` 都只看合成电流（I 口径）或有功（P 口径），**纯无功阶跃在那两条序列上看不见**，
于是它既不成候选、也不成"别的变化"，候选的后窗把它整个吃进去。

修法（v0.99.27）：`detect_profile` 额外在 **Q 序列**上找变点，只用于截断前后窗、不产生候选；Q 序列没有变化时跳过。

覆盖：
- 有 Q 变点时，候选的 ΔQ 取干净段（+902 var），匹配通过；
- 退回旧行为（只有主序列变点）时，ΔQ 被 −25 kvar 污染 ⇒ D² 爆表被拒（证明这处修复是必需的）；
- 画像有无功份额时，纯无功阶跃**自己也出候选**（source='q'，用户说的"成为变点"）；纯电阻设备则只当变点、不造候选；
- Q 恒零时新旧行为一致（不会因 thr=0 退化成"处处是变点"）。
"""
from __future__ import annotations

import numpy as np
import pytest

import elec_tool.nilm_profile as NP
from elec_tool.nilm_profile import FEATURES, detect_profile, fit_group

L = 1000
ONSET = 400          # 设备启动
CAP = ONSET + 20     # 电容组投切（纯无功，紧跟设备启动 20 周波）
PRE, POST = 10, 50

PRM = {"d2_max": 9.0, "min_confidence": 0.3, "k_sigma": 4.0, "margin": 1.0, "lambda_rel": 0.1,
       "state_check": 0, "phase_map": 1, "max_scale": 1, "min_scale": 1}     # 关闭状态机与多尺度，只看几何/特征


def _profile(dp=866.0, di=5.0, dq=902.0, n=3):
    """画像：启动时 +5 A/相、+866 W、+902 var、无谐波；停止对称。"""
    up = fit_group([{"vec": {"d_ia": di, "d_ib": di, "d_ic": di, "d_p": dp, "d_q": dq, "peak_ratio": 1.0,
                             "dur_cycles": 2.0, "d_ih": 0.0}, "template": [1.0] * 16,
                    "t_start": 1.7e9 + k, "onset": k * 100, "end": k * 100 + 2} for k in range(n)])
    dn = fit_group([{"vec": {"d_ia": -di, "d_ib": -di, "d_ic": -di, "d_p": -dp, "d_q": -dq, "peak_ratio": 1.0,
                             "dur_cycles": 2.0, "d_ih": 0.0}, "template": [1.0] * 16,
                    "t_start": 1.7e9 + k, "onset": k * 100, "end": k * 100 + 2} for k in range(n)])
    return {"schema": "nilm_profile/1", "device_id": "RC", "version": "1.0", "quantity": "i", "unit": "A",
            "features": list(FEATURES), "pre_cycles": PRE, "post_cycles": POST, "startup": up, "shutdown": dn, "notes": []}


def _series(with_cap=True, flat_q=False, device=True):
    """p4/q4/i4：基荷 100 A/相；device=True 时 ONSET 起 +5 A/相、+866 W、+902 var；with_cap 时 CAP 起 −25 kvar（只有 Q）。"""
    p = np.full((4, L), 10000.0)
    q = np.full((4, L), 5000.0)
    i = np.full((4, L), 100.0)
    if device:
        p[0, ONSET:] += 866.0
        q[0, ONSET:] += 902.0
        for k in (1, 2, 3):
            i[k, ONSET:] += 5.0
        i[0, ONSET:] = np.sqrt(np.sum(i[1:, ONSET:] ** 2, axis=0))
    if flat_q:
        q[:] = 0.0
    elif with_cap:
        q[0, CAP:] -= 25000.0
    return p, q, i


def _deltas(p, q, i, prof):
    res = detect_profile(p, q, i, prof, PRM, False, "unknown", (), None)
    return res


def test_candidates_are_tagged_with_source():
    """每个候选都带 `source`（x＝检测量序列 / q＝无功序列），界面与候选诊断 CSV 都靠它区分。"""
    p, q, i = _series(device=False)
    res = _deltas(p, q, i, _profile())
    assert res and all(r["source"] in ("x", "q") for r in res)


def test_reactive_step_truncates_post_window_and_feature_stays_clean():
    """有 Q 变点 ⇒ 后窗在电容投切前截断，ΔQ 取到干净值 +902 var，候选被接受。"""
    p, q, i = _series()
    res = _deltas(p, q, i, _profile())
    hits = [r for r in res if abs(r["onset"] - ONSET) <= 3]
    assert hits, [(r["onset"], r["match"]["direction"], round(r["confidence"], 3)) for r in res]
    r = hits[0]
    assert r["feat"]["vec"]["d_q"] == pytest.approx(902.0, abs=60.0), r["feat"]["vec"]
    assert r["accepted"] and r["match"]["direction"] == "START", (r["status"], r["flags"], round(r["confidence"], 3))


def test_without_q_change_points_the_feature_is_polluted(monkeypatch):
    """退回 v0.99.26（只在主序列上找变点）⇒ 后窗吃进 −25 kvar，ΔQ 差 2.4 万，D² 爆表被拒。"""
    p, q, i = _series()
    r_new = [r for r in _deltas(p, q, i, _profile()) if abs(r["onset"] - ONSET) <= 3][0]
    assert r_new["feat"]["vec"]["d_q"] == pytest.approx(902.0, abs=60.0) and r_new["accepted"]

    real = NP.change_points
    # Q 序列的量级（上万 var）与电流序列（百 A）差两个数量级：按幅值把 Q 上的调用屏蔽掉 ＝ v0.99.26 的行为
    monkeypatch.setattr(NP, "change_points",
                        lambda x, pre_n, post_n, min_d, k_sig: [] if float(np.max(np.abs(x))) > 1e4
                        else real(x, pre_n, post_n, min_d, k_sig))
    r_old = [r for r in _deltas(p, q, i, _profile()) if abs(r["onset"] - ONSET) <= 3][0]
    assert r_old["feat"]["vec"]["d_q"] < -20000.0                      # 被电容投切污染
    assert not r_old["accepted"] and "d2_exceeds" in r_old["flags"]


def test_pure_reactive_step_becomes_candidate_for_reactive_profile():
    """纯无功阶跃 + 不动的 I/P：画像有无功份额（|ΔQ|/√(ΔP²+ΔQ²)≈0.72）⇒ 在 Q 序列上也出一个候选（source='q'）。

    这条就是用户说的「纯无功阶跃仍不是变点」：v0.99.26 它在 I 口径下既不成候选也不成变点。候选本身仍要过
    匹配（这里 ΔQ 是 −25 kvar、画像 +902 var ⇒ d2_exceeds 被拒），但**候选诊断里能看到它**、窗口也被它截断。
    """
    p, q, i = _series(device=False)
    res = _deltas(p, q, i, _profile())
    hit = [r for r in res if abs(r["onset"] - CAP) <= 5]
    assert hit and hit[0]["source"] == "q", [(r["onset"], r["source"]) for r in res]
    assert hit[0]["feat"]["vec"]["d_q"] == pytest.approx(-25000.0, abs=100.0)
    assert not hit[0]["accepted"] and "d2_exceeds" in hit[0]["flags"]      # 幅值对不上，靠匹配把关


def test_resistive_profile_does_not_make_candidates_from_reactive_step():
    """纯电阻设备（ΔQ≈0、无功份额 <10 %）⇒ 电容投切不造候选，只当变点截断，避免"任何投切都像它启停"。"""
    p, q, i = _series(device=False)
    prof = _profile(dq=0.0)                      # 画像 ΔQ=0 ⇒ 份额 0
    res = _deltas(p, q, i, prof)
    assert [r for r in res if abs(r["onset"] - CAP) <= 5] == []
    assert all(r["source"] == "x" for r in res)


def test_flat_q_behaves_like_before():
    """Q 恒零（纯有功设备 / 无 Q 数据）⇒ 跳过 Q 变点，结果与旧行为一致，候选照常检出。"""
    p, q, i = _series(with_cap=False, flat_q=True)
    res = _deltas(p, q, i, _profile())
    hits = [r for r in res if abs(r["onset"] - ONSET) <= 3]
    assert hits and hits[0]["accepted"], [(r["onset"], r["status"], r["flags"]) for r in res]
    assert hits[0]["feat"]["vec"]["d_q"] == 0.0          # Q 序列恒零 ⇒ 没有 Q 变点、ΔQ 如实取 0（不报错、也不误截断）
    assert not any(c in hits[0]["flags"] for c in ("d2_exceeds", "ambiguous_direction"))


def test_q_change_point_is_not_used_when_delta_is_within_own_transient():
    """电容投切落在候选自身过渡窗内（onsets 很近）⇒ 视为同一次动作，不截断（避免把长斜坡的尾巴切掉）。"""
    p, q, i = _series()
    q2 = q.copy()
    q2[0, CAP:] = 5000.0 + 902.0                       # 把投切撤掉，只留设备的无功
    res2 = _deltas(p, q2, i, _profile())
    r2 = [r for r in res2 if abs(r["onset"] - ONSET) <= 3]
    assert r2 and r2[0]["accepted"]
