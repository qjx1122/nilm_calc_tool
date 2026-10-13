"""第 12 轮：负荷辨识子界面 · 逐周波事件检测（6 种算法、方向/幅值/时刻、参数可配、CSV 落盘、REST、前端接线）。

合成信号：三相 57.74 V，P 总 1000 W → 2.0 s 投入 +500 W → 4.4 s 切除 −300 W，3.0 s 处 1 个周波 +400 W 尖峰。
PT=100 / CT=15 默认启用 → 一次侧 1.5 MW / +750 kW / −450 kW。
"""
from __future__ import annotations

import csv
import os
import shutil
import time
from pathlib import Path

import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, ConfigError, NILM_ALGO_DEFAULTS, NilmConfig
from elec_tool.engine import LiveEngine
from elec_tool.nilm import CycleFeatures, NilmDetector, detect_steps, effective_params

ROOT = Path(__file__).resolve().parents[1]
FS, F = 6400, 50.0
T_UP, T_DOWN, T_SPIKE = 2.0, 4.4, 3.0


def _wave(dur=6.0, noise=0.002, base=1.79e9):
    n = int(FS * dur); t = np.arange(n) / FS; w = 2 * np.pi * F * t
    P = np.full(n, 1000.0); P[t >= T_UP] += 500; P[t >= T_DOWN] -= 300
    P[int(T_SPIKE * FS):int(T_SPIKE * FS) + 128] += 400
    U, ang = 57.74, np.arccos(0.9)
    u = np.zeros((3, n)); i = np.zeros((3, n))
    rng = np.random.default_rng(1)
    for k, ph in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        u[k] = U * np.sqrt(2) * np.sin(w + ph)
        i[k] = (P / 3) / (U * 0.9) * np.sqrt(2) * np.sin(w + ph - ang) + rng.normal(0, noise, n)
    return base + t, u, i


def _write_csv(path, dur=6.0):
    t, u, i = _wave(dur)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(t.size):
            wr.writerow([f"{t[k]:.6f}", f"{u[0,k]:.5f}", f"{i[0,k]:.5f}", f"{u[1,k]:.5f}", f"{i[1,k]:.5f}", f"{u[2,k]:.5f}", f"{i[2,k]:.5f}"])
    return str(path)


# ------------------------------------------------------------------ 算法层
def test_all_algorithms_find_both_steps_and_ignore_spike():
    rng = np.random.default_rng(0)
    p = np.full(300, 1000.0); p[100:] += 500; p[220:] -= 300; p += rng.normal(0, 2, 300); p[150] += 400
    for a, prm in NILM_ALGO_DEFAULTS.items():
        steps = detect_steps(a, p, prm)
        real = [s for s in steps if abs(s[3] - s[2]) >= 200]
        assert len(real) == 2, (a, steps)
        (o1, e1, pre1, post1, _), (o2, e2, pre2, post2, _) = real
        assert abs(o1 - 100) <= 1 and abs(o2 - 220) <= 1, (a, o1, o2)
        assert post1 - pre1 == pytest.approx(500, abs=15) and post2 - pre2 == pytest.approx(-300, abs=15), a
        assert e1 >= o1 and e2 >= o2
        if a not in ("two_window",):                                     # 双滑窗按均值摊尖峰（已在文档说明）
            assert len(steps) == 2, (a, steps)


def test_effective_params_scale_with_level():
    prm = effective_params(NILM_ALGO_DEFAULTS["threshold"], level=1.5e6, rel_tol_pct=1.0, min_delta_pct=2.0)
    assert prm["settle_tol_w"] == pytest.approx(15000) and prm["min_delta_w"] == pytest.approx(30000)
    prm2 = effective_params(NILM_ALGO_DEFAULTS["threshold"], level=100.0, rel_tol_pct=1.0, min_delta_pct=0.0)
    assert prm2["settle_tol_w"] == 20.0 and prm2["min_delta_w"] == 50.0                 # 绝对值更大时保留绝对值


def test_cycle_features_exact_pq_and_carry():
    t, u, i = _wave(0.5)
    cf = CycleFeatures(FS, F)
    assert cf.n_cycle == 128 and cf.exact
    # 以 100 点的零头块喂入，周波跨块结转不丢
    got = []
    for a in range(0, t.size, 100):
        f = cf.push(SampleBlock(t=t[a:a + 100], u=u[:, a:a + 100], i=i[:, a:a + 100]))
        got.append(f)
    tt = np.concatenate([g["t"] for g in got]); p = np.concatenate([g["p"] for g in got], axis=1)
    q = np.concatenate([g["q"] for g in got], axis=1)
    assert tt.size == 25 and np.allclose(np.diff(tt), 128 / FS, atol=1e-6)      # epoch 量级 double 精度 ~2.4e-7 s
    assert np.allclose(p[0], 1000, atol=1.0) and np.allclose(p[1:], 1000 / 3, atol=0.5)
    assert np.allclose(q[0], 1000 * np.tan(np.arccos(0.9)), atol=1.5)                    # 感性 Q 为正


