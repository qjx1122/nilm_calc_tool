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
    # v0.17.2：分路侧输出目录与总线侧相同（两侧写同一文件，按 source_id 区分）
    bc = client.get("/api/branch/config").json(); cc = client.get("/api/config").json()
    assert bc["output"]["realtime_dir"] == cc["output"]["realtime_dir"] and bc["nilm"]["nilm_dir"] == cc["nilm"]["nilm_dir"]
    assert bc["events"]["events_dir"] == cc["events"]["events_dir"] and "output/branch" not in bc["output"]["realtime_dir"]
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
    # v0.16：两侧输入方式各自独立——总线侧为模拟器、分路侧为离线文件也同时启动（不共用节拍钟）
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": br_p, "file_speed": 1}})
    client.put("/api/config", json={"branch": {"enabled": True}})
    r = client.post("/api/engine/start", json={"kind": "simulator"})
    assert r.status_code == 200 and r.json()["branch"]["ok"] and r.json()["branch"]["synced_pace"] is False
    time.sleep(0.5)
    assert client.get("/api/branch/state").json()["running"] is True
    client.post("/api/engine/stop")
    assert client.get("/api/branch/state").json()["running"] is False
    # 分路侧为模拟器：总线侧离线文件 + 分路侧模拟器同时跑
    client.put("/api/branch/config", json={"source": {"kind": "simulator", "path": ""}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 0})
    assert r.status_code == 200 and r.json()["branch"]["ok"] and r.json()["branch"]["source_kind"] == "simulator"
    client.post("/api/engine/stop")
    # 分路侧 csv_file 但文件不存在 → 启动时报错、不影响总线
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(client.dir / "nope.csv")}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 0})
    assert r.status_code == 200
    time.sleep(0.5)
    bst = client.get("/api/branch/state").json()
    assert bst["running"] is False and bst.get("error")
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
    assert 'id="side-bus"' not in html and html.count('class="navitem" data-view="') >= 17 and 'id="ov-sides"' in html
    # v0.23：电气量 9 个子界面合并为「左总线/右分路」双列，导航只保留一组（data-side=bus）；分路侧分组只剩事件/负荷辨识/窗口/导出
    for v in ("voltage", "current", "power", "power_factor", "fundamental", "harmonic", "interharmonic", "dc", "spectrum"):
        assert f'data-view="{v}" data-side="bus"' in html and f'data-view="{v}" data-side="branch"' not in html, v
    for v in ("events", "nilm", "windows", "export"):
        assert f'data-view="{v}" data-side="branch"' in html, v
    for s in ("const DUAL_VIEWS", "function buildDualViews", "function renderDual", "function branchDualActive", "function refreshBranchDual", "'no-branch-nav'"):
        assert s in js, s
    assert 'data-view="source" data-side="branch"' not in html      # 分路侧配置集中在总览的数据源页
    for s in ('data-view="voltage" data-side="bus"', 'id="branch-panel"',
              'data-view="compare"', 'id="view-compare"', 'id="br-pt"', 'id="br-fs"', 'id="br-toffset"', 'id="topstats-bus"', 'id="topstats-branch"', 'id="st-br-running"', 'id="st-br-samples"',
              'id="br-mapen"', 'id="br-map-ua"', 'id="br-common"', 'id="br-common-start"', 'id="topstats-common"', 'id="st-cw-dur"', 'id="btn-br-map-save"', 'id="btn-map-save"', 'id="br-enabled"', 'id="br-path"', 
              'id="br-customtime"', 'id="br-utc"', 'id="btn-br-probe"', 'id="br-mode-note"'):
        assert s in html, s
    for s in ("function apiUrl", "async function setSide", "/ws/branch", "'/api/branch/' + path.slice(5)",
              "async function saveBranchSource", "async function switchView(v, side)", "function renderOverviewSides",
              "function renderBadges", "function peerSummary", "async function refreshCompare", "/api/compare/", "async function saveColumns(side)", "async function refreshOverviewBranch", "function installIncrementalDom", "function chartSig", "async function previewCommonWindow"):
        assert s in js, s


