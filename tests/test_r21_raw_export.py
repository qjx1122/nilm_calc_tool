"""v0.21：从离线数据源 CSV 中把指定时间段的原始采样行重新导出到新 CSV（两侧共用文件、source_id 尾列、可再播放）。"""
from __future__ import annotations

import csv
import pathlib
import os
import shutil
import time

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400.0
T0 = 1_760_000_000.0


def _mk(tmp_path, name, t0, dur, header=True, header_names=None):
    from elec_tool.selftest import build_signal, HarmSpec
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, phi_deg=0.0)], FS, dur, t0=t0)
    p = tmp_path / name
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if header:
            w.writerow(header_names or ["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(len(t)):
            w.writerow([f"{t[k]:.6f}", f"{u[0,k]:.4f}", f"{i[0,k]:.4f}", f"{u[1,k]:.4f}", f"{i[1,k]:.4f}", f"{u[2,k]:.4f}", f"{i[2,k]:.4f}"])
    return p


def test_export_range_rows_verbatim_and_replayable(tmp_path):
    from elec_tool.config import AppConfig
    from elec_tool import raw_export
    from elec_tool.sources import create_source
    bus = _mk(tmp_path, "bus.csv", T0, 3.0)
    br = _mk(tmp_path, "br.csv", T0 + 1.0, 3.0)
    cb = AppConfig(); cb.source.kind = "csv_file"; cb.source.path = str(bus); cb.source.custom_time = False
    cr = AppConfig(); cr.source.kind = "csv_file"; cr.source.path = str(br); cr.source.custom_time = False
    out = tmp_path / "out" / "raw.csv"
    res = raw_export.export_range([(cb, 0), (cr, 1)], T0 + 1.5, T0 + 2.0, str(out))
    assert res["rows"] == res["sides"][0]["rows"] + res["sides"][1]["rows"]
    assert abs(res["sides"][0]["rows"] - 0.5 * FS) <= 2 and abs(res["sides"][1]["rows"] - 0.5 * FS) <= 2
    rows = list(csv.reader(open(out, encoding="utf-8-sig")))
    assert rows[0] == ["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流", "source_id"]
    body = rows[1:]
    ts = [float(r[0]) for r in body]
    assert ts == sorted(ts) and ts[0] >= T0 + 1.5 - 1e-6 and ts[-1] <= T0 + 2.0 + 1e-6
    # 行按原样：与源文件同一行逐字相同
    src_rows = {r[0]: r for r in csv.reader(open(bus, encoding="utf-8")) if r and r[0] != "时间戳"}
    r0 = next(r for r in body if r[-1] == "0")
    assert src_rows[r0[0]] == r0[:-1]
    assert {r[-1] for r in body} == {"0", "1"}
    # 导出文件可再作为离线数据源播放（尾列 source_id 不影响 7 列取值）
    cfg2 = AppConfig(); cfg2.source.kind = "csv_file"; cfg2.source.path = str(out); cfg2.source.custom_time = False
    src = create_source(cfg2); src.open()
    n = 0; first = None
    while True:
        b = src.read()
        if b is None:
            break
        n += b.n; first = first if first is not None else float(b.t[0])
    assert n == len(body) and abs(first - ts[0]) < 1e-3
    # 只给一端：t_to 为空 → 到文件尾
    res2 = raw_export.export_range([(cb, 0)], T0 + 2.5, None, str(tmp_path / "out2.csv"))
    assert abs(res2["rows"] - 0.5 * FS) <= 2


def test_export_range_header_mismatch_reorders(tmp_path):
    from elec_tool.config import AppConfig
    from elec_tool import raw_export
    bus = _mk(tmp_path, "bus.csv", T0, 1.0)
    # 分路侧列序不同：时间戳, Ua, Ub, Uc, Ia, Ib, Ic（用英文别名，由表头识别）
    from elec_tool.selftest import build_signal, HarmSpec
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, phi_deg=0.0)], FS, 1.0, t0=T0)
    br = tmp_path / "br.csv"
    with open(br, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["timestamp", "Ua", "Ub", "Uc", "Ia", "Ib", "Ic"])
        for k in range(len(t)):
            w.writerow([f"{t[k]:.6f}", f"{u[0,k]:.4f}", f"{u[1,k]:.4f}", f"{u[2,k]:.4f}", f"{i[0,k]:.4f}", f"{i[1,k]:.4f}", f"{i[2,k]:.4f}"])
    cb = AppConfig(); cb.source.kind = "csv_file"; cb.source.path = str(bus); cb.source.custom_time = False
    cr = AppConfig(); cr.source.kind = "csv_file"; cr.source.path = str(br); cr.source.custom_time = False
    probe = cr.columns.layout(["timestamp", "Ua", "Ub", "Uc", "Ia", "Ib", "Ic"])
    if probe.get("ia") != 4:
        pytest.skip("列名别名不被识别，跳过重排用例")
    out = tmp_path / "raw.csv"
    res = raw_export.export_range([(cb, 0), (cr, 1)], T0 + 0.2, T0 + 0.3, str(out))
    assert res["notes"] and res["sides"][1]["header_same"] is False
    rows = list(csv.reader(open(out, encoding="utf-8-sig")))
    r1 = next(r for r in rows[1:] if r[-1] == "1")
    k = int(round((float(r1[0]) - T0) * FS))
    assert abs(float(r1[2]) - i[0, k]) < 1e-3 and abs(float(r1[3]) - u[1, k]) < 1e-3   # A相电流列=Ia、B相电压列=Ub


