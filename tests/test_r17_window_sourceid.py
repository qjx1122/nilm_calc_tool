"""v0.17（第 23 轮）：① 指定时间段播放（单侧 / 公共时间段 common_end）② 曲线缩放前端契约 ③ 所有 CSV 的 source_id 列 + 分路曲线一并保存。"""
from __future__ import annotations

import csv
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
    d = tmp_path_factory.mktemp("r17")
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


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv
    d = tmp_path_factory.mktemp("r17data")
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=0.0)]
    t, u, i = build_signal(specs, FS, 4.0, t0=T0)                 # 总线 T0 → T0+4
    write_csv(str(d / "bus.csv"), t, u, i)
    t2, u2, i2 = build_signal(specs, FS, 4.0, t0=T0 + 1.0)        # 分路 T0+1 → T0+5；公共 [T0+1, T0+4]
    write_csv(str(d / "br.csv"), t2, u2, i2)
    return d


# ---------- ① 配置层 ----------

def test_config_play_window_fields_and_validation():
    from elec_tool.config import AppConfig, ConfigError, SourceConfig
    cfg = AppConfig()
    assert cfg.source.play_window is False and cfg.source.play_window_start == "" and cfg.source.play_window_end == ""
    assert cfg.branch.common_end == "" and cfg.output.source_id == 0
    s = SourceConfig(kind="csv_file", path="x.csv", play_window=True, play_window_start="08:00:00", play_window_end="08:00:10")
    s.validate()
    s = SourceConfig(kind="csv_file", path="x.csv", play_window=True, play_window_start="", play_window_end="")
    s.validate()                                                 # 两端留空＝整个文件
    with pytest.raises(ConfigError):
        SourceConfig(kind="csv_file", path="x.csv", play_window=True, play_window_start="abc").validate()
    with pytest.raises(ConfigError):
        SourceConfig(kind="csv_file", path="x.csv", play_window=True, play_window_start="08:00:10", play_window_end="08:00:05").validate()
    from elec_tool.config import OutputConfig
    with pytest.raises(ConfigError):
        OutputConfig(source_id=2).validate()


# ---------- ① 单侧时间段播放 ----------

def test_single_side_play_window_start_end_and_empty_semantics(client, files):
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": False, "common_window": False}})
    base = {"kind": "csv_file", "path": str(files / "bus.csv"), "file_speed": 0, "custom_time": False}
    # 起止都给：T0+1 → T0+3 → 2 s
    r = client.post("/api/engine/start", json={**base, "play_window": True, "play_window_start": repr(T0 + 1.0), "play_window_end": repr(T0 + 3.0)}).json()
    assert r["ok"], r
    a = _wait_done(client)
    assert abs(a["engine"]["samples_in"] - 2 * FS) <= 640, a["engine"]["samples_in"]
    assert abs(a["source"]["play_end_time"] - (T0 + 3.0)) < 1e-6
    # 对外配置仍是用户字段：起点模式不被自动值污染
    c = client.get("/api/config").json()
    assert c["source"]["play_window"] is True and c["source"]["play_start_mode"] == "begin" and c["source"]["play_end_time"] == ""
    # 只给终点：从数据起点播到 T0+1.5 → 1.5 s
    r = client.post("/api/engine/start", json={**base, "play_window": True, "play_window_start": "", "play_window_end": repr(T0 + 1.5)}).json()
    assert r["ok"], r
    a = _wait_done(client)
    assert abs(a["engine"]["samples_in"] - 1.5 * FS) <= 640, a["engine"]["samples_in"]
    # 只给起点：T0+3 播到文件尾 → 1 s
    r = client.post("/api/engine/start", json={**base, "play_window": True, "play_window_start": repr(T0 + 3.0), "play_window_end": ""}).json()
    assert r["ok"], r
    a = _wait_done(client)
    assert abs(a["engine"]["samples_in"] - 1 * FS) <= 640, a["engine"]["samples_in"]
    # 未启用（默认）：整个文件 4 s，即使起止文本还在
    r = client.post("/api/engine/start", json={**base, "play_window": False, "play_window_start": repr(T0 + 3.0), "play_window_end": repr(T0 + 3.5)}).json()
    assert r["ok"], r
    a = _wait_done(client)
    assert abs(a["engine"]["samples_in"] - 4 * FS) <= 640, a["engine"]["samples_in"]


def test_play_window_tod_end_text(client, files):
    """终点只填 HH:MM:SS：按文件时标当天折算。"""
    from elec_tool.timefmt import fmt_local
    client.post("/api/engine/stop")
    end_txt = fmt_local(T0 + 2.0, ms=False).split(" ")[1]           # 本地时刻 HH:MM:SS
    base = {"kind": "csv_file", "path": str(files / "bus.csv"), "file_speed": 0, "custom_time": False}
    r = client.post("/api/engine/start", json={**base, "play_window": True, "play_window_start": "", "play_window_end": end_txt}).json()
    assert r["ok"], r
    a = _wait_done(client)
    assert abs(a["engine"]["samples_in"] - 2 * FS) <= 640, a["engine"]["samples_in"]


