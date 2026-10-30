"""v0.99.26（第 173 轮）：画像两项改进——① 谐波电流特征 d_ih；② 多画像同时加载。

覆盖
- ``CycleFeatures.push`` 新增逐周波谐波电流 ``ih``（2~13 次合量），解析解校验；
- ``event_features`` 的 ΔIh（后窗−前窗）与缺省行为（不给 ih4 时为 0，旧调用方不受影响）；
- 画像第 8 维 d_ih：提取（fit_group）→ 存盘 → 加载 → 匹配，全链路维度一致；
- **旧画像向后兼容**：v0.99.25 及更早的 7 维画像照旧加载、匹配时缺的 d_ih 自动跳过，
  头部 features 被写成 8 项而 μ/σ 仍为 7 项的"半新不旧"文件也能加载（按 7 维解释）；
- **多画像**：``nilm.profile_path`` 用 ``;`` 分隔 / ``nilm.profile_paths`` 列表，各自独立状态机、
  独立去重、独立设备判定；``summary()["profile"]["profiles"]`` 逐画像明细，旧字段仍指向第一个；
  候选诊断 CSV 带 ``device_id`` 与 ``d_ih`` 列。
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, ConfigError
from elec_tool.nilm import HARM_ORDERS, CycleFeatures, NilmDetector, NilmWriter
from elec_tool.nilm_profile import (FEATURES, LEGACY_FEATURES, event_features, fit_group, load_profile, mahalanobis_diag,
                                    match_event, profile_feature_names, profile_summary, save_profile)

FS, F = 6400.0, 50.0
N = int(FS / F)                      # 128 点/周波
U = 57.74                            # 相电压有效值


# ---------------------------------------------------------------- 工具
def _cycle_block(amps_rms, orders=(), t0=1.79e9, cycles=8, phase_shift=0.0):
    """生成 ``cycles`` 个周波的三相波形：基波有效值 ``amps_rms``（3 相）、叠加 ``orders``＝[(次数, 有效值)]。"""
    n = cycles * N
    t = np.arange(n) / FS
    w = 2 * np.pi * F * t
    u = np.zeros((3, n)); i = np.zeros((3, n))
    for k, ph in enumerate((0.0, -2 * np.pi / 3, 2 * np.pi / 3)):
        u[k] = U * math.sqrt(2) * np.sin(w + ph)
        sig = amps_rms[k] * math.sqrt(2) * np.sin(w + ph + phase_shift)
        for order, rms in orders:
            sig = sig + rms * math.sqrt(2) * np.sin(order * w + ph * order)
        i[k] = sig
    return SampleBlock(t=t0 + t, u=u, i=i)


def _ramp_series(dur_s, prof_s, blocks_per_s=5):
    """按时间生成 (p4, q4, i4, ih4) 序列：``prof_s(t)`` 返回 (每相电流 A, 有功 W, 无功 var, 谐波电流 A)。"""
    feat = CycleFeatures(FS, F)
    ps, qs, is_, hs, ts = [], [], [], [], []
    m = int(FS / blocks_per_s)
    n = int(dur_s * FS)
    for a in range(0, n - n % m, m):
        ia, p, q, ih = prof_s(a / FS)
        d = CycleFeatures(FS, F)
        d.__dict__.update(feat.__dict__)          # 复用同一周波相位（避免跨块结转丢点）
        blk = _cycle_block((ia, ia, ia), (), t0=1.79e9 + a / FS, cycles=max(1, m // N))
        f = d.push(blk)
        if f["t"].size:
            ts.append(f["t"]); ps.append(f["p"]); qs.append(f["q"]); is_.append(f["i"])
            hs.append(np.vstack([np.full(f["t"].size, ih), np.full((3, f["t"].size), ih)]))   # total＝三相平均
    cat = lambda xs, ax: np.concatenate(xs, axis=ax)      # noqa: E731
    return cat(ts, 0), cat(ps, 1), cat(qs, 1), cat(is_, 1), cat(hs, 1)


# ---------------------------------------------------------------- ① 谐波电流
def test_cycle_features_harmonic_current_analytic():
    """5 次谐波 1.5 A 有效值 + 7 次 0.8 A ⇒ ih(total) = √(1.5²+0.8²) ≈ 1.70 A，各相相同。"""
    cf = CycleFeatures(FS, F)
    f = cf.push(_cycle_block((10.0, 10.0, 10.0), ((5, 1.5), (7, 0.8)), cycles=8))
    assert "ih" in f and f["ih"].shape == (4, f["t"].size)
    expect_ph = math.sqrt(1.5 ** 2 + 0.8 ** 2)
    assert np.allclose(f["ih"][1:], expect_ph, rtol=0.02)
    assert np.allclose(f["ih"][0], expect_ph, rtol=0.02)                     # total＝三相平均（可加）
    # 纯正弦（无谐波）⇒ ih≈0
    g = CycleFeatures(FS, F).push(_cycle_block((10.0, 10.0, 10.0), cycles=8))
    assert np.allclose(g["ih"], 0.0, atol=0.05)


def test_cycle_features_harmonic_orders_cover_2_to_13():
    assert tuple(HARM_ORDERS) == (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
    cf = CycleFeatures(FS, F)
    assert cf.harm_orders == HARM_ORDERS and cf._kmax <= N // 2 - 1
    off = CycleFeatures(FS, F, harmonics=False)
    assert off.harm_orders == () and np.allclose(off.push(_cycle_block((5.0, 5.0, 5.0)))[ "ih"], 0.0)


def _synthetic(dur_s=4.0, step=(2.0, 20.0), pre=10, post=40):
    """t<step[0] 时谐波电流为 0，之后为 ``step[1]`` A；其余量恒定 ⇒ 用于检验 ΔIh 的口径。"""
    t, p4, q4, i4, ih4 = _ramp_series(dur_s, lambda s: (5.0, 1500.0, 0.0, 0.0 if s < step[0] else step[1]))
    on = int(np.searchsorted(t, t[0] + step[0]))
    return t, p4, q4, i4, ih4, on


def test_event_features_harmonic_delta():
    t, p4, q4, i4, ih4, on = _synthetic()
    f = event_features(p4, q4, i4, on, on + 2, 10, 40, ih4=ih4)
    assert f["vec"]["d_ih"] == pytest.approx(20.0, abs=1.5)          # 后窗 20 A − 前窗 0 A
    assert f["d_ih"] == pytest.approx(20.0, abs=1.5)
    assert f["vec"]["d_p"] == pytest.approx(0.0, abs=50.0)            # 有功没变
    # 不给 ih4：d_ih＝0（旧调用方 / 旧测试不受影响）
    g = event_features(p4, q4, i4, on, on + 2, 10, 40)
    assert g["vec"]["d_ih"] == 0.0 and "d_ih" in g["vec"]


def test_event_features_harmonic_wrong_length_is_ignored():
    t, p4, q4, i4, ih4, on = _synthetic()
    f = event_features(p4, q4, i4, on, on + 2, 10, 40, ih4=ih4[:, :-5])
    assert f["vec"]["d_ih"] == 0.0                                     # 长度不匹配 ⇒ 按"没有谐波数据"处理


def test_thd_delta_reports_relative_harmonic_increment():
    # 只有谐波变、基波不变：不报增量 THD（分母为 0 时不产生 inf）
    t, p4, q4, i4, ih4, on = _synthetic(step=(2.0, 20.0))
    f = event_features(p4, q4, i4, on, on + 2, 10, 40, ih4=ih4)
    assert abs(f["d_it"]) < 1e-9 and f["thd_delta"] == 0.0
    # 基波与谐波同时变：增量 THD＝ΔIh/|ΔI合成|
    t2, p4b, q4b, i4b, ih4b = _ramp_series(4.0, lambda x: (5.0 if x < 2.0 else 8.0, 1500.0, 0.0, 0.0 if x < 2.0 else 20.0))
    onb = int(np.searchsorted(t2, t2[0] + 2.0))
    g = event_features(p4b, q4b, i4b, onb, onb + 2, 10, 40, ih4=ih4b)
    assert abs(g["d_ih"]) > 10.0 and abs(g["d_it"]) > 1.0
    assert g["thd_delta"] == pytest.approx(g["d_ih"] / abs(g["d_it"]), rel=1e-6)


# ---------------------------------------------------------------- ② 画像第 8 维
def _two_samples(dev_p, dev_i, dur=100.0, d_ih=15.0, n=3):
    out = []
    for k in range(n):
        out.append({"vec": {"d_ia": dev_i, "d_ib": dev_i * 0.9, "d_ic": dev_i * 1.15, "d_p": dev_p, "d_q": 0.0,
                            "peak_ratio": 1.05, "dur_cycles": dur, "d_ih": d_ih},
                    "template": [1.0] * 16, "t_start": 1.7e9 + k, "onset": k * 1000, "end": k * 1000 + 100})
    return out


def test_fit_group_produces_eight_dimensions_with_harmonic():
    g = fit_group(_two_samples(-24000.0, 36.0))
    assert len(g["mu"]) == len(FEATURES) == 8 and FEATURES[-1] == "d_ih"
    assert g["mu"][-1] == pytest.approx(15.0)
    assert g["sigma"][-1] >= 2.0                       # 绝对下限 2 A


def test_profile_roundtrip_keeps_harmonic_dimension(tmp_path):
    doc = {"schema": "nilm_profile/1", "device_id": "devA", "version": "1.0", "quantity": "p", "unit": "W",
           "features": list(FEATURES), "pre_cycles": 10, "post_cycles": 50,
           "startup": fit_group(_two_samples(-24000.0, 36.0)), "shutdown": fit_group(_two_samples(24000.0, 36.0))}
    p = str(tmp_path / "p8.json")
    save_profile(doc, p)
    back = load_profile(p)
    assert profile_feature_names(back) == FEATURES
    summ = profile_summary(back)
    assert summ["has_harmonic"] is True and summ["features"][-1] == "d_ih"
    assert summ["startup"]["mu"]["d_ih"] == pytest.approx(15.0)     # 界面 / summary 里也看得到


def test_legacy_seven_dim_profile_loads_and_skips_harmonic(tmp_path):
    """v0.99.25 及更早的 7 维画像：照旧加载，匹配时 d_ih 不参与（等价于该维不提供证据）。"""
    g = fit_group(_two_samples(-24000.0, 36.0))
    g7 = {"n": g["n"], "mu": g["mu"][:7], "sigma": g["sigma"][:7], "template": g["template"],
          "template_spread": g["template_spread"], "dur_cycles": g["dur_cycles"]}
    doc = {"schema": "nilm_profile/1", "device_id": "old", "version": "1.0", "quantity": "p", "unit": "W",
           "features": list(LEGACY_FEATURES), "pre_cycles": 10, "post_cycles": 50,
           "startup": g7, "shutdown": dict(g7, mu=[-v for v in g7["mu"]])}
    p = str(tmp_path / "p7.json")
    save_profile(doc, p)
    back = load_profile(p)
    assert profile_feature_names(back) == LEGACY_FEATURES
    feat = {"vec": dict(g["mu"] and dict(zip(FEATURES, g["mu"]))), "template": [1.0] * 16, "d_it": 36.0}
    feat["vec"]["d_ih"] = 999.0                        # 旧画像没有这一维：无论多大都不影响
    m = match_event(back, feat)
    assert m["direction"] == "START" and "d_ih" not in m["contrib"]
    d2, contrib = mahalanobis_diag(feat["vec"], back["startup"]["mu"], back["startup"]["sigma"], 0.1, (), LEGACY_FEATURES)
    assert len(contrib) == 7 and d2 == pytest.approx(m["d2_start"], rel=1e-9)


def test_declared_features_newer_than_values_falls_back_to_value_length(tmp_path):
    """头部 features 写成 8 项、μ/σ 仍是 7 项的旧文件（曾被新版本改写头部的场景）按 7 维解释，不报错。"""
    g = fit_group(_two_samples(-24000.0, 36.0))
    g7 = {"n": g["n"], "mu": g["mu"][:7], "sigma": g["sigma"][:7], "template": g["template"],
          "template_spread": g["template_spread"], "dur_cycles": g["dur_cycles"]}
    doc = {"schema": "nilm_profile/1", "device_id": "old", "quantity": "p", "unit": "W", "features": list(FEATURES),
           "pre_cycles": 10, "post_cycles": 50, "startup": g7, "shutdown": dict(g7, mu=[-v for v in g7["mu"]])}
    p = str(tmp_path / "p77.json")
    save_profile(doc, p)
    assert profile_feature_names(load_profile(p)) == LEGACY_FEATURES


def test_unknown_feature_names_are_rejected(tmp_path):
    doc = {"schema": "nilm_profile/1", "features": ["d_ia", "d_ib", "d_ic", "d_p", "d_q", "peak_ratio", "bogus"],
           "startup": {"n": 2, "mu": [1.0] * 7, "sigma": [1.0] * 7, "template": [1.0] * 16}}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from elec_tool.nilm_profile import ProfileError
    with pytest.raises(ProfileError):
        load_profile(str(p))


def test_harmonic_dimension_separates_linear_from_rectifier_load():
    """同幅值、同有功、同 ΔQ 的线性负荷（ΔIh≈0）与整流设备（ΔIh≈15 A）：

    去掉谐波维时两者的 7 维特征完全一样（D²=0、置信度 1.0，必然误报）；加上 d_ih 后，
    线性负荷的全部差异都记在谐波维上，D²≈29 ⇒ 置信度 exp(−D²/2d)=0.16 < min_confidence 0.3 ⇒ 拒识。
    """
    g = fit_group(_two_samples(-24000.0, 36.0, d_ih=15.0))
    doc = {"features": list(FEATURES), "startup": g, "shutdown": None}
    base = {"d_ia": 36.0, "d_ib": 32.4, "d_ic": 41.4, "d_p": -24000.0, "d_q": 0.0, "peak_ratio": 1.05, "dur_cycles": 100.0}
    rect = dict(base, d_ih=15.0); linear = dict(base, d_ih=0.0)
    m_rect = match_event(doc, {"vec": rect, "template": [1.0] * 16, "d_it": 36.0})
    m_lin = match_event(doc, {"vec": linear, "template": [1.0] * 16, "d_it": 36.0})
    assert m_rect["d2"] < 1e-6 and m_rect["confidence"] > 0.99          # 真设备：完全命中
    assert m_lin["contrib"]["d_ih"] == pytest.approx(m_lin["d2"], rel=1e-9)   # 差异 100% 记在谐波维
    assert m_lin["d2"] > 20.0 and m_lin["confidence"] < 0.3             # 低于默认 min_confidence ⇒ 拒识
    # 对照：把谐波维从画像里去掉（等价于 v0.99.25 的 7 维画像）⇒ 线性负荷被完全接受（这就是加维度的收益）
    doc7 = {"features": list(LEGACY_FEATURES), "startup": dict(g, mu=g["mu"][:7], sigma=g["sigma"][:7]), "shutdown": None}
    m7 = match_event(doc7, {"vec": linear, "template": [1.0] * 16, "d_it": 36.0})
    assert m7["d2"] < 1e-6 and m7["confidence"] > 0.99


# ---------------------------------------------------------------- ③ 多画像
def _write_pair(tmp_path):
    """两个设备画像：A(ΔP −1000 W, ΔI 5.774 A/相, ΔIh 0)、B(ΔP −3000 W, ΔI 17.32 A/相, ΔIh 12 A)。"""
    out = []
    for name, dp, di, ih in (("A", 1000.0, 1000.0 / (3 * U), 0.0), ("B", 3000.0, 3000.0 / (3 * U), 12.0)):
        up = fit_group([{"vec": {"d_ia": di, "d_ib": di, "d_ic": di, "d_p": dp, "d_q": 0.0, "peak_ratio": 1.0,
                                 "dur_cycles": 2.0, "d_ih": ih}, "template": [1.0] * 16,
                           "t_start": 1.7e9 + k, "onset": k * 100, "end": k * 100 + 2} for k in range(3)])
        dn = fit_group([{"vec": {"d_ia": -di, "d_ib": -di, "d_ic": -di, "d_p": -dp, "d_q": 0.0, "peak_ratio": 1.0,
                                 "dur_cycles": 2.0, "d_ih": -ih}, "template": [1.0] * 16,
                           "t_start": 1.7e9 + k, "onset": k * 100, "end": k * 100 + 2} for k in range(3)])
        doc = {"schema": "nilm_profile/1", "device_id": name, "version": "1.0", "quantity": "p", "unit": "W",
               "features": list(FEATURES), "pre_cycles": 10, "post_cycles": 40,
               "startup": up, "shutdown": dn, "notes": []}
        p = str(tmp_path / f"p{name}.json")
        save_profile(doc, p)
        out.append(p)
    return out


def _cfg_with(profiles, **kw):
    cfg = AppConfig()
    cfg.source.kind = "csv_file"; cfg.source.path = "x"
    cfg.nilm.quantity = "p"
    cfg.nilm.channels = ["total"]
    cfg.nilm.window_cycles = 300
    cfg.nilm.eval_every_cycles = 5
    cfg.nilm.save = False
    cfg.nilm.algorithms["profile"].update({"enabled": True, "max_scale": 1, "min_scale": 1, "k_sigma": 4.0,
                                           "d2_max": 9.0, "min_confidence": 0.3, "margin": 1.0})
    if isinstance(profiles, str):
        cfg.nilm.profile_path = profiles
    else:
        cfg.nilm.profile_paths = list(profiles)
    cfg.validate()
    return cfg


def _power_block(p_w, t0, ih=0.0):
    """每相电流由有功推得（pf=1）⇒ ΔP 与 ΔI 严格同比例；``ih``＝叠加的 5 次谐波电流（A/相）。"""
    ia = p_w / (3 * U)
    return _cycle_block((ia, ia, ia), ((5, ih),) if ih else (), t0=t0, cycles=3)


def _run(cfg, steps, dur_s=8.0):
    """steps＝[(t_switch, 新增有功 W[, 新增谐波电流 A/相])]（阶跃，不累积）；返回 (events, detector)。"""
    det = NilmDetector(cfg)
    nb = int(dur_s * FS / 640)
    out = []
    for b in range(nb):
        t = b * 640 / FS
        on = [(dp, ih) for st in steps for (ts, dp, ih) in [(tuple(st) + (0.0,))[:3]] if t >= ts]
        p = 500.0 + sum(dp for dp, _ in on)
        h = sum(ih for _, ih in on)
        out += det.ingest(_power_block(p, 1.79e9 + t, h))
    return out, det


def test_config_accepts_semicolon_and_list_paths(tmp_path):
    a, b = _write_pair(tmp_path)
    cfg = _cfg_with(f"{a};{b}")
    assert cfg.nilm.profile_path_list() == [a, b]
    assert _cfg_with([a, b]).nilm.profile_path_list() == [a, b]
    mixed = _cfg_with([a]); mixed.nilm.profile_path = f"{b};{a}"
    assert mixed.nilm.profile_path_list() == [b, a]          # 去重保序
    d = _cfg_with([a]); d.nilm.profile_path = f"{a};{a}"
    assert d.nilm.profile_path_list() == [a]


def test_config_rejects_more_than_eight_profiles(tmp_path):
    a, _ = _write_pair(tmp_path)
    cfg = AppConfig(); cfg.nilm.profile_paths = [f"{a}#{k}" for k in range(9)]
    with pytest.raises(ConfigError):
        cfg.validate()


def test_multi_profile_independent_state_and_device_id(tmp_path):
    a, b = _write_pair(tmp_path)
    cfg = _cfg_with(f"{a};{b}")
    evs, det = _run(cfg, [(1.0, 1000.0, 0.0), (4.0, 3000.0, 12.0)])
    prof = [e for e in evs if e["algorithm"] == "profile"]
    ids = [e["device_id"] for e in prof]
    assert ids == ["A", "B"], [(e["device_id"], e["profile_direction"], round(e["confidence"], 3)) for e in prof]
    assert [e["profile_direction"] for e in prof] == ["START", "START"]
    assert [round(e["delta_p_w"]) for e in prof] == [1000, 3000]      # 各自只报自己的幅值，不串味
    summ = det.summary()
    assert len(summ["profiles"]) == 2 and summ["profile"]["count"] == 2
    states = {d["device_id"]: d["device_state"] for d in summ["profiles"]}
    assert states == {"A": "on", "B": "on"}                  # B 的动作没有被记到 A 头上
    assert summ["profile"]["device_state"] == "on"           # 旧字段＝第一个画像
    assert summ["profiles"][0]["candidates"] >= 1


def test_multi_profile_one_bad_file_does_not_kill_the_other(tmp_path):
    a, _ = _write_pair(tmp_path)
    cfg = _cfg_with(f"{a};{tmp_path / 'missing.json'}")
    evs, det = _run(cfg, [(1.0, 1000.0)], dur_s=6.0)
    prof = [e for e in evs if e["algorithm"] == "profile"]
    assert [e["device_id"] for e in prof] == ["A"]
    summ = det.summary()
    assert summ["profiles"][0]["loaded"] and not summ["profiles"][1]["loaded"]
    assert "画像文件不存在" in summ["profiles"][1]["error"]
    assert summ["profile"]["loaded_count"] == 1


def test_single_profile_backward_compatible_fields(tmp_path):
    a, _ = _write_pair(tmp_path)
    cfg = _cfg_with(a)
    evs, det = _run(cfg, [(1.0, 1000.0)], dur_s=6.0)
    assert [e["device_id"] for e in evs if e["algorithm"] == "profile"] == ["A"]
    assert det.device_state == "on" and det._profile is not None and det.profile_hist
    assert isinstance(det._profile_err, str) and det._profile_err == ""
    s = det.summary()["profile"]
    assert s["path"] == a and s["loaded"] and s["summary"]["device_id"] == "A"


def test_candidate_csv_has_device_id_and_harmonic_columns(tmp_path):
    from elec_tool.config import NilmConfig
    import csv as _csv
    nc = NilmConfig(nilm_dir="nilm"); nc.save = True
    w = NilmWriter(nc, root=str(tmp_path))
    w.write_profile_candidate({"t_start": 1.79e9, "t_start_local": "x", "g_on": 12, "device_id": "devA", "direction": "START",
                               "status": "rejected", "flags": ["d2_exceeds"], "scale": 0.25, "scales_hit": [0.25, 1],
                               "confidence": 0.01, "d2": 100.0, "d2_per_dim": 14.3, "margin": 1.1,
                               "vec": {"d_ia": 60.0, "d_p": -44000.0, "d_ih": 0.3},
                               "contrib": {"d_ia": 3.0, "d_p": 30.0, "d_ih": 18.0}})
    w.close()
    f = next((tmp_path / "nilm").glob("nilm_profile_candidates_*.csv"))
    rows = list(_csv.reader(open(f, encoding="utf-8-sig")))
    head = rows[0]
    assert "device_id" in head and "d_ih" in head and "c_d_ih" in head
    assert len(rows[1]) == len(head)
    r = dict(zip(head, rows[1]))
    assert r["device_id"] == "devA" and float(r["d_ih"]) == pytest.approx(0.3) and float(r["c_d_ih"]) == pytest.approx(18.0)
