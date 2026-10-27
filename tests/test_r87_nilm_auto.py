"""v0.87：负荷辨识「启用自适应算法参数」（只有总线数据场景）——参数由周波窗数据推导，人工不再手填。"""
from __future__ import annotations

import pathlib
import shutil

import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, NILM_ALGO_DEFAULTS
from elec_tool.nilm import NilmDetector, detect_steps
from elec_tool.nilm_auto import AUTO_MIN_CYCLES, auto_params, window_stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS, F = 6400.0, 50.0


def _steps_series(seed=1, L=1200, base=50000.0, sigma=80.0):
    rng = np.random.default_rng(seed)
    p = base + rng.normal(0, sigma, L)
    p[300:320] += np.linspace(0, 12000, 20); p[320:] += 12000; p[700:] -= 12000
    return p


def test_window_stats_white_noise_and_all_algos_detect_both_steps():
    p = _steps_series()
    st = window_stats(p, F)
    assert st["hold"] == 1 and abs(st["sigma"] - 80) < 15 and st["settle"] >= 3 and st["min_steady"] >= 5
    assert 20 <= st["transient"] <= 400 and 4.5 < st["k"] < 6.5 and st["min_delta"] >= 4 * st["sigma"]
    ap = auto_params(p, F)
    for a, prm in ap["algorithms"].items():
        steps = detect_steps(a, p, prm)
        ons = [o for o, *_ in steps]
        assert any(295 <= o <= 325 for o in ons) and any(695 <= o <= 705 for o in ons), (a, steps)
        assert len(steps) == 2, (a, steps)                                   # 噪声不触发
        if a in ("threshold", "steady_state", "median_diff"):                # 幅值＝稳态差（双窗 / GLR / CUSUM 的 score 口径不同）
            assert sorted(round(d / 1000) for *_, d in steps) == [-12, 12], (a, steps)
    assert window_stats(p[:AUTO_MIN_CYCLES - 1], F) is None


def test_sample_and_hold_data_recognized_and_scaled():
    """秒值×50 逐位重复 + 微抖动（第 108 轮用户文件形态）：识别保持长度 50，σ 按段间跳变，周波数参数 ×50。"""
    rng = np.random.default_rng(3)
    sec = [0.0025] * 100 + list(np.linspace(0.0025, 0.39, 24)) + [0.39, 0.31, 0.33, 0.37, 0.39, 0.40] * 2 + list(np.linspace(0.39, 1.57, 16)) \
        + list(1.56 - 0.23 * np.linspace(0, 1, 22)) + list(1.40 + rng.normal(0, 0.0086, 400)) + list(np.linspace(1.4, 0.0025, 45)) + [0.0025] * 60
    p = np.repeat(np.array(sec), 50) + rng.normal(0, 4e-7, len(sec) * 50)
    ap = auto_params(p, F); st = ap["stats"]
    assert st["hold"] == 50 and 0.006 < st["sigma"] < 0.012 and st["settle"] % 50 == 0 and st["transient"] >= 2000
    ev = detect_steps("steady_state", p, ap["algorithms"]["steady_state"])
    mags = sorted(round(d, 1) for *_, d in ev)
    assert mags == [-1.4, 1.4], ev                                          # 只有起动 / 停机两个事件，秒级台阶不是事件
    # 手填默认参数（未调参）会把每个 1 s 台阶都当事件
    # 若按相邻差分口径手填（σ≈4e-7 → 门槛 0.01 量级），每个 1 s 台阶都成事件
    assert len(detect_steps("threshold", p, {**NILM_ALGO_DEFAULTS["threshold"], "min_delta_w": 0.01, "settle_tol_w": 0.005})) > 10


def _wave(dur=8.0, noise=0.002, base=1.79e9):
    n = int(FS * dur); t = np.arange(n) / FS; w = 2 * np.pi * F * t
    P = np.full(n, 1000.0); P[t >= 3.0] += 500; P[t >= 6.0] -= 300
    U, ang = 57.74, np.arccos(0.9)
    u = np.zeros((3, n)); i = np.zeros((3, n)); rng = np.random.default_rng(1)
    for k, ph in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        u[k] = U * np.sqrt(2) * np.sin(w + ph)
        i[k] = (P / 3) / (U * 0.9) * np.sqrt(2) * np.sin(w + ph - ang) + rng.normal(0, noise, n)
    return base + t, u, i


def _run(cfg, t, u, i):
    det = NilmDetector(cfg); out = []
    for a in range(0, t.size, 640):
        out += det.ingest(SampleBlock(t=t[a:a + 640], u=u[:, a:a + 640], i=i[:, a:a + 640]))
    return det, out


