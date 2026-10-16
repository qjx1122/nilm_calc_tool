"""v0.27：功率因数 / 基波 / 谐波 / 间谐波 / 直流 的三相分相标量进入曲线记录（历史 / 实时落盘 / 保存曲线数据同一出口）；
功率页 P/Q/S 趋势、功率因数页分相 PF 曲线（图例可选）。"""
import csv
import os
import time
from pathlib import Path

import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")

PHASE_FIELDS = {
    "power": ["Pa", "Pb", "Pc", "Qa", "Qb", "Qc", "Sa", "Sb", "Sc"],
    "power_factor": ["PFa", "PFb", "PFc"],
    "fundamental": ["U1a", "U1b", "U1c", "I1a", "I1b", "I1c", "phiA_deg", "phiB_deg", "phiC_deg"],
    "harmonic": ["THD_Ua", "THD_Ub", "THD_Uc", "THD_Ia", "THD_Ib", "THD_Ic"],
    "interharmonic": ["TIHD_Ua", "TIHD_Ub", "TIHD_Uc", "TIHD_Ia", "TIHD_Ib", "TIHD_Ic"],
    "dc": ["Ua_dc", "Ub_dc", "Uc_dc", "Ia_dc", "Ib_dc", "Ic_dc", "Ua_dc_pct", "Ub_dc_pct", "Uc_dc_pct", "Ia_dc_pct", "Ib_dc_pct", "Ic_dc_pct"],
}


def _wait(client, pred, timeout=25.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r27")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json"))
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    mp.setenv("ELEC_TOOL_LAST_RESULT_FILE", str(d / "last_result.json"))
    for k in ("ELEC_TOOL_EVENTS_DIR", "ELEC_TOOL_REALTIME_DIR", "ELEC_TOOL_NILM_DIR"):
        mp.delenv(k, raising=False)
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


def test_phase_fields_in_history_realtime_and_curves(client, tmp_path, monkeypatch):
    for k in ("ELEC_TOOL_REALTIME_DIR", "ELEC_TOOL_EVENTS_DIR", "ELEC_TOOL_NILM_DIR"):
        monkeypatch.delenv(k, raising=False)        # conftest 的 autouse 隔离目录会覆盖 realtime_dir，这里改用本测试的 tmp 目录
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv, FS
    specs = [HarmSpec(1, 57.735, 5.0, phi_deg=20.0), HarmSpec(5, 3.0, 0.3, phi_deg=0.0)]
    t, u, i = build_signal(specs, FS, 3.0, u_dc=0.5)
    write_csv(str(tmp_path / "bus.csv"), t, u, i)
    rt_dir = tmp_path / "rt"
    r = client.put("/api/config", json={"branch": {"enabled": False},
                                       "output": {"realtime_save": True, "realtime_dir": str(rt_dir), "curves_dir": str(tmp_path / "curves")},
                                       "events": {"events_dir": str(tmp_path / "ev")}, "nilm": {"nilm_dir": str(tmp_path / "nl")}})
    assert r.status_code == 200, r.text
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus.csv"), "file_speed": 0, "custom_time": False})
    assert r.status_code == 200 and r.json()["ok"], r.text
    try:
        assert _wait(client, lambda: all(client.get(f"/api/history/{k}").json().get("count", 0) >= 2 for k in PHASE_FIELDS)), \
            {k: client.get(f"/api/history/{k}").json().get("count") for k in PHASE_FIELDS}
        # ① 历史曲线点带分相字段，且三相值为有限数
        for k, fields in PHASE_FIELDS.items():
            pts = client.get(f"/api/history/{k}").json()["points"]
            last = pts[-1]
            for f in fields:
                assert f in last, (k, f, sorted(last))
                assert isinstance(last[f], (int, float)), (k, f, last[f])
        # 分相与总量一致性：Pa+Pb+Pc ≈ P；PFa 与 pf_per_phase 一致
        p = client.get("/api/history/power").json()["points"][-1]
        assert abs(p["Pa"] + p["Pb"] + p["Pc"] - p["P"]) < 1e-6 * max(1.0, abs(p["P"]))
        res = client.get("/api/result?full=false").json()
        pf = res["quantities"]["power_factor"]["values"]["pf_per_phase"]
        hpf = client.get("/api/history/power_factor").json()["points"][-1]
        assert abs(hpf["PFa"] - pf["A"]) < 1e-3 and abs(hpf["PFc"] - pf["C"]) < 1e-3
        # ② 保存曲线数据 CSV 表头含分相列
        r = client.post("/api/curves/save", json={})
        assert r.status_code == 200, r.text
        for f in r.json()["files"]:
            fields = PHASE_FIELDS.get(f["quantity"])
            if not fields:
                continue
            with open(f["path"], encoding="utf-8-sig", newline="") as fh:
                head = next(csv.reader(fh))
            assert set(fields) <= set(head), (f["quantity"], head)
        # ③ 实时落盘文件表头含分相列
        assert _wait(client, lambda: any(n.startswith("power_factor_") for n in os.listdir(rt_dir)) if rt_dir.exists() else False)
        for k, fields in PHASE_FIELDS.items():
            names = [n for n in os.listdir(rt_dir) if n.startswith(k + "_") and n.endswith(".csv") and ".pre-v032" not in n]
            assert names, (k, os.listdir(rt_dir))
            with open(rt_dir / names[0], encoding="utf-8-sig", newline="") as fh:
                head = next(csv.reader(fh))
            assert set(fields) <= set(head), (k, head)
    finally:
        client.post("/api/engine/stop")


