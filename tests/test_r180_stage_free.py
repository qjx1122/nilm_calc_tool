"""v0.99.29（第 180 轮）：**档位自由匹配**（方案 B）与 `lambda_rel` 默认值下调。

第 179 轮的结论是：一份画像只代表**录到的那一档**，实测只认 0.70~1.30×，低于 0.5× 的档位连候选
都不生成（`min_d = 0.5·画像幅值`）。本轮把"档位"变成**待估参数**：

* `match_event(..., stage_free=True)`：先用加权最小二乘解出唯一的档位缩放 `s*`，再算形状残差；
  `σ` 随 `s` 同比缩放（低档位容差不会被绝对下限压死），事件里多出 `stage_scale`；
* `nilm.algorithms.profile.stage_free=1` 打开；`min_stage` 把候选门槛从"画像幅值的一半"改成可配；
* `stage_min_scale` / `stage_max_scale` 限制可解的档位范围；`stage_dim_max` 是**单维否决**
  （档位自由会系统性压平均值 D²，必须补一条"任一维 |z|>√stage_dim_max 就拒"，否则 ΔIh 只有 0.4× 的
  假负荷会以 conf 0.396 混进来）；
* `lambda_rel` 默认 0.1→0.02：λ·median(σ²) 是**跨量纲**的中位数，0.1 会把 peak_ratio 的有效 σ
  放大 4 倍，判别力白送。

本文件只测"开关与阈值是否按设计生效"，真实数据复核见 `REPORT_TEST.md` 第 180 轮专题。
"""
from __future__ import annotations

import copy
import csv
import datetime
import json

import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, ConfigError, NILM_SCALAR_ALGOS, NilmConfig
from elec_tool.nilm import NILM_ALGO_DEFAULTS, NilmDetector, NilmEvent, _CSV_FIELDS, _stage_kind
from elec_tool.nilm_profile import (FEATURES, PROFILE_SCHEMA, build_profile, detect_profile, fit_group, match_event,
                                    profile_feature_names, save_profile, stage_window, validate_profile)

# 与 tests/test_r173_harmonic_multi_profile.py 同口径的"真设备"：单次启停
MU = {"d_ia": 10.0, "d_ib": 9.0, "d_ic": 11.0, "d_p": -1732.0, "d_q": 200.0,
      "peak_ratio": 1.2, "dur_cycles": 100.0, "d_ih": 16.0}
SIGMA = {"d_ia": 1.5, "d_ib": 1.35, "d_ic": 1.65, "d_p": 260.0, "d_q": 50.0,
         "peak_ratio": 0.36, "dur_cycles": 50.0, "d_ih": 2.5}
PRE, POST = 10, 50


def _doc(n_events: int = 1, drop_harmonic: bool = False) -> dict:
    names = [f for f in FEATURES if not (drop_harmonic and f == "d_ih")]
    vec = {k: MU[k] for k in names}
    samples = [{"vec": dict(vec), "template": [0.0, 1.0, 0.4, 0.0], "t_start": 100.0 + i, "t_start_local": f"2026-10-30 10:00:0{i}",
                "onset": 100 + i, "end": 200 + i, "source": "dev.csv"} for i in range(n_events)]
    if drop_harmonic or n_events < 2:                       # fit_group 只认 8 维；7 维旧画像手工拼
        g = {"n": n_events, "mu": [float(vec[k]) for k in names], "sigma": [float(SIGMA[k]) for k in names],
             "template": [0.0, 1.0, 0.4, 0.0], "template_spread": 0.25,
             "dur_cycles": {"min": float(MU["dur_cycles"]), "max": float(MU["dur_cycles"]), "mean": float(MU["dur_cycles"])},
             "events": [dict(s, vec={k: float(vec[k]) for k in names}) for s in samples]}
    else:
        g = fit_group(samples)
        g["sigma"] = [float(SIGMA[k]) for k in names]        # 固定 σ，测试不依赖 _REL_FLOOR 的具体数值
    doc = {"schema": PROFILE_SCHEMA, "version": "1.0", "device_id": "pumpA", "quantity": "i", "unit": "A", "pre_cycles": PRE, "post_cycles": POST,
           "label_mode": "labels", "wiring": {"wiring": "3p4w"}, "pt_ct": {"pt_ratio": 1.0, "ct_ratio": 1.0},
           "features": list(names), "startup": copy.deepcopy(g), "shutdown": copy.deepcopy(g)}
    doc["shutdown"]["mu"] = [-float(v) for v in doc["startup"]["mu"]]   # 停止＝镜像（σ 仍为正）
    doc["shutdown"]["sigma"] = [float(v) for v in doc["startup"]["sigma"]]
    doc["shutdown"]["events"] = []
    doc["shutdown"]["template"] = [-0.0, -1.0, -0.4, -0.0]
    doc["shutdown"]["dur_cycles"] = dict(doc["startup"]["dur_cycles"])
    return validate_profile(doc)


