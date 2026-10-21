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
    assert "case 'nilm': renderDual(renderNilm); break;" in js and "m.type === 'nilm_event'" in js
    assert "JSON.stringify({ nilm: payload })" in js and "/api/nilm/cycles" in js and "opt.marks" in js


# ------------------------------------------------------------------ v0.36：仅电流事件检测（数据源无电压）

def _write_csv_current_only(path, dur=6.0):
    t, _u, i = _wave(dur)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["时间戳", "A相电流", "B相电流", "C相电流"])
        for k in range(t.size):
            wr.writerow([f"{t[k]:.6f}", f"{i[0,k]:.5f}", f"{i[1,k]:.5f}", f"{i[2,k]:.5f}"])
    return str(path)


def _feed(det, t, u, i, step=640):
    out = []
    for a in range(0, t.size, step):
        out += det.ingest(SampleBlock(t=t[a:a + step], u=u[:, a:a + step], i=i[:, a:a + step]))
    return out


def test_current_only_detection_all_algorithms(tmp_path, monkeypatch):
    """电压全 0（数据源只有电流）：quantity=auto 自动切到 I，六种算法在 A 上都报出 2.0 s ↑ / 4.4 s ↓。
    v0.39：I 口径没有跨相合并——配置里的 total 被忽略（channels_effective=[A]），不产生 total 事件。"""
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    t, u, i = _wave(6.0)
    u0 = np.zeros_like(u)
    cfg = AppConfig(); cfg.nilm.channels = ["total", "A"]; cfg.validate()
    assert cfg.nilm.quantity == "auto"
    det = NilmDetector(cfg)
    evs = _feed(det, t, u0, i)
    sm = det.summary()
    assert sm["voltage_missing"] is True and sm["quantity_effective"] == "i" and sm["errors"] == []
    assert any("电流有效值" in n for n in sm["notes"]) and any("跨相合并" in n for n in sm["notes"])
    assert sm["channels"] == ["total", "A"] and sm["channels_effective"] == ["A"] and det.channels_effective == ["A"]
    assert not any(e["channel"] == "total" for e in evs)
    key = {}
    for e in evs:
        key.setdefault((e["algorithm"], e["channel"], e["direction"]), []).append(e)
    for a in NILM_ALGO_DEFAULTS:
        for ch in ("A",):
            ups, downs = key.get((a, ch, "up"), []), key.get((a, ch, "down"), [])
            assert ups and downs, (a, ch)
            big_up = max(ups, key=lambda e: e["magnitude"]); big_dn = max(downs, key=lambda e: e["magnitude"])
            assert abs(big_up["t_start"] - (t[0] + T_UP)) < 0.06 and abs(big_dn["t_start"] - (t[0] + T_DOWN)) < 0.06, (a, ch)
            assert big_up["unit"] == "A" and big_up["quantity"] == "i" and big_up["magnitude"] == big_up["delta_i_a"]
            assert big_up["delta_p_w"] == 0.0 and big_up["pre_p_w"] == 0.0 and big_up["magnitude_w"] == 0.0
    # A 相：I = P/(3·U·pf)；1000 W → 1500 W：ΔI_A = 500/3/(57.74·0.9) ≈ 3.207 A
    a_up = max(key[("glr", "A", "up")], key=lambda e: e["magnitude"])
    assert a_up["magnitude"] == pytest.approx(500 / 3 / (57.74 * 0.9), rel=0.03)
    # 落盘：新增 quantity / magnitude / unit 列
    f = [p for p in (tmp_path / "nilm").iterdir() if p.suffix == ".csv"][0]
    rows = list(csv.reader(open(f, encoding="utf-8-sig")))
    assert rows[0][-4:] == ["quantity", "magnitude", "unit", "run_id"] and rows[1][-4] == "i" and rows[1][-2] == "A"


def test_quantity_p_without_voltage_reports_error_and_i_with_voltage_works(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    t, u, i = _wave(6.0)
    cfg = AppConfig(); cfg.nilm.quantity = "p"; cfg.validate()
    det = NilmDetector(cfg)
    assert _feed(det, t, np.zeros_like(u), i) == []
    sm = det.summary()
    assert sm["voltage_missing"] and sm["quantity_effective"] == "p" and any("数据源无电压" in e for e in sm["errors"])
    # 有电压也可强制按电流检测：ΔI 与 ΔP 同时给出（v0.39：I 口径只能单相，默认 total → A/B/C，单相 ΔP = 500/3）
    cfg2 = AppConfig(); cfg2.nilm.quantity = "i"; cfg2.validate()
    det2 = NilmDetector(cfg2)
    evs = _feed(det2, t, u, i)
    sm2 = det2.summary()
    assert sm2["voltage_missing"] is False and sm2["quantity_effective"] == "i" and sm2["channels_effective"] == ["A", "B", "C"]
    up = max((e for e in evs if e["algorithm"] == "glr" and e["direction"] == "up" and e["channel"] == "A"), key=lambda e: e["magnitude"])
    assert up["unit"] == "A" and up["delta_p_w"] == pytest.approx(500 / 3, rel=0.03) and up["magnitude_w"] == pytest.approx(500 / 3, rel=0.03)
    # auto + 有电压 → p
    det3 = NilmDetector(AppConfig().validate())
    _feed(det3, t, u, i)
    assert det3.quantity_effective == "p" and det3.summary()["voltage_missing"] is False
    # 配置校验
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"nilm": {"quantity": "u"}}).validate()
    assert AppConfig.from_dict({"nilm": {"quantity": " I "}}).validate().nilm.quantity == "i"
    assert AppConfig.from_dict(AppConfig().to_dict()).nilm.quantity == "auto"


