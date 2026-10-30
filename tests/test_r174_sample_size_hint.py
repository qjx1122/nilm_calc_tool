"""v0.99.27（第 174 轮）：**每方向 ≥3 个启停样本**的界面提示。

用户原话：「建议每方向 ≥3 个启停样本，这点修改代码在界面上给出提示」。

为什么要提示：σ 由样本估计——1 个样本时 σ=0，完全靠 `_REL_FLOOR` / `_ABS_FLOOR` 托底（ΔI/ΔP 15 %、ΔQ 25 %、ΔIh 15 %）；
2 个样本只有 1 个自由度。容差偏紧的直接后果第 167 轮已实录：单样本画像把一次幅值只差 20 % 的他负荷两级下跌
判成 `STOP confirmed 0.46`。所以这属于"数据不够、算法无解"的情形，必须在界面上讲清楚，而不是等用户去翻文档。

落点（同一段文字，四处复用 `sample_size_notes()`）：
1. 提取结果 JSON / CLI（`build_profile` 的 notes，CLI 打 `⚠`）；
2. `/api/process/nilm_profile` 返回值（`profile.sample_notes` + `notes`）→ 结果卡片标红；
3. `NilmDetector.summary()` 每画像的 `notes` → 负荷辨识页画像状态行标红；
4. `profile_summary()`（界面 / 工具共用）。
"""
from __future__ import annotations

import os

import pytest

from elec_tool.config import AppConfig
from elec_tool.nilm import NilmDetector
from elec_tool.nilm_profile import (FEATURES, MIN_EVENTS_PER_DIR, fit_group, profile_summary, sample_size_notes, save_profile)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HINT = "建议每方向 ≥3 次启停"


def _group(n: int, sign: float = 1.0):
    return fit_group([{"vec": {"d_ia": sign * 5.0, "d_ib": sign * 5.0, "d_ic": sign * 5.0, "d_p": sign * 866.0,
                               "d_q": sign * 902.0, "peak_ratio": 1.0, "dur_cycles": 2.0, "d_ih": 0.0},
                       "template": [1.0] * 16, "t_start": 1.7e9 + k, "onset": k * 100, "end": k * 100 + 2} for k in range(n)])


def _doc(n_start: int, n_stop: int):
    return {"schema": "nilm_profile/1", "device_id": "DEV", "version": "1.0", "quantity": "i", "unit": "A",
            "features": list(FEATURES), "pre_cycles": 10, "post_cycles": 50,
            "startup": _group(n_start, 1.0) if n_start else None,
            "shutdown": _group(n_stop, -1.0) if n_stop else None, "notes": []}


def test_constant_and_texts():
    assert MIN_EVENTS_PER_DIR == 3
    assert sample_size_notes(_doc(3, 3)) == []                       # 够了就不提示
    one = sample_size_notes(_doc(1, 1))
    assert len(one) == 2 and all(HINT in x for x in one)
    assert "启动画像只有 1 次事件" in one[0] and "停止画像只有 1 次事件" in one[1]
    assert "σ 取经验下限" in one[0] and "0.46" in one[0]              # 第 167 轮实录：单样本画像把他负荷判成 STOP 0.46
    two = sample_size_notes(_doc(2, 3))
    assert len(two) == 1 and "启动画像只有 2 次事件" in two[0]
    zero = sample_size_notes(_doc(0, 3))
    assert len(zero) == 1 and "没有启动事件样本" in zero[0] and HINT in zero[0]
    assert sample_size_notes({}) and len(sample_size_notes({})) == 2   # 空 doc 也不炸


def test_profile_summary_carries_min_events_and_notes():
    s = profile_summary(_doc(1, 3))
    assert s["min_events"] == 3 and len(s["sample_notes"]) == 1 and HINT in s["sample_notes"][0]
    assert profile_summary(_doc(3, 3))["sample_notes"] == []