# ---------- ① 公共时间段 + common_end ----------

def test_common_window_end(client, files):
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(files / "br.csv"), "file_speed": 0, "custom_time": False,
                                                       "play_window": True, "play_window_start": repr(T0 + 4.5)}})   # 公共时间段启用时被忽略
    client.put("/api/config", json={"source": {"kind": "csv_file", "path": str(files / "bus.csv"), "custom_time": False},
                                    "branch": {"enabled": True, "common_window": True, "common_start": repr(T0 + 2.0), "common_end": repr(T0 + 3.0)}})
    pv = client.get("/api/common_window?preview=1").json()
    assert pv["ok"] and pv["play_end_source"] == "自定义播放结束时间" and abs(pv["play_duration_s"] - 1.0) < 1e-6, pv
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(files / "bus.csv"), "file_speed": 0}).json()
    assert r["ok"] and r["branch"]["ok"], r
    a = _wait_done(client); b = _wait_done(client, "/api/branch/state")
    assert abs(a["engine"]["samples_in"] - FS) <= 640 and abs(b["engine"]["samples_in"] - FS) <= 640, (a["engine"]["samples_in"], b["engine"]["samples_in"])
    # 结束时间越界 → 400
    client.put("/api/config", json={"branch": {"common_end": repr(T0 + 4.5)}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(files / "bus.csv"), "file_speed": 0})
    assert r.status_code == 400 and "结束时间" in r.json()["error"]
    client.put("/api/config", json={"branch": {"common_window": False, "common_start": "", "common_end": ""}})


# ---------- ③ source_id ----------

def test_source_id_in_realtime_events_nilm_and_curve_csv(client, files, tmp_path):
    """两侧启动（分路启用、非公共时间段）→ realtime/curves save 的 CSV 带 source_id（0 总线 / 1 分路），分路曲线保存到 branch/。"""
    import os
    os.environ.pop("ELEC_TOOL_REALTIME_DIR", None)                 # 按配置里的 realtime_dir 落盘
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    rt = tmp_path / "rt_shared"
    client.put("/api/config", json={"branch": {"enabled": True, "common_window": False},
                                    "output": {"realtime_save": True, "realtime_dir": str(rt), "source_id": 1,   # 用户填 1 也被服务端改回 0
                                               "curve_save": {"voltage": True, "power": True}}})
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(files / "br.csv"), "file_speed": 0, "custom_time": False, "play_window": False},
                                           "output": {"realtime_save": True, "realtime_dir": str(tmp_path / "ignored_br_dir"), "source_id": 0,
                                                      "curve_save": {"voltage": True, "power": False}}})
    assert client.get("/api/config").json()["output"]["source_id"] == 0
    bcfg = client.get("/api/branch/config").json()
    assert bcfg["output"]["source_id"] == 1
    assert bcfg["output"]["realtime_dir"] == str(rt)                # v0.17.2：分路侧目录强制与总线侧相同
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(files / "bus.csv"), "file_speed": 0, "play_window": False}).json()
    assert r["ok"] and r["branch"]["ok"], r
    _wait_done(client); _wait_done(client, "/api/branch/state")
    vfiles = list(rt.glob("voltage_*.csv"))
    assert len(vfiles) == 1, vfiles                                 # 同一个文件
    rows = list(csv.reader(open(vfiles[0], encoding="utf-8-sig")))
    assert rows[0][:3] == ["t_epoch_s", "time_local", "source_id"]
    assert sum(1 for rr in rows if rr[:3] == rows[0][:3]) == 1       # 表头只有一行
    sids = [rr[2] for rr in rows[1:]]
    assert set(sids) == {"0", "1"}, set(sids)
    assert all(len(rr) == len(rows[0]) for rr in rows[1:])          # 行不交错
    assert not (tmp_path / "ignored_br_dir").exists()
    # 曲线保存：总线目录含 voltage/power（source_id 0），branch/ 子目录只含分路勾选的 voltage（source_id 1）
    out = tmp_path / "curves"
    r = client.post("/api/curves/save", json={"dir": str(out)}).json()
    assert r["ok"], r
    # 同一个 <曲线>.csv 内两侧行并存：voltage 含 0/1，power 只有 0（分路侧未勾选 power），不另建 branch/ 目录
    byq = {f["quantity"]: f for f in r["files"]}
    assert byq["voltage"]["source_ids"] == [0, 1] and byq["voltage"]["rows_branch"] > 0, byq["voltage"]
    assert byq["power"]["source_ids"] == [0] and byq["power"]["rows_branch"] == 0, byq["power"]
    assert "voltage" in r["branch_quantities"] and "power" in r["branch_skipped"]
    outd = pathlib.Path(r["dir"]) if pathlib.Path(r["dir"]).is_absolute() else ROOT / r["dir"]
    assert not (outd / "branch").exists() and sorted(p.name for p in outd.iterdir() if p.is_dir()) == []
    hb = open(outd / "voltage.csv", encoding="utf-8-sig").read().splitlines()
    assert hb[0].startswith("t_epoch_s,time_local,source_id,quantity,") and "_sid" not in hb[0]
    sids = [ln.split(",")[2] for ln in hb[1:]]
    assert set(sids) == {"0", "1"} and len(sids) == byq["voltage"]["rows"]
    ts = [float(ln.split(",")[0]) for ln in hb[1:]]
    assert ts == sorted(ts)                                      # 按时间排序
    hp = open(outd / "power.csv", encoding="utf-8-sig").read().splitlines()
    assert {ln.split(",")[2] for ln in hp[1:]} == {"0"}
    # 合并下载：两侧都在，source_id 两种
    merged = client.get("/api/curves/export").text.splitlines()
    assert merged[0] == "t_epoch_s,time_local,source_id,quantity,field,value"
    assert {ln.split(",")[2] for ln in merged[1:] if ln} == {"0", "1"}
    # 结果导出
    ex = client.get("/api/export?fmt=csv").text.splitlines()
    assert ex[0] == "source_id,t_ref,quantity,metric,value,unit,window_s" and ex[1].startswith("0,")
    ex = client.get("/api/branch/export?fmt=csv").text.splitlines()
    assert ex[1].startswith("1,")
    client.post("/api/engine/stop"); client.post("/api/branch/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": False}, "output": {"realtime_save": False}})


