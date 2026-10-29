"""v0.90：基于设备画像的事件检测（elec_tool.nilm_profile + NilmDetector profile 算法 + API + CLI）。

合成数据：设备侧 500 W 设备（0.3 s 冲击 1.6×）三次启停 → 画像；总线侧 3000 W 基荷 + 该设备 1 次启停 +
1500 W 他设备启停 + 120 W 小负荷 → 应只报出该设备的 START/STOP，他设备被拒识。
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

from elec_tool.blocks import SampleBlock
from elec_tool.config import NILM_ALGO_DEFAULTS, NILM_SCALAR_ALGOS, AppConfig, ConfigError
from elec_tool.nilm import NilmDetector
from elec_tool.nilm_auto import auto_params
from elec_tool.nilm_profile import (FEATURES, ProfileError, build_profile, detect_profile, load_profile, match_event, parse_labels,
                                    save_profile)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
            wr.writerow([f"0/00/00 {d:%H:%M:%S}.{int(round((t[k] % 1) * 10000)):04d}"] + [f"{v:.5f}" for v in (u[0, k], i[0, k], u[1, k], i[1, k], u[2, k], i[2, k])])


DEV_EVENTS = ((2.0, "开"), (5.0, "关"), (8.0, "开"), (11.0, "关"), (14.0, "开"), (17.5, "关"))


def _dev(t):
    P = np.full(t.size, 100.0)
    for s, e in ((2.0, 5.0), (8.0, 11.0), (14.0, 17.5)):
        P[(t >= s) & (t < e)] += 500; P[(t >= s) & (t < s + 0.3)] += 300
    return P


def _bus(t):
    P = np.full(t.size, 3000.0)
    P[(t >= 3.0) & (t < 9.0)] += 500; P[(t >= 3.0) & (t < 3.3)] += 300        # 目标设备
    P[(t >= 5.0) & (t < 12.0)] += 1500                                        # 他设备
    P[t >= 6.5] += 120                                                        # 小负荷
    return P


@pytest.fixture(scope="module")
def dev_csv(tmp_path_factory):
    d = tmp_path_factory.mktemp("prof")
    t, u, i = _wave(_dev, 20.0)
    p = str(d / "dev.csv"); _write_csv(p, t, u, i)
    return p


@pytest.fixture(scope="module")
def base_cfg():
    cfg = AppConfig(); cfg.transform.enabled = False; cfg.validate(); return cfg


def _labels():
    return "\n".join(f"{datetime.datetime.fromtimestamp(T0 + s):%H:%M:%S},{a}" for s, a in DEV_EVENTS)


@pytest.fixture(scope="module")
def profile_path(dev_csv, base_cfg, tmp_path_factory):
    doc = build_profile(base_cfg, dev_csv, device_id="pumpA", labels=_labels(), pre_cycles=10, post_cycles=50)
    p = str(tmp_path_factory.mktemp("prof_out") / "pumpA.json"); save_profile(doc, p); return p


# ---------------------------------------------------------------- 配置
def test_config_profile_defaults():
    assert "profile" in NILM_ALGO_DEFAULTS and NILM_ALGO_DEFAULTS["profile"]["enabled"] is False
    assert "profile" not in NILM_SCALAR_ALGOS and len(NILM_SCALAR_ALGOS) == 6
    cfg = AppConfig(); cfg.nilm.algorithms["profile"]["state_check"] = 0; cfg.validate()      # state_check 允许 0
    cfg.nilm.algorithms["profile"]["d2_max"] = 0
    with pytest.raises(ConfigError):
        cfg.validate()
    assert AppConfig.from_dict({"nilm": {"profile_path": " a.json "}}).nilm.profile_path == "a.json"


def test_auto_params_skips_profile():
    rng = np.random.default_rng(0)
    out = auto_params(1000 + rng.normal(0, 5, 400))
    assert set(out["algorithms"]) == set(NILM_SCALAR_ALGOS)


# ---------------------------------------------------------------- 标签解析与画像构建
def test_parse_labels():
    rows = parse_labels("时间,动作\n08:00:02.5,开\n1790000005,off\n2026-10-13 08:00:10,start\n# 注释\n", day_hint=T0)
    assert [r["direction"] for r in rows] == ["START", "STOP", "START"] and rows[0]["t"] > T0 - 86400
    with pytest.raises(ProfileError):
        parse_labels("08:00:02,跳舞", day_hint=T0)


def test_build_profile_with_labels(dev_csv, base_cfg):
    doc = build_profile(base_cfg, dev_csv, device_id="pumpA", labels=_labels(), pre_cycles=10, post_cycles=50)
    assert doc["schema"].startswith("nilm_profile") and doc["features"] == FEATURES and doc["quantity"] == "p"
    st, sd = doc["startup"], doc["shutdown"]
    assert st["n"] == 3 and sd["n"] == 3
    mu = dict(zip(FEATURES, st["mu"]))
    assert abs(mu["d_p"] - 500) < 10 and 1.4 < mu["peak_ratio"] < 1.8 and mu["d_ia"] > 2.5
    assert abs(dict(zip(FEATURES, sd["mu"]))["d_p"] + 500) < 10
    # 启动点对齐到标签时刻（±1 周波；文件时标 0/00/00 无日期，只比较当天时刻）
    for e, (s, _) in zip(st["events"], [x for x in DEV_EVENTS if x[1] == "开"]):
        assert abs(((e["t_start"] - (T0 + s)) + 43200) % 86400 - 43200) <= 0.021
    assert all(s > 0 for s in st["sigma"])          # σ 有下限，单样本 / 完全一致样本也不为 0
    assert doc["calibration"]["bus_mapping"] is None


def test_build_profile_auto(dev_csv, base_cfg):
    doc = build_profile(base_cfg, dev_csv, device_id="pumpA", labels=None)
    assert doc["label_mode"] == "auto" and doc["startup"]["n"] == 3 and doc["shutdown"]["n"] == 3


def test_build_profile_errors(dev_csv, base_cfg):
    with pytest.raises(ProfileError):
        build_profile(base_cfg, dev_csv, device_id="x", labels="23:59:59,开")      # 标签不在文件内
    with pytest.raises(ProfileError):
        load_profile(os.path.join(ROOT, "configs", "default.json"))                 # 不是画像文件


# ---------------------------------------------------------------- 匹配
def test_match_event_direction_and_confidence(profile_path):
    prof = load_profile(profile_path)
    st = prof["startup"]
    feat = {"vec": dict(zip(FEATURES, st["mu"])), "template": np.asarray(st["template"])}
    m = match_event(prof, feat, 0.1)
    assert m["direction"] == "START" and m["confidence"] > 0.95 and m["d2"] < 1.0
    feat2 = {"vec": dict(zip(FEATURES, prof["shutdown"]["mu"])), "template": np.asarray(prof["shutdown"]["template"])}
    assert match_event(prof, feat2, 0.1)["direction"] == "STOP"
    far = dict(feat["vec"]); far["d_p"] *= 3; far["d_ia"] *= 3; far["d_ib"] *= 3; far["d_ic"] *= 3
    m3 = match_event(prof, {"vec": far, "template": feat["template"]}, 0.1)
    assert m3["confidence"] < 0.05


def _run_bus(profile_path, **algo):
    cfg = AppConfig(); cfg.transform.enabled = False
    cfg.nilm.profile_path = profile_path; cfg.nilm.save = False
    for a in NILM_SCALAR_ALGOS:
        cfg.nilm.algorithms[a]["enabled"] = False
    cfg.nilm.algorithms["profile"].update({"enabled": True, **algo})
    cfg.validate()
    det = NilmDetector(cfg)
    t, u, i = _wave(_bus, 16.0, seed=2)
    evs = []
    for a in range(0, t.size, 640):
        evs += det.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    return det, evs


def test_detector_bus_side(profile_path):
    det, evs = _run_bus(profile_path)
    assert [(e["profile_direction"], round(e["t_start"] - T0, 1)) for e in evs] == [("START", 3.0), ("STOP", 9.0)]
    for e in evs:
        assert e["algorithm"] == "profile" and e["channel"] == "total" and e["device_id"] == "pumpA"
        assert e["confidence"] > 0.8 and e["status"] == "confirmed" and abs(abs(e["delta_p_w"]) - 500) < 15
        assert e["estimated_device_delta_p"] is None and e["observed_delta_p"] == e["delta_p_w"]
    assert evs[0]["direction"] == "up" and evs[1]["direction"] == "down"
    sm = det.summary()
    assert sm["profile"]["loaded"] and sm["profile"]["device_state"] == "off" and sm["counts"]["profile"] == 2
    assert any("设备画像匹配：设备 pumpA" in n for n in sm["notes"])
    assert "profile" in sm["algorithms_enabled"]


def test_detector_state_machine_blocks_double_start(profile_path):
    # 两次连续「启动」：第二次在 ON 状态下 → state_mismatch 降置信（仍可能 low_confidence 报出），不得是 confirmed
    def two_starts(t):
        P = np.full(t.size, 3000.0)
        P[t >= 3.0] += 500; P[(t >= 3.0) & (t < 3.3)] += 300
        P[t >= 7.0] += 500; P[(t >= 7.0) & (t < 7.3)] += 300
        return P
    cfg = AppConfig(); cfg.transform.enabled = False; cfg.nilm.profile_path = profile_path; cfg.nilm.save = False
    for a in NILM_SCALAR_ALGOS:
        cfg.nilm.algorithms[a]["enabled"] = False
    cfg.nilm.algorithms["profile"]["enabled"] = True; cfg.validate()
    det = NilmDetector(cfg); t, u, i = _wave(two_starts, 11.0, seed=3); evs = []
    for a in range(0, t.size, 640):
        evs += det.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    assert evs and evs[0]["status"] == "confirmed" and round(evs[0]["t_start"] - T0, 1) == 3.0
    for e in evs[1:]:
        assert "state_mismatch" in e["quality_flags"] and e["status"] != "confirmed"
    # 关闭状态机 → 第二次也 confirmed
    cfg.nilm.algorithms["profile"]["state_check"] = 0; det2 = NilmDetector(cfg); evs2 = []
    for a in range(0, t.size, 640):
        evs2 += det2.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    assert [e["status"] for e in evs2] == ["confirmed", "confirmed"]


def test_detector_missing_profile_reports(tmp_path):
    cfg = AppConfig(); cfg.transform.enabled = False; cfg.nilm.save = False
    cfg.nilm.profile_path = str(tmp_path / "nope.json"); cfg.nilm.algorithms["profile"]["enabled"] = True; cfg.validate()
    det = NilmDetector(cfg); sm = det.summary()
    assert sm["profile"]["loaded"] is False and "画像加载失败" in (sm["profile"]["error"] or "")
    assert any("画像加载失败" in n for n in sm["notes"])
    cfg.nilm.profile_path = ""; det.update_config(cfg)
    assert any("profile_path 为空" in n for n in det.summary()["notes"])


def test_csv_roundtrip(profile_path, tmp_path):
    from elec_tool.replay_load import load_nilm_events
    cfg = AppConfig(); cfg.transform.enabled = False; cfg.nilm.profile_path = profile_path
    cfg.nilm.save = True; cfg.nilm.nilm_dir = str(tmp_path)
    for a in NILM_SCALAR_ALGOS:
        cfg.nilm.algorithms[a]["enabled"] = False
    cfg.nilm.algorithms["profile"]["enabled"] = True; cfg.validate()
    det = NilmDetector(cfg, root=str(tmp_path)); t, u, i = _wave(_bus, 16.0, seed=2); evs = []
    for a in range(0, t.size, 640):
        evs += det.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    det.writer.close()
    rows = load_nilm_events(det.writer.info()["dir"], 0)          # conftest 用 ELEC_TOOL_NILM_DIR 覆盖落盘目录
    assert len(rows) == 2 and rows[0]["device_id"] == "pumpA" and rows[0]["profile_direction"] == "START" and rows[0]["confidence"] > 0.8
    det2 = NilmDetector(cfg, root=str(tmp_path)); det2.load_events(rows)
    assert det2.summary()["counts"]["profile"] == 2 and det2._log[0].device_id == "pumpA"


# ---------------------------------------------------------------- CLI 与 API
def test_cli(dev_csv, tmp_path):
    lab = tmp_path / "lab.csv"; lab.write_text("时间,动作\n" + _labels().replace("\n", "\n") + "\n", encoding="utf-8")
    out = tmp_path / "p.json"
    cfg = tmp_path / "cfg.json"; c = AppConfig(); c.transform.enabled = False; cfg.write_text(json.dumps(c.to_dict(), ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_profile.py"), "--file", dev_csv, "--device", "pumpA", "--labels", str(lab),
                        "--config", str(cfg), "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert "启动画像：3 次事件" in r.stdout and out.is_file()
    doc = json.load(open(out, encoding="utf-8")); assert doc["device_id"] == "pumpA" and "command" in doc


def test_api_profile(dev_csv, tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_AUTOSTART", ""); monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path))
    from fastapi.testclient import TestClient
    import app.server as srv
    with TestClient(srv.app) as c:
        r = c.post("/api/process/nilm_profile", json={"path": dev_csv, "device_id": "pumpA", "labels": _labels(), "base": {"pt_ct_enabled": False}})
        assert r.status_code == 200, r.text
        j = r.json(); assert j["ok"] and j["profile"]["startup"]["n"] == 3 and len(j["events"]) == 6
        assert os.path.isfile(j["saved_to"]) and "tools/nilm_profile.py" in j["command"]
        r2 = c.post("/api/branch/process/nilm_profile", json={"path": dev_csv, "device_id": "pumpA", "base": {"pt_ct_enabled": False}})
        assert r2.status_code == 200 and r2.json()["profile"]["label_mode"] == "auto" and r2.json()["side"] == "branch"
        r3 = c.post("/api/process/nilm_profile", json={"path": dev_csv, "labels": "xx"})
        assert r3.status_code == 400 and "标签" in r3.json()["error"]
        r4 = c.post("/api/process/nilm_profile", json={"path": "/no/such.csv"})
        assert r4.status_code == 400


def test_ui_assets_mention_profile():
    js = open(os.path.join(ROOT, "app", "static", "app.js"), encoding="utf-8").read()
    html = open(os.path.join(ROOT, "app", "static", "index.html"), encoding="utf-8").read()
    assert "profile:" in js and "nilm-profile_path" in js and "/api/process/nilm_profile" in js and "nilmProfileCell" in js
    assert 'id="np-form"' in html and 'id="btn-np-fill-bus"' in html and 'id="np-labels"' in html


# ---------------------------------------------------------------- v0.99.6：相序映射 + PT/CT 口径判定修正
def test_phase_map_remap_and_auto(profile_path):
    from elec_tool.nilm_profile import PHASE_MAPS, phase_map_code, remap_phases
    prof = load_profile(profile_path)
    st = prof["startup"]
    vec = dict(zip(FEATURES, st["mu"]))
    # 构造不平衡的分相特征，使相序可辨：ΔIa=3, ΔIb=1, ΔIc=0.5（画像以此为准）
    prof2 = json.loads(json.dumps(prof))
    for g in ("startup", "shutdown"):
        mu = list(prof2[g]["mu"]); mu[0], mu[1], mu[2] = 3.0, 1.0, 0.5
        prof2[g]["sigma"][0] = prof2[g]["sigma"][1] = prof2[g]["sigma"][2] = 0.1
        prof2[g]["mu"] = mu
    dev = dict(vec); dev["d_ia"], dev["d_ib"], dev["d_ic"] = 3.0, 1.0, 0.5
    # 总线侧 A 相上接的是设备 B 相、B 上是设备 C、C 上是设备 A ⇒ mapping "BCA"：bus[A]=dev B=1.0, bus[B]=dev C=0.5, bus[C]=dev A=3.0
    bus = dict(dev); bus["d_ia"], bus["d_ib"], bus["d_ic"] = 1.0, 0.5, 3.0
    assert remap_phases(bus, "BCA")["d_ia"] == 3.0 and remap_phases(bus, "BCA")["d_ic"] == 0.5
    feat = {"vec": bus, "template": np.asarray(st["template"])}
    m_abc = match_event(prof2, feat, 0.1, (), 1)
    m_bca = match_event(prof2, feat, 0.1, (), 4)
    m_auto = match_event(prof2, feat, 0.1, (), 0)
    assert m_bca["d2"] < m_abc["d2"] and m_bca["phase_map"] == "BCA"
    assert m_auto["phase_map"] == "BCA" and m_auto["phase_map_auto"] and abs(m_auto["d2"] - m_bca["d2"]) < 1e-9
    assert phase_map_code("auto") == 0 and phase_map_code("bca") == 4 and phase_map_code(6) == 6 and PHASE_MAPS[1] == "ABC"
    with pytest.raises(ProfileError):
        phase_map_code(7)


def test_config_phase_map_validation():
    cfg = AppConfig(); cfg.nilm.algorithms["profile"]["phase_map"] = 0; cfg.validate()
    cfg.nilm.algorithms["profile"]["phase_map"] = 7
    with pytest.raises(ConfigError):
        cfg.validate()
    cfg.nilm.algorithms["profile"]["phase_map"] = 4; cfg.validate()


def test_detector_auto_phase_map_still_detects(profile_path):
    det, evs = _run_bus(profile_path, phase_map=0)
    pe = [e for e in evs if e["algorithm"] == "profile"]
    assert [e["profile_direction"] for e in pe] == ["START", "STOP"]
    assert all(e["status"] == "confirmed" for e in pe)        # 平衡负荷下自动相序取 ABC，不产生 phase_map_* 标志


def test_ptct_check_primary_side_ratios_may_differ(profile_path, tmp_path):
    """两侧都启用 PT/CT 但变比不同 ⇒ 一次侧口径一致，应正常匹配（旧版误判为口径不一致）。"""
    prof = load_profile(profile_path)
    prof["pt_ct"] = {"enabled": True, "pt_ratio": 1.0, "ct_ratio": 15.0}
    p2 = str(tmp_path / "prof_primary.json"); save_profile(prof, p2)
    cfg = AppConfig(); cfg.transform.enabled = True; cfg.transform.pt_ratio = 1.0; cfg.transform.ct_ratio = 40.0
    cfg.nilm.profile_path = p2; cfg.nilm.save = False
    for a in NILM_SCALAR_ALGOS:
        cfg.nilm.algorithms[a]["enabled"] = False
    cfg.nilm.algorithms["profile"]["enabled"] = True; cfg.validate()
    det = NilmDetector(cfg)
    t, u, i = _wave(_bus, 4.0, seed=2)
    for a in range(0, t.size, 640):
        det.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    assert not any("口径不一致" in e for e in det.errors)
    # 一侧启用一侧关闭 ⇒ 拒绝
    cfg2 = AppConfig(); cfg2.transform.enabled = False; cfg2.nilm.profile_path = p2; cfg2.nilm.save = False
    for a in NILM_SCALAR_ALGOS:
        cfg2.nilm.algorithms[a]["enabled"] = False
    cfg2.nilm.algorithms["profile"]["enabled"] = True; cfg2.validate()
    det2 = NilmDetector(cfg2)
    for a in range(0, t.size, 640):
        det2.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    assert any("口径不一致" in e for e in det2.errors)
