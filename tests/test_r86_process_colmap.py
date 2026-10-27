"""v0.86：数据处理页三功能（重采样 / 负荷辨识调参 / 波形预览）的「离线文件列映射」开关 + 7 个列号。
默认不启用＝各列依次为 时间, A相电压, A相电流, B相电压, B相电流, C相电压, C相电流；启用后按列号取列。"""
from __future__ import annotations

import csv
import json
import pathlib
import shutil
import time

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400.0
T0 = 1_760_000_000.0
U_RMS, I_RMS = 57.735, 5.0


def _swapped_csv(path):
    """表头不可识别（c1..c7），且 **第 2 列是 A 相电流、第 3 列是 A 相电压**（与默认列序相反）。"""
    n = int(FS * 2.0); t = T0 + np.arange(n) / FS; w = 2 * np.pi * 50 * (t - T0)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["c1", "c2", "c3", "c4", "c5", "c6", "c7"])
        for k in range(n):
            u = [U_RMS * np.sqrt(2) * np.sin(w[k] + ph) for ph in (0, -2.0944, 2.0944)]
            i = [I_RMS * np.sqrt(2) * np.sin(w[k] + ph) for ph in (0, -2.0944, 2.0944)]
            wr.writerow([f"{t[k]:.9f}", f"{i[0]:.5f}", f"{u[0]:.4f}", f"{u[1]:.4f}", f"{i[1]:.5f}", f"{u[2]:.4f}", f"{i[2]:.5f}"])
    return str(path)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r86cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json")); mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    mp.setenv("ELEC_TOOL_NILM_DIR", str(d / "nilm"))
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


@pytest.fixture(scope="module")
def swapped(tmp_path_factory):
    return _swapped_csv(tmp_path_factory.mktemp("r86") / "swap.csv")


MAP = {"timestamp": "1", "ua": "3", "ia": "2", "ub": "4", "ib": "5", "uc": "6", "ic": "7"}


def test_apply_col_map_helper():
    from elec_tool.config import AppConfig
    from elec_tool.wave_preview import apply_col_map, make_base, WaveError
    cfg = AppConfig.from_dict({})
    apply_col_map(cfg, False, None)
    assert cfg.columns.mapping_enabled is False
    apply_col_map(cfg, "1", json.dumps({"ua": "3", "ia": "2"}))
    assert cfg.columns.mapping_enabled is True and cfg.columns.mapping == MAP
    with pytest.raises(Exception):
        apply_col_map(cfg, True, {"ua": "x"})
    b = make_base(AppConfig.from_dict({}), col_map_enabled="1", col_map=json.dumps(MAP))
    assert b.columns.mapping_enabled and b.columns.mapping["ia"] == "2"
    b = make_base(AppConfig.from_dict({}))
    assert b.columns.mapping_enabled is False
    with pytest.raises(WaveError):
        make_base(AppConfig.from_dict({}), col_map_enabled="1", col_map="{bad")


def test_wave_preview_col_map(client, swapped):
    # 不启用：按默认列序 → Ua 列读到的是电流（有效值 ≈5），Ia 读到电压（≈57.7）
    r = client.get("/api/process/wave/rms", params={"path": swapped, "duration_s": 1, "pt_ct_enabled": "0"}).json()
    assert r["ok"] and abs(np.median(r["channels"]["Ua"]) - I_RMS) < 0.2 and abs(np.median(r["channels"]["Ia"]) - U_RMS) < 1
    # 启用 + 列号 → 正确
    q = {"path": swapped, "duration_s": 1, "pt_ct_enabled": "0", "col_map_enabled": "1", "col_map": json.dumps(MAP)}
    r = client.get("/api/process/wave/rms", params=q).json()
    assert r["ok"] and abs(np.median(r["channels"]["Ua"]) - U_RMS) < 1 and abs(np.median(r["channels"]["Ia"]) - I_RMS) < 0.2
    assert client.get("/api/process/wave/info", params=q).json()["ok"]
    assert client.get("/api/process/wave/load", params=dict(q, n_cycles=10)).json()["ok"]
    # 列号非法 → 400
    rr = client.get("/api/process/wave/rms", params={"path": swapped, "col_map_enabled": "1", "col_map": json.dumps({"ua": "abc"})})
    assert rr.status_code == 400 and "列映射" in rr.json()["error"]


