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
