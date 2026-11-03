"""v0.99.30（第 184 轮）：设备画像提取支持**单相 / 分相设备**。

覆盖
- ``normalize_phases`` / ``profile_phases`` / ``profile_skip_dims``：相别字符串归一、旧画像（无 phases 字段）不跳过任何维；
- ``detect_phases``：单相（另两相只剩噪声）判 "A"、三相不平衡设备判 "ABC"、全零退回 "ABC"；
- ``build_profile``：三列单相 CSV（时间,A相电压,A相电流）能提取，画像写 ``phases="A"`` + ``phase_stats`` + 提示；
  人工指定相别与数据不符时给出 ⚠ 提示；
- ``validate_profile``：非法相别报错、缺字段保持向后兼容；
- ``detect_profile``：**同一份画像**在总线侧遇到"未接相的他负荷落在前后窗内"时，跳过 d_ib/d_ic 后真事件 accepted，
  不跳过（phases=ABC，等价旧行为）则 D² 爆掉被拒；
- 档位派生画像继承 ``phases``；
- 引擎：单相画像加载提示；3p3w 无 B 相 CT 时的 B 相画像提示。
"""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from elec_tool.config import AppConfig
from elec_tool.nilm import NilmDetector
from elec_tool.nilm_profile import (FEATURES, ProfileError, build_profile, derive_stage_profile, detect_phases,
                                    detect_profile, fit_group, normalize_phases, profile_phase_rows, profile_phases,
                                    profile_skip_dims, save_profile, validate_profile)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FS, F, T0 = 6400.0, 50.0, 1791878400.0


# ---------------------------------------------------------------- 工具
def _cfg(**kw):
    cfg = AppConfig()
    cfg.sampling.fs, cfg.sampling.f_nom = FS, F
    cfg.transform.pt_ratio = cfg.transform.ct_ratio = 1.0
    cfg.source.kind = "csv_file"; cfg.source.path = "x"
    cfg.nilm.quantity = kw.pop("quantity", "auto")
    cfg.nilm.save = False
    for k, v in kw.items():
        setattr(cfg.nilm, k, v)
    cfg.validate()
    return cfg


def _write_single_phase_csv(path, *, step_s=2.0, before=5.0, after=8.0, dur_s=4.0):
    """三列单相录波：时间,A相电压,A相电流（B/C 两相在文件里根本不存在）。"""
    t = np.arange(0.0, dur_s, 1.0 / FS)
    ia = np.where(t >= step_s, after, before)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("时间,A相电压,A相电流\n")
        for k, tk in enumerate(t):
            ua = 230.0 * np.sqrt(2) * np.sin(2 * np.pi * F * tk)
            ii = ia[k] * np.sqrt(2) * np.sin(2 * np.pi * F * tk)
            fh.write(f"{T0 + tk:.6f},{ua:.6f},{ii:.6f}\n")
    return str(path)


def _vec(dia, dib, dic, dp, peak=1.05, dur=6.0, dih=1.5):
    return {"d_ia": dia, "d_ib": dib, "d_ic": dic, "d_p": dp, "d_q": 0.0, "peak_ratio": peak,
            "dur_cycles": dur, "d_ih": dih}


TMPL = [0.0, 0.5, 0.9, 1.0] + [1.0] * 12


def _single_phase_doc(phases="A", n=3):
    smp = [{"vec": _vec(3.0 + 0.02 * k, 0.03 * (-1) ** k, -0.02, 660.0), "template": TMPL,
            "t_start": T0 + k, "onset": 10, "end": 16, "source": f"label:{k}"} for k in range(n)]
    doc = {"schema": "nilm_profile/1", "device_id": "pump1ph", "quantity": "p", "unit": "W",
           "features": list(FEATURES), "pre_cycles": 10, "post_cycles": 50,
           "startup": fit_group(smp), "shutdown": None, "notes": []}
    if phases:
        doc["phases"] = phases
    return validate_profile(doc)


PRM = {"d2_max": 9.0, "min_confidence": 0.3, "k_sigma": 4.0, "margin": 1.5, "lambda_rel": 0.02,
       "state_check": 1, "max_scale": 8, "min_scale": 0.25, "min_stage": 0.5, "phase_map": 1,
       "stage_free": 0, "stage_dim_max": 9.0}


# ---------------------------------------------------------------- 相别归一
@pytest.mark.parametrize("raw, want", [("auto", ""), (None, ""), ("", ""), ("ABC", "ABC"), ("abc", "ABC"),
                                       ("A", "A"), ("a,c", "AC"), ("AB", "AB"), (["B"], "B"), ("C/A", "AC")])
