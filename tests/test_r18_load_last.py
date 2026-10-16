"""v0.18：不播放时加载上次播放落盘的曲线 / 事件 / 负荷辨识事件（按 source_id 过滤，两侧共用文件）。"""
from __future__ import annotations

import csv
import os
import pathlib
import shutil
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400.0
T0 = 1_760_000_000.0


def _wait_done(client, path="/api/state", n=60):
    a = None
    for _ in range(n):
        time.sleep(0.2)
        a = client.get(path).json()
        if not a["running"]:
            break
    return a


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r18")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json"))
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    for k in ("ELEC_TOOL_EVENTS_DIR", "ELEC_TOOL_REALTIME_DIR", "ELEC_TOOL_NILM_DIR"):
        mp.delenv(k, raising=False)
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


def test_replay_load_pure_functions(tmp_path):
    from elec_tool import replay_load as rl
    d = tmp_path / "rt"; d.mkdir()
    (d / "voltage_20261015.csv").write_text(
        "t_epoch_s,time_local,source_id,window_s,Ua\n1.0,x,0,1,100\n1.0,x,1,1,50\n2.0,x,0,1,101\n2.0,x,0,1,102\n", encoding="utf-8")
    (d / "voltage_20261014.csv").write_text("t_epoch_s,time_local,window_s,Ua\n0.5,x,1,99\n", encoding="utf-8")   # 旧文件无来源号 → 总线
    (d / "voltage_20261013.v016.csv").write_text("t_epoch_s,time_local,window_s,Ua\n0.1,x,1,1\n", encoding="utf-8")  # 备份跳过
    r0 = rl.load_curves(str(d), 0, hours=24)
    assert [x["t"] for x in r0["records"]["voltage"]] == [0.5, 1.0, 2.0] and r0["records"]["voltage"][-1]["Ua"] == 102   # 同时刻重复留最后
    r1 = rl.load_curves(str(d), 1, hours=24)
    assert [x["t"] for x in r1["records"]["voltage"]] == [1.0] and r1["records"]["voltage"][0]["Ua"] == 50
    e = tmp_path / "ev"; e.mkdir()
    (e / "events_20261015.csv").write_text(
        "source_id,id,status,type,type_name,subject,start_t,start_time,end_t,end_time,duration_s,value_start,value_peak,limit,unit,direction,detail\n"
        "0,1,start,fund_phasor,基波,U1-A,10.0,x,,,,1,1,0.9,V,high,\n"
        "0,1,end,fund_phasor,基波,U1-A,10.0,x,12.0,x,2,1,1.5,0.9,V,high,\n"
        "1,1,start,fund_phasor,基波,U1-A,11.0,x,,,,1,1,0.9,V,high,\n", encoding="utf-8")
    ev0 = rl.load_events(str(e), 0); ev1 = rl.load_events(str(e), 1)
    assert len(ev0) == 1 and ev0[0]["end_t"] == 12.0 and ev0[0]["value_peak"] == 1.5
    assert len(ev1) == 1 and ev1[0]["end_t"] is None
    n = tmp_path / "nl"; n.mkdir()
    (n / "nilm_events_20261015.csv").write_text(
        "source_id,id,algorithm,algorithm_name,channel,t_start,t_start_local,t_end,t_end_local,duration_s,cycles,direction,magnitude_w,delta_p_w,delta_q_var,delta_i_a,pre_p_w,post_p_w,score\n"
        "1,1,cusum,CUSUM,total,5.0,x,5.1,x,0.1,5,up,100,100,0,1,0,100,3\n"
        "1,2,cusum,CUSUM,total,5.0,x,5.1,x,0.1,5,up,100,100,0,1,0,100,3\n", encoding="utf-8")
    assert len(rl.load_nilm_events(str(n), 1)) == 1 and rl.load_nilm_events(str(n), 0) == []