def _vec(doc: dict, k: float) -> dict:
    names = profile_feature_names(doc)
    out = {}
    for i, f in enumerate(names):
        m = float(doc["startup"]["mu"][i])
        out[f] = m * k if f in ("d_ia", "d_ib", "d_ic", "d_p", "d_q", "d_ih") else m
    return out


def _judge(doc: dict, vec: dict, *, stage_free: bool, lam: float = 0.02, min_conf: float = 0.3) -> tuple:
    r = match_event(doc, {"vec": vec, "template": list(doc["startup"]["template"])}, lam, (), 1, stage_free)
    ok = r["d2_per_dim"] <= 9.0 and r["confidence"] >= min_conf
    return r, ok


def _series(doc: dict, steps, *, pre: int = PRE, post: int = POST, tail: int = 300) -> tuple:
    """按 (位置, 倍数) 造一条三相总电流 / 有功 / 无功 / 谐波序列（每步保持到下一个步）。"""
    names = profile_feature_names(doc)
    start = doc["startup"]["mu"]
    L = (max(p for p, _k in steps) + post + tail) if steps else tail + 200
    base_i, base_p, base_q, base_h = 50.0, 5000.0, 1200.0, 3.0
    i0, p0, q0, h0 = base_i, base_p, base_q, base_h
    di = float(np.sqrt(sum(float(start[names.index(f)]) ** 2 for f in ("d_ia", "d_ib", "d_ic"))))   # 三相合成 ΔI
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L)); ih4 = np.zeros((4, L))
    i4[:] = i0; p4[:] = p0; q4[:] = q0; ih4[:] = h0
    for pos, k in steps:
        for j in range(pos, L):
            i4[0, j] = i0 + k * di
            for ph, f in enumerate(("d_ia", "d_ib", "d_ic"), start=1):     # 分相电流同步台阶（特征要用）
                if f in names:
                    i4[ph, j] = i0 + k * float(start[names.index(f)])
            p4[0, j] = p0 + k * float(start[names.index("d_p")])
            q4[0, j] = q0 + k * float(start[names.index("d_q")])
            if "d_ih" in names:
                ih4[0, j] = h0 + k * float(start[names.index("d_ih")])
    return p4, q4, i4, ih4


def _prm(**kw) -> dict:
    p = dict(NILM_ALGO_DEFAULTS["profile"])
    p.update(kw)
    return p


# ---------------------------------------------------------------- 配置 / 默认值
def test_config_defaults_stage_free_and_lambda():
    p = NilmConfig().params("profile")
    assert p["lambda_rel"] == pytest.approx(0.02)          # 第 180 轮：0.1 → 0.02
    assert p["stage_free"] == 0 and p["min_stage"] == pytest.approx(0.5)   # 默认＝旧行为
    assert p["stage_min_scale"] == pytest.approx(0.2) and p["stage_max_scale"] == pytest.approx(3.0)
    assert p["stage_dim_max"] == pytest.approx(9.0)


@pytest.mark.parametrize("key,val", [("stage_free", 2), ("stage_free", -1), ("min_stage", 0.0), ("min_stage", 3.5),
                                     ("stage_dim_max", -1.0), ("stage_min_scale", 0.0)])
def test_config_rejects_bad_stage_params(key, val):
    cfg = NilmConfig(); cfg.algorithms["profile"][key] = val
    with pytest.raises(ConfigError):
        cfg.validate()


def test_config_rejects_inverted_stage_range():
    cfg = NilmConfig(); cfg.algorithms["profile"].update({"stage_min_scale": 2.0, "stage_max_scale": 1.5})
    with pytest.raises(ConfigError, match="stage_min_scale"):
        cfg.validate()


def test_stage_free_allows_zero_values():
    cfg = NilmConfig(); cfg.algorithms["profile"].update({"stage_free": 0, "stage_dim_max": 0})
    cfg.validate()