def test_normalize_phases(raw, want):
    assert normalize_phases(raw) == want


@pytest.mark.parametrize("bad", ["D", "ABD", "1", "三相"])
def test_normalize_phases_rejects_bad(bad):
    with pytest.raises(ProfileError):
        normalize_phases(bad)


def test_profile_skip_dims():
    assert profile_skip_dims({}) == ()                      # 旧画像：不跳过任何维
    assert profile_phases({}) == "ABC"
    assert profile_skip_dims({"phases": "ABC"}) == ()
    assert set(profile_skip_dims({"phases": "A"})) == {"d_ib", "d_ic"}
    assert set(profile_skip_dims({"phases": "AB"})) == {"d_ic"}


# ---------------------------------------------------------------- 自动判定
def test_detect_phases_auto_single_vs_three():
    single = [{"vec": _vec(3.0 + 0.03 * k, 0.03 * (-1) ** k, -0.02 * k, 660.0)} for k in range(3)]
    ph, stats = detect_phases(single)
    assert ph == "A"
    assert stats["A"]["active"] and not stats["B"]["active"] and not stats["C"]["active"]

    three = [{"vec": _vec(3.0, 2.0, 1.2, 3000.0)} for _ in range(3)]
    assert detect_phases(three)[0] == "ABC"

    zeros = [{"vec": _vec(0.0, 0.0, 0.0, 0.0)} for _ in range(3)]
    assert detect_phases(zeros)[0] == "ABC"                  # 无从判断：按三相（不改变旧行为）


# ---------------------------------------------------------------- 提取
def test_build_profile_from_three_column_csv(tmp_path):
    f = _write_single_phase_csv(tmp_path / "dev1ph.csv")
    doc = build_profile(_cfg(), f, device_id="pump1ph", labels=f"{T0 + 2.0:.3f},开",
                        pre_cycles=10, post_cycles=50)
    assert doc["phases"] == "A" and doc["phase_source"] == "auto"
    assert doc["phase_stats"]["A"]["active"] and not doc["phase_stats"]["B"]["active"]
    assert set(profile_skip_dims(doc)) == {"d_ib", "d_ic"}
    assert any("单相 / 分相画像" in n for n in doc["notes"])
    # 幅值：ΔIa≈3 A，ΔP≈690 W（230 V×3 A）
    mu = dict(zip(doc["features"], doc["startup"]["mu"]))
    assert abs(mu["d_ia"] - 3.0) < 0.15
    assert abs(mu["d_p"] - 690.0) < 30.0


def test_build_profile_manual_phase_mismatch_warns(tmp_path):
    f = _write_single_phase_csv(tmp_path / "dev1ph.csv")
    doc = build_profile(_cfg(), f, device_id="pump1ph", labels=f"{T0 + 2.0:.3f},开", phases="B")
    assert doc["phases"] == "B" and doc["phase_source"] == "manual"
    assert any("不一致" in n for n in doc["notes"])


def test_build_profile_explicit_abc_keeps_all(tmp_path):
    f = _write_single_phase_csv(tmp_path / "dev1ph.csv")
    doc = build_profile(_cfg(), f, device_id="pump1ph", labels=f"{T0 + 2.0:.3f},开", phases="ABC")
    assert doc["phases"] == "ABC"
    assert profile_skip_dims(doc) == ()
    assert not any("单相 / 分相画像" in n for n in doc["notes"])


# ---------------------------------------------------------------- 校验 / 派生
def test_validate_profile_phases():
    with pytest.raises(ProfileError):
        validate_profile({**_single_phase_doc(None), "phases": "D"})
    with pytest.raises(ProfileError):
        validate_profile({**_single_phase_doc(None), "phases": ""})
    legacy = _single_phase_doc(None)
    assert "phases" not in legacy                            # 旧画像：字段缺省，行为不变


def test_derive_stage_inherits_phases():
    doc = _single_phase_doc("A")
    sub = derive_stage_profile(doc, 0.5)
    assert sub["phases"] == "A"
    assert set(profile_skip_dims(sub)) == {"d_ib", "d_ic"}


# ---------------------------------------------------------------- 匹配（核心收益）
def _bus_series():
    """A 相目标设备 +3 A / +690 W @500 周波；B 相他负荷 +1 A / +230 W **同一周波**（同时投切 ⇒ 落在同一前后窗）。"""
    L = 1200
    p = np.full((4, L), 1000.0); q = np.zeros((4, L)); i = np.full((4, L), 5.0)
    p[1, 500:] += 690.0; i[1, 500:] += 3.0
    p[2, 500:] += 230.0; i[2, 500:] += 1.0
    p[0] = p[1:].sum(axis=0)
    i[0] = np.sqrt((i[1:] ** 2).sum(axis=0))
    return p, q, i


