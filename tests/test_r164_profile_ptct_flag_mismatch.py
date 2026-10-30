"""第 164 轮（v0.99.22/23）：画像 PT/CT 与本侧不同 ⇒ 只提示、照常匹配（原为按「启用」标志位硬拒绝、画像匹配从不运行）。
v0.99.23：「启用 PT/CT」开关已去掉，旧画像 pt_ct.enabled=false ⇒ PT=CT=1；本侧 PT=4 CT=250 ⇒ 变比不同 ⇒ 提示一次。

实录：分路侧记录仪直接输出一次侧量（PT/CT 关闭），总线侧二次侧 ×CT=250 ⇒ 两侧都是一次侧、可比，却被标志位拒绝。"""
import json, os, numpy as np, pytest
from elec_tool.config import AppConfig
from elec_tool.nilm import NilmDetector
from elec_tool.nilm_profile import FEATURES


def _profile(pt_enabled: bool):
    return {"schema": "nilm_profile/1", "device_id": "dev", "version": "1.0", "quantity": "i", "unit": "A", "fs": 10000.0, "f_nom": 50.0,
            "pt_ct": {"enabled": pt_enabled, "pt_ratio": 1.0, "ct_ratio": 1.0}, "wiring": {"wiring": "3p4w"},
            "pre_cycles": 10, "post_cycles": 50, "features": FEATURES, "template_points": 16,
            "shutdown": {"n": 3, "mu": [-30.0, -30.0, -30.0, 0.0, 0.0, 1.0, 5.0], "sigma": [4.5, 4.5, 4.5, 100.0, 100.0, 0.3, 5.0],
                         "template_spread": 0.25, "dur_cycles": {"min": 3, "max": 8, "mean": 5}, "template": [1.0] * 16}}


def _detector(tmp_path, prof, bus_ptct_enabled):
    pp = tmp_path / "prof.json"; pp.write_text(json.dumps(prof), encoding="utf-8")
    cfg = AppConfig.from_dict({"transform": {"enabled": bus_ptct_enabled, "pt_ratio": 4, "ct_ratio": 250},
                               "nilm": {"enabled": True, "save": True, "quantity": "i", "window_cycles": 400, "min_gap_cycles": 20,
                                        "profile_path": str(pp), "auto_params": False,
                                        "algorithms": {a: {"enabled": False} for a in ("threshold", "two_window", "cusum", "glr", "steady_state", "median_diff")} | {"profile": {"enabled": True, "max_scale": 1}}}})
    det = NilmDetector(cfg, root=str(tmp_path), run_id=7, run_dir=str(tmp_path / "run"))
    assert det._profile is not None, det._profile_err
    return det


def _feed(det, L=600, k_on=300):
    ia = np.full(L, 90.0); ia[k_on:] = 60.0
    rng = np.random.default_rng(1); ia = ia + rng.normal(0, 0.3, L)
    i4 = np.vstack([ia * np.sqrt(3), ia, ia, ia]); p4 = np.zeros((4, L)); q4 = np.zeros((4, L))
    t = 1.7e9 + np.arange(L) * 0.02

    class Stub:
        fs = 10000.0; f_nom = 50.0
        def __init__(s): s.k = 0
        def push(s, blk):
            a, b = s.k, min(s.k + 5, L); s.k = b
            return {"t": t[a:b], "p": p4[:, a:b], "q": q4[:, a:b], "i": i4[:, a:b]}
    det.feat = Stub()
    from elec_tool.blocks import SampleBlock
    evs = []
    while det.feat.k < L:
        evs += det.ingest(SampleBlock(t=np.zeros(5), u=np.ones((3, 5)), i=np.ones((3, 5))))
    return evs


def test_ptct_flag_mismatch_warns_but_still_matches(tmp_path):
    det = _detector(tmp_path, _profile(False), bus_ptct_enabled=True)
    evs = _feed(det)
    prof_evs = [e for e in evs if e["algorithm"] == "profile"]
    assert prof_evs and prof_evs[0]["direction"] == "down" and prof_evs[0]["status"] in ("confirmed", "low_confidence")
    assert any("换算后提取" in m and "本侧 ΔI 是画像的" in m for m in det.errors)   # v0.99.26：提示里给出实际倍数
    assert not any("画像匹配不会命中" in m for m in det.errors)
    assert det.profile_hist, "候选诊断应已累积"
    files = os.listdir(tmp_path / "run")
    assert any(f.startswith("nilm_profile_candidates_") for f in files), files


def test_ptct_flag_same_no_warning(tmp_path):
    prof = _profile(True); prof["pt_ct"] = {"enabled": True, "pt_ratio": 4.0, "ct_ratio": 250.0}
    det = _detector(tmp_path, prof, bus_ptct_enabled=True)
    evs = _feed(det)
    assert [e for e in evs if e["algorithm"] == "profile"]
    assert not any("换算后提取" in m for m in det.errors)   # 画像 PT/CT=1/1 vs 本侧 4/250 不同 ⇒ 会提示；这里改为同变比