def test_current_only_csv_header_and_web_playback(client):
    """只有三相电流列的 CSV：列映射自动识别（电压 None → 0），Web 播放后按 I 检测出事件。"""
    from elec_tool.config import ColumnMap
    lay = ColumnMap().layout(["时间戳", "A相电流", "B相电流", "C相电流"])
    assert lay == {"timestamp": 0, "ua": None, "ia": 1, "ub": None, "ib": 2, "uc": None, "ic": 3}
    assert ColumnMap().layout(["时间戳", "x1", "x2", "x3", "x4", "x5", "x6"])["ua"] == 1      # 7 列不可识别 → 仍默认列序
    p = _write_csv_current_only(client.dir / "i_only.csv", dur=6.0)
    client.post("/api/engine/stop")
    client.post("/api/nilm/clear")
    assert client.put("/api/config", json={"nilm": {"quantity": "auto", "channels": ["total", "A"]}}).status_code == 200
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": p, "realtime": False})
    assert r.status_code == 200, r.text
    deadline = time.time() + 20
    while time.time() < deadline:
        st = client.get("/api/state").json()
        if st.get("finished") or st.get("error"):
            break
        time.sleep(0.2)
    d = client.get("/api/nilm/events?limit=200").json()
    sm = d["summary"]
    assert sm["voltage_missing"] is True and sm["quantity_effective"] == "i" and sm["total"] >= 12, sm
    assert {e["algorithm"] for e in d["events"]} == set(NILM_ALGO_DEFAULTS)
    assert all(e["unit"] == "A" and e["quantity"] == "i" and e["delta_p_w"] == 0 for e in d["events"])
    # 一次侧（CT=15）：A 相 ΔI ≈ 3.207×15 ≈ 48.1 A
    a_up = max((e for e in d["events"] if e["channel"] == "A" and e["direction"] == "up"), key=lambda e: e["magnitude"])
    assert a_up["magnitude"] == pytest.approx(500 / 3 / (57.74 * 0.9) * 15, rel=0.03)
    client.post("/api/engine/stop")
    client.post("/api/nilm/clear")
    client.put("/api/config", json={"nilm": {"quantity": "auto", "channels": ["total"]}})


def test_frontend_quantity_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'id="nilm-quantity"' in html and 'value="auto"' in html
    assert "'quantity'" in js.split("const NILM_FIELDS")[1].split(";")[0] and "function nilmMag(" in js


# ------------------------------------------------------------------ v0.37：I 口径使用 A 这套绝对阈值

def test_current_params_set_and_relative_floor():
    from elec_tool.config import NILM_W_TO_A
    from elec_tool.nilm import params_for_current
    for a, d in NILM_ALGO_DEFAULTS.items():
        for kw, ka in NILM_W_TO_A.items():
            assert (kw in d) == (ka in d), (a, kw)            # 每个 W 阈值都有对应 A 阈值
            if kw in d:
                assert 0 < d[ka] < d[kw]
    prm = params_for_current(NILM_ALGO_DEFAULTS["cusum"])
    assert prm["drift_w"] == 0.05 and prm["threshold_w"] == 1.0 and prm["min_delta_w"] == 0.3     # 算法函数读 *_w 键，值已换成 A 套
    assert prm["drift_a"] == 0.05 and prm["settle_cycles"] == 5
    # CUSUM 的 h/k 比例在 A 套中保持（20 倍），不会像「全部清零只留相对门槛」那样退化成 h=k
    assert prm["threshold_w"] / prm["drift_w"] == pytest.approx(20.0)
    # 相对门槛仍按中位数取较大者：level=100 A、min_delta_pct=5 → 5 A > 0.3 A
    eff = effective_params(prm, 100.0, 1.0, 5.0)
    assert eff["min_delta_w"] == 5.0 and eff["drift_w"] == 1.0 and eff["threshold_w"] == 1.0
    # 配置：A 套可单独改、往返、校验 > 0
    cfg = AppConfig.from_dict({"nilm": {"algorithms": {"glr": {"noise_a": 0.2, "min_delta_a": 1.5}}}}).validate()
    g = cfg.nilm.params("glr")
    assert g["noise_a"] == 0.2 and g["min_delta_a"] == 1.5 and g["noise_w"] == 10.0 and g["min_delta_w"] == 50.0
    assert AppConfig.from_dict(cfg.to_dict()).nilm.params("glr")["noise_a"] == 0.2
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"nilm": {"algorithms": {"threshold": {"settle_tol_a": 0}}}}).validate()