def test_detector_summary_shows_hint_in_profile_row(tmp_path, monkeypatch):
    """负荷辨识页画像状态行（summary.profile.profiles[i].notes）要有提示；同时进全局 notes。"""
    p1 = str(tmp_path / "p1.json"); save_profile(_doc(1, 1), p1)
    cfg = AppConfig(); cfg.transform.enabled = False; cfg.nilm.profile_path = p1
    cfg.nilm.algorithms["profile"]["enabled"] = True; cfg.validate()
    det = NilmDetector(cfg, root=str(tmp_path))
    s = det.summary()
    row = s["profile"]["profiles"][0]
    assert row["loaded"] and any(HINT in x for x in row["notes"]), row["notes"]
    assert any(HINT in x for x in s["notes"])
    assert len(row["summary"]["sample_notes"]) == 2                    # 画像文件本身的提示（界面直接读这一份）
    # 画像文件自身也带 sample_notes（提取时就写进 notes 的同一段文字）
    p3 = str(tmp_path / "p3.json"); save_profile(_doc(3, 3), p3)
    cfg2 = AppConfig(); cfg2.transform.enabled = False; cfg2.nilm.profile_path = p3
    cfg2.nilm.algorithms["profile"]["enabled"] = True; cfg2.validate()
    s2 = NilmDetector(cfg2, root=str(tmp_path)).summary()
    assert s2["profile"]["profiles"][0]["notes"] == [] and not any(HINT in x for x in s2["notes"])


def test_old_seven_dim_profile_also_gets_hint(tmp_path):
    """旧 7 维画像（v0.99.25 及更早）同样按样本数提示——只读 startup/shutdown 的 n，不看特征维数。"""
    from elec_tool.nilm_profile import LEGACY_FEATURES
    d = _doc(1, 3)
    for k in ("startup", "shutdown"):
        d[k]["mu"] = d[k]["mu"][:len(LEGACY_FEATURES)]
        d[k]["sigma"] = d[k]["sigma"][:len(LEGACY_FEATURES)]
    d["features"] = list(LEGACY_FEATURES)
    p = str(tmp_path / "old.json"); save_profile(d, p)
    cfg = AppConfig(); cfg.transform.enabled = False; cfg.nilm.profile_path = p
    cfg.nilm.algorithms["profile"]["enabled"] = True; cfg.validate()
    s = NilmDetector(cfg, root=str(tmp_path)).summary()
    assert any("启动画像只有 1 次事件" in x for x in s["profile"]["profiles"][0]["notes"])


def test_api_profile_returns_sample_notes(tmp_path, monkeypatch):
    """提取接口：1 次启动 + 1 次停止 ⇒ 返回 profile.sample_notes 与 notes 都带提示（界面据此标红）。"""
    import csv
    import datetime

    import numpy as np

    monkeypatch.setenv("ELEC_TOOL_AUTOSTART", "")
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path))
    fs, f, t0 = 6400.0, 50.0, 1.79e9
    n = int(fs * 6.0); t = np.arange(n) / fs; w = 2 * np.pi * f * t
    P = np.full(n, 100.0); P[(t >= 2.0) & (t < 4.0)] += 500.0
    i = (P / 3) / (57.74 * 0.9) * np.sqrt(2) * np.sin(w - np.arccos(0.9))
    u = 57.74 * np.sqrt(2) * np.sin(w)
    path = str(tmp_path / "dev.csv")
    with open(path, "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(n):
            d = datetime.datetime.fromtimestamp(t0 + t[k])
            wr.writerow([f"0/00/00 {d:%H:%M:%S}.{int(round((t[k] % 1) * 10000)):04d}"] + [f"{v:.5f}" for v in (u[k], i[k], u[k], i[k], u[k], i[k])])
    from fastapi.testclient import TestClient
    import app.server as srv
    with TestClient(srv.app) as c:
        r = c.post("/api/process/nilm_profile", json={"path": path, "device_id": "one",
                                                      "labels": (f"{datetime.datetime.fromtimestamp(t0 + 2):%H:%M:%S},开\n"
                                                                 f"{datetime.datetime.fromtimestamp(t0 + 4):%H:%M:%S},关"),
                                                      "base": {"pt_ct_enabled": False}})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["profile"]["startup"]["n"] == 1 and j["profile"]["shutdown"]["n"] == 1
        assert j["profile"]["min_events"] == 3
        assert len(j["profile"]["sample_notes"]) == 2 and all(HINT in x for x in j["profile"]["sample_notes"])
        assert sum(1 for x in j["notes"] if HINT in x) == 2            # 不重复


def test_ui_exposes_hint():
    js = open(os.path.join(ROOT, "app", "static", "app.js"), encoding="utf-8").read()
    html = open(os.path.join(ROOT, "app", "static", "index.html"), encoding="utf-8").read()
    assert "sample_notes" in js and "min_events" in js and "建议各 ≥" in js and "样本量不足" in js
    assert "建议每方向 ≥3 次启停" in html and "<b>样本量</b>" in html