# ---------------------------------------------------------------- λ 下调：窗口收窄
def test_lambda_rel_down_narrows_stage_window():
    doc = _doc()
    w10 = stage_window(doc, lam_rel=0.1)
    w02 = stage_window(doc, lam_rel=0.02)
    assert w02["k_lo"] >= w10["k_lo"] - 1e-9 and w02["k_hi"] <= w10["k_hi"] + 1e-9
    assert w02["k_lo"] > 0.60 and w02["k_hi"] < 1.40          # 仍是"一份画像只认这一档 ±30 %"的量级


# ---------------------------------------------------------------- 档位自由：收全档位
def test_stage_free_accepts_all_stages_fixed_rejects_far_ones():
    doc = _doc()
    for k in (0.3, 0.5, 0.8, 1.0, 1.5, 2.0):
        r, ok = _judge(doc, _vec(doc, k), stage_free=True)
        assert ok, (k, r["d2_per_dim"], r["confidence"])
        assert r["stage_scale"] == pytest.approx(k, rel=1e-6)
    for k in (0.3, 0.5, 2.0):                                 # 固定档位：0.7~1.3 之外全拒
        _r, ok = _judge(doc, _vec(doc, k), stage_free=False)
        assert not ok, k


def test_stage_free_respects_stage_range():
    doc = _doc()
    r = match_event(doc, {"vec": _vec(doc, 4.0), "template": list(doc["startup"]["template"])}, 0.02, (), 1, True,
                    (0.2, 3.0))
    assert r["stage_scale"] == pytest.approx(3.0)             # 夹到上限，残差留在 D² 里
    assert r["d2_per_dim"] > 2.0


# ---------------------------------------------------------------- 档位自由：不能丢判别力
def test_stage_free_rejects_harmonic_and_reactive_impostors():
    doc = _doc()
    lin = _vec(doc, 1.0); lin["d_ih"] = 0.0                    # 同幅值纯线性假负荷
    r, ok = _judge(doc, lin, stage_free=True)
    assert not ok and r["confidence"] < 0.3
    qflip = _vec(doc, 1.0); qflip["d_q"] = -float(MU["d_q"])   # 容性/反号无功
    r, ok = _judge(doc, qflip, stage_free=True)
    assert not ok


def test_dim_veto_catches_what_mean_gate_misses():
    """ΔIh 只有 0.4× 的假负荷：平均 D² 被 8 维摊薄后 conf 约 0.4（会混进来），单维否决必须拦住。"""
    doc = _doc()
    bad = _vec(doc, 1.0); bad["d_ih"] = float(MU["d_ih"]) * 0.4
    r = match_event(doc, {"vec": bad, "template": list(doc["startup"]["template"])}, 0.02, (), 1, True)
    assert r["d2_per_dim"] < 3.0 and r["confidence"] > 0.3    # 平均门确实拦不住
    assert r["d2_dim_max"] > 9.0                              # 单维贡献 12+
    assert r["d2_dim_name"] == "d_ih"


def test_detect_profile_applies_dim_veto_and_reports_stage_scale():
    doc = _doc()
    p4, q4, i4, ih4 = _series(doc, [(100, 0.4)])
    res = detect_profile(p4, q4, i4, doc, _prm(stage_free=1, min_stage=0.2, stage_dim_max=9.0), False, "unknown", (), ih4)
    acc = [r for r in res if r["accepted"]]
    assert acc, [(r["flags"], r["confidence"]) for r in res]
    assert acc[0]["stage_scale"] == pytest.approx(0.4, rel=0.05)
    assert acc[0]["match"]["direction"] == "START"
    # 全幅事件、但谐波只有 0.4×：平均 D² 仍低，单维否决必须拒
    p4b, q4b, i4b, ih4b = _series(doc, [(100, 1.0)])
    ih4b[0, 100:] = ih4b[0, 100] - 0.6 * 1.0 * float(MU["d_ih"])
    res_b = detect_profile(p4b, q4b, i4b, doc, _prm(stage_free=1, min_stage=0.2, stage_dim_max=9.0), False, "unknown", (), ih4b)
    assert any("dim_exceeds" in r["flags"] for r in res_b)
    assert not [r for r in res_b if r["accepted"]]


def test_min_stage_gate_controls_candidate_generation():
    """0.3× 的台阶：min_stage=0.5（旧行为）连候选都不生成；0.2 才看得见。"""
    doc = _doc()
    p4, q4, i4, ih4 = _series(doc, [(100, 0.3)])
    assert detect_profile(p4, q4, i4, doc, _prm(stage_free=1, min_stage=0.5), False, "unknown", (), ih4) == []
    res = detect_profile(p4, q4, i4, doc, _prm(stage_free=1, min_stage=0.2), False, "unknown", (), ih4)
    assert res and res[0]["stage_scale"] == pytest.approx(0.3, rel=0.1)