def test_current_mode_uses_a_thresholds_not_w(tmp_path, monkeypatch):
    """I 口径：把 A 套门槛抬到 ΔI 之上 → 不报；W 套改成天文数字 → 不影响 I 口径。"""
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    t, u, i = _wave(6.0)
    u0 = np.zeros_like(u)
    # ΔI_A ≈ 3.2 A（投入）、≈1.9 A（切除）：min_delta_a=2.5 → 只剩投入事件
    cfg = AppConfig(); cfg.nilm.channels = ["A"]
    for a in NILM_ALGO_DEFAULTS:
        cfg.nilm.algorithms[a]["min_delta_a"] = 2.5
        cfg.nilm.algorithms[a]["min_delta_w"] = 1e9                     # W 套应被忽略
    cfg.validate()
    evs = _feed(NilmDetector(cfg), t, u0, i)
    assert evs and all(e["direction"] == "up" for e in evs) and {e["algorithm"] for e in evs} == set(NILM_ALGO_DEFAULTS)
    assert all(e["unit"] == "A" and e["magnitude"] > 2.5 for e in evs)
    # 全部 A 套抬到 10 A → 0 事件
    for a in NILM_ALGO_DEFAULTS:
        cfg.nilm.algorithms[a]["min_delta_a"] = 10.0
    cfg.validate()
    assert _feed(NilmDetector(cfg), t, u0, i) == []
    # P 口径不受 A 套影响：A 套 10 A、W 套恢复默认 → 事件照常
    cfg2 = AppConfig(); cfg2.nilm.quantity = "p"; cfg2.nilm.channels = ["A"]
    for a in NILM_ALGO_DEFAULTS:
        cfg2.nilm.algorithms[a]["min_delta_a"] = 10.0
    cfg2.validate()
    evs2 = _feed(NilmDetector(cfg2), t, u, i)
    assert {e["algorithm"] for e in evs2} == set(NILM_ALGO_DEFAULTS) and all(e["unit"] == "W" for e in evs2)


def test_frontend_a_params_wiring():
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    block = js.split("const NILM_ALGOS")[1].split("};")[0]
    for a in NILM_ALGO_DEFAULTS:
        for k in NILM_ALGO_DEFAULTS[a]:
            if k.endswith("_a"):
                assert f"{k}:" in block and "A · I口径" in block, (a, k)
    assert "function nilmDimUnits(" in js and "nilm-inactive" in js


# ------------------------------------------------------------------ v0.39：I 口径只能单相；趋势图可画三相电流

def test_current_mode_only_single_phase_total_falls_back_to_abc(tmp_path, monkeypatch):
    """配置只有 total 时，I 口径按 A/B/C 三相各自单独检测；P 口径不受影响仍用 total。"""
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    t, u, i = _wave(6.0)
    cfg = AppConfig(); cfg.nilm.channels = ["total"]; cfg.validate()
    det = NilmDetector(cfg)
    evs = _feed(det, t, np.zeros_like(u), i)
    sm = det.summary()
    assert det.channels_effective == ["A", "B", "C"] and sm["channels_effective"] == ["A", "B", "C"] and sm["channels"] == ["total"]
    assert any("按 A/B/C 三相各自单独检测" in n for n in sm["notes"])
    chans = {e["channel"] for e in evs}
    assert chans == {"A", "B", "C"}
    for ch in ("A", "B", "C"):
        ups = [e for e in evs if e["algorithm"] == "glr" and e["channel"] == ch and e["direction"] == "up"]
        assert ups and abs(max(ups, key=lambda e: e["magnitude"])["t_start"] - (t[0] + T_UP)) < 0.06
    # P 口径：total 照常
    det2 = NilmDetector(AppConfig().validate())
    evs2 = _feed(det2, t, u, i)
    assert det2.channels_effective == ["total"] and {e["channel"] for e in evs2} == {"total"} and "channels_effective" in det2.summary()
    # 有电压但强制 i：同样去掉 total
    cfg3 = AppConfig(); cfg3.nilm.quantity = "i"; cfg3.nilm.channels = ["total", "B"]; cfg3.validate()
    det3 = NilmDetector(cfg3); evs3 = _feed(det3, t, u, i)
    assert det3.channels_effective == ["B"] and {e["channel"] for e in evs3} == {"B"}