def test_detect_profile_skips_unused_phases():
    p, q, i = _bus_series()
    doc = _single_phase_doc("A")
    res = detect_profile(p, q, i, doc, PRM, use_p=True)
    hit = [r for r in res if r["accepted"] and r["onset"] == 500]
    assert hit and hit[0]["match"]["direction"] == "START"
    assert "d_ib" not in [k for k, v in hit[0]["match"]["contrib"].items() if abs(v) > 1e-9]

    # 同一画像写成 phases=ABC（等价 v0.99.29 的行为）：B 相他负荷把 d_ib 顶爆，真事件被拒
    res3 = detect_profile(p, q, i, _single_phase_doc("ABC"), PRM, use_p=True)
    rej = [r for r in res3 if r["onset"] == 500][0]
    assert rej["status"] == "rejected" and rej["confidence"] < PRM["min_confidence"]
    assert rej["match"]["contrib"]["d_ib"] > 20.0            # 被跳过的那一维正是罪魁
    assert hit[0]["confidence"] > PRM["min_confidence"]      # 跳过之后同一份画像能认


def test_detect_profile_single_phase_still_rejects_other_load():
    """跳过未接相 ≠ 什么台阶都收：**只**在 B 相上投切的另一台设备不能被认成这台 A 相设备。"""
    L = 1200
    p = np.full((4, L), 1000.0); q = np.zeros((4, L)); i = np.full((4, L), 5.0)
    p[2, 500:] += 690.0; i[2, 500:] += 3.0                   # 幅值与目标设备相同，但在 B 相
    p[0] = p[1:].sum(axis=0)
    i[0] = np.sqrt((i[1:] ** 2).sum(axis=0))
    res = detect_profile(p, q, i, _single_phase_doc("A"), PRM, use_p=True)
    assert not [r for r in res if r["accepted"]]
    # v0.99.30 起候选序列按本相取 ⇒ B 相的台阶在 A 相序列上根本不成候选（更彻底）；万一成候选也必须被拒（d_ia≈0）
    cands = [r for r in res if r["onset"] == 500]
    assert not cands or all(r["status"] == "rejected" for r in cands)


# ---------------------------------------------------------------- 引擎提示
def _engine_with_profile(tmp_path, phases, wiring="3p4w", reconstruct=False):
    doc = _single_phase_doc(phases)
    path = str(tmp_path / f"p_{phases}.json")
    save_profile(doc, path)
    cfg = _cfg()
    cfg.transform.wiring = wiring
    cfg.transform.reconstruct_3w = reconstruct
    cfg.nilm.channels = ["total"]
    cfg.nilm.algorithms["profile"].update({"enabled": True, "max_scale": 1, "min_scale": 1})
    cfg.nilm.profile_path = path
    cfg.validate()
    return NilmDetector(cfg)


def test_engine_note_single_phase(tmp_path):
    det = _engine_with_profile(tmp_path, "A")
    notes = det._profiles[0]["notes"]
    assert any("画像相别 A" in n and "d_ib" in n and "d_ic" in n for n in notes)


def test_engine_note_b_phase_on_3p3w(tmp_path):
    det = _engine_with_profile(tmp_path, "B", wiring="3p3w", reconstruct=False)
    notes = det._profiles[0]["notes"]
    assert any("B 相单相" in n and "永远匹配不上" in n for n in notes)
    # 重构之后 B 相由 Ia/Ic 算出，不再警告
    det2 = _engine_with_profile(tmp_path, "B", wiring="3p3w", reconstruct=True)
    assert not any("永远匹配不上" in n for n in det2._profiles[0]["notes"])


def test_engine_note_ab_profile_on_3p3w_keeps_a_phase(tmp_path):
    """AB 相画像 + 3p3w 无 B 相：只提示跳过 d_ib（不是"永远匹配不上"），A 相证据照用。"""
    det = _engine_with_profile(tmp_path, "AB", wiring="3p3w", reconstruct=False)
    notes = det._profiles[0]["notes"]
    assert any("跳过 d_ic、d_ib" in n or "跳过 d_ib、d_ic" in n for n in notes)
    assert not any("只在 B 相" in n for n in notes)


# ---------------------------------------------------------------- 候选序列按画像相别取（v0.99.30 补）
def test_profile_phase_rows():
    assert profile_phase_rows({}) == ()              # 旧画像 / 三相：沿用 total 行
    assert profile_phase_rows({"phases": "ABC"}) == ()
    assert profile_phase_rows({"phases": "A"}) == (1,)
    assert profile_phase_rows({"phases": "AC"}) == (1, 3)