def test_nilm_tune_col_map(client, swapped):
    base = {"fs": 6400, "f_nom": 50, "pt_ct_enabled": "0", "file_time_utc": "0"}
    body = {"path": swapped, "quantity": "i", "channel": "A", "base_mode": "custom", "base": base}
    r0 = client.post("/api/process/nilm_tune", json=body).json()
    assert r0["ok"] is not False and r0["col_map_enabled"] is False and abs(r0["measure"]["level"] - U_RMS) < 1   # 默认列序：Ia 列读到电压
    r1 = client.post("/api/process/nilm_tune", json=dict(body, col_map_enabled=True, col_map=MAP)).json()
    assert r1["col_map_enabled"] is True and r1["col_map"] == MAP and abs(r1["measure"]["level"] - I_RMS) < 0.2
    # 独立基准配置落盘文件带列映射（等价命令 --config 可复现）
    bf = r1["base_file"]; bf = bf if pathlib.Path(bf).is_absolute() else str(ROOT / bf)
    bdoc = json.load(open(bf, encoding="utf-8"))
    assert bdoc["columns"]["mapping_enabled"] is True and bdoc["columns"]["mapping"]["ia"] == "2"
    # 沿用运行配置时也按本次请求
    r2 = client.post("/api/process/nilm_tune", json={"path": swapped, "base_mode": "running", "col_map_enabled": True, "col_map": MAP}).json()
    assert r2["col_map_enabled"] is True
    rr = client.post("/api/process/nilm_tune", json=dict(body, col_map_enabled=True, col_map={"ua": "2", "ia": "2"}))
    assert rr.status_code == 400 and "列映射" in rr.json()["error"]


def _wait(client, s=30.0):
    t0 = time.time()
    while time.time() - t0 < s:
        st = client.get("/api/process/resample").json()
        if not st["running"] and (st["result"] or st["error"]):
            return st
        time.sleep(0.05)
    raise AssertionError("重采样任务超时")


def test_resample_col_map(client, swapped):
    """重采样保持文件原列布局，列映射决定**时间戳列**（及误差报告的通道名）：时间在第 2 列的文件，不启用映射按默认
    第 1 列（电流值）当时间会得到无意义的时间轴；启用并指定 timestamp=2 → 正确重采样。"""
    data_dir = ROOT / "data"; data_dir.mkdir(exist_ok=True)
    src = data_dir / "_r86_t2.csv"; out = data_dir / "_r86_t2_re_3200.csv"
    with open(swapped, encoding="utf-8") as fi, open(src, "w", encoding="utf-8", newline="") as fo:
        rd, wr = csv.reader(fi), csv.writer(fo)
        for row in rd:
            wr.writerow([row[1], row[0]] + row[2:])            # 第 1 列＝A 相电流，第 2 列＝时间
    try:
        m2 = {"timestamp": "2", "ia": "1", "ua": "3", "ub": "4", "ib": "5", "uc": "6", "ic": "7"}
        r = client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 3200, "err_report": True, "overwrite": True,
                                                       "col_map_enabled": True, "col_map": m2}).json()
        assert r["ok"], r
        st = _wait(client)
        assert st["error"] is None and out.exists() and st["result"]["rows_out"] in (6400, 6399)
        assert st["params"]["col_map_enabled"] is True and st["params"]["col_map"]["timestamp"] == "2"
        # 列号重复 → 直接拒绝
        assert client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 3200, "col_map_enabled": True,
                                                          "col_map": {"ua": "2", "ia": "2"}}).json()["ok"] is False
    finally:
        for f in (src, out, data_dir / "_r86_t2_re_3200_err.csv"):
            if f.exists():
                f.unlink()