def test_frontend_current_trend_and_total_dim_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'id="nilm-pqs-kind"' in html and 'id="nilm-ch-total-lbl"' in html
    assert 'nilm-pqs-ph' not in html and 'nilm-pqs-phases' not in js      # v0.40：标题栏不再放三相勾选，三相显隐用曲线下方图例
    assert "function nilmCurrentSeries(" in js and "curHist('current')" in js.split("function renderNilmPqs")[1].split("\n}")[0]
    assert "nilm-ch-total-lbl" in js.split("function nilmDimUnits")[1].split("\n}")[0]
    assert "channels_effective" in js


# ------------------------------------------------------------------ v0.46：非运行状态下从离线文件装载周波窗

def test_load_cycles_from_file_begin_and_center():
    from elec_tool.nilm import load_cycles_from_file
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = str(ROOT / "data" / "nilm_steps.csv")
    d = load_cycles_from_file(cfg)                                   # 默认：数据起点起 300 个周波
    assert d["source"]["mode"] == "begin" and len(d["t"]) == 300 and d["n_cycle_samples"] == 128
    t0 = d["t"][0]
    assert d["channels"]["total"]["p"][0] == pytest.approx(1.5e6, rel=0.02)
    c = load_cycles_from_file(cfg, t_center=t0 + 2.0, n=100)          # 以 2.0 s 阶跃为中心
    assert c["source"]["mode"] == "center" and len(c["t"]) == 100 and abs(c["t"][50] - (t0 + 2.0)) < 0.011
    assert c["channels"]["total"]["p"][45] == pytest.approx(1.5e6, rel=0.02) and c["channels"]["total"]["p"][55] == pytest.approx(2.25e6, rel=0.02)
    e = load_cycles_from_file(cfg, t_center=t0 + 0.1, n=100)          # 靠近起点：取最接近的一段
    assert len(e["t"]) == 100 and e["t"][0] == pytest.approx(t0)
    far = load_cycles_from_file(cfg, t_center=t0 + 5.9, n=100)
    assert len(far["t"]) == 100 and far["t"][-1] == pytest.approx(d["t"][-1])
    with pytest.raises(ValueError, match="csv_file"):
        bad = AppConfig(); bad.source.kind = "simulator"; load_cycles_from_file(bad)


def test_api_cycles_file_requires_stopped_engine(client):
    client.post("/api/engine/stop")
    assert client.put("/api/config", json={"source": {"kind": "csv_file", "path": "data/nilm_steps.csv"}}).status_code == 200
    r = client.get("/api/nilm/cycles_file?n=40").json()
    assert r["ok"] and len(r["t"]) == 40 and r["source"]["mode"] == "begin"
    tc = r["t"][0] + 2.0
    c = client.get(f"/api/nilm/cycles_file?n=60&t={tc}").json()
    assert c["ok"] and len(c["t"]) == 60 and abs(c["t"][30] - tc) < 0.011 and c["source"]["t_center"] == pytest.approx(tc)
    assert client.get("/api/nilm/cycles_file?t=abc").status_code == 400
    # 运行中 → 409
    st = client.post("/api/engine/start", json={"kind": "csv_file", "path": "data/nilm_bus_mixed.csv", "file_speed": 1.0}).json()
    assert st.get("ok", True)
    try:
        resp = client.get("/api/nilm/cycles_file?n=40")
        assert resp.status_code == 409 and "运行中" in resp.json()["error"]
    finally:
        client.post("/api/engine/stop")


def test_frontend_window_load_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert all(x in html for x in ('id="nilm-win-t"', 'id="nilm-win-count"', 'id="btn-nilm-win-load"', 'id="btn-nilm-win-live"', 'value="300"'))
    assert "function bindCtxMenu(" in js and "key: 'show-window'" in js and "/api/nilm/cycles_file" in js
    assert "disabled: running || noX" in js and "el.disabled = running" in js      # 仅非运行可操作


# ------------------------------------------------------------------ v0.50：nilm_tune --apply / POST /api/nilm/tune/apply
def _tune_json(unit="W"):
    sx = "_w" if unit == "W" else "_a"
    return {"file": "bg.csv", "channel": "total", "quantity": "p" if unit == "W" else "i", "unit": unit,
            "suggest": {"quantity": "p" if unit == "W" else "i", "rel_tol_pct": 1.5, "min_delta_pct": 3.0,
                        "algorithms": {"threshold": {f"min_delta{sx}": 123.0, f"settle_tol{sx}": 9.0, "bogus": 1},
                                       "glr": {"threshold": 31.0, f"noise{sx}": 2.5},
                                       "not_an_algo": {"x": 1}}}}