def test_history_and_detector_loaders():
    from elec_tool.config import AppConfig
    from elec_tool.metrics import History
    from elec_tool.events import EventDetector
    from elec_tool.nilm import NilmDetector
    h = History(hours=24)
    n = h.load_records("voltage", [{"t": 1.0, "Ua": 1.0}, {"t": 2.0, "Ua": 2.0, "Ub": 3.0}])
    assert n == 2 and h.count("voltage") == 2
    rows = h.get("voltage")
    assert rows[1]["Ub"] == 3.0 and rows[0].get("Ub") is None
    cfg = AppConfig()
    det = EventDetector(cfg, root=None)
    assert det.load_events([{"type": "fund_phasor", "subject": "U1-A", "start_t": 1.0, "end_t": 2.0, "value_start": 1, "limit": .9, "unit": "V", "direction": "high"},
                            {"type": "nope", "start_t": 1.0}]) == 1
    lst = det.list(); assert len(lst) == 1 and lst[0]["status"] == "ended"
    nd = NilmDetector(cfg, root=None)
    assert nd.load_events([{"algorithm": "cusum", "channel": "total", "t_start": 1.0, "t_end": 1.1, "direction": "up", "magnitude_w": 1}]) == 1
    assert nd.list()[0]["algorithm"] == "cusum"


def test_web_load_last_both_sides(client, tmp_path):
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv
    import app.server as srv
    os.environ.pop("ELEC_TOOL_REALTIME_DIR", None); os.environ.pop("ELEC_TOOL_EVENTS_DIR", None); os.environ.pop("ELEC_TOOL_NILM_DIR", None)
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=0.0)]
    t, u, i = build_signal(specs, FS, 3.0, t0=T0); write_csv(str(tmp_path / "bus.csv"), t, u, i)
    t2, u2, i2 = build_signal(specs, FS, 3.0, t0=T0 + 1.0); write_csv(str(tmp_path / "br.csv"), t2, u2, i2)
    rt = tmp_path / "rt"
    client.put("/api/config", json={"branch": {"enabled": True, "common_window": False},
                                    "output": {"realtime_save": True, "realtime_dir": str(rt)},
                                    "events": {"events_dir": str(tmp_path / "ev")}, "nilm": {"nilm_dir": str(tmp_path / "nl")}})
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(tmp_path / "br.csv"), "file_speed": 0, "custom_time": False},
                                           "output": {"realtime_save": True}})
    # 运行中 → 409
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 1, "custom_time": False}).json()
    assert r["ok"], r
    assert client.post("/api/history/load_last", json={}).status_code == 409
    client.post("/api/engine/stop"); _wait_done(client); _wait_done(client, "/api/branch/state")
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0, "custom_time": False}).json()
    assert r["ok"] and r["branch"]["ok"], r
    _wait_done(client); _wait_done(client, "/api/branch/state")
    rows = []
    for vf in sorted(rt.glob("voltage_*.csv")):
        rows += list(csv.reader(open(vf, encoding="utf-8-sig")))[1:]
    rows = [x for x in rows if x and x[0] != "t_epoch_s"]
    ts0 = {x[0] for x in rows if x[2] == "0"}; ts1 = {x[0] for x in rows if x[2] == "1"}     # 同一时刻重复行只算一次
    n0, n1 = len(ts0), len(ts1)
    rows = [None] + rows
    assert n0 >= 2 and n1 >= 2
    # 模拟「重开软件、尚未播放」：两侧引擎丢弃
    from elec_tool.config import AppConfig
    for side in ("bus", "branch"):
        rn = srv.RUNNERS[side]
        keep = AppConfig.from_dict(rn.cfg.to_dict())
        with rn.lock:
            rn.engine = None; rn.latest = None; rn.thread = None
        rn.set_cfg(keep)                          # 等价于重开软件后从配置文件加载（本测试关闭了持久化，故手工放回）
    assert client.get("/api/history/voltage").json()["count_total"] == 0
    res = client.post("/api/history/load_last", json={}).json()
    assert res["ok"] and res["source_id"] == 0 and res["curves"]["voltage"] == n0, res
    assert res["branch"]["ok"] and res["branch"]["source_id"] == 1 and res["branch"]["curves"]["voltage"] == n1, res["branch"]
    assert client.get("/api/history/voltage").json()["count_total"] == n0
    assert client.get("/api/branch/history/voltage").json()["count_total"] == n1
    hb = client.get("/api/history/voltage").json()["points"]
    assert all(hb[i]["t"] <= hb[i + 1]["t"] for i in range(len(hb) - 1))
    st = client.get("/api/state").json()
    assert st["loaded_last"] and st["loaded_last"]["curves"]["voltage"] == n0 and st["running"] is False
    # 事件/负荷辨识接口可用（数量 ≥0，不报错）
    assert client.get("/api/events").json()["ok"] and client.get("/api/nilm/events").json()["ok"]
    client.put("/api/config", json={"branch": {"enabled": False}, "output": {"realtime_save": False}})