def test_realtime_writer_rotates_file_with_old_header(tmp_path, monkeypatch):
    """旧表头（缺分相列）的当天文件 → 改名 .pre-v032.csv，新建完整表头，不把新列硬塞进旧表头。"""
    monkeypatch.delenv("ELEC_TOOL_REALTIME_DIR", raising=False)
    from elec_tool.realtime_writer import RealtimeCurveWriter
    from elec_tool.config import AppConfig
    d = tmp_path / "rt"
    d.mkdir()
    cfg = AppConfig.from_dict({"output": {"realtime_save": True, "realtime_dir": str(d)}})
    w = RealtimeCurveWriter(cfg)
    t = time.time()
    from elec_tool.timefmt import local_day
    day = local_day(t)
    old = d / f"power_factor_{day}.csv"
    old.write_text("t_epoch_s,time_local,source_id,window_s,PF,DPF,phi1_deg\n1,2000-01-01 00:00:00.000,0,0.2,0.9,0.95,10\n", encoding="utf-8-sig")
    w._append("power_factor", t, {"window_s": 0.2, "PF": 0.9, "DPF": 0.95, "phi1_deg": 10.0, "PFa": 0.91, "PFb": 0.9, "PFc": 0.89})
    w.close()
    assert (d / f"power_factor_{day}.pre-v032.csv").exists()
    with open(old, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    assert "PFa" in rows[0] and len(rows) == 2 and rows[1][rows[0].index("PFc")] == "0.89"


def test_frontend_contract():
    # v0.28：功率页不再是趋势线，而是分相瞬时功率波形 #p-wave-ph；谐波/间谐波/基波趋势含分相线（默认隐藏、图例勾选）
    assert 'id="p-wave-ph"' in HTML and 'id="p-trend"' not in HTML
    assert "drawLine($('#p-wave-ph'), serPh" in APP_JS and "p.series.p_per_phase" in APP_JS
    assert "name: 'PF' + ph.toLowerCase()" in APP_JS and "defaultHidden: true, data: hp.map(x => [x.t - t0, x['PF' + ph.toLowerCase()]])" in APP_JS
    for cid in ("h-trend", "f-u1-trend", "f-i1-trend"):
        assert f'id="{cid}"' in HTML and f"drawLine($('#{cid}')" in APP_JS, cid
    for f in ("THD_U${k.toLowerCase()}", "THD_I${k.toLowerCase()}", "TIHD_U${k.toLowerCase()}", "TIHD_I${k.toLowerCase()}"):
        assert f in APP_JS, f
    assert "['overview', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc', 'nilm'].includes(v)" in APP_JS


def test_power_series_has_per_phase(client, tmp_path, monkeypatch):
    """v0.28：/api/result 的 power.series 带 p_per_phase（A/B/C 各一条、与 p_total 同长度、逐点之和≈p_total）。"""
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv, FS
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, phi_deg=20.0)], FS, 2.0)
    write_csv(str(tmp_path / "bus2.csv"), t, u, i)
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(tmp_path / "bus2.csv"), "file_speed": 0, "custom_time": False})
    assert r.status_code == 200 and r.json()["ok"], r.text
    try:
        assert _wait(client, lambda: "power" in client.get("/api/result?full=true").json().get("quantities", {}))
        ser = client.get("/api/result?full=true").json()["quantities"]["power"]["series"]
        pp = ser["p_per_phase"]
        assert set(pp) == {"A", "B", "C"} and all(len(pp[k]) == len(ser["p_total"]) for k in pp) and len(ser["p_total"]) > 10
        for j in range(0, len(ser["p_total"]), 97):
            assert abs(pp["A"][j] + pp["B"][j] + pp["C"][j] - ser["p_total"][j]) < 1e-6 * max(1.0, abs(ser["p_total"][j]))
    finally:
        client.post("/api/engine/stop")