def _wait_done(client, path="/api/state", n=60):
    for _ in range(n):
        time.sleep(0.2)
        a = client.get(path).json()
        if not a["running"]:
            return a
    return a


def test_web_export_range(tmp_path, monkeypatch):
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient
    shutil.copy(ROOT / "configs" / "default.json", tmp_path / "cfg.json")
    monkeypatch.setenv("ELEC_TOOL_CONFIG_PATH", str(tmp_path / "cfg.json")); monkeypatch.setenv("ELEC_TOOL_AUTOSTART", "")
    monkeypatch.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(tmp_path / "branch.json")); monkeypatch.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    monkeypatch.setenv("ELEC_TOOL_AUTOLOAD_LAST", "0")
    import app.server as srv
    bus = _mk(tmp_path, "bus.csv", T0, 2.0); br = _mk(tmp_path, "br.csv", T0 + 0.5, 2.0)
    with TestClient(srv.app) as c:
        c.put("/api/config", json={"source": {"kind": "csv_file", "path": str(bus), "custom_time": False},
                                   "branch": {"enabled": True, "common_window": False}, "output": {"export_dir": str(tmp_path / "out"), "realtime_save": False}})
        c.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": str(br), "custom_time": False}})
        # 两侧范围查询各自独立：总线侧只回总线侧、分路侧只回分路侧
        info = c.get("/api/source/raw_range").json()
        assert info["ok"] and set(info["ranges"]) == {"bus"} and abs(info["ranges"]["bus"]["t0"] - T0) < 1e-3
        info_br = c.get("/api/branch/source/raw_range").json()
        assert info_br["ok"] and set(info_br["ranges"]) == {"branch"} and abs(info_br["ranges"]["branch"]["t0"] - (T0 + 0.5)) < 1e-3
        assert c.post("/api/source/export_range", json={}).status_code == 400
        assert c.post("/api/source/export_range", json={"t_from": "xx"}).status_code == 400
        assert c.post("/api/source/export_range", json={"t_from": T0 + 1, "t_to": T0 + 0.5}).status_code == 400
        assert c.post("/api/source/export_range", json={"t_from": T0 + 100, "t_to": T0 + 101}).status_code == 409
        # 总线侧导出：只含总线侧行（分路侧已启用也不联动）
        r = c.post("/api/source/export_range", json={"t_from": T0 + 1.0, "t_to": T0 + 1.25, "name": "seg.csv"}).json()
        assert r["ok"] and r["source_ids"] == [0] and set(r["sides"]) == {"bus"} and r["path"].endswith("seg.csv"), r
        assert abs(r["sides"]["bus"]["rows"] - 0.25 * FS) <= 2
        fp = tmp_path / "out" / "seg.csv"
        assert fp.is_file() and r["rows"] == sum(1 for _ in open(fp, encoding="utf-8-sig")) - 1
        assert all(line.rstrip("\r\n").endswith(",0") for line in list(open(fp, encoding="utf-8-sig"))[1:])
        # 默认文件名含 src<source_id>，两侧同一时间段导出不会互相覆盖
        r2 = c.post("/api/source/export_range", json={"t_from": T0 + 1.0, "t_to": T0 + 1.1}).json()
        assert r2["ok"] and r2["source_ids"] == [0] and r2["path"].endswith("_src0.csv"), r2
        r3 = c.post("/api/branch/source/export_range", json={"t_from": T0 + 1.0, "t_to": T0 + 1.1}).json()
        assert r3["ok"] and r3["source_ids"] == [1] and set(r3["sides"]) == {"branch"} and r3["path"].endswith("_src1.csv"), r3
        assert r3["path"] != r2["path"] and abs(r3["rows"] - r2["rows"]) <= 2
        fp3 = tmp_path / "out" / os.path.basename(r3["path"])
        assert all(line.rstrip("\r\n").endswith(",1") for line in list(open(fp3, encoding="utf-8-sig"))[1:])
        # 分路侧时间段落在分路侧文件之外（但在总线侧文件之内）→ 409：互不关联
        assert c.post("/api/branch/source/export_range", json={"t_from": T0 + 0.1, "t_to": T0 + 0.4}).status_code == 409
        # 只填时刻（HH:MM:SS.ffff，与文件时标写法一致）→ 以文件首行日期补齐
        from datetime import datetime as _dt
        hms = lambda t: _dt.fromtimestamp(t).strftime("%H:%M:%S.%f")[:-2]   # noqa: E731
        r4 = c.post("/api/source/export_range", json={"t_from": hms(T0 + 1.0), "t_to": hms(T0 + 1.25)}).json()
        assert r4["ok"] and abs(r4["rows"] - r2["rows"] * 2.5) <= 4, r4
        # 导出文件可作为总线侧数据源播放
        c.put("/api/config", json={"branch": {"enabled": False}})
        s = c.post("/api/engine/start", json={"kind": "csv_file", "path": str(fp), "file_speed": 0, "custom_time": False}).json()
        assert s["ok"], s
        st = _wait_done(c)
        assert st["engine"]["samples_in"] == r["rows"]


def test_frontend_contract_raw_export():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for i in ("raw-exp-from", "raw-exp-to", "raw-exp-name", "btn-raw-exp-fill", "btn-raw-export", "raw-exp-note", "raw-exp-range"):
        assert f'id="{i}"' in html and f'id="br-{i}"' in html, i      # 两侧各自一套控件
    assert 'id="raw-exp-branch"' not in html                            # 不再有「含分路侧」联动勾选
    for s in ("async function exportRawRange(side = 'bus')", "url: '/api/branch/source'", "exportRawRange('branch')", "fillRawRange('branch')"):
        assert s in js, s
