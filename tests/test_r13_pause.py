"""第 13 轮：离线文件源的暂停 / 恢复播放。

语义：暂停＝引擎线程不再读文件、不计算、数据时刻原地不动，缓冲/历史/事件保留；恢复＝从暂停处继续（不重读、不跳过）。
仅 csv_file 源可用；其他源 / 未运行 / 已播完 → 400。停止时若处于暂停也能立刻退出。
"""
from __future__ import annotations

import csv
import pathlib
import shutil
import time

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400


def _write_csv(path, dur=8.0):
    n = int(dur * FS); t = np.arange(n) / FS; w = 2 * np.pi * 50 * t
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(n):
            row = [f"{1_700_000_000 + t[k]:.6f}"]
            for ph in (0, -2.0944, 2.0944):
                row += [f"{81.65 * np.sin(w[k] + ph):.4f}", f"{7.07 * np.sin(w[k] + ph - 0.3):.5f}"]
            wr.writerow(row)
    return str(path)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r13cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0"); mp.setenv("ELEC_TOOL_EVENTS_DIR", str(d / "ev"))
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(d / "rt")); mp.setenv("ELEC_TOOL_NILM_DIR", str(d / "nilm"))
    # 让离线回放慢一点（每次 poll 多睡 15 ms），否则 8 s 文件瞬间播完、来不及暂停
    import elec_tool.engine as eng_mod
    real_poll = eng_mod.LiveEngine.poll_once

    def slow_poll(self):
        time.sleep(0.015)
        return real_poll(self)
    mp.setattr(eng_mod.LiveEngine, "poll_once", slow_poll)
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


def _samples(client):
    return int(client.get("/api/state").json()["engine"].get("samples_in", 0))


def test_pause_resume_roundtrip(client):
    p = _write_csv(client.dir / "p.csv")
    client.post("/api/engine/stop")
    # 未运行 → 400
    assert client.post("/api/engine/pause").status_code == 400
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": p, "block_samples": 640})
    assert r.status_code == 200, r.text
    time.sleep(0.4)
    st = client.get("/api/state").json()
    assert st["running"] and st["pausable"] and not st["paused"]
    # 暂停：样本数冻结、状态 paused、数据时刻不变
    r = client.post("/api/engine/pause"); assert r.status_code == 200 and r.json()["paused"]
    time.sleep(0.1)
    s1 = _samples(client); t1 = client.get("/api/state").json()["engine"].get("data_t_end")
    time.sleep(0.6)
    st = client.get("/api/state").json()
    assert st["paused"] and st["running"] and not st["finished"]
    assert _samples(client) == s1 and st["engine"].get("data_t_end") == t1
    assert st["paused_total_s"] >= 0.5
    # 暂停期间重复暂停幂等；缓冲仍可取快照
    assert client.post("/api/engine/pause").status_code == 200
    assert client.get("/api/result").status_code == 200
    # 恢复：继续推进且不重读（样本只增不减、单调）
    r = client.post("/api/engine/resume"); assert r.status_code == 200 and not r.json()["paused"]
    time.sleep(0.6)
    st = client.get("/api/state").json()
    assert not st["paused"] and _samples(client) > s1
    assert 0.5 <= st["paused_total_s"] < 1.5                      # 恢复后累计暂停时长不再增长
    # 播完 → finished；之后暂停 → 400（已播放完毕）
    for _ in range(200):
        st = client.get("/api/state").json()
        if st["finished"] or not st["running"]:
            break
        time.sleep(0.1)
    assert st["finished"] and st["engine"]["samples_in"] == 8 * FS
    assert client.post("/api/engine/pause").status_code == 400


def test_pause_then_stop_exits_promptly_and_non_file_sources_refused(client):
    p = _write_csv(client.dir / "q.csv", dur=4.0)
    client.post("/api/engine/start", json={"kind": "csv_file", "path": p, "block_samples": 640})
    time.sleep(0.3)
    assert client.post("/api/engine/pause").status_code == 200
    t0 = time.time()
    assert client.post("/api/engine/stop").status_code == 200
    assert time.time() - t0 < 1.5
    st = client.get("/api/state").json()
    assert not st["running"] and not st["paused"]
    # 模拟器源：不可暂停
    client.post("/api/engine/start", json={"kind": "simulator", "sim_speed": 1.0})
    time.sleep(0.3)
    st = client.get("/api/state").json()
    assert st["running"] and not st["pausable"]
    r = client.post("/api/engine/pause")
    assert r.status_code == 400 and "csv_file" in r.json()["error"]
    client.post("/api/engine/stop")


def test_frontend_wiring():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'id="btn-pause"' in html and 'id="btn-pause2"' in html
    for s in ("/api/engine/pause", "/api/engine/resume", "function renderPauseButtons", "function togglePause",
              "st.paused", "st.pausable", "'已暂停'"):
        assert s in js, s
    assert ".pill.warn" in (ROOT / "app" / "static" / "style.css").read_text(encoding="utf-8")
