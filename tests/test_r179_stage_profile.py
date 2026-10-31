"""v0.99.28（第 179 轮）：多档位 / 变频设备只录到部分档位时的补救 —— **派生档位画像**。

覆盖
- ``stage_window``：量出"这份画像到底认几档"（相对录制档位）与候选门槛对应的档位（低于它连候选都不生成）；
- ``derive_stage_profile``：μ/σ 同比缩放、σ 抬回经验下限、peak/dur 不动、事件明细丢弃、``stage`` 元数据、
  ``validate_profile`` 通过、坏倍数报错；
- 派生画像**认自己那一档、不认别的档**，且不认"同幅值纯线性负荷"；
- 档位网格（间距 1.857＝窗口 1.30/0.70）**无缝且不重叠**：0.25~2.5× 每个档位至少被一份接受、正常不与相邻重复；
- 端到端：把 40 % 档的真实台阶喂给派生画像，``detect_profile`` 报出 accepted 的 START；
- CLI：``--derive-stages`` 写盘 + 命令串可复现。
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from elec_tool.nilm_profile import (FEATURES, ProfileError, derive_stage_profile, derive_stage_profiles, detect_profile,
                                    fit_group, load_profile, match_event, save_profile, stage_window, validate_profile)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FS, F, T0 = 6400.0, 50.0, 1.79e9

# 一档"设备"的真值特征：ΔI 10 A/相（合成 17.32 A）、ΔP −1732 W、ΔQ 200 var、ΔIh 5 A、峰值比 1.2、持续 100 周波
TRUTH = {"d_ia": 10.0, "d_ib": 10.0, "d_ic": 10.0, "d_p": -1732.0, "d_q": 900.0,
         "peak_ratio": 1.2, "dur_cycles": 100.0, "d_ih": 16.0}


def _scaled(k):
    v = dict(TRUTH)
    for f in ("d_ia", "d_ib", "d_ic", "d_p", "d_q", "d_ih"):
        v[f] = TRUTH[f] * k
    return v


def _profile(events_per_dir: int = 1):
    """按 TRUTH 造一份最小画像（n 次同档事件，几何取 10/50 周波）。"""
    def grp(sign, n):
        return fit_group([{"vec": {f: sign * v for f, v in TRUTH.items()}, "template": [1.0] * 16,
                           "t_start": T0 + i, "onset": i * 1000, "end": i * 1000 + 100, "source": "sim"} for i in range(n)])
    doc = {"schema": "nilm_profile/1", "device_id": "pump", "version": "1.0", "quantity": "i", "unit": "A",
           "features": list(FEATURES), "pre_cycles": 10, "post_cycles": 50, "notes": [],
           "startup": grp(+1, events_per_dir), "shutdown": grp(-1, events_per_dir)}
    return validate_profile(doc)


AMP = ("d_ia", "d_ib", "d_ic", "d_p", "d_q", "d_ih")


def _vec_for(doc, k, key="startup"):
    """把画像 μ 按档位 k 缩放（只缩放幅度维，peak/dur 不动——与 derive_stage_profile 同口径）。"""
    mu = doc[key]["mu"]
    return {f: float(mu[i]) * (k if f in AMP else 1.0) for i, f in enumerate(FEATURES)}


# ---------------------------------------------------------------- ① 档位窗口
def test_stage_window_measures_acceptance_and_gate():
    doc = _profile()
    w = stage_window(doc)
    # 8 维、σ 下限 15 %/25 %、λ=0.1 ⇒ 实测窗口约 0.7~1.3×（与真实画像 0.70~1.30 一致）
    assert 0.60 <= w["k_lo"] <= 0.78 and 1.22 <= w["k_hi"] <= 1.40
    # 候选门槛＝0.5×画像幅值 ⇒ 低于 0.5× 的档位连候选都不会生成（静默漏报区）
    assert w["k_gate"] == pytest.approx(0.5, abs=0.02)
    assert w["min_d"] == pytest.approx(0.5 * 17.32, rel=0.02)
    assert w["unit"] == "A" and w["probes"] > 100


# ---------------------------------------------------------------- ② 派生规则
def test_derive_scales_mu_sigma_and_keeps_peak_dur():
    doc = _profile()
    sub = derive_stage_profile(doc, 0.4)
    assert sub["device_id"] == "pump@40%"
    assert sub["stage"]["scale"] == 0.4 and sub["stage"]["derived_from"] == "pump"
    for key in ("startup", "shutdown"):
        for i, f in enumerate(FEATURES):
            if f in ("d_ia", "d_ib", "d_ic", "d_p", "d_q", "d_ih"):
                assert sub[key]["mu"][i] == pytest.approx(doc[key]["mu"][i] * 0.4, rel=1e-9)
            else:
                assert sub[key]["mu"][i] == pytest.approx(doc[key]["mu"][i], rel=1e-9)   # peak/dur 不动
            assert sub[key]["sigma"][i] > 0
        assert "events" not in sub[key]                     # 原始事件明细不跟着缩放
        assert sub[key]["n"] == doc[key]["n"]
    assert any("档位派生" in n for n in sub["notes"])
    assert "d_ih" in sub["features"] or len(sub["features"]) == 8


def test_derive_bad_scale_rejected():
    doc = _profile()
    for bad in (0.0, -1.0, 50.0):
        with pytest.raises(ProfileError):
            derive_stage_profile(doc, bad)


# ---------------------------------------------------------------- ③ 认自己、不认别人
def test_derived_profile_matches_own_stage_only():
    doc = _profile()
    sub = derive_stage_profile(doc, 0.4)
    own = match_event(sub, {"vec": _vec_for(sub, 1.0), "template": sub["startup"]["template"]})
    other = match_event(sub, {"vec": _vec_for(doc, 1.0), "template": doc["startup"]["template"]})
    assert own["d2_per_dim"] < 1e-6 and own["confidence"] > 0.99          # 40 % 档：完全命中
    assert other["d2_per_dim"] > 9.0 or other["confidence"] < 0.3         # 100 % 档：拒
    # 同幅值但纯线性（ΔIh=0、ΔQ=0）⇒ 不是这台设备
    lin = _vec_for(sub, 1.0); lin["d_ih"] = 0.0; lin["d_q"] = 0.0
    m = match_event(sub, {"vec": lin, "template": sub["startup"]["template"]})
    assert m["d2_per_dim"] > 9.0 or m["confidence"] < 0.3


def test_low_stage_derived_margin_is_thin_for_small_harmonic_device():
    """**已知限制**：ΔIh 只有 5 A 的小谐波设备，派生到 40 % 档后 σ_ih 被 2 A 绝对下限接管，
    "同幅值纯线性假负荷"的置信度落在 0.35 左右——高于 0.3 就会被误纳。低档派生画像必须靠现场复核
    （候选 CSV 的 c_d_ih / c_d_q），或改用 δIh/ΔP 比值约束；详见 REPORT_TEST.md 第 179 轮第四节。"""
    small = dict(TRUTH, d_ih=5.0)
    g = fit_group([{"vec": dict(small), "template": [1.0] * 16, "t_start": T0, "onset": 0, "end": 100, "source": "sim"}])
    doc = validate_profile({"schema": "nilm_profile/1", "device_id": "small", "version": "1.0", "quantity": "i", "unit": "A",
                            "features": list(FEATURES), "pre_cycles": 10, "post_cycles": 50, "notes": [],
                            "startup": g, "shutdown": None})
    sub = derive_stage_profile(doc, 0.4)
    lin = _vec_for(sub, 1.0); lin["d_ih"] = 0.0; lin["d_q"] = 0.0
    m = match_event(sub, {"vec": lin, "template": sub["startup"]["template"]})
    assert 0.2 < m["confidence"] < 0.45          # 贴着 min_confidence=0.3 的门槛：可能误纳
    # 真设备自己的 40 % 档（ΔIh=2 A）仍然完全命中
    own = match_event(sub, {"vec": _vec_for(sub, 1.0), "template": sub["startup"]["template"]})
    assert own["d2_per_dim"] < 1e-6


# ---------------------------------------------------------------- ④ 网格：无缝、不重叠
def test_stage_grid_covers_without_gap_or_overlap():
    doc = _profile()
    grid = derive_stage_profiles(doc, count=5)
    assert len(grid) == 5 and [round(g["stage"]["scale"], 3) for g in grid] == sorted(round(g["stage"]["scale"], 3) for g in grid)
    def hits(k):
        out = []
        for g in grid:
            m = match_event(g, {"vec": _vec_for(doc, k), "template": doc["startup"]["template"]})
            if m["d2_per_dim"] <= 9.0 and m["confidence"] >= 0.3:
                out.append(g["device_id"])
        return out
    ks = [round(0.25 + 0.0131 + 0.0371 * i, 4) for i in range(62)]   # 0.263~2.513
    empty = [k for k in ks if not hits(k)]
    assert not empty, f"档位网格有空洞：{empty}"
    # 相邻两份的窗口按"上一份上界＝下一份下界"摆放；窗口本身按 0.01 的 k 步长扫描，交界带 ≈ ±0.5 % 会两份都过
    edges = [float(g["stage"]["scale"]) * stage_window(g)["k_hi"] for g in grid[:-1]]
    def near_edge(k):
        return any(abs(k / e - 1.0) <= 0.01 for e in edges)
    bad = [(k, hits(k)) for k in ks if len(hits(k)) > 1 and not near_edge(k)]
    assert not bad, f"相邻派生画像在非交界处重复接受同一档位：{bad}"
    assert any(len(hits(k)) > 1 for k in ks), "交界带应当能被两份接受（这是交接处，不是空洞）"


# ---------------------------------------------------------------- ⑤ 端到端：40 % 档台阶
def _series(step_scale, L=400, onset=100):
    """i4[0] 在 onset 处台阶 step_scale×17.32 A（并同步 ΔP/ΔIh），供 detect_profile 用。"""
    i4 = np.zeros((4, L)); p4 = np.zeros((4, L)); q4 = np.zeros((4, L)); ih4 = np.zeros((4, L))
    base_a = 50.0
    i4[:, :onset] = base_a
    i4[:, onset:] = base_a + 17.32 / np.sqrt(3) * step_scale        # 每相 ΔI = 10×k
    p4[:, :onset] = -80000.0; p4[:, onset:] = -80000.0 + TRUTH["d_p"] * step_scale
    q4[:, :onset] = 5000.0; q4[:, onset:] = 5000.0 + TRUTH["d_q"] * step_scale
    ih4[:, :onset] = 20.0; ih4[:, onset:] = 20.0 + TRUTH["d_ih"] * step_scale
    return p4, q4, i4, ih4


def test_detect_profile_with_derived_stage():
    doc = _profile()
    sub = derive_stage_profile(doc, 0.4)
    prm = {"d2_max": 9.0, "min_confidence": 0.3, "k_sigma": 4.0, "margin": 1.5, "lambda_rel": 0.1,
           "state_check": 0, "max_scale": 1}
    p4, q4, i4, ih4 = _series(0.4)
    res = detect_profile(p4, q4, i4, sub, prm, False, "unknown", (), ih4)
    acc = [r for r in res if r["accepted"]]
    assert len(acc) == 1 and acc[0]["match"]["direction"] == "START"
    assert abs(acc[0]["onset"] - 100) <= 3 and acc[0]["match"]["d2_per_dim"] < 2.0
    # 同一段数据喂给"100 % 原画像"⇒ 不该认（档位不对）
    res2 = detect_profile(p4, q4, i4, doc, prm, False, "unknown", (), ih4)
    assert not any(r["accepted"] for r in res2)


# ---------------------------------------------------------------- ⑥ CLI
def _write_dev_csv(path, dur=20.0):
    n = int(FS * dur); t = np.arange(n) / FS; w = 2 * np.pi * F * t
    P = np.full(n, 100.0)
    for s, e in ((2.0, 6.0), (9.0, 13.0), (16.0, 19.5)):
        P[(t >= s) & (t < e)] += 500.0
    U, pf = 57.74, 0.9
    u = np.zeros((3, n)); i = np.zeros((3, n)); rng = np.random.default_rng(3)
    for k, ph in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        u[k] = U * np.sqrt(2) * np.sin(w + ph)
        i[k] = (P / 3) / (U * pf) * np.sqrt(2) * np.sin(w + ph - np.arccos(pf)) + rng.normal(0, 0.002, n)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(n):
            d = datetime.datetime.fromtimestamp(t[k])
            wr.writerow([f"0/00/00 {d:%H:%M:%S}.{int(round((t[k] % 1) * 10000)):04d}"]
                        + [f"{v:.5f}" for v in (u[0, k], i[0, k], u[1, k], i[1, k], u[2, k], i[2, k])])


def test_cli_derive_stages(tmp_path):
    from elec_tool.config import AppConfig
    dev = tmp_path / "dev.csv"; _write_dev_csv(str(dev))
    cfg = tmp_path / "cfg.json"
    c = AppConfig(); c.transform.enabled = False
    cfg.write_text(json.dumps(c.to_dict(), ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "p.json"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_profile.py"), "--file", str(dev), "--device", "pump",
                        "--config", str(cfg), "--out", str(out), "--pre", "10", "--post", "50", "--derive-stages", "0.5,0.7"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert "档位派生" in r.stdout and "可接受区间" in r.stdout
    for k in ("0.5", "0.7"):
        p = tmp_path / f"p_stage{k}.json"
        assert p.is_file(), r.stdout
        sub = load_profile(str(p))
        assert sub["device_id"] == f"pump@{float(k) * 100:g}%" and sub["stage"]["scale"] == float(k)
        assert "--derive-stages" in sub["command"] and "0.5,0.7" in sub["command"]
    # 网格模式
    r2 = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_profile.py"), "--file", str(dev), "--device", "pump",
                         "--config", str(cfg), "--out", str(out), "--pre", "10", "--post", "50", "--derive-grid", "3",
                         "--stage-out-dir", str(tmp_path / "grid")], capture_output=True, text=True, cwd=ROOT)
    assert r2.returncode == 0, r2.stderr
    # 网格 3 份以基准（k=1）为中心 ⇒ 中间那份就是基准画像本身，不再复制，故落盘 2 个文件
    assert len(list((tmp_path / "grid").glob("p_stage*.json"))) == 2
    assert "＝基准画像" in r2.stdout
    # 坏参数
    r3 = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_profile.py"), "--file", str(dev), "--device", "pump",
                         "--config", str(cfg), "--out", str(out), "--derive-stages", "abc"], capture_output=True, text=True, cwd=ROOT)
    assert r3.returncode == 2 and "倍数" in r3.stderr
