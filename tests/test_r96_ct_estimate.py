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


def test_estimate_ct_three_wire_bus(files):
    bus, br = files; cfg = AppConfig.load(str(ROOT / "configs" / "default.json"))
    for phase, rec in (("A", "0"), ("C", "0"), ("B", "1")):
        r = estimate_ct(cfg, {"path": bus, "t_event": str(T0 + 6), "phase": phase, "wiring": "3p3w", "invert_phases": "A", "reconstruct_3w": rec},
                        {"path": br, "t_event": str(T0 + 6), "phase": phase}, known_side="branch", known_ct=15)
        assert r["estimated_side"] == "bus" and abs(r["estimated_ct"] - 40.0) < 0.5, (phase, r["estimated_ct"])
        assert r["bus"]["direction"] == "down" == r["branch"]["direction"]
        assert abs(r["bus"]["t_step"] - (T0 + 6)) < 0.05 and abs(r["branch"]["delta_a"] + 2.4) < 0.02
        assert any("200/5" in n for n in r["notes"])
    # 反向：已知总线 CT=40 → 估计分路 ≈15
    r = estimate_ct(cfg, {"path": bus, "t_event": str(T0 + 6), "phase": "A", "wiring": "3p3w", "invert_phases": "A"},
                    {"path": br, "t_event": str(T0 + 6), "phase": "A"}, known_side="bus", known_ct=40)
    assert r["estimated_side"] == "branch" and abs(r["estimated_ct"] - 15.0) < 0.2
    # 3p3w 选 B 相且未重构 → 明确报错；时刻超出范围 → 报错；坏参数 → 报错
    with pytest.raises(CtEstimateError, match="B 相"):
        measure_step(cfg, {"path": bus, "t_event": str(T0 + 6), "phase": "B", "wiring": "3p3w"}, side="bus")
    with pytest.raises(CtEstimateError, match="范围"):
        measure_step(cfg, {"path": bus, "t_event": str(T0 + 60), "phase": "A"}, side="bus")
    with pytest.raises(CtEstimateError):
        estimate_ct(cfg, {"path": bus, "t_event": str(T0 + 6), "phase": "A"}, {"path": br, "t_event": str(T0 + 6), "phase": "A"}, known_ct=0)
    with pytest.raises(CtEstimateError):
        estimate_ct(cfg, {"path": bus, "t_event": str(T0 + 6), "phase": "A", "wiring": "xx"}, {"path": br, "t_event": str(T0 + 6), "phase": "A"})
    # HH:MM:SS 写法（按文件当天）
    from elec_tool.timefmt import local_tod_s
    tod = local_tod_s(T0 + 6); hh, mm, ss = int(tod // 3600), int(tod % 3600 // 60), tod % 60
    m = measure_step(cfg, {"path": br, "t_event": f"{hh:02d}:{mm:02d}:{ss:06.3f}", "phase": "A"}, side="branch")
    assert abs(m["t_step"] - (T0 + 6)) < 0.05


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
        body = {"bus": {"path": bus, "t_event": str(T0 + 6), "phase": "A", "wiring": "3p3w", "invert_phases": "A"},
                "branch": {"path": br, "t_event": str(T0 + 6), "phase": "A"}, "known_side": "branch", "known_ct": 15}
        r = client.post("/api/process/ct_estimate", json=body)
        assert r.status_code == 200, r.text
        j = r.json(); assert abs(j["estimated_ct"] - 40) < 0.5 and j["command"].startswith("python tools/ct_estimate.py") and "--bus-wiring 3p3w" in j["command"]
        assert j["bus"]["t_step_local"] and j["branch"]["t_event_local"]
        assert client.post("/api/process/ct_estimate", json={"bus": {"path": bus}, "branch": {"path": br}}).status_code == 400
        assert client.post("/api/process/ct_estimate", json={**body, "known_ct": "x"}).status_code == 400
    # CLI
    import subprocess
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "ct_estimate.py"), "--bus-file", bus, "--bus-time", str(T0 + 6), "--bus-wiring", "3p3w",
                          "--bus-invert-phases", "A", "--branch-file", br, "--branch-time", str(T0 + 6), "--known-ct", "15", "--json"],
                         capture_output=True, text=True, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    import json
    assert abs(json.loads(out.stdout)["estimated_ct"] - 40) < 0.5