def test_candidate_series_follows_phase_p():
    """P 口径：单相画像的候选 delta 只含本相（690 W），不受 B 相他负荷（+230 W）影响。"""
    p, q, i = _bus_series()
    a = [r for r in detect_profile(p, q, i, _single_phase_doc("A"), PRM, use_p=True) if r["onset"] == 500]
    t = [r for r in detect_profile(p, q, i, _single_phase_doc("ABC"), PRM, use_p=True) if r["onset"] == 500]
    assert a and abs(a[0]["delta"] - 690.0) < 1e-6            # 本相序列
    assert t and abs(t[0]["delta"] - 920.0) < 1e-6            # 三相 total 序列（旧行为）


def test_candidate_series_follows_phase_i():
    """I 口径：三相合成电流把单相设备的 3 A 压成 0.275 A（背景 50 A）⇒ 0 候选；
    按本相电流则正常出候选（旧版本对 I 口径的单相设备是**静默漏报**）。"""
    L = 1200
    p = np.zeros((4, L)); q = np.zeros((4, L)); i = np.full((4, L), 50.0)
    i[1] = 5.0
    i[1, 500:] += 3.0
    i[0] = np.sqrt((i[1:] ** 2).sum(axis=0))
    assert abs((i[0, 510] - i[0, 490]) - 0.275) < 0.01        # 合成量只涨 0.275 A
    doc = _single_phase_doc("A")
    doc["quantity"] = "i"
    doc["startup"]["mu"][FEATURES.index("d_p")] = 0.0          # I 口径画像不看 ΔP
    doc["startup"]["sigma"][FEATURES.index("d_p")] = 5.0
    hit = [r for r in detect_profile(p, q, i, doc, PRM, use_p=False) if r["onset"] == 500]
    assert hit and abs(hit[0]["delta"] - 3.0) < 1e-6           # 本相序列的台阶就是 3 A
    assert hit[0]["status"] in ("confirmed", "low_confidence")

    doc3 = _single_phase_doc("ABC")
    doc3["quantity"] = "i"
    doc3["startup"]["mu"][FEATURES.index("d_p")] = 0.0
    doc3["startup"]["sigma"][FEATURES.index("d_p")] = 5.0
    assert not detect_profile(p, q, i, doc3, PRM, use_p=False)  # 旧行为：连候选都没有


def test_engine_note_single_phase_wording(tmp_path):
    det = _engine_with_profile(tmp_path, "A")
    n = det._profiles[0]["notes"]
    assert any("三相求和" in s for s in n) and any("d_ib" in s for s in n)


def test_legacy_profile_without_phases_uses_total_series():
    """旧画像（无 phases 字段）必须与 v0.99.29 完全一致：不跳维、候选台阶取三相 total。"""
    p, q, i = _bus_series()
    doc = _single_phase_doc(None)                       # 不写 phases
    assert "phases" not in doc and profile_skip_dims(doc) == ()
    r = [x for x in detect_profile(p, q, i, doc, PRM, use_p=True) if x["onset"] == 500]
    assert r and abs(r[0]["delta"] - 920.0) < 1e-6       # total 序列（含 B 相他负荷）


def test_two_phase_profile_sums_declared_phases():
    """两相画像（AB）：只跳 C 相；候选台阶取 A+B 两相之和（A 690 W + B 230 W ⇒ 920 W，A 单独则 690 W）。"""
    L = 1200
    p = np.full((4, L), 1000.0); q = np.zeros((4, L)); i = np.full((4, L), 5.0)
    p[1, 500:] += 690.0; i[1, 500:] += 3.0
    p[2, 500:] += 230.0; i[2, 500:] += 1.0
    p[0] = p[1:].sum(axis=0)
    i[0] = np.sqrt((i[1:] ** 2).sum(axis=0))
    ab = _single_phase_doc("AB")
    assert profile_skip_dims(ab) == ("d_ic",)
    d_ab = [r for r in detect_profile(p, q, i, ab, PRM, use_p=True) if r["onset"] == 500]
    d_a = [r for r in detect_profile(p, q, i, _single_phase_doc("A"), PRM, use_p=True) if r["onset"] == 500]
    d_abc = [r for r in detect_profile(p, q, i, _single_phase_doc("ABC"), PRM, use_p=True) if r["onset"] == 500]
    assert d_ab and abs(d_ab[0]["delta"] - 920.0) < 1e-6
    assert d_a and abs(d_a[0]["delta"] - 690.0) < 1e-6
    assert d_abc and abs(d_abc[0]["delta"] - 920.0) < 1e-6      # ABC 走 total 行，与 AB 同值