def test_export_tuned_config_keeps_base_untouched_and_writes_full_config(tmp_path):
    from elec_tool.nilm_tuning import apply_nilm_params, export_tuned_config
    base = AppConfig.from_dict(AppConfig().to_dict())
    base.nilm.nilm_dir = str(tmp_path / "nilm"); base.nilm.window_cycles = 321
    base.nilm.algorithms["glr"] = {"enabled": False, "threshold": 10.0}
    base_json = base.to_json()
    cfg, path, notes = export_tuned_config(base, _tune_json())
    assert base.to_json() == base_json                              # 基准配置未被修改
    assert path.startswith(str(tmp_path / "nilm")) and os.path.isfile(path)
    data = __import__("json").load(open(path, encoding="utf-8"))
    assert data["nilm"]["window_cycles"] == 321                     # 非调参项保留
    assert data["nilm"]["quantity"] == "p" and data["nilm"]["rel_tol_pct"] == 1.5 and data["nilm"]["min_delta_pct"] == 3.0
    assert data["nilm"]["algorithms"]["threshold"]["min_delta_w"] == 123.0 and "bogus" not in data["nilm"]["algorithms"]["threshold"]
    g = data["nilm"]["algorithms"]["glr"]                           # enabled 保留、建议项覆盖、其余为默认值；未知算法忽略
    assert g["enabled"] is False and g["threshold"] == 31.0 and g["noise_w"] == 2.5 and g["window_cycles"] == 15
    assert "not_an_algo" not in data["nilm"]["algorithms"]
    assert data["_tuning"]["changes"] == notes and data["_tuning"]["file"] == "bg.csv"
    re = AppConfig.load(path)                                       # 写出的是可直接加载的完整配置
    assert re.nilm.algorithms["glr"]["threshold"] == 31.0
    assert apply_nilm_params(AppConfig(), {"foo": 1}) == []         # 没有可套用项 → 空


def test_nilm_tune_cli_apply_writes_to_output_dir_not_config(tmp_path):
    import json, subprocess, sys
    p = _write_csv(tmp_path / "bg.csv", dur=3.0)
    cfgp = tmp_path / "cfg.json"
    c = AppConfig.from_dict(AppConfig().to_dict()); c.nilm.nilm_dir = str(tmp_path / "out"); c.save(str(cfgp))
    before = cfgp.read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "nilm_tune.py"), "--file", str(p), "--config", str(cfgp),
                        "--min-load-w", "500", "--apply", "--json"], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    ap = out["applied"]
    assert ap["config_file_updated"] is False and cfgp.read_text(encoding="utf-8") == before   # 默认不改配置文件
    assert ap["saved_to"].startswith(str(tmp_path / "out")) and os.path.isfile(ap["saved_to"])
    nc = AppConfig.load(ap["saved_to"])
    assert nc.nilm.algorithms["threshold"]["min_delta_w"] == out["suggest"]["algorithms"]["threshold"]["min_delta_w"]
    assert nc.nilm.rel_tol_pct == out["suggest"]["rel_tol_pct"] and nc.nilm.nilm_dir == str(tmp_path / "out")
    # --save-config 才回写；--out 指定文件
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "nilm_tune.py"), "--file", str(p), "--config", str(cfgp),
                        "--min-load-w", "500", "--apply", "--save-config", "--out", str(tmp_path / "x.json")],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    assert os.path.isfile(tmp_path / "x.json") and "已回写" in r.stdout
    assert AppConfig.load(str(cfgp)).nilm.algorithms["threshold"]["min_delta_w"] == nc.nilm.algorithms["threshold"]["min_delta_w"]


