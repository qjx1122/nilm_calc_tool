"""v0.21：导出指定时间段的原始周波数据（两侧共用文件、source_id 区分、保留区裁剪）。"""
from __future__ import annotations

import csv
import pathlib
import shutil
import time

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400.0
T0 = 1_760_000_000.0


def test_keep_buffer_and_range():
    from elec_tool.blocks import SampleBlock
    from elec_tool.config import AppConfig
    from elec_tool.nilm import NilmDetector
    cfg = AppConfig(); cfg.nilm.cycle_keep_cycles = 120; cfg.nilm.window_cycles = 50
    det = NilmDetector(cfg, root=None)
    n = int(FS / 50)
    for b in range(10):                       # 每块 20 周波 → 共 200 周波，保留 120
        t = T0 + (b * 20 * n + np.arange(20 * n)) / FS
        w = 2 * np.pi * 50 * t
        u = np.vstack([np.sin(w), np.sin(w - 2.094), np.sin(w + 2.094)]) * 100
        i = u / 10
        det.ingest(SampleBlock(t=t, u=u, i=i, scaled=True, source="x", seq=b))
    k = det.keep_info()
    assert k["cycles"] == 120 and k["keep_cycles"] == 120
    assert abs(k["t_first"] - (T0 + 80 * n / FS)) < 1e-6          # 前 80 个被裁掉
    d = det.cycles_between(T0 + 100 * n / FS, T0 + 110 * n / FS)
    assert d["t"].shape[0] == 11 and d["idx"][0] == 100 and d["p"].shape == (4, 11)
    assert det.cycles_between(None, None)["t"].shape[0] == 120
    assert det.summary()["keep"]["cycles"] == 120
    cfg0 = AppConfig(); cfg0.nilm.cycle_keep_cycles = 0
    det0 = NilmDetector(cfg0, root=None)
    det0.ingest(SampleBlock(t=T0 + np.arange(5 * n) / FS, u=u[:, :5 * n], i=i[:, :5 * n], scaled=True, source="x", seq=0))
    assert det0.keep_info()["cycles"] == 0


def _wait_done(client, path="/api/state", n=60):
    for _ in range(n):
        time.sleep(0.2)
        a = client.get(path).json()
        if not a["running"]:
            return a
    return a


def test_web_export_both_sides(tmp_path, monkeypatch):
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv
    shutil.copy(ROOT / "configs" / "default.json", tmp_path / "cfg.json")
    monkeypatch.setenv("ELEC_TOOL_CONFIG_PATH", str(tmp_path / "cfg.json")); monkeypatch.setenv("ELEC_TOOL_AUTOSTART", "")
    monkeypatch.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(tmp_path / "branch.json")); monkeypatch.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    monkeypatch.setenv("ELEC_TOOL_AUTOLOAD_LAST", "0")
    import app.server as srv
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=0.0)]
    t, u, i = build_signal(specs, FS, 2.0, t0=T0); write_csv(str(tmp_path / "bus.csv"), t, u, i)
    t2, u2, i2 = build_signal(specs, FS, 2.0, t0=T0 + 0.5); write_csv(str(tmp_path / "br.csv"), t2, u2, i2)
    with TestClient(srv.app) as c:
        c.put("/api/config", json={"branch": {"enabled": True, "common_window": False}, "output": {"export_dir": str(tmp_path / "out"), "realtime_save": False}})
        c.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(tmp_path / "br.csv"), "file_speed": 0, "custom_time": False}})
        assert c.post("/api/nilm/cycles/export", json={"t_from": "abc"}).status_code == 400
        assert c.post("/api/nilm/cycles/export", json={"t_from": T0 + 10, "t_to": T0 + 1}).status_code == 400
        r = c.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0, "custom_time": False}).json()
        assert r["ok"] and r["branch"]["ok"], r
        _wait_done(c); _wait_done(c, "/api/branch/state")
        # 1) 指定 1 s 时间段：两侧写同一文件
        r = c.post("/api/nilm/cycles/export", json={"t_from": T0 + 0.5, "t_to": T0 + 1.5}).json()
        assert r["ok"], r
        assert r["source_ids"] == [0, 1] and r["sides"]["bus"]["rows"] >= 45 and r["sides"]["branch"]["rows"] >= 45
        fp = pathlib.Path(r["path"]) if pathlib.Path(r["path"]).is_absolute() else ROOT / r["path"]
        rows = list(csv.DictReader(open(fp, encoding="utf-8-sig")))
        assert len(rows) == r["rows"] and rows[0]["source_id"] == "0"
        assert set(rows[0]) == set(srv.NILM_CYCLE_HEADER)
        ts_ = [float(x["t_epoch_s"]) for x in rows]
        assert ts_ == sorted(ts_) and min(ts_) >= T0 + 0.5 - 1e-6 and max(ts_) <= T0 + 1.5 + 1e-6
        sid1 = [x for x in rows if x["source_id"] == "1"]
        assert sid1 and min(float(x["t_epoch_s"]) for x in sid1) >= T0 + 0.5
        tr = c.get("/api/config").json()["transform"]
        ratio = (tr["pt_ratio"] * tr["ct_ratio"]) if tr.get("enabled", True) else 1.0
        expect = 3 * 57.735 * 5.0 * ratio                                   # 三相总有功 ≈ 3·U·I（计算口径：一次侧）
        assert abs(float(rows[0]["P_total"]) - expect) < expect * 0.02, (rows[0]["P_total"], expect)
        # 2) 不带分路侧 / 分路侧自己导出
        r2 = c.post("/api/nilm/cycles/export", json={"with_branch": False}).json()
        assert r2["ok"] and r2["source_ids"] == [0]
        r3 = c.post("/api/branch/nilm/cycles/export", json={}).json()
        assert r3["ok"] and r3["source_ids"] == [1] and r3["sides"]["branch"]["rows"] >= 90
        # 3) 时间段外 → 409；GET 下载
        assert c.post("/api/nilm/cycles/export", json={"t_from": T0 + 100}).status_code == 409
        g = c.get("/api/nilm/cycles/export", params={"t_from": T0 + 0.5, "t_to": T0 + 0.6})
        assert g.status_code == 200 and "text/csv" in g.headers["content-type"] and g.text.count("\n") >= 6
        c.put("/api/config", json={"branch": {"enabled": False}})


def test_frontend_contract_cycles_export():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for i in ("nilm-exp-from", "nilm-exp-to", "btn-nilm-export", "btn-nilm-exp-fill", "nilm-exp-download", "nilm-keep-range", "nilm-cycle_keep_cycles"):
        assert f'id="{i}"' in html, i
    for s in ("async function exportNilmCycles()", "'/api/nilm/cycles/export'", "'cycle_keep_cycles'",
              "$('#btn-nilm-export').addEventListener('click', exportNilmCycles);"):
        assert s in js, s