# ------------------------------------------------------------------ 检测器 + 引擎 + CSV
def test_engine_detects_direction_magnitude_time_and_writes_csv(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    p = _write_csv(tmp_path / "steps.csv")
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = p; cfg.validate()
    eng = LiveEngine(cfg)
    for _ in eng.run():
        pass
    evs = eng.nilm.list(limit=100)
    by_algo = {}
    for e in evs:
        by_algo.setdefault(e["algorithm"], []).append(e)
    for a in NILM_ALGO_DEFAULTS:
        big = sorted([e for e in by_algo.get(a, []) if e["magnitude_w"] > 3e5], key=lambda e: e["t_start"])
        assert len(big) == 2, (a, by_algo.get(a))
        up, down = big
        assert up["direction"] == "up" and down["direction"] == "down"
        assert up["magnitude_w"] == pytest.approx(750e3, rel=0.01) and down["magnitude_w"] == pytest.approx(450e3, rel=0.01)
        assert up["t_start"] - 1.79e9 == pytest.approx(T_UP, abs=0.021) and down["t_start"] - 1.79e9 == pytest.approx(T_DOWN, abs=0.021)
        assert up["t_end"] >= up["t_start"] and up["delta_q_var"] > 0 and down["delta_i_a"] < 0
        assert up["channel"] == "total" and up["algorithm_name"]
    sm = eng.nilm.summary()
    assert sm["cycles_total"] == 300 and sm["n_cycle_samples"] == 128 and sm["by_direction"]["up"] >= 6
    assert eng.state.nilm_events_total == len(evs) and eng.state.nilm_cycles == 300
    # CSV：算法类型、起止时间、方向、幅值
    files = list((tmp_path / "nilm").glob("nilm_events_*.csv"))
    assert len(files) == 1
    with open(files[0], encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(evs) == sm["writer"]["rows_written"]
    r = next(x for x in rows if x["algorithm"] == "steady_state" and x["direction"] == "down")
    assert {"algorithm_name", "t_start", "t_start_local", "t_end", "t_end_local", "direction", "magnitude_w", "delta_p_w", "channel"} <= set(r)
    assert float(r["magnitude_w"]) == pytest.approx(450e3, rel=0.01) and float(r["delta_p_w"]) < 0 and float(r["t_end"]) >= float(r["t_start"])


def test_detector_dedupes_across_blocks_and_respects_disable(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    t, u, i = _wave(6.0)
    cfg = AppConfig()
    cfg.nilm.algorithms["two_window"]["enabled"] = False
    cfg.nilm.algorithms["cusum"]["enabled"] = False
    cfg.nilm.channels = ["total", "A"]
    cfg.validate()
    det = NilmDetector(cfg)
    emitted = []
    for a in range(0, t.size, 640):                                        # 块边界与周波不对齐也只报一次
        emitted += det.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    assert not any(e["algorithm"] in ("two_window", "cusum") for e in emitted)
    key = {}
    for e in emitted:
        key.setdefault((e["algorithm"], e["channel"], e["direction"]), []).append(e)
    for a in ("threshold", "glr", "steady_state", "median_diff"):
        for ch in ("total", "A"):
            assert len(key[(a, ch, "up")]) == 1 and len(key[(a, ch, "down")]) == 1, (a, ch)
    a_up = key[("glr", "A", "up")][0]
    assert a_up["magnitude_w"] == pytest.approx(500 / 3, rel=0.02)          # 直接喂未变换块＝二次侧 W；分相 = 总/3
    assert det.summary()["algorithms_enabled"] == ["threshold", "glr", "steady_state", "median_diff"]
    assert det.cycles(50)["channels"]["A"]["p"][-1] == pytest.approx(1200 / 3, rel=0.02)
    # 禁用后不再产出
    cfg.nilm.enabled = False
    det.update_config(cfg)
    assert det.ingest(SampleBlock(t=t[:640] + 10, u=u[:, :640], i=i[:, :640])) == []


def test_config_validation_and_roundtrip():
    c = AppConfig()
    c.nilm.algorithms["glr"]["threshold"] = -1
    with pytest.raises(ConfigError, match="nilm.algorithms.glr.threshold"):
        c.validate()
    c = AppConfig(); c.nilm.channels = ["X"]
    with pytest.raises(ConfigError, match="nilm.channels"):
        c.validate()
    c = AppConfig(); c.nilm.window_cycles = 20
    with pytest.raises(ConfigError, match="window_cycles"):
        c.validate()
    c = AppConfig(); c.nilm.algorithms["threshold"]["settle_cycles"] = 2.5
    with pytest.raises(ConfigError, match="整数周波数"):
        c.validate()
    c = AppConfig(); c.nilm.algorithms["cusum"]["threshold_w"] = 999
    d = c.validate().to_dict()
    assert d["nilm"]["algorithms"]["cusum"]["threshold_w"] == 999
    c2 = AppConfig.from_dict({"nilm": {"algorithms": {"cusum": {"threshold_w": 123, "bogus": 1}}, "channels": ["B"]}})
    assert c2.nilm.params("cusum")["threshold_w"] == 123 and "bogus" not in c2.nilm.algorithms["cusum"]
    assert c2.nilm.params("glr") == NILM_ALGO_DEFAULTS["glr"] and c2.nilm.channels == ["B"]
    with pytest.raises(ConfigError, match="未知算法"):
        NilmConfig(algorithms={"nope": {}}).validate()


# ------------------------------------------------------------------ Web
@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r12cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0"); mp.setenv("ELEC_TOOL_EVENTS_DIR", str(d / "ev"))
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(d / "rt")); mp.setenv("ELEC_TOOL_NILM_DIR", str(d / "nilm"))
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


def test_web_nilm_endpoints_config_and_playback(client):
    p = _write_csv(client.dir / "w.csv", dur=6.0)
    client.post("/api/engine/stop")
    r = client.get("/api/nilm/events").json()
    assert r["ok"] and r["events"] == [] and "counts" in r["summary"]
    # 参数热更新（深合并）与校验
    r = client.put("/api/config", json={"nilm": {"min_delta_pct": 5.0, "algorithms": {"glr": {"threshold": 30}}}})
    assert r.status_code == 200, r.text
    nc = r.json()["config"]["nilm"]
    assert nc["min_delta_pct"] == 5.0 and nc["algorithms"]["glr"]["threshold"] == 30 and nc["algorithms"]["glr"]["noise_w"] == 10.0
    assert client.put("/api/config", json={"nilm": {"algorithms": {"glr": {"threshold": 0}}}}).status_code == 400
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": p, "realtime": False})
    assert r.status_code == 200, r.text
    deadline = time.time() + 20
    while time.time() < deadline:
        st = client.get("/api/state").json()
        if st.get("finished") or st.get("error"):
            break
        time.sleep(0.2)
    d = client.get("/api/nilm/events?limit=100").json()
    assert d["summary"]["total"] >= 12 and st["engine"]["nilm_events_total"] == d["summary"]["total"] and st["engine"]["nilm_cycles"] == 300
    algos = {e["algorithm"] for e in d["events"]}
    assert algos == set(NILM_ALGO_DEFAULTS)                                  # min_delta_pct=5% 后双滑窗的尖峰小事件被滤掉
    assert all(e["magnitude_w"] > 3e5 for e in d["events"])
    f = client.get("/api/nilm/events?algos=glr,cusum&channel=total").json()["events"]
    assert f and {e["algorithm"] for e in f} <= {"glr", "cusum"}
    c = client.get("/api/nilm/cycles?n=50").json()
    assert c["ok"] and len(c["t"]) == 50 and len(c["channels"]["total"]["p"]) == 50 and c["channels"]["total"]["p"][-1] == pytest.approx(1.8e6, rel=0.02)
    assert d["summary"]["writer"]["rows_written"] == d["summary"]["total"]
    r = client.post("/api/nilm/clear").json()
    assert r["ok"] and r["removed"] == d["summary"]["total"] and client.get("/api/nilm/events").json()["summary"]["total"] == 0
    client.post("/api/engine/stop")
    client.put("/api/config", json={"nilm": {"min_delta_pct": 0.0, "algorithms": {"glr": {"threshold": 25}}}})


def test_frontend_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'data-view="nilm"' in html and 'id="view-nilm"' in html
    for i in ("nilm-cards", "nilm-chart", "nilm-table", "nilm-filter", "nilm-algos", "btn-nilm-save", "btn-nilm-clear", "nilm-enabled", "nilm-rel_tol_pct"):
        assert f'id="{i}"' in html, i
    for a in NILM_ALGO_DEFAULTS:
        assert f"{a}:" in js.split("const NILM_ALGOS")[1].split("};")[0], a
        for k in NILM_ALGO_DEFAULTS[a]:
            if k != "enabled":
                assert f"{k}:" in js, (a, k)
    assert "case 'nilm': renderNilm(); break;" in js and "m.type === 'nilm_event'" in js
    assert "JSON.stringify({ nilm: payload })" in js and "/api/nilm/cycles" in js and "opt.marks" in js