def test_r15_align_rows_and_compare_endpoint(client):
    """第 15 轮：跨侧时间轴对齐与差值。纯函数 + 端点形状。"""
    from app.server import _align_rows
    bus = [{"t": 100.0 + i, "window_s": 1.0, "P": 1000.0 + i, "Q": 10.0} for i in range(5)]
    br = [{"t": 90.05 + i, "window_s": 1.0, "P": 400.0, "Q": 4.0} for i in range(4)]   # 起点差 10 s，相位差 50 ms
    r0 = _align_rows(bus, br, offset=0.0, tol=0.6, max_points=100)
    assert r0["aligned_count"] == 0
    r1 = _align_rows(bus, br, offset=10.0, tol=0.6, max_points=100)
    assert r1["aligned_count"] == 4 and r1["unmatched_bus"] == 1
    p = r1["points"][0]
    assert abs(p["dt_s"] - 0.05) < 1e-9 and p["diff"]["P"] == 600.0 and abs(p["ratio_pct"]["P"] - 40.0) < 1e-9
    assert "Q" in p["diff"] and "Q" in p["ratio_pct"]
    # 容差太小 → 不配对
    assert _align_rows(bus, br, offset=10.0, tol=0.01, max_points=100)["aligned_count"] == 0
    # 端点：两侧无引擎时形状完整
    d = client.get("/api/compare/power").json()
    assert d["quantity"] == "power" and d["aligned_count"] >= 0 and "offset_s" in d and "tol_s" in d and "points" in d
    assert client.get("/api/compare/nope").status_code == 400
    sm = client.get("/api/compare").json()
    assert set(sm["quantities"]) >= {"power", "current", "voltage"}
    # 对齐参数随总线侧 config.branch 保存
    r = client.put("/api/config", json={"branch": {"time_offset_s": 1.5, "align_tol_s": 0.2}})
    assert r.status_code == 200
    assert client.get("/api/config").json()["branch"]["time_offset_s"] == 1.5
    assert client.get("/api/compare/power").json()["offset_s"] == 1.5
    client.put("/api/config", json={"branch": {"time_offset_s": 0.0, "align_tol_s": 0.0}})


def test_r15_common_window(client, tmp_path):
    """v0.15：只播放两侧公共时间段 + 自定义起始时间 + 倍速同步 + 残留起点还原。"""
    import numpy as np
    from elec_tool.selftest import build_signal
    from tests.conftest import write_csv, default_specs as _ds  # noqa
    from elec_tool.selftest import HarmSpec
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=0.0)]
    fs = 6400.0; T0 = 1_760_000_000.0
    t, u, i = build_signal(specs, fs, 3.0, t0=T0)                      # 总线：T0 → T0+3
    write_csv(str(tmp_path / "bus.csv"), t, u, i)
    t2, u2, i2 = build_signal(specs, fs, 3.0, t0=T0 + 1.0)             # 分路：T0+1 → T0+4 → 公共 [T0+1, T0+3]
    write_csv(str(tmp_path / "br.csv"), t2, u2, i2)
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": True, "common_window": True, "common_start": ""}})
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(tmp_path / "br.csv"), "file_speed": 5, "custom_time": False}})
    pv = client.get("/api/common_window?preview=1").json()
    assert pv["ok"] is False                                                 # 总线侧还没配文件
    client.put("/api/config", json={"source": {"kind": "csv_file", "path": str(tmp_path / "bus.csv")}})
    pv = client.get("/api/common_window?preview=1").json()
    assert pv["ok"] and abs(pv["duration_s"] - 2.0) < 1e-3 and abs(pv["t_start"] - (T0 + 1.0)) < 1e-6
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0}).json()
    assert r["ok"] and r["common_window"]["enabled"] and r["branch"]["ok"], r
    for _ in range(60):
        time.sleep(0.2)
        a = client.get("/api/state").json(); b = client.get("/api/branch/state").json()
        if not a["running"] and not b["running"]:
            break
    assert abs(a["engine"]["samples_in"] - 2 * fs) <= 640 and abs(b["engine"]["samples_in"] - 2 * fs) <= 640, (a["engine"]["samples_in"], b["engine"]["samples_in"])
    assert b["config"]["source"]["file_speed"] == 0 and a["common_window"]["duration_s"] > 1.9      # 倍速同步 + state 带公共时间段
    # 自定义起始时间：公共起点 + 1 s → 两侧各播 1 s
    client.put("/api/config", json={"branch": {"common_start": repr(T0 + 2.0)}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0}).json()
    assert r["common_window"]["play_start_source"] == "自定义播放起始时间"
    for _ in range(60):
        time.sleep(0.2)
        a = client.get("/api/state").json(); b = client.get("/api/branch/state").json()
        if not a["running"] and not b["running"]:
            break
    assert abs(a["engine"]["samples_in"] - fs) <= 640 and abs(b["engine"]["samples_in"] - fs) <= 640, (a["engine"]["samples_in"], b["engine"]["samples_in"])
    # 起始时间不在公共段内 → 400，两侧都不启动
    client.put("/api/config", json={"branch": {"common_start": repr(T0 + 3.5)}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0})
    assert r.status_code == 400 and "不在公共时间段" in r.json()["error"]
    # 关闭公共时间段 → 自动写入的起点/终点被还原，总线侧播完整 3 s
    client.put("/api/config", json={"branch": {"common_window": False, "common_start": ""}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0}).json()
    assert r["ok"] and "common_window" not in r and r["config"]["source"]["play_start_mode"] == "begin" and r["config"]["source"]["play_end_time"] == ""
    for _ in range(60):
        time.sleep(0.2)
        a = client.get("/api/state").json()
        if not a["running"]:
            break
    assert abs(a["engine"]["samples_in"] - 3 * fs) <= 640
    assert a["common_window"] is None
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": False}})