def test_web_nilm_tune_apply_hot_updates_running_config_without_persist(client):
    client.post("/api/engine/stop")
    cfg0 = client.get("/api/config").json()
    cfg_file_before = (client.dir / "cfg.json").read_text(encoding="utf-8")
    assert client.post("/api/nilm/tune/apply", json={}).status_code == 400
    assert client.post("/api/nilm/tune/apply", json={"params": {"foo": 1}}).status_code == 400
    r = client.post("/api/nilm/tune/apply", json={"params": _tune_json()})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] and d["hot"] and d["config_file_updated"] is False and len(d["changes"]) >= 4
    assert d["config"]["nilm"]["algorithms"]["threshold"]["min_delta_w"] == 123.0
    assert d["config"]["nilm"]["window_cycles"] == cfg0["nilm"]["window_cycles"]
    assert client.get("/api/config").json()["nilm"]["algorithms"]["glr"]["threshold"] == 31.0   # 已热生效
    assert (client.dir / "cfg.json").read_text(encoding="utf-8") == cfg_file_before           # 未写配置文件
    saved = ROOT / d["saved_to"] if not os.path.isabs(d["saved_to"]) else Path(d["saved_to"])
    assert saved.is_file() and "nilm_tuned_config_bus_" in saved.name
    exp_dir = os.environ.get("ELEC_TOOL_NILM_DIR") or d["config"]["nilm"]["nilm_dir"]           # 输出目录＝事件 CSV 所在 nilm 目录
    assert str(saved.parent) == os.path.abspath(exp_dir)
    # hot=false：只写文件、不改运行配置
    r = client.post("/api/nilm/tune/apply", json={"params": {"nilm": {"algorithms": {"glr": {"threshold": 44.0}}}}, "hot": False}).json()
    assert r["ok"] and r["config"]["nilm"]["algorithms"]["glr"]["threshold"] == 44.0
    assert client.get("/api/config").json()["nilm"]["algorithms"]["glr"]["threshold"] == 31.0
    # 非法值 → 400
    assert client.post("/api/nilm/tune/apply", json={"params": {"nilm": {"algorithms": {"glr": {"threshold": 0}}}}}).status_code == 400
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8"); js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert all(x in html for x in ('id="nilm-tune-file"', 'id="btn-nilm-tune-apply"', 'id="nilm-tune-persist"', 'id="nilm-tune-note"'))
    assert "/api/nilm/tune/apply" in js and "function applyNilmTune(" in js


# ------------------------------------------------------------------ v0.52：数据处理子界面「负荷辨识调参」
def test_run_tune_time_range_and_errors(tmp_path):
    from elec_tool.nilm_tuning import TuneError, run_tune, tune_result_path
    p = _write_csv(tmp_path / "bg.csv", dur=6.0)
    base = AppConfig()
    whole = run_tune(base, str(p))
    assert whole["t_range"]["whole_file"] and whole["measure"]["cycles"] == 300 and whole["quantity"] == "p"
    d2 = run_tune(base, str(p), duration_s=2.0)
    assert 99 <= d2["measure"]["cycles"] <= 101 and d2["t_range"]["duration_s"] == 2.0 and not d2["t_range"]["whole_file"]
    t0 = whole["t_range"]["t_first"]
    seg = run_tune(base, str(p), t_start=f"{t0 + 1.0:.3f}", t_end=f"{t0 + 3.0:.3f}")
    assert 98 <= seg["measure"]["cycles"] <= 101 and abs(seg["t_range"]["t_first"] - (t0 + 1.0)) < 0.03
    both = run_tune(base, str(p), t_start=f"{t0 + 1.0:.3f}", t_end=f"{t0 + 5.0:.3f}", duration_s=1.0)   # 先到者
    assert 49 <= both["measure"]["cycles"] <= 51
    with pytest.raises(TuneError):
        run_tune(base, str(p), t_start=f"{t0 + 100:.3f}")                                     # 段内无数据
    with pytest.raises(TuneError):
        run_tune(base, str(p), t_start=f"{t0 + 3:.3f}", t_end=f"{t0 + 1:.3f}")                # 结束早于开始
    with pytest.raises(TuneError):
        run_tune(base, str(p), duration_s=0)
    with pytest.raises(ConfigError):
        run_tune(base, str(p), t_start="not a time")
    with pytest.raises(TuneError):
        run_tune(base, str(p), quantity="i", channel="total")
    fp = tune_result_path(base, "", out_dir=str(tmp_path))
    assert os.path.basename(fp).startswith("tune_") and fp.endswith(".json")
    assert os.path.basename(tune_result_path(base, "../x_{时间}", out_dir=str(tmp_path))).startswith("x_20") and ".." not in tune_result_path(base, "../x", out_dir=str(tmp_path))[len(str(tmp_path)):]


