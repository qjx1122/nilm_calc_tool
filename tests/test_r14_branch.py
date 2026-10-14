"""第 14 轮：总线侧 + 分路侧设备 双数据源。

- 分路侧＝独立 AppConfig（独立文件、独立输出目录）+ 独立引擎；接口 `/api/branch/<同名>`、`/ws/branch`。
- 总线侧 `branch.enabled=true` 时：总线「启动」同时启动分路侧；停止 / 暂停 / 恢复联动。
- 两侧配置互不污染；两侧结果各自可查。
"""
from __future__ import annotations

import csv
import json
import pathlib
import shutil
import time

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400


def _csv(path, dur, amp_i=7.07):
    n = int(dur * FS); t = np.arange(n) / FS; w = 2 * np.pi * 50 * t
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(n):
            row = [f"{1_700_000_000 + t[k]:.6f}"]
            for ph in (0, -2.0944, 2.0944):
                row += [f"{81.65 * np.sin(w[k] + ph):.4f}", f"{amp_i * np.sin(w[k] + ph):.5f}"]
            wr.writerow(row)
    return str(path)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r14")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json"))
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "1")                    # 本组专门验证两侧各自落盘
    mp.delenv("ELEC_TOOL_EVENTS_DIR", raising=False); mp.delenv("ELEC_TOOL_REALTIME_DIR", raising=False); mp.delenv("ELEC_TOOL_NILM_DIR", raising=False)
    import elec_tool.engine as eng_mod
    real_poll = eng_mod.LiveEngine.poll_once

    def slow_poll(self):
        time.sleep(0.01)
        return real_poll(self)
    mp.setattr(eng_mod.LiveEngine, "poll_once", slow_poll)
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


def test_sides_and_independent_configs(client):
    s = client.get("/api/sides").json()
    assert set(s["sides"]) == {"bus", "branch"} and s["current"] == "bus"
    assert s["sides"]["branch"]["api_prefix"] == "/api/branch" and s["sides"]["branch"]["ws_path"] == "/ws/branch"
    assert client.get("/api/state").json()["side"] == "bus"
    b = client.get("/api/branch/state").json()
    assert b["side"] == "branch" and b["branch"] is None
    # 分路侧出厂：输出目录分开
    bc = client.get("/api/branch/config").json()
    assert bc["output"]["realtime_dir"].startswith("output/branch") and bc["nilm"]["nilm_dir"].startswith("output/branch")
    # 改分路侧 PT/CT 不影响总线侧；改总线侧不影响分路侧
    r = client.put("/api/branch/config", json={"transform": {"pt_ratio": 10.0}})
    assert r.status_code == 200 and r.json()["config"]["transform"]["pt_ratio"] == 10.0
    assert client.get("/api/config").json()["transform"]["pt_ratio"] == 100.0
    r = client.put("/api/config", json={"transform": {"ct_ratio": 20.0}})
    assert r.status_code == 200
    assert client.get("/api/branch/config").json()["transform"]["ct_ratio"] == 15.0
    # 两侧各自持久化到不同文件
    assert (client.dir / "branch.json").exists() and json.load(open(client.dir / "branch.json", encoding="utf-8"))["transform"]["pt_ratio"] == 10.0
    assert json.load(open(client.dir / "cfg.json", encoding="utf-8"))["transform"]["ct_ratio"] == 20.0
    # 分路侧配置非法 → 400，且不改动
    assert client.put("/api/branch/config", json={"sampling": {"fs": -1}}).status_code == 400
    client.put("/api/branch/config", json={"transform": {"pt_ratio": 100.0}}); client.put("/api/config", json={"transform": {"ct_ratio": 15.0}})