# ---------------------------------------------------------------- 档位变化 vs 启停
def test_stage_change_keeps_device_state():
    """已在运行又出现一次同向台阶＝升档（不改 on/off 状态、事件落成 stage_up）。"""
    doc = _doc()
    p4, q4, i4, ih4 = _series(doc, [(100, 1.0), (200, 1.6)])
    res = detect_profile(p4, q4, i4, doc, _prm(stage_free=1, min_stage=0.2), False, "unknown", (), ih4)
    acc = [r for r in res if r["accepted"]]
    assert len(acc) >= 2
    assert acc[0]["stage_change"] is False                     # 第一次：停机 → 启动
    assert acc[1]["stage_change"] is True                      # 第二次：运行中升档
    assert acc[1]["stage_scale"] == pytest.approx(0.6, rel=0.1)   # 升档台阶 1.0→1.6 相对画像档位＝0.6


# ---------------------------------------------------------------- 落盘字段
def test_event_csv_has_stage_columns():
    assert _CSV_FIELDS[-2:] == ["stage_scale", "event_kind"]
    ev = NilmEvent(id=1, algorithm="profile", channel="total", t_start=1.0, t_end=2.0, direction="up",
                   magnitude_w=0.0, delta_p_w=-100.0, delta_q_var=10.0, delta_i_a=5.0, pre_p_w=0.0, post_p_w=0.0,
                   cycles=100, score=0.0, device_id="pumpA", stage_scale=0.4, event_kind="stage_up")
    d = ev.to_dict()
    assert d["stage_scale"] == pytest.approx(0.4) and d["event_kind"] == "stage_up"


# ---------------------------------------------------------------- 向后兼容
def test_old_seven_dim_profile_still_works_with_stage_free():
    doc = _doc(drop_harmonic=True)
    assert profile_feature_names(doc) == FEATURES[:7]
    r, ok = _judge(doc, _vec(doc, 0.5), stage_free=True)
    assert ok and r["stage_scale"] == pytest.approx(0.5, rel=1e-6)


def test_derived_json_roundtrip_keeps_stage_metadata():
    doc = _doc()
    from elec_tool.nilm_profile import derive_stage_profile
    sub = derive_stage_profile(doc, 0.4)
    assert sub["device_id"].endswith("@40%")
    assert json.loads(json.dumps(sub))["stage"]["scale"] == pytest.approx(0.4)


# ---------------------------------------------------------------- 界面 / 接口
def test_ui_has_stage_derive_entry():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    for i in ("np-stage-scales", "np-stage-dir", "btn-np-stage", "btn-np-stage-copy", "np-stage-result", "np-stage-pathstr"):
        assert f'id="{i}"' in html, i
    assert "function npStageRun" in js and "/api/process/nilm_profile_stage" in js
    assert "stage_scale" in js                                  # 事件表显示档位倍数


def test_stage_endpoint_registered():
    from app.server import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/process/nilm_profile_stage" in paths


def test_auto_phase_map_inherits_stage_free():
    """phase_map=0（自动）内部递归时必须把 stage_free/stage_range 带下去，否则自动相序会悄悄退回固定档位。"""
    doc = _doc()
    r = match_event(doc, {"vec": _vec(doc, 0.4), "template": list(doc["startup"]["template"])}, 0.02, (), 0, True)
    assert r["phase_map_auto"] is True and r["stage_free"] is True
    assert r["stage_scale"] == pytest.approx(0.4, rel=1e-6) and r["confidence"] > 0.9


# ---------------------------------------------------------------- 运行档位 → 事件类型（stop vs stage_down）
def test_stage_kind_table():
    """方向都是 STOP，靠"运行档位"分清降档与停机；升档/启动同理。"""
    up, dn = {"direction": "START"}, {"direction": "STOP"}
    assert _stage_kind(up, 1.0, 0.0) == ("start", 1.0)             # 停机 → 满档启动
    assert _stage_kind(up, 0.2, 0.0) == ("start", 0.2)             # 停机 → 0.2 档启动（仍是 start）
    assert _stage_kind(up, 0.6, 1.0) == ("stage_up", 1.6)          # 1.0 档运行中 +0.6
    assert _stage_kind(dn, 0.6, 1.6) == ("stage_down", 1.0)        # 1.6 → 1.0 档
    assert _stage_kind(dn, 0.2, 0.2) == ("stop", 0.0)              # 0.2 档运行 → 停（不是降档）
    assert _stage_kind(dn, 1.0, 1.0) == ("stop", 0.0)              # 满档 → 停
    assert _stage_kind(dn, 0.4, 1.0) == ("stage_down", 0.6)        # 满档 → 0.6 档（设备还在转）