def test_detector_auto_params_bus_only(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    t, u, i = _wave()
    cfg = AppConfig(); cfg.nilm.auto_params = True; cfg.nilm.channels = ["total"]
    # 故意把手填参数设成荒谬值：自适应模式下不应影响结果
    for a in NILM_ALGO_DEFAULTS:
        cfg.nilm.algorithms[a]["min_delta_w"] = 1e9
    cfg.nilm.rel_tol_pct = 50; cfg.nilm.min_delta_pct = 100
    cfg.validate()
    det, ev = _run(cfg, t, u, i)
    sm = det.summary()
    assert sm["auto_params"] is True and sm["auto_params_effective"] is True and "total" in sm["auto_last"]
    st = sm["auto_last"]["total"]["stats"]; algs = sm["auto_last"]["total"]["algorithms"]
    assert st["hold"] == 1 and set(algs) == set(NILM_ALGO_DEFAULTS) and algs["steady_state"]["min_delta_w"] < 100
    assert any("自适应算法参数已启用" in n for n in sm["notes"])
    ups = {e["algorithm"] for e in ev if e["direction"] == "up"}; downs = {e["algorithm"] for e in ev if e["direction"] == "down"}
    assert ups == set(NILM_ALGO_DEFAULTS) and downs == set(NILM_ALGO_DEFAULTS), (ups, downs)
    for e in ev:
        assert abs(e["magnitude_w"] - (500 if e["direction"] == "up" else 300)) < 60, e
    # 同样配置手填荒谬值但不启用自适应 → 没有事件
    cfg2 = AppConfig.from_dict(cfg.to_dict()); cfg2.nilm.auto_params = False; cfg2.validate()
    _, ev2 = _run(cfg2, t, u, i)
    assert ev2 == []
    # 分路侧（source_id=1）忽略自适应：按配置参数 → 同样没有事件，summary 有说明
    cfg3 = AppConfig.from_dict(cfg.to_dict()); cfg3.output.source_id = 1; cfg3.validate()
    det3, ev3 = _run(cfg3, t, u, i)
    sm3 = det3.summary()
    assert ev3 == [] and sm3["auto_params"] is True and sm3["auto_params_effective"] is False and any("只对总线侧生效" in n for n in sm3["notes"])
    # 算法启停仍按配置
    cfg4 = AppConfig.from_dict(cfg.to_dict()); cfg4.nilm.algorithms["cusum"]["enabled"] = False; cfg4.validate()
    det4, ev4 = _run(cfg4, t, u, i)
    assert not any(e["algorithm"] == "cusum" for e in ev4) and "cusum" not in det4.summary()["auto_last"]["total"]["algorithms"]


def test_config_roundtrip_and_tune_report():
    cfg = AppConfig.from_dict({"nilm": {"auto_params": "1"}}); cfg.validate()
    assert cfg.nilm.auto_params is True and cfg.to_dict()["nilm"]["auto_params"] is True
    assert AppConfig.from_dict({}).nilm.auto_params is False
    from elec_tool.nilm_tuning import run_tune
    from tests.conftest import write_csv
    from elec_tool.selftest import HarmSpec, build_signal
    import tempfile, os
    d = tempfile.mkdtemp()
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, phi_deg=0.0)], FS, 3.0, t0=1_760_000_000.0)
    i = i + np.random.default_rng(0).normal(0, 0.002, i.shape)
    write_csv(os.path.join(d, "w.csv"), t, u, i)
    base = AppConfig.load(str(ROOT / "configs" / "default.json"))
    r = run_tune(base, os.path.join(d, "w.csv"))
    assert r["auto_params"] and r["auto_params"]["stats"]["n"] == 150 and "steady_state" in r["auto_params"]["algorithms"]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r87cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json")); mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    import app.server as srv
    with TestClient(srv.app) as c:
        yield c
    mp.undo()


def test_api_config_and_summary(client):
    r = client.put("/api/config", json={"nilm": {"auto_params": True}}).json()
    assert r["config"]["nilm"]["auto_params"] is True
    sm = client.get("/api/nilm/events").json()["summary"]
    assert sm["auto_params"] is True and sm["auto_params_effective"] is True
    r = client.put("/api/branch/config", json={"nilm": {"auto_params": True}}).json()
    assert r["config"]["nilm"]["auto_params"] is True
    sm = client.get("/api/branch/nilm/events").json()["summary"]
    assert sm["auto_params_effective"] is False
    client.put("/api/config", json={"nilm": {"auto_params": False}})


def test_frontend_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'id="nilm-auto_params"' in html and 'id="nilm-auto-out"' in html and 'id="nilm-auto_params-lbl"' in html
    assert "'auto_params'" in js and "function nilmDimAuto" in js and "p.auto_params = false" in js and "auto_params_effective" in js