def test_web_process_nilm_tune_endpoint(client):
    client.post("/api/engine/stop")
    p = _write_csv(client.dir / "bg.csv", dur=6.0)
    assert client.post("/api/process/nilm_tune", json={}).status_code == 400
    assert client.post("/api/process/nilm_tune", json={"path": str(client.dir / "nope.csv")}).status_code == 400
    cfg_before = client.get("/api/config").json()
    raw_before = (client.dir / "cfg.json").read_text(encoding="utf-8")
    r = client.post("/api/process/nilm_tune", json={"path": str(p), "min_load_w": 500})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] and d["saved_to"] is None and d["measure"]["cycles"] == 300 and d["t_range"]["whole_file"]
    assert d["suggest"]["algorithms"]["threshold"]["min_delta_w"] == 250 and d["side"] == "bus"
    assert client.get("/api/config").json() == cfg_before                               # 不改运行配置
    # 时间段 + 保存（默认文件名 tune_<时间>.json，落在 nilm 目录）
    t0 = d["t_range"]["t_first"]
    r = client.post("/api/process/nilm_tune", json={"path": str(p), "t_start": f"{t0 + 1:.3f}", "duration_s": 2, "save": True}).json()
    assert r["ok"] and 99 <= r["measure"]["cycles"] <= 101 and r["saved_to"]
    saved = Path(r["saved_to"]) if os.path.isabs(r["saved_to"]) else ROOT / r["saved_to"]
    assert saved.is_file() and saved.name.startswith("tune_") and saved.suffix == ".json"
    assert str(saved.parent) == os.path.abspath(os.environ.get("ELEC_TOOL_NILM_DIR") or cfg_before["nilm"]["nilm_dir"])
    import json as _j
    data = _j.loads(saved.read_text(encoding="utf-8"))
    # v0.53：保存的是以原配置文件（ELEC_TOOL_CONFIG_PATH=cfg.json）为基准、只更新算法参数的完整配置
    base_file = _j.loads((client.dir / "cfg.json").read_text(encoding="utf-8"))
    assert data["nilm"]["algorithms"]["threshold"]["min_delta_w"] == r["suggest"]["algorithms"]["threshold"]["min_delta_w"]
    assert data["nilm"]["rel_tol_pct"] == r["suggest"]["rel_tol_pct"] and data["nilm"]["quantity"] == "p"
    norm = AppConfig.from_dict(base_file).to_dict()
    assert data["sampling"] == norm["sampling"] and data["transform"] == norm["transform"] and data["columns"] == norm["columns"]
    assert data["nilm"]["window_cycles"] == norm["nilm"]["window_cycles"] and data["nilm"]["algorithms"]["glr"]["enabled"] == norm["nilm"]["algorithms"]["glr"]["enabled"]
    assert data["_tuning"]["suggest"]["algorithms"]["glr"]["threshold"] == 25.0 and r["base_config"].endswith("cfg.json") and len(r["changes"]) >= 4
    assert AppConfig.load(str(saved)).nilm.algorithms["threshold"]["min_delta_w"] == r["suggest"]["algorithms"]["threshold"]["min_delta_w"]
    assert (client.dir / "cfg.json").read_text(encoding="utf-8") == raw_before          # 原配置文件内容未变
    assert client.get("/api/config").json() == cfg_before                               # 运行配置也未变
    # 自定义文件名 + {时间} 占位符
    r = client.post("/api/process/nilm_tune", json={"path": str(p), "save": True, "name": "site_{时间}"}).json()
    assert r["ok"] and os.path.basename(r["saved_to"]).startswith("site_20") and r["saved_to"].endswith(".json")
    # 错误：无效时间 / I 口径 total / 段内无数据 → 400
    assert client.post("/api/process/nilm_tune", json={"path": str(p), "t_start": "xx"}).status_code == 400
    assert client.post("/api/process/nilm_tune", json={"path": str(p), "quantity": "i", "channel": "total"}).status_code == 400
    assert client.post("/api/process/nilm_tune", json={"path": str(p), "t_start": f"{t0 + 999:.0f}"}).status_code == 400
    # 结果可直接套用
    a = client.post("/api/nilm/tune/apply", json={"params": d, "hot": False}).json()
    assert a["ok"] and a["config"]["nilm"]["algorithms"]["threshold"]["min_delta_w"] == 250
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8"); js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert all(f'id="{i}"' in html for i in ("nt-path", "nt-files", "nt-tstart", "nt-tend", "nt-duration", "nt-side", "nt-save", "nt-name", "btn-nt-run", "btn-nt-apply", "nt-result"))
    assert "/api/process/nilm_tune" in js and "function ntRun(" in js


# ------------------------------------------------------------------ v0.54：结果 JSON 带等价命令
def test_build_cli_command_and_endpoint_command(client):
    from elec_tool.nilm_tuning import build_cli_command
    c = build_cli_command("data/bg.csv")
    assert c == "python tools/nilm_tune.py --file data/bg.csv --json"
    c = build_cli_command("data/a b.csv", config="configs/runtime.json", channel="A", quantity="i", min_load_a=2.5,
                          t_start="2026-10-13 08:00:01", duration_s=30, max_cycles=6000, apply=True, out="output/nilm/x.json")
    assert c == ("python tools/nilm_tune.py --file 'data/a b.csv' --config configs/runtime.json --channel A --quantity i "
                 "--min-load-a 2.5 --t-start '2026-10-13 08:00:01' --duration 30 --max-cycles 6000 --json --apply --out output/nilm/x.json")
    assert "--max-cycles" not in build_cli_command("x.csv", max_cycles=30000) and "--min-load-w 500 " in build_cli_command("x.csv", min_load_w=500.0)
    # 端点：未保存 → --json；保存 → 追加 --apply --out <保存路径>，且写入文件的 _tuning.command 一致；--config 为本侧原配置文件
    p = _write_csv(client.dir / "bg2.csv", dur=3.0)
    t0 = None
    d = client.post("/api/process/nilm_tune", json={"path": str(p), "min_load_w": 500, "channel": "A", "duration_s": 1}).json()
    assert d["ok"] and d["command"].startswith("python tools/nilm_tune.py --file ")
    assert "--config " in d["command"] and d["command"].endswith("--channel A --min-load-w 500 --duration 1 --json"), d["command"]
    d = client.post("/api/process/nilm_tune", json={"path": str(p), "save": True, "name": "cmdchk"}).json()
    assert d["ok"] and d["command"].endswith(f"--json --apply --out {d['saved_to']}"), d["command"]
    saved = Path(d["saved_to"]) if os.path.isabs(d["saved_to"]) else ROOT / d["saved_to"]
    import json as _j
    assert _j.loads(saved.read_text(encoding="utf-8"))["_tuning"]["command"] == d["command"]
    assert "nt-cmd" in (ROOT / "app/static/app.js").read_text(encoding="utf-8")