def test_r15_1_pace_sync_and_merged_result(client, tmp_path):
    """v0.15.1：两侧共用节拍钟（state.source.pace_clock 同一 wall0、两侧进度差 ≤ 容差）；
    两侧长度不一致时先播完的一侧 done、另一侧继续播到自己的结尾；/api/result?full=false 为各量并集。"""
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=0.0)]
    fs = 6400.0; T0 = 1_760_000_000.0
    t, u, i = build_signal(specs, fs, 3.0, t0=T0); write_csv(str(tmp_path / "bus.csv"), t, u, i)            # 总线 3 s
    t2, u2, i2 = build_signal(specs, fs, 1.5, t0=T0); write_csv(str(tmp_path / "br.csv"), t2, u2, i2)       # 分路 1.5 s（更短）
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": True, "common_window": False, "common_start": ""},
                                    "source": {"kind": "csv_file", "path": str(tmp_path / "bus.csv")}})
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(tmp_path / "br.csv"), "custom_time": False}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 3}).json()
    assert r["ok"] and r["branch"]["ok"], r
    worst = 0.0; n_both = 0; a = b = None
    for _ in range(100):
        time.sleep(0.1)
        a = client.get("/api/state").json(); b = client.get("/api/branch/state").json()
        pa, pb = a["source"].get("pace_clock"), b["source"].get("pace_clock")
        if a["running"] and b["running"] and pa and pb and pa.get("wall0") and pb.get("wall0"):
            assert pa["wall0"] == pb["wall0"]                          # 同一只钟
            pr = pa.get("progress_s") or {}
            if "bus" in pr and "branch" in pr:
                n_both += 1; worst = max(worst, abs(pr["bus"] - pr["branch"]))
        if not a["running"] and not b["running"]:
            break
    assert n_both >= 2 and worst <= 0.25, (n_both, worst)              # 严格同步：块起点领先 ≤0.1 s → 进度差 ≤ 1 块 + 0.1
    assert abs(b["engine"]["samples_in"] - 1.5 * fs) <= 640 and abs(a["engine"]["samples_in"] - 3.0 * fs) <= 640   # 短的播完停，长的播完整
    assert a["finished"] and b["finished"]
    pc = a["source"]["pace_clock"]; assert pc["done"].get("branch") and pc["done"].get("bus")
    full = client.get("/api/result?full=false").json()
    assert {"voltage", "power", "fundamental", "harmonic"} <= set(k for k, v in full["quantities"].items() if v.get("ok"))


def test_r15_3_auto_play_fields_never_leak(client, tmp_path):
    """v0.15.3：公共时间段自动写入的 play_start/play_end 只进引擎，不进 /api/config、不被持久化；
    旧版本泄漏到配置文件里的残留值在加载时被清理（否则下次播放别的文件会按时标扫到文件尾才开始）。"""
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv
    import app.server as srv
    from elec_tool.config import AppConfig
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=0.0)]
    fs = 6400.0; T0 = 1_760_000_000.0
    t, u, i = build_signal(specs, fs, 2.0, t0=T0); write_csv(str(tmp_path / "bus.csv"), t, u, i)
    t2, u2, i2 = build_signal(specs, fs, 2.0, t0=T0 + 0.5); write_csv(str(tmp_path / "br.csv"), t2, u2, i2)
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": True, "common_window": True, "common_start": ""},
                                    "source": {"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "play_start_mode": "begin", "play_start_value": ""}})
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(tmp_path / "br.csv"), "custom_time": False}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0}).json()
    assert r["ok"] and r["common_window"]["enabled"], r
    # 运行中：引擎按公共时间段播放（引擎配置里是 time 起点），但对外配置仍是用户的 begin
    st = client.get("/api/state").json()
    assert st["source"]["play_start_mode"] == "time"                      # 引擎（数据源 info）确实在按时标起点播
    c = client.get("/api/config").json()["source"]
    assert c["play_start_mode"] == "begin" and c["play_start_value"] == "" and c["play_end_time"] == ""
    assert r["config"]["source"]["play_start_mode"] == "begin"
    bc = client.get("/api/branch/config").json()["source"]
    assert bc["play_start_mode"] == "begin" and bc["play_end_time"] == ""
    # 运行中保存别的设置，也不会把自动值带出去
    client.put("/api/config", json={"branch": {"common_start": ""}})
    c = client.get("/api/config").json()["source"]
    assert c["play_start_mode"] == "begin" and c["play_end_time"] == ""
    for _ in range(50):
        time.sleep(0.1)
        a = client.get("/api/state").json()
        if not a["running"]:
            break
    assert abs(a["engine"]["samples_in"] - 1.5 * fs) <= 640                # 公共段 1.5 s 仍然生效
    # 旧版本泄漏的配置文件：加载时清理
    cfg = AppConfig(); cfg.source.kind = "csv_file"
    cfg.source.play_start_mode = "time"; cfg.source.play_start_value = "1792044861.0"; cfg.source.play_end_time = "1792044865.41"
    notes = srv._sanitize_leaked_play(cfg, "bus")
    assert len(notes) == 2 and cfg.source.play_start_mode == "begin" and cfg.source.play_end_time == ""
    cfg.source.play_start_mode = "time"; cfg.source.play_start_value = "2026-10-15 08:00:00"
    assert srv._sanitize_leaked_play(cfg, "bus") == [] and cfg.source.play_start_mode == "time"   # 人填的时标不动