FS, F, T0 = 6400.0, 50.0, 1.79e9


def _wave(P_of_t, dur, seed=1, pf=0.9, noise=0.002):
    n = int(FS * dur); t = np.arange(n) / FS; w = 2 * np.pi * F * t; P = P_of_t(t)
    U, ang = 57.74, np.arccos(pf); u = np.zeros((3, n)); i = np.zeros((3, n)); rng = np.random.default_rng(seed)
    for k, ph in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        u[k] = U * np.sqrt(2) * np.sin(w + ph)
        i[k] = (P / 3) / (U * pf) * np.sqrt(2) * np.sin(w + ph - ang) + rng.normal(0, noise, n)
    return T0 + t, u, i


def _write_csv(path, t, u, i):
    with open(path, "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(t.size):
            d = datetime.datetime.fromtimestamp(t[k])
            wr.writerow([f"0/00/00 {d:%H:%M:%S}.{int(round((t[k] % 1) * 10000)):04d}"]
                        + [f"{v:.5f}" for v in (u[0, k], i[0, k], u[1, k], i[1, k], u[2, k], i[2, k])])


def test_detector_labels_stage_down_before_stop(tmp_path):
    """实测量级的多档位序列：1.0 档启动 → 降到 0.4 档（−0.6×）→ 停机（−0.4×）。

    旧规则只看方向与二元状态机 ⇒ 中间那次报 stop（设备其实还在 0.4 档运行）、最后那次报 stage_down（其实停了）。
    """
    def dev(t):                                      # 两次启停（间隔 ≥ 4 s：标签定位容差 2 s 不会串到相邻动作）
        P = np.full(t.size, 100.0)
        for a, b in ((2.0, 5.0), (9.0, 12.0)):
            P[(t >= a) & (t < b)] += 500
        return P

    def bus(t):
        P = np.full(t.size, 3000.0)
        P[(t >= 3.0) & (t < 9.0)] += 500        # 1.0 档
        P[(t >= 6.0) & (t < 9.0)] -= 300        # 降到 0.4 档
        return P

    t, u, i = _wave(dev, 16.0)
    dev_csv = str(tmp_path / "dev.csv"); _write_csv(dev_csv, t, u, i)
    labels = "\n".join(f"{datetime.datetime.fromtimestamp(T0 + a):%H:%M:%S},{w}" for a, w in
                        ((2.0, "开"), (5.0, "关"), (9.0, "开"), (12.0, "关")))
    cfg = AppConfig(); cfg.transform.enabled = False
    doc = build_profile(cfg, dev_csv, device_id="pumpA", labels=labels, pre_cycles=10, post_cycles=50)
    prof = str(tmp_path / "pumpA.json"); save_profile(doc, prof)

    cfg.nilm.profile_path = prof; cfg.nilm.save = False
    for a in NILM_SCALAR_ALGOS:
        cfg.nilm.algorithms[a]["enabled"] = False
    cfg.nilm.algorithms["profile"].update({"enabled": True, "stage_free": 1, "min_stage": 0.2, "max_scale": 1})
    cfg.validate()
    det = NilmDetector(cfg)
    t2, u2, i2 = _wave(bus, 14.0, seed=2)
    evs = []
    for a in range(0, t2.size, 640):
        evs += det.ingest(SampleBlock(t=t2[a:a + 640], u=u2[:, a:a + 640], i=i2[:, a:a + 640]))
    evs = [e for e in evs if e["algorithm"] == "profile"]
    assert [e["event_kind"] for e in evs] == ["start", "stage_down", "stop"], [(e["event_kind"], e["stage_scale"]) for e in evs]
    assert [round(e["stage_scale"], 2) for e in evs] == [1.0, 0.6, 0.4]
    assert [round(e["t_start"] - T0, 1) for e in evs] == [3.0, 6.0, 9.0]
    assert det.summary()["profile"]["profiles"][0]["device_state"] == "off"
    assert det.summary()["profile"]["profiles"][0]["level"] == pytest.approx(0.0, abs=0.15)