def test_events_and_nilm_csv_source_id(tmp_path):
    from elec_tool.config import AppConfig
    from elec_tool.events import EventWriter
    from elec_tool.nilm import NilmWriter
    cfg = AppConfig(); cfg.output.source_id = 1
    w = EventWriter(cfg, str(tmp_path / "ev"), 1)
    assert list(w.fields)[0] == "source_id" if hasattr(w, "fields") else True
    import elec_tool.events as ev, elec_tool.nilm as nm
    assert ev._CSV_FIELDS[0] == "source_id" and nm._CSV_FIELDS[0] == "source_id"


def test_realtime_writer_legacy_file_rotated(tmp_path, monkeypatch):
    """v0.17.2：旧版（无 source_id 列）实时落盘文件不再续写——改名为 <名>.v016.csv，新建带 source_id 的同名文件。"""
    import time as _t
    from elec_tool.config import AppConfig
    from elec_tool.realtime_writer import RealtimeCurveWriter
    monkeypatch.delenv("ELEC_TOOL_REALTIME_DIR", raising=False)
    d = tmp_path / "rt"; d.mkdir()
    (d / "voltage_20261015.csv").write_text("t_epoch_s,time_local,window_s,Ua\r\n1.0,x,1,2\r\n", encoding="utf-8-sig")
    cfg = AppConfig(); cfg.output.realtime_dir = str(d)
    w = RealtimeCurveWriter(cfg)
    t = _t.mktime((2026, 10, 15, 12, 0, 0, 0, 0, -1))
    w._append("voltage", t, {"window_s": 1, "Ua": 3.0}); w.close()
    assert sorted(p.name for p in d.iterdir()) == ["voltage_20261015.csv", "voltage_20261015.v016.csv"]
    rows = list(csv.reader(open(d / "voltage_20261015.csv", encoding="utf-8-sig")))
    assert rows[0] == ["t_epoch_s", "time_local", "source_id", "window_s", "Ua"] and rows[1][2] == "0" and len(rows) == 2
    assert open(d / "voltage_20261015.v016.csv", encoding="utf-8-sig").read().startswith("t_epoch_s,time_local,window_s")


# ---------- ② 前端契约 ----------

def test_frontend_zoom_and_window_contract():
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    for s in ("const ZOOM = {}", "function zoomAxis(cv, axis, factor, center)", "function zoomReset(cv)",
              "cv.addEventListener('wheel'", "e.shiftKey", "cv.addEventListener('dblclick'", "cv.addEventListener('mousedown'",
              "if (zoom && zoom.x)", "if (zoom && zoom.y)", "ctx.clip()", "class=\"zoom-btn\"", "['reset', '复位'",
              "p.play_window = chk('window')", "p.play_window_start = txt('winstart')", "p.play_window_end = txt('winend')",
              "common_end: $('#br-common-end').value.trim()",
              # v0.17.3 配置表单排版规范化：init 首先规范化、NILM 动态表单也规范化
              "function normalizeConfigForms(root = document)", "  normalizeConfigForms();\n  bind();", "normalizeConfigForms(host);"):
        assert s in js, s
    for i in ("src-window", "src-winstart", "src-winend", "br-window", "br-winstart", "br-winend", "br-common-end"):
        assert f'id="{i}"' in html, i