# ------------------------------------------------------------------ v0.55：从文件投切台阶估计最小关心负荷
def test_estimate_min_load_rules():
    from elec_tool.nilm_tuning import estimate_min_load
    rng = np.random.default_rng(3)
    sig = 20.0
    # 单设备三档：1.5M → 1.8M → 2.25M → 1.8M → 1.5M（每段 60 周波）；最小台阶间距 300k、最小跳变 300k
    lv = [1.5e6, 1.8e6, 2.25e6, 1.8e6, 1.5e6]
    x = np.concatenate([l + rng.normal(0, sig, 60) for l in lv])
    e = estimate_min_load(x, sig, "W")
    assert e["reliable"] and abs(e["candidate"] - 3e5) < 2e3 and e["n_steady"] == 5 and len(e["levels"]) == 3
    # 纯背景 → 不可靠、候选 None
    e0 = estimate_min_load(1.5e6 + rng.normal(0, sig, 300), sig, "W")
    assert not e0["reliable"] and e0["candidate"] is None and "未发现投切" in e0["note"]
    # 软启斜坡：碎段 < 25 周波不计稳态；起止两个稳态仍给出一次跳变
    ramp = np.concatenate([1.5e6 + rng.normal(0, sig, 60), np.linspace(1.5e6, 2.0e6, 40) + rng.normal(0, sig, 40), 2.0e6 + rng.normal(0, sig, 60)])
    er = estimate_min_load(ramp, sig, "W")
    assert er["n_steady"] == 2 and er["reliable"] and abs(er["candidate"] - 5e5) < 5e3
    # 候选过小（< 20σ）→ 不可靠
    tiny = np.concatenate([100.0 + rng.normal(0, 1.0, 60), 112.0 + rng.normal(0, 1.0, 60)])
    assert estimate_min_load(tiny, 1.0, "W")["reliable"] is False


def test_run_tune_min_load_auto_and_endpoint(client, tmp_path):
    from elec_tool.nilm_tuning import build_cli_command, run_tune
    p = _write_csv(tmp_path / "steps.csv", dur=6.0)
    base = AppConfig()
    r = run_tune(base, str(p), min_load_auto=True)
    est = r["min_load_estimate"]
    assert est["candidate"] is not None and r["min_load_source"] in ("estimated", "none") and "min_load_used" in r
    if est["reliable"]:
        assert r["min_load_source"] == "estimated" and r["min_load_used"] == est["candidate"]
        assert r["suggest"]["algorithms"]["threshold"]["min_delta_w"] >= 0.5 * est["candidate"] * 0.9
    r2 = run_tune(base, str(p), min_load_auto=True, min_load_w=500)        # 手填优先
    assert r2["min_load_source"] == "manual" and r2["min_load_used"] == 500 and any("仅供参考" in n for n in r2["notes"])
    r3 = run_tune(base, str(p))                                              # 不勾选也带估计，但不采用
    assert r3["min_load_source"] == "none" and r3["min_load_estimate"]["candidate"] is not None
    assert build_cli_command("x.csv", min_load_auto=True) == "python tools/nilm_tune.py --file x.csv --min-load-auto --json"
    # 端点
    client.post("/api/engine/stop")
    d = client.post("/api/process/nilm_tune", json={"path": str(p), "min_load_auto": True}).json()
    assert d["ok"] and "min_load_estimate" in d and "--min-load-auto" in d["command"] and d["min_load_source"] == r["min_load_source"]
    d = client.post("/api/process/nilm_tune", json={"path": str(p)}).json()
    assert d["ok"] and "--min-load-auto" not in d["command"] and d["min_load_source"] == "none"
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8"); js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert all(f'id="{i}"' in html for i in ("nt-minauto", "nt-estrow", "nt-est-text", "btn-nt-est-fill")) and "min_load_auto" in js