def test_frontend_contract_load_last():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for i in ("btn-load-last", "btn-load-last2", "src-loaded-last"):
        assert f'id="{i}"' in html, i
    for s in ("async function loadLastData()", "'/api/history/load_last'", "function renderLoadedLast(st, eng)",
              "$('#btn-load-last').addEventListener('click', loadLastData);", "$('#btn-load-last2').addEventListener('click', loadLastData);",
              "b.disabled = !!eng.running"):
        assert s in js, s


def test_r19_power_history_has_per_phase_and_overview_series():
    """v0.19：power 趋势记录含分相 Pa..Sc；总览 P/Q/S 图分相曲线默认隐藏。"""
    from elec_tool.metrics import _EXTRACTORS
    q = {"p_total": 3.0, "q_total": 1.5, "s_total": 3.4,
         "p_per_phase": {"A": 1.0, "B": 1.0, "C": 1.0}, "q_per_phase": {"A": .5, "B": .5, "C": .5},
         "s_per_phase": {"A": 1.1, "B": 1.1, "C": 1.2}}
    import types
    rec = _EXTRACTORS["power"](None, types.SimpleNamespace(ok=True, values=q))
    assert list(rec)[:3] == ["P", "Q", "S"] and rec["Pa"] == 1.0 and rec["Qc"] == .5 and rec["Sc"] == 1.2
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for s in ("function pqsSeries(hp, t0)", "defaultHidden: true", "const SER_NONE = '*none*'",
              "drawLine($('#ov-p'), pqsSeries(hp, t0p)", "drawLine($('#ov-p-br'), pqsSeries(bhp, b0p)",
              "function seriesHiddenSet(cv, series)", "function shadeColor(hex, amt)"):
        assert s in js, s
    assert "PQS_DASH" not in js and "dash: PQS_DASH" not in js      # v0.20.1：分相线实线，不再用虚线（曾被看成散点）


def test_r20_restart_autoload(tmp_path, monkeypatch):
    """v0.20：运行→停止后 last_result.json 两侧分键；重启（新 TestClient）自动把 CSV 与最新电气量读回。"""
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv
    import json as _json
    import app.server as srv
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=0.0)]
    t, u, i = build_signal(specs, FS, 3.0, t0=T0); write_csv(str(tmp_path / "bus.csv"), t, u, i)
    t2, u2, i2 = build_signal(specs, FS, 3.0, t0=T0 + 1.0); write_csv(str(tmp_path / "br.csv"), t2, u2, i2)
    cfg = _json.loads((ROOT / "configs" / "default.json").read_text(encoding="utf-8"))
    cfg.setdefault("output", {}).update({"realtime_save": True, "realtime_dir": str(tmp_path / "rt")})
    cfg.setdefault("events", {})["events_dir"] = str(tmp_path / "ev"); cfg.setdefault("nilm", {})["nilm_dir"] = str(tmp_path / "nl")
    cfg.setdefault("branch", {}).update({"enabled": True, "common_window": False})
    (tmp_path / "cfg.json").write_text(_json.dumps(cfg), encoding="utf-8")
    bcfg = {"source": {"kind": "csv_file", "path": str(tmp_path / "br.csv"), "file_speed": 0, "custom_time": False}, "output": {"realtime_save": True}}
    (tmp_path / "branch.json").write_text(_json.dumps(bcfg), encoding="utf-8")
    lr = tmp_path / "last_result.json"
    monkeypatch.setenv("ELEC_TOOL_CONFIG_PATH", str(tmp_path / "cfg.json")); monkeypatch.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(tmp_path / "branch.json"))
    monkeypatch.setenv("ELEC_TOOL_AUTOSTART", ""); monkeypatch.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    for k in ("ELEC_TOOL_EVENTS_DIR", "ELEC_TOOL_REALTIME_DIR", "ELEC_TOOL_NILM_DIR"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(srv.EngineRunner, "LAST_RESULT_FILE", str(lr), raising=False)

    def fresh():
        for side in ("bus", "branch"):
            rn = srv.RUNNERS[side]
            with rn.lock:
                rn.engine = None; rn.latest = None; rn.latest_merged = None; rn.thread = None
            rn.loaded_last = None
    fresh()
    with TestClient(srv.app) as c:
        r = c.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0, "custom_time": False}).json()
        assert r["ok"] and r["branch"]["ok"], r
        _wait_done(c); _wait_done(c, "/api/branch/state")
        assert c.get("/api/history/voltage").json()["count_total"] >= 2
    data = _json.loads(lr.read_text(encoding="utf-8"))
    assert "0" in data and "1" in data and data["0"]["result"]["quantities"] and data["1"]["source_id"] == 1
    # —— 模拟重启：引擎丢弃，新客户端触发 _startup → 自动加载 ——
    fresh()
    with TestClient(srv.app) as c:
        st = c.get("/api/state").json()
        assert st["loaded_last"] and st["loaded_last"]["auto"] is True and st["loaded_last"]["result"] is True, st["loaded_last"]
        assert c.get("/api/history/voltage").json()["count_total"] >= 2
        assert c.get("/api/branch/history/voltage").json()["count_total"] >= 2
        res = c.get("/api/result?full=true").json()
        assert res and res.get("quantities") and "voltage" in res["quantities"]
        bres = c.get("/api/branch/result?full=false").json()
        assert bres and bres.get("quantities")
        bst = c.get("/api/branch/state").json()
        assert bst["loaded_last"] and bst["loaded_last"]["auto"] is True
    # 关闭自动加载 → 重启后不加载
    cfg["output"]["autoload_last"] = False
    (tmp_path / "cfg.json").write_text(_json.dumps(cfg), encoding="utf-8")
    fresh()
    with TestClient(srv.app) as c:
        assert c.get("/api/state").json()["loaded_last"] is None
        assert c.get("/api/history/voltage").json()["count_total"] == 0


