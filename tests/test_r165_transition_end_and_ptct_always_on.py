"""第 165 轮（v0.99.23）：
① transition_end——过渡终点「平滑 + 首次进带并保持」，对总线侧噪声 / 孤立抖动稳健（实录：旧规则 dur 2161 vs 画像 256 ⇒ 被拒）；
② 去掉「启用 PT/CT 变换」开关：PT/CT 恒参与换算、出厂 1/1，旧配置 / 旧画像 enabled=false 折算为 PT=CT=1。"""
import json, pathlib, re, numpy as np
from elec_tool.nilm_profile import transition_end, _two_window_candidates, load_profile, FEATURES
from elec_tool.config import AppConfig, TransformConfig

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _ramp(L=9000, onset=3000, ramp=700, a0=94.0, a1=56.0, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    x = np.full(L, a0); k = np.arange(ramp); x[onset:onset + ramp] = a0 + (a1 - a0) * k / ramp; x[onset + ramp:] = a1
    return x + rng.normal(0, noise, L)


def test_transition_end_robust_to_noise_and_isolated_wobble():
    clean = _ramp(); noisy = _ramp(noise=4.0, seed=3)
    noisy[3000 + 1850:3000 + 1850 + 60] -= 6.5           # 后窗里其它负荷的一次 −6.5 A 孤立抖动（实录 14:38:53）
    tgt = float(np.mean(clean[3000:6000])); dlt = abs(tgt - 94.0)
    e_clean = transition_end(clean, 3000, 3000, tgt, dlt) - 3000
    e_noisy = transition_end(noisy, 3000, 3000, float(np.mean(noisy[3000:6000])), dlt) - 3000
    assert 450 <= e_clean <= 700                           # 进入 ±20 % 带（80 % 幅值处 ≈ 560 周波）
    assert abs(e_noisy - e_clean) <= 120, (e_clean, e_noisy)   # 旧规则在此噪声下会到 ~1900+（最后一次越带）
    # 旧规则对照：最后一次越带
    seg = noisy[3000:6000]; exc = np.nonzero(np.abs(seg - np.mean(seg)) > 0.2 * dlt)[0]
    assert exc[-1] + 1 > 1500


def test_two_window_candidates_use_transition_end():
    x = _ramp(noise=2.0, seed=5)
    c = _two_window_candidates(x, 3000, 3000, 10.0, 4.0)
    assert c and 3000 <= c[0][0] <= 3700 and c[0][1] - c[0][0] < 900     # 均值双滑窗对斜坡的峰值在坡中段（既有行为）


def test_transform_enabled_false_coerced_to_unity():
    t = TransformConfig(pt_ratio=100.0, ct_ratio=15.0, enabled=False)
    assert t.enabled is True and t.pt_ratio == 1.0 and t.ct_ratio == 1.0
    cfg = AppConfig(); cfg.transform.enabled = False; cfg.validate()
    assert cfg.transform.enabled is True and cfg.transform.pt_ratio == 1.0
    for f in ("configs/default.json", "configs/branch.json"):
        d = json.loads((ROOT / f).read_text(encoding="utf-8"))["transform"]
        assert d["pt_ratio"] == 1.0 and d["ct_ratio"] == 1.0 and d["enabled"] is True


def test_load_profile_legacy_ptct_disabled_becomes_unity(tmp_path):
    prof = {"schema": "nilm_profile/1", "device_id": "d", "version": "1.0", "quantity": "i", "unit": "A",
            "pt_ct": {"enabled": False, "pt_ratio": 100.0, "ct_ratio": 15.0}, "pre_cycles": 10, "post_cycles": 50, "features": FEATURES,
            "shutdown": {"n": 1, "mu": [-1.0] * 3 + [0.0, 0.0, 1.0, 5.0], "sigma": [0.2] * 3 + [5.0, 5.0, 0.3, 5.0], "template_spread": 0.25,
                         "dur_cycles": {"min": 5, "max": 5, "mean": 5}, "template": [1.0] * 16}}
    p = tmp_path / "p.json"; p.write_text(json.dumps(prof), encoding="utf-8")
    assert load_profile(str(p))["pt_ct"] == {"enabled": True, "pt_ratio": 1.0, "ct_ratio": 1.0}


def test_ui_has_no_visible_ptct_enable_toggle():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    # 所有 PT/CT 启用复选框都必须是 hidden 且 checked
    for cid in ("cfg-scale", "br-scale", "nt-base-ptct", "np-base-ptct", "wp-base-ptct"):
        m = re.search(r'<input id="%s"[^>]*>' % cid, html); assert m, cid
        assert "hidden" in m.group(0) and "checked" in m.group(0), m.group(0)
    assert "启用 PT/CT 变换（" not in html
    # PT/CT 输入框仍在
    for cid in ("cfg-pt", "cfg-ct", "br-pt", "br-ct", "nt-base-pt", "np-base-ct", "wp-base-pt"):
        assert f'id="{cid}"' in html, cid
