# -*- coding: utf-8 -*-
"""第 8 轮：数据处理子界面——离线波形 CSV 重采样（elec_tool.resample / API / CLI）。"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from elec_tool.resample import ResampleError, ResampleJob, output_name, resample_csv  # noqa: E402

HEADER = ["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"]


def _write(path: Path, fs: float, seconds: float, ts_style: str = "clock", encoding: str = "utf-8",
           header: bool = True, harmonic: bool = False) -> int:
    n = int(fs * seconds)
    t = np.arange(n) / fs
    w = 2 * np.pi * 50 * t
    cols = [100 * np.sin(w), 5 * np.sin(w - 0.5) + (0.5 * np.sin(2 * np.pi * 1250 * t) if harmonic else 0),
            100 * np.sin(w - 2.094), 5 * np.sin(w - 2.6), 100 * np.sin(w + 2.094), 5 * np.sin(w + 1.6)]
    with open(path, "w", encoding=encoding, newline="") as fh:
        wr = csv.writer(fh)
        if header:
            wr.writerow(HEADER)
        for i in range(n):
            if ts_style == "clock":
                tod = 12 * 3600 + 40 * 60 + t[i]
                hh = int(tod // 3600); mm = int(tod % 3600 // 60); ss = tod - hh * 3600 - mm * 60
                stamp = f"0/00/00 {hh:02d}:{mm:02d}:{ss:07.4f}"
            elif ts_style == "epoch":
                stamp = f"{1791861203.0 + t[i]:.6f}"
            elif ts_style == "epoch_ms_int":
                stamp = str(int(round((1791861203.0 + t[i]) * 1000)))
            else:  # iso
                from datetime import datetime, timezone, timedelta
                stamp = (datetime(2026, 10, 12, 8, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=float(t[i]))).strftime("%Y-%m-%d %H:%M:%S.%f")
            wr.writerow([stamp] + [f"{c[i]:.6f}" for c in cols])
    return n


def _read(path: Path, encoding="utf-8"):
    with open(path, "r", encoding=encoding, newline="") as fh:
        rows = list(csv.reader(fh))
    return rows


# ------------------------------------------------------------------ 文件名

def test_output_name_matches_user_spec():
    assert output_name("波形_农业排灌_大水泵_80_1.csv", 6400) == "波形_农业排灌_大水泵_80_1_re_6400.csv"
    assert output_name("/abs/dir/x.CSV", 3200.0) == "x_re_3200.CSV"
    assert output_name("x.csv", 6400.5) == "x_re_6400p5.csv"


# ------------------------------------------------------------------ 算法

def test_upsample_linear_keeps_format_and_values(tmp_path):
    src = tmp_path / "波形_农业排灌_大水泵_80_1.csv"
    n = _write(src, 3200, 2.0)
    r = resample_csv(str(src), 6400, out_dir=str(tmp_path / "data"))
    assert r["out_name"] == "波形_农业排灌_大水泵_80_1_re_6400.csv"
    assert r["rows_in"] == n and r["rows_out"] == 2 * n - 1
    assert r["fs_src"] == 3200 and r["fs_src_source"] == "estimated"
    rows = _read(tmp_path / "data" / r["out_name"])
    assert rows[0] == HEADER                                  # 表头原样
    assert rows[1][0] == "0/00/00 12:40:00.0000"              # 时间戳写法保持 4 位小数
    assert rows[2][0] == "0/00/00 12:40:00.0002"              # 1/6400 = 0.00015625 → 四舍五入 0.0002
    assert rows[-1][0].startswith("0/00/00 12:40:01.99")
    ua = np.array([float(x[1]) for x in rows[1:]])
    tt = np.arange(len(ua)) / 6400
    assert np.max(np.abs(ua - 100 * np.sin(2 * np.pi * 50 * tt))) < 0.13   # 线性插值 50Hz 的理论误差上限 ~0.12
    assert ua[1] == pytest.approx(50 * np.sin(2 * np.pi * 50 / 3200), abs=1e-5)  # 恰为中点


def test_fft_resample_is_near_exact_and_antialiases(tmp_path):
    src = tmp_path / "s.csv"
    n = _write(src, 6400, 1.0, harmonic=True)                 # Ia 含 1250 Hz 分量
    up = resample_csv(str(src), 12800, out_dir=str(tmp_path / "o"), method="fft")
    rows = _read(tmp_path / "o" / up["out_name"])
    ua = np.array([float(x[1]) for x in rows[1:]])
    tt = np.arange(len(ua)) / 12800
    assert up["rows_out"] == 2 * n
    assert np.max(np.abs(ua - 100 * np.sin(2 * np.pi * 50 * tt))) < 1e-4
    down = resample_csv(str(src), 800, out_dir=str(tmp_path / "o"), method="fft")   # Nyquist 400 Hz < 1250
    rows = _read(tmp_path / "o" / down["out_name"])
    ia = np.array([float(x[2]) for x in rows[1:]])
    tt = np.arange(len(ia)) / 800
    assert np.max(np.abs(ia - 5 * np.sin(2 * np.pi * 50 * tt - 0.5))) < 1e-4         # 1250 Hz 被理想低通滤掉
    lin = resample_csv(str(src), 800, out_dir=str(tmp_path / "o"), method="linear", overwrite=True)
    assert any("无抗混叠" in x for x in lin["notes"])


def test_nearest_and_decimate_integer_factor(tmp_path):
    src = tmp_path / "s.csv"
    n = _write(src, 6400, 0.5)
    r = resample_csv(str(src), 1600, out_dir=str(tmp_path / "o"), method="nearest")
    rows = _read(tmp_path / "o" / r["out_name"])
    orig = _read(src)
    assert r["rows_out"] == (n - 1) // 4 + 1
    assert [x[1] for x in rows[1:4]] == [orig[1][1], orig[5][1], orig[9][1]]   # 整数倍抽取 = 直接取样


@pytest.mark.parametrize("style,enc,header", [("epoch", "utf-8", True), ("epoch_ms_int", "utf-8", False),
                                              ("iso", "gbk", True), ("clock", "utf-8-sig", True)])
def test_timestamp_styles_encodings_header(tmp_path, style, enc, header):
    src = tmp_path / f"{style}.csv"
    n = _write(src, 3200, 0.5, ts_style=style, encoding=enc, header=header)
    r = resample_csv(str(src), 6400, out_dir=str(tmp_path / "o"))
    out = tmp_path / "o" / r["out_name"]
    raw = out.read_bytes()
    if enc == "utf-8-sig":
        assert raw.startswith(b"\xef\xbb\xbf")                 # 源带 BOM → 输出带 BOM
    else:
        assert not raw.startswith(b"\xef\xbb\xbf")
    rows = _read(out, encoding=enc)
    assert r["header_kept"] is header and (rows[0] == HEADER) is header
    data = rows[1:] if header else rows
    assert len(data) == 2 * n - 1
    if style == "epoch":
        assert data[0][0] == "1791861203.000000" and float(data[1][0]) == pytest.approx(1791861203 + 1 / 6400, abs=1e-6)
    elif style == "epoch_ms_int":
        # 原为整数毫秒，1/6400 s = 0.15625 ms 不可整数表示 → 自动加小数位
        from decimal import Decimal
        assert data[0][0] == "1791861203000.00"         # 整数毫秒 + 自动加的小数位（分辨率 ≤ 步长/10）
        assert Decimal(data[1][0]) - Decimal(data[0][0]) == Decimal("0.16")    # 0.15625 ms 按 2 位写出
        assert Decimal(data[64][0]) - Decimal(data[0][0]) == Decimal("10.00")  # 64 步 = 10 ms 无累积误差
    elif style == "iso":
        assert data[0][0] == "2026-10-12 08:00:00.000000" and data[2][0] == "2026-10-12 08:00:00.000313"
    # 二次解析：输出必须能被播放链路正确读出 6400 Hz
    from elec_tool.sources.parsing import parse_timestamps
    info = parse_timestamps([d[0] for d in data[:3000]])
    assert info.fs_est == pytest.approx(6400, rel=2e-3)


def test_fs_src_override_and_notes(tmp_path):
    src = tmp_path / "s.csv"
    n = _write(src, 3200, 0.5)
    r = resample_csv(str(src), 6400, out_dir=str(tmp_path / "o"), fs_src=1600)
    assert r["fs_src"] == 1600 and r["fs_src_source"] == "user" and r["rows_out"] == 4 * (n - 1) + 1
    assert any("偏差 >5%" in x for x in r["notes"])


def test_errors(tmp_path):
    src = tmp_path / "s.csv"
    _write(src, 3200, 0.2)
    with pytest.raises(ResampleError, match="不存在"):
        resample_csv(str(tmp_path / "nope.csv"), 6400, out_dir=str(tmp_path))
    with pytest.raises(ResampleError, match="> 0"):
        resample_csv(str(src), 0, out_dir=str(tmp_path))
    with pytest.raises(ResampleError, match="method"):
        resample_csv(str(src), 6400, out_dir=str(tmp_path), method="cubic")
    resample_csv(str(src), 6400, out_dir=str(tmp_path / "o"))
    with pytest.raises(ResampleError, match="已存在"):
        resample_csv(str(src), 6400, out_dir=str(tmp_path / "o"))
    resample_csv(str(src), 6400, out_dir=str(tmp_path / "o"), overwrite=True)
    bad = tmp_path / "bad.csv"
    bad.write_text("时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流\n1.0,1,2,3,4,5,6\n1.001,x,2,3,4,5,6\n1.002,1,2,3,4,5,6\n", encoding="utf-8")
    with pytest.raises(ResampleError, match="非数值"):
        resample_csv(str(bad), 2000, out_dir=str(tmp_path / "o"))
    assert not list((tmp_path / "o").glob("*.part"))          # 失败不留半成品


def test_cancel_via_job(tmp_path):
    src = tmp_path / "s.csv"
    _write(src, 6400, 12.0)                                   # 76800 行，跨多个 64k 块
    job = ResampleJob()
    seen = []

    def on_progress(j):
        seen.append(j.progress)
        if j.stage == "resample":
            j.cancel.set()
    job.on_progress = on_progress
    with pytest.raises(ResampleError, match="已取消"):
        resample_csv(str(src), 12800, out_dir=str(tmp_path / "o"), job=job)
    assert seen and not list((tmp_path / "o").glob("*.csv"))


def test_streaming_matches_whole_file(tmp_path):
    """分块流式线性插值必须与一次性 np.interp 完全一致（块边界 carry 行正确）。"""
    import elec_tool.resample as rs
    src = tmp_path / "s.csv"
    n = _write(src, 3200, 3.0)                                # 9600 行
    old = rs._CHUNK_ROWS
    try:
        rs._CHUNK_ROWS = 1000                                 # 强制 10 个块
        r = resample_csv(str(src), 7000, out_dir=str(tmp_path / "o"))      # 非整数比
    finally:
        rs._CHUNK_ROWS = old
    rows = _read(tmp_path / "o" / r["out_name"])
    got = np.array([float(x[1]) for x in rows[1:]])
    orig = np.array([float(x[1]) for x in _read(src)[1:]])
    ks = np.arange(len(got)); pos = ks * 3200 / 7000
    ref = np.interp(pos, np.arange(n), orig)
    assert len(got) == int(np.floor((n - 1) * 7000 / 3200)) + 1
    assert np.max(np.abs(got - ref)) < 1e-6


# ------------------------------------------------------------------ Web API

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    cfg_dir = tmp_path_factory.mktemp("r8cfg")
    cfg_path = cfg_dir / "cfg.json"
    shutil.copy(ROOT / "configs" / "default.json", cfg_path)
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(cfg_path))
    mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(tmp_path_factory.mktemp("r8rt")))
    import app.server as srv
    with TestClient(srv.app) as c:
        yield c
    mp.undo()


def _wait(client, s=20.0):
    t0 = time.time()
    while time.time() - t0 < s:
        st = client.get("/api/process/resample").json()
        if not st["running"] and (st["result"] or st["error"]):
            return st
        time.sleep(0.05)
    raise AssertionError("重采样任务超时")


def test_api_resample_roundtrip(client):
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    src = data_dir / "_r8_api_波形_80_1.csv"
    out = data_dir / "_r8_api_波形_80_1_re_6400.csv"
    try:
        n = _write(src, 3200, 1.0)
        pv = client.get("/api/process/resample/preview", params={"path": "data/" + src.name, "fs_new": 6400}).json()
        assert pv["out_name"] == out.name and pv["exists"] is False and pv["src_exists"] is True
        r = client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400}).json()
        assert r["ok"], r
        st = _wait(client)
        assert st["error"] is None and st["result"]["rows_out"] == 2 * n - 1 and st["progress"] == 1.0
        assert out.exists() and st["result"]["out_path"] == "data/" + out.name
        # 覆盖保护
        client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400})
        st = _wait(client)
        assert st["error"] and "已存在" in st["error"]
        r = client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400, "overwrite": True, "method": "fft"}).json()
        assert r["ok"]
        st = _wait(client)
        assert st["error"] is None and st["result"]["method"] == "fft" and st["result"]["rows_out"] == 2 * n
        # 参数校验
        assert client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": -1}).json()["ok"] is False
        assert client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": "abc"}).json()["ok"] is False
        assert client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400, "method": "cubic"}).json()["ok"] is False
        assert client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400, "out_dir": "/etc"}).json()["ok"] is False
        assert client.post("/api/process/resample", json={"path": "data/nope.csv", "fs_new": 6400}).json()["ok"] is False
        assert client.post("/api/process/resample", json={"fs_new": 6400}).json()["ok"] is False
    finally:
        for p in (src, out, out.with_name(out.stem + "_err.csv")):
            if p.exists():
                p.unlink()


def test_api_cancel(client):
    src = ROOT / "data" / "_r8_cancel.csv"
    try:
        _write(src, 6400, 12.0)
        r = client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 25600}).json()
        assert r["ok"]
        time.sleep(0.05)
        c = client.post("/api/process/resample/cancel").json()
        st = _wait(client)
        if c.get("cancelling"):
            assert st["error"] == "已取消"
        assert not list((ROOT / "data").glob("_r8_cancel_re_*.part"))
    finally:
        if src.exists():
            src.unlink()
        for p in (ROOT / "data").glob("_r8_cancel_re_*"):
            p.unlink()


# ------------------------------------------------------------------ CLI

def test_cli_resample(tmp_path):
    src = tmp_path / "波形_农业排灌_大水泵_80_1.csv"
    n = _write(src, 3200, 0.5)
    out_dir = tmp_path / "data"
    p = subprocess.run([sys.executable, str(ROOT / "cli.py"), "resample", str(src), "--fs", "6400",
                        "--out-dir", str(out_dir), "--format", "json"], capture_output=True, text=True, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr
    r = json.loads(p.stdout)
    assert r["out_name"] == "波形_农业排灌_大水泵_80_1_re_6400.csv" and r["rows_out"] == 2 * n - 1
    assert (out_dir / r["out_name"]).exists()
    p2 = subprocess.run([sys.executable, str(ROOT / "cli.py"), "resample", str(src), "--fs", "6400", "--out-dir", str(out_dir)],
                        capture_output=True, text=True, cwd=str(ROOT))
    assert p2.returncode == 2 and "已存在" in p2.stderr


# ------------------------------------------------------------------ 前端静态断言

def test_frontend_has_process_view():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'data-view="process"' in html and 'id="view-process"' in html
    for i in ("rs-files", "rs-path", "rs-fs", "rs-fssrc", "rs-method", "rs-overwrite", "btn-rs-run", "btn-rs-cancel",
              "rs-bar", "rs-result", "btn-rs-use"):
        assert f'id="{i}"' in html, i
    assert "case 'process': renderProcess(); break;" in js
    assert "/api/process/resample" in js and "bindProcess();" in js


# ------------------------------------------------------------------ v0.34：重采样前后相对误差（时间窗可配）

def _read_err(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


def test_error_report_windows_and_metrics(tmp_path):
    src = tmp_path / "波形_农业排灌_大水泵_80_1.csv"
    n = _write(src, 3200, 3.0)                         # 9600 行
    # 窗 1 s → 3 窗；fft 升采样纯正弦：误差应极小
    r = resample_csv(str(src), 6400, out_dir=str(tmp_path / "data"), method="fft", error_window_s=1.0)
    assert r["err_windows"] == 3 and r["err_window_s"] == 1.0
    err = tmp_path / "data" / "波形_农业排灌_大水泵_80_1_re_6400_err.csv"
    assert err.exists() and r["err_path"].endswith("_re_6400_err.csv") and r["err_name"] == err.name
    rows = _read_err(err)
    head = rows[0]
    assert head[:6] == ["窗序号", "起始时间戳", "起始秒", "结束秒", "原始行数", "重采样行数"]
    assert "A相电压_RMS相对误差" in head and "C相电流_波形相对误差NRMSE" in head and len(head) == 6 + 6 * 4
    assert len(rows) == 1 + 3 + 1 and rows[-1][0] == "汇总"
    assert [int(x[4]) for x in rows[1:4]] == [3200, 3200, 3200] and sum(int(x[5]) for x in rows[1:4]) == r["rows_out"]
    assert rows[1][1].startswith("0/00/00 12:40:00") and rows[2][2] == "1.000000"
    assert r["err_rms_rel_max"] < 1e-3 and r["err_nrmse_max"] < 0.01
    assert set(r["err_summary"]) == set(HEADER[1:]) and all(v["nrmse_max"] >= v["nrmse_mean"] for v in r["err_summary"].values())
    # 窗 0.25 s → 12 窗；末窗不足整窗也统计（2.9 s → 12 窗，最后一窗 0.15 s）
    n2 = _write(src, 3200, 2.9)
    r2 = resample_csv(str(src), 6400, out_dir=str(tmp_path / "data"), overwrite=True, error_window_s=0.25)
    assert r2["err_windows"] == 12 and int(_read_err(err)[12][4]) == n2 - 11 * 800
    # 关闭：不生成文件、结果无 err_path
    err.unlink()
    r3 = resample_csv(str(src), 6400, out_dir=str(tmp_path / "data"), overwrite=True)
    assert "err_path" not in r3 and not err.exists()
    # 降采样 linear 对含 1250 Hz 谐波的电流：折叠 → 误差明显大于 fft
    _write(src, 3200, 1.0, harmonic=True)
    rl = resample_csv(str(src), 1600, out_dir=str(tmp_path / "data"), method="linear", error_window_s=0.5)
    rf = resample_csv(str(src), 1600, out_dir=str(tmp_path / "data"), method="fft", overwrite=True, error_window_s=0.5)
    assert rl["err_summary"]["A相电流"]["nrmse_max"] > rf["err_summary"]["A相电流"]["nrmse_max"]


def test_error_window_config_and_api(client):
    from elec_tool.config import AppConfig, ConfigError
    cfg = AppConfig.from_dict({"processing": {"error_window_s": "0.5", "error_report": 1}}).validate()
    assert cfg.processing.error_window_s == 0.5 and cfg.processing.error_report is True
    assert AppConfig.from_dict(AppConfig().to_dict()).processing.error_window_s == 1.0
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"processing": {"error_window_s": 0}}).validate()
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    src = data_dir / "_r34_api_波形_80_1.csv"
    out = data_dir / "_r34_api_波形_80_1_re_6400.csv"
    err = data_dir / "_r34_api_波形_80_1_re_6400_err.csv"
    try:
        _write(src, 3200, 1.0)
        # 默认来自配置
        st0 = client.get("/api/process/resample").json()
        assert st0["defaults"]["err_window_s"] == 1.0 and st0["defaults"]["err_report"] is True
        assert client.put("/api/config", json={"processing": {"error_window_s": 0.2}}).json()["ok"]
        assert client.get("/api/process/resample").json()["defaults"]["err_window_s"] == 0.2
        r = client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400}).json()
        assert r["ok"], r
        st = _wait(client)
        assert st["error"] is None and st["result"]["err_windows"] == 5 and err.exists()
        # 载荷显式覆盖窗长
        r = client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400, "overwrite": True, "err_window_s": 0.5}).json()
        assert r["ok"], r
        st = _wait(client)
        assert st["result"]["err_windows"] == 2 and st["params"]["err_window_s"] == 0.5
        # 关闭
        err.unlink()
        r = client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400, "overwrite": True, "err_report": False}).json()
        assert r["ok"], r
        st = _wait(client)
        assert "err_path" not in st["result"] and not err.exists()
        # 非法窗
        assert client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400, "err_window_s": 0}).json()["ok"] is False
        assert client.post("/api/process/resample", json={"path": "data/" + src.name, "fs_new": 6400, "err_window_s": "x"}).json()["ok"] is False
    finally:
        client.put("/api/config", json={"processing": {"error_window_s": 1.0, "error_report": True}})
        for p in (src, out, err):
            if p.exists():
                p.unlink()


def test_cli_resample_err_window(tmp_path):
    src = tmp_path / "波形_农业排灌_大水泵_80_1.csv"
    _write(src, 3200, 1.0)
    out_dir = tmp_path / "data"
    p = subprocess.run([sys.executable, str(ROOT / "cli.py"), "resample", str(src), "--fs", "6400", "--out-dir", str(out_dir),
                        "--err-window", "0.5", "--format", "json"], capture_output=True, text=True, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr
    r = json.loads(p.stdout)
    assert r["err_windows"] == 2 and (out_dir / r["err_name"]).exists()
    p2 = subprocess.run([sys.executable, str(ROOT / "cli.py"), "resample", str(src), "--fs", "6400", "--out-dir", str(out_dir),
                         "--overwrite", "--no-err", "--format", "json"], capture_output=True, text=True, cwd=str(ROOT))
    assert p2.returncode == 0 and "err_path" not in json.loads(p2.stdout)


def test_frontend_has_error_window_controls():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for i in ("rs-err", "rs-errwin", "rs-err-summary"):
        assert f'id="{i}"' in html, i
    assert "processing: { error_window_s" in js and "err_window_s" in js