def test_load_last_anchored_on_last_result_t_ref(tmp_path):
    """v0.30：目录里混有「数据时标更新」的曲线/事件时，load_last 以 last_result.json 的 t_ref（上次播放结束的数据时刻）为锚点，
    只取 [t_ref-hours, t_ref] —— 否则上次实际播放（时标更旧）的曲线与负荷事件会被 24 h 窗滤掉（实测踩坑：先播今天时标的样例、再播三天前的真实数据，重启后负荷事件 0 条）。"""
    from elec_tool import replay_load
    d = tmp_path / "rt"; d.mkdir()
    nl = tmp_path / "nl"; nl.mkdir()
    old_t = 1791878400.0           # 2026-10-13
    new_t = old_t + 3 * 86400      # 2026-10-16（更新的时标，属于别的播放）
    hdr = "t_epoch_s,time_local,source_id,window_s,P,Q,S\n"
    (d / "power_20261013.csv").write_text(hdr + "".join(f"{old_t + k},x,0,1,{100 + k},1,1\n" for k in range(5)), encoding="utf-8-sig")
    (d / "power_20261016.csv").write_text(hdr + "".join(f"{new_t + k},x,0,1,{900 + k},1,1\n" for k in range(5)), encoding="utf-8-sig")
    nh = "source_id,id,algorithm,algorithm_name,channel,t_start,t_start_local,t_end,t_end_local,duration_s,cycles,direction,magnitude_w,delta_p_w,delta_q_var,delta_i_a,pre_p_w,post_p_w,score\n"
    (nl / "nilm_events_20261013.csv").write_text(nh + f"0,1,cusum,CUSUM,total,{old_t + 2},x,{old_t + 2},x,0,0,up,100,100,0,0,0,100,1\n", encoding="utf-8-sig")
    (nl / "nilm_events_20261016.csv").write_text(nh + f"0,1,cusum,CUSUM,total,{new_t + 2},x,{new_t + 2},x,0,0,up,900,900,0,0,0,900,1\n", encoding="utf-8-sig")
    # 无锚点：旧行为 → 取最新时标（10-16）
    r0 = replay_load.load_curves(str(d), 0, 24)
    assert [p["P"] for p in r0["records"]["power"]] == [900, 901, 902, 903, 904]
    assert [e["magnitude_w"] for e in replay_load.load_nilm_events(str(nl), 0, t_from=r0["t_last"] - 86400)] == [900.0]
    # 锚点 = 上次播放结束时刻（10-13）→ 只取 10-13 的曲线与事件
    anchor = old_t + 4
    r1 = replay_load.load_curves(str(d), 0, 24, t_anchor=anchor)
    assert [p["P"] for p in r1["records"]["power"]] == [100, 101, 102, 103, 104] and r1["t_last"] == anchor
    evs = replay_load.load_nilm_events(str(nl), 0, t_from=anchor - 86400, t_to=anchor)
    assert [e["magnitude_w"] for e in evs] == [100.0]
    assert replay_load.load_events(str(nl), 0, t_from=anchor - 86400, t_to=anchor) == []      # 目录里没有 events_*.csv → 空，不报错
