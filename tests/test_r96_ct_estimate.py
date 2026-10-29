"""v0.96：估计 CT（elec_tool.ct_estimate / POST /api/process/ct_estimate / tools/ct_estimate.py）。"""
from __future__ import annotations

import csv
import pathlib
import shutil
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from elec_tool.config import AppConfig  # noqa: E402
from elec_tool.ct_estimate import CtEstimateError, estimate_ct, measure_step  # noqa: E402

FS, F, T0 = 6400.0, 50.0, 1.79e9


def _write(path, t, u, i):
    with open(path, "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        arr = np.column_stack([t, u[0], i[0], u[1], i[1], u[2], i[2]])
        wr.writerows([[f"{r[0]:.6f}"] + [f"{v:.5f}" for v in r[1:]] for r in arr])


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    """一次侧：设备 36 A 在 t=6 s 停机；总线另有 120 A 背景。分路 CT 15（四线）；总线 CT 40（三相三线、A 相 CT 反）。"""
    d = tmp_path_factory.mktemp("ct"); n = int(FS * 12); t = np.arange(n) / FS; w = 2 * np.pi * F * t
    ph = (0, -2 * np.pi / 3, 2 * np.pi / 3); rng = np.random.default_rng(0)
    Idev = np.where(t < 6, 36.0, 0.0); U = 57.74
    u = np.vstack([U * np.sqrt(2) * np.sin(w + p) for p in ph])
    i_dev = np.vstack([Idev * np.sqrt(2) * np.sin(w + p - 0.4) for p in ph]); i_bg = np.vstack([120 * np.sqrt(2) * np.sin(w + p - 0.3) for p in ph])
    br = str(d / "branch.csv"); _write(br, T0 + t, u, i_dev / 15 + rng.normal(0, 0.01, (3, n)))
    ib = (i_dev + i_bg) / 40
    bus = str(d / "bus.csv"); _write(bus, T0 + t, np.vstack([u[0] - u[1], np.zeros(n), u[2] - u[1]]), np.vstack([-ib[0], np.zeros(n), ib[2]]) + rng.normal(0, 0.01, (3, n)))
    return bus, br


def _spec(path, phase="A", event="stop", tb=T0 + 5.5, te=T0 + 6.5, **kw):
    d = {"path": path, "event": event, "t_begin": str(tb), "t_end": str(te), "phase": phase}; d.update(kw); return d


def test_estimate_ct_three_wire_bus(files):
    bus, br = files; cfg = AppConfig.load(str(ROOT / "configs" / "default.json"))
    for phase, rec in (("A", "0"), ("C", "0"), ("B", "1")):
        r = estimate_ct(cfg, _spec(bus, phase, wiring="3p3w", invert_phases="A", reconstruct_3w=rec),
                        _spec(br, phase, known="1", ct=15))
        assert r["estimated_side"] == "bus" and abs(r["estimated_ct"] - 40.0) < 0.5, (phase, r["estimated_ct"])
        assert r["estimates"]["branch"] is None and r["estimates"]["bus"]["from"] == "branch"
        assert r["bus"]["direction"] == "down" == r["branch"]["direction"] == r["bus"]["expected"]
        assert abs(r["bus"]["t_step"] - (T0 + 6)) < 0.05 and abs(r["branch"]["delta_a"] + 2.4) < 0.02
        assert r["bus"]["n_pre"] == 50 == r["bus"]["n_post"]
        assert any("200/5" in n for n in r["notes"])
    # 反向：已知总线 CT=40 → 估计分路 ≈15；两侧都勾 → 互相核对并给偏差；都不勾 → 只给比值
    r = estimate_ct(cfg, _spec(bus, wiring="3p3w", invert_phases="A", known="1", ct=40), _spec(br))
    assert r["estimated_side"] == "branch" and abs(r["estimated_ct"] - 15.0) < 0.2
    r = estimate_ct(cfg, _spec(bus, wiring="3p3w", invert_phases="A", known="1", ct=42), _spec(br, known="1", ct=15))
    assert r["estimated_side"] is None and abs(r["estimates"]["bus"]["ct"] - 40) < 0.5 and 4 < r["estimates"]["bus"]["deviation_pct"] < 6
    assert abs(r["estimates"]["branch"]["ct"] - 15.75) < 0.1
    r = estimate_ct(cfg, _spec(bus, wiring="3p3w", invert_phases="A"), _spec(br))
    assert r["estimates"] == {"bus": None, "branch": None} and abs(r["ratio_branch_over_bus"] - 2.665) < 0.02 and any("都未勾选" in n for n in r["notes"])
    # 事件类型与方向不符 → 提示；计算周波数可配
    r = estimate_ct(cfg, _spec(bus, event="start", wiring="3p3w", invert_phases="A"), _spec(br, event="start", known="1", ct=15), win_cycles=20)
    assert any("不符" in n for n in r["notes"]) and r["bus"]["n_pre"] == 20
    # 错误：3p3w 选 B 相未重构 / 时刻超范围 / 勾已知未填 CT / 结束早于开始 / 非法接线 / 事件类型
    with pytest.raises(CtEstimateError, match="B 相"):
        measure_step(cfg, _spec(bus, "B", wiring="3p3w"), side="bus")
    with pytest.raises(CtEstimateError, match="范围"):
        measure_step(cfg, _spec(bus, tb=T0 + 60, te=T0 + 61), side="bus")
    with pytest.raises(CtEstimateError, match="未填写 CT"):
        estimate_ct(cfg, _spec(bus, wiring="3p3w", invert_phases="A"), _spec(br, known="1", ct=""))
    with pytest.raises(CtEstimateError, match="早于"):
        measure_step(cfg, _spec(br, tb=T0 + 7, te=T0 + 6), side="branch")
    with pytest.raises(CtEstimateError):
        estimate_ct(cfg, _spec(bus, wiring="xx"), _spec(br))
    with pytest.raises(CtEstimateError, match="事件类型"):
        measure_step(cfg, _spec(br, event="boom"), side="branch")
    # HH:MM:SS 写法（按文件当天）
    from elec_tool.timefmt import local_tod_s
    f = lambda x: (lambda tod: f"{int(tod // 3600):02d}:{int(tod % 3600 // 60):02d}:{tod % 60:06.3f}")(local_tod_s(x))   # noqa: E731
    m = measure_step(cfg, {"path": br, "event": "stop", "t_begin": f(T0 + 5.5), "t_end": f(T0 + 6.5), "phase": "A"}, side="branch")
    assert abs(m["t_step"] - (T0 + 6)) < 0.05 and abs(m["delta_a"] + 2.39) < 0.02


def test_ct_estimate_api_and_cli(files, tmp_path_factory, monkeypatch):
    bus, br = files
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("ctcfg"); shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    monkeypatch.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); monkeypatch.setenv("ELEC_TOOL_AUTOSTART", "")
    monkeypatch.setenv("ELEC_TOOL_PERSIST_CONFIG", "0"); monkeypatch.setenv("ELEC_TOOL_EVENTS_DIR", str(d / "ev"))
    import importlib
    import app.server as srv
    importlib.reload(srv)
    with TestClient(srv.app) as client:
        body = {"bus": _spec(bus, wiring="3p3w", invert_phases="A"), "branch": _spec(br, known="1", ct=15)}
        r = client.post("/api/process/ct_estimate", json=body)
        assert r.status_code == 200, r.text
        j = r.json(); assert abs(j["estimated_ct"] - 40) < 0.5 and j["command"].startswith("python tools/ct_estimate.py")
        assert "--bus-wiring 3p3w" in j["command"] and "--branch-ct 15" in j["command"] and "--bus-event stop" in j["command"]
        assert j["bus"]["t_begin_local"] and j["bus"]["t_end_local"] and j["branch"]["t_step_local"]
        # 每侧逐周波 RMS 曲线（界面用同一 GET，带本侧接线 / 极性）
        rr = client.get("/api/process/wave/rms", params={"path": bus, "channels": "Ia", "pt_ct_enabled": "0", "wiring": "3p3w", "invert_phases": "A", "agg_cycles": 1}).json()
        assert rr["ok"] and rr["cycles_total"] == 600 and abs(rr["channels"]["Ia"][10] - 3.897) < 0.02 and abs(rr["channels"]["Ia"][-10] - 3.0) < 0.02
        assert client.post("/api/process/ct_estimate", json={"bus": {"path": bus}, "branch": {"path": br}}).status_code == 400
        assert client.post("/api/process/ct_estimate", json={**body, "win_cycles": "x"}).status_code == 400
    # CLI
    import subprocess
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "ct_estimate.py"), "--bus-file", bus, "--bus-event", "stop", "--bus-begin", str(T0 + 5.5), "--bus-end", str(T0 + 6.5),
                          "--bus-wiring", "3p3w", "--bus-invert-phases", "A", "--branch-file", br, "--branch-event", "stop", "--branch-begin", str(T0 + 5.5),
                          "--branch-end", str(T0 + 6.5), "--branch-ct", "15", "--json"], capture_output=True, text=True, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    import json
    assert abs(json.loads(out.stdout)["estimated_ct"] - 40) < 0.5