def test_coupled_start_pause_resume_stop(client):
    bus_p = _csv(client.dir / "bus.csv", 6.0, amp_i=7.07)
    br_p = _csv(client.dir / "br.csv", 6.0, amp_i=1.414)
    client.post("/api/engine/stop")
    # 离线文件限定：总线侧为模拟器时即使启用也不联动
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": br_p, "file_speed": 1}})
    client.put("/api/config", json={"branch": {"enabled": True}})
    r = client.post("/api/engine/start", json={"kind": "simulator"})
    assert r.status_code == 200 and r.json()["branch"]["skipped"] and "离线文件" in r.json()["branch"]["reason"]
    client.post("/api/engine/stop")
    # 分路侧路径未配置 → 启动时报错、不影响总线
    client.put("/api/branch/config", json={"source": {"kind": "simulator", "path": ""}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 0})
    assert r.status_code == 200 and r.json()["branch"]["ok"] is False and "csv_file" in r.json()["branch"]["error"]
    client.post("/api/engine/stop")
    # 未启用：总线启动不带动分路侧
    client.put("/api/config", json={"branch": {"enabled": False}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 1})
    assert r.status_code == 200 and r.json()["branch"]["skipped"]
    time.sleep(0.5)
    assert client.get("/api/branch/state").json()["running"] is False
    client.post("/api/engine/stop")
    # 启用 + 分路侧配置好 → 同时播放
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": br_p, "file_speed": 1}})
    client.put("/api/config", json={"branch": {"enabled": True}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 1})
    assert r.status_code == 200 and r.json()["branch"]["ok"], r.text
    time.sleep(1.5)
    st, bst = client.get("/api/state").json(), client.get("/api/branch/state").json()
    assert st["running"] and bst["running"] and bst["engine"]["samples_in"] > 0
    assert st["branch"]["enabled"] and st["branch"]["running"] and st["branch"]["source_path"] == br_p
    # 两侧结果独立：电流幅值不同（总线 7.07/√2≈5 A ×CT，分路 1 A ×CT）
    rb, rr = client.get("/api/result?full=true").json(), client.get("/api/branch/result?full=true").json()
    ib = rb["quantities"]["current"]["values"]["rms"]["A"]; ir = rr["quantities"]["current"]["values"]["rms"]["A"]
    assert ib == pytest.approx(5.0 * 15, rel=0.05) and ir == pytest.approx(1.0 * 15, rel=0.05), (ib, ir)
    # 联动暂停
    r = client.post("/api/engine/pause"); assert r.status_code == 200 and r.json()["branch"]["ok"]
    time.sleep(0.2); n1 = client.get("/api/branch/state").json()["engine"]["samples_in"]
    time.sleep(0.6); b2 = client.get("/api/branch/state").json()
    assert b2["paused"] and b2["engine"]["samples_in"] == n1
    # 联动恢复
    r = client.post("/api/engine/resume"); assert r.status_code == 200 and r.json()["branch"]["ok"]
    time.sleep(0.8)
    assert client.get("/api/branch/state").json()["engine"]["samples_in"] > n1
    # 分路侧单独可控：只暂停分路侧
    assert client.post("/api/branch/engine/pause").status_code == 200
    assert client.get("/api/state").json()["paused"] is False and client.get("/api/branch/state").json()["paused"] is True
    client.post("/api/branch/engine/resume")
    # 联动停止
    client.post("/api/engine/stop")
    time.sleep(0.3)
    assert not client.get("/api/state").json()["running"] and not client.get("/api/branch/state").json()["running"]
    # 分路侧启动失败（路径不存在）不影响总线侧
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(client.dir / "nope.csv")}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 0})
    assert r.status_code == 200 and r.json()["ok"]                     # 文件不存在在分路侧线程打开时才报：异步错误
    time.sleep(0.6)
    st = client.get("/api/state").json()
    assert st["running"] and st["branch"]["error"] and not st["branch"]["running"], st["branch"]
    client.post("/api/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": False}})


def test_branch_websocket_and_outputs(client):
    br_p = _csv(client.dir / "br2.csv", 1.0)
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": br_p, "file_speed": 0},
                                           "output": {"realtime_dir": str(client.dir / "out_br" / "rt")},
                                           "events": {"events_dir": str(client.dir / "out_br" / "ev")},
                                           "nilm": {"nilm_dir": str(client.dir / "out_br" / "nilm")}})
    with client.websocket_connect("/ws/branch") as ws:
        hello = json.loads(ws.receive_text())
        assert hello["type"] == "hello" and hello["data"]["side"] == "branch"
        r = client.post("/api/branch/engine/start", json={})
        assert r.status_code == 200 and r.json()["side"] == "branch" and "branch" not in r.json()
        got_result = False
        for _ in range(200):
            m = json.loads(ws.receive_text())
            if m["type"] == "result":
                got_result = True
            if m["type"] == "state" and m["data"].get("finished"):
                break
        assert got_result
    stb = client.get("/api/state").json()
    assert stb["running"] is False, (stb["engine"].get("source_kind"), stb["source"].get("path"), stb["engine"].get("samples_in"))   # 总线侧没被带起来
    import app.server as srv
    assert srv.RUNNERS["branch"].engine.writer.rows_written and any(srv.RUNNERS["branch"].engine.writer.rows_written.values())


def test_frontend_wiring():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for s in ('id="side-bus"', 'id="side-branch"', 'id="branch-panel"', 'id="br-enabled"', 'id="br-path"', 'id="st-branch"',
              'id="br-customtime"', 'id="br-utc"', 'id="btn-br-probe"', 'id="br-mode-note"'):
        assert s in html, s
    for s in ("function apiUrl", "async function setSide", "/ws/branch", "'/api/branch/' + path.slice(5)",
              "function renderBranchChip", "async function saveBranchSource", "localStorage.setItem('elec_side'"):
        assert s in js, s
