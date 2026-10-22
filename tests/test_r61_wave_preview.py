"""v0.61：数据处理页「波形预览」——文件信息 / 原始波形加载（重采样、通道、时间段 / 点数）/ 逐周波有效值曲线 + REST 端点。"""
from __future__ import annotations

import math
import pathlib
import shutil

import numpy as np
import pytest

from tests.conftest import write_csv

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400.0
T0 = 1_760_000_000.0
U_RMS = 57.735          # 二次侧 V（PT=100 → 一次侧 5773.5 V）
I_RMS = 5.0             # 二次侧 A（CT=15 → 一次侧 75 A）


@pytest.fixture(scope="module")
def wave_file(tmp_path_factory):
    from elec_tool.selftest import HarmSpec, build_signal
    d = tmp_path_factory.mktemp("r61")
    t, u, i = build_signal([HarmSpec(1, U_RMS, I_RMS, phi_deg=0.0)], FS, 4.0, t0=T0)     # 4 s = 200 周波
    write_csv(str(d / "w.csv"), t, u, i)
    return d / "w.csv"


@pytest.fixture(scope="module")
def cfg():
    from elec_tool.config import AppConfig
    return AppConfig.load(str(ROOT / "configs" / "default.json"))


# ---------- ① 文件信息 ----------
def test_file_info(cfg, wave_file):
    from elec_tool.wave_preview import file_info, WaveError
    d = file_info(cfg, str(wave_file))
    assert d["ok"] and d["n_channels"] == 6 and d["channels"] == ["Ua", "Ub", "Uc", "Ia", "Ib", "Ic"]
    assert d["fs"] == 6400.0 and d["samples_per_cycle"] == 128 and d["rows"] == 25600
    assert abs(d["duration_s"] - 4.0) < 1e-6
    assert abs(d["t_start"] - T0) < 1e-6 and abs(d["t_end"] - (T0 + 4.0 - 1 / FS)) < 1e-6      # v0.62：结束＝起始 + (行数−1)/fs
    assert abs(d["t_end_by_timestamp"] - d["t_end"]) < 1e-3
    assert d["pt_ct"]["enabled"] and d["pt_ct"]["pt_ratio"] == 100.0
    with pytest.raises(WaveError, match="文件不存在"):
        file_info(cfg, str(wave_file.parent / "nope.csv"))


# ---------- ② 原始波形 ----------
def test_load_waveform_defaults_and_options(cfg, wave_file):
    from elec_tool.wave_preview import load_waveform, WaveError
    p = str(wave_file)
    # 周波数（v0.62 界面默认 300）：300 × 128 = 38400 点、原采样率、全部通道、一次侧口径
    d = load_waveform(cfg, p, n_cycles=300)                # 文件只有 200 周波 → 到文件末尾
    assert d["n"] == 25600 and d["samples_per_cycle"] == 128 and d["eof"]
    d = load_waveform(cfg, p, n_cycles=100)
    assert d["n"] == 12800 and d["samples_per_cycle"] == 128 and d["fs"] == 6400.0 and not d["resampled"] and d["method"] is None
    d = load_waveform(cfg, p, n_points=1000)
    assert d["n"] == 1000 and d["fs"] == 6400.0 and not d["resampled"] and d["channels_loaded"] == ["Ua", "Ub", "Uc", "Ia", "Ib", "Ic"]
    assert abs(d["t"][0] - T0) < 1e-6 and abs((d["t"][1] - d["t"][0]) - 1 / FS) < 1e-6
    ua = np.array(d["channels"]["Ua"], dtype=float)
    assert abs(np.max(np.abs(ua)) - U_RMS * math.sqrt(2) * 100) / (U_RMS * math.sqrt(2) * 100) < 0.01     # PT=100 → 一次侧峰值
    assert d["units"] == {"Ua": "V", "Ub": "V", "Uc": "V", "Ia": "A", "Ib": "A", "Ic": "A"}
    # 指定通道（大小写不敏感、去重）+ 重采样 1600 Hz + 点数 500
    d = load_waveform(cfg, p, fs_out=1600, n_points=500, channels=["ia", "Ub", "IA"])
    assert d["n"] == 500 and d["fs"] == 1600.0 and d["resampled"] and d["channels_loaded"] == ["Ia", "Ub"]
    assert abs((d["t"][1] - d["t"][0]) - 1 / 1600) < 1e-6      # epoch 1.76e9 的 float64 分辨率 ≈ 2e-7
    ia = np.array(d["channels"]["Ia"], dtype=float)
    assert abs(np.sqrt(np.mean(ia ** 2)) - I_RMS * 15) / (I_RMS * 15) < 0.02                           # 线性插值后有效值基本不变
    # 指定时间段；时间段与点数同时给出时取先到者（v0.62）
    d = load_waveform(cfg, p, t_start=f"{T0 + 1.0:.6f}", t_end=f"{T0 + 1.5:.6f}")
    assert d["n"] == 3200 and abs(d["t_first"] - (T0 + 1.0)) < 1e-6 and d["t_last"] < T0 + 1.5
    assert load_waveform(cfg, p, t_start=f"{T0 + 1.0:.6f}", t_end=f"{T0 + 1.5:.6f}", n_points=10)["n"] == 10
    assert load_waveform(cfg, p, t_start=f"{T0 + 1.0:.6f}", t_end=f"{T0 + 1.5:.6f}", n_cycles=300)["n"] == 3200
    # 三种重采样方式（与「重采样」功能同一组）：都保持有效值；fft 为周期语义、记录实际采样率
    for m in ("linear", "nearest", "fft"):
        d = load_waveform(cfg, p, fs_out=1600, n_cycles=10, method=m, channels=["Ia"])
        x = np.array(d["channels"]["Ia"]); assert d["n"] == 320 and d["method"] == m, m
        assert abs(np.sqrt(np.mean(x ** 2)) - I_RMS * 15) / (I_RMS * 15) < 0.02, m
    d = load_waveform(cfg, p, fs_out=1000, n_cycles=10, method="fft", channels=["Ua"])
    assert d["fs_effective"] is not None and d["n"] == 200
    with pytest.raises(WaveError, match="重采样方式"):
        load_waveform(cfg, p, fs_out=1600, method="cubic")
    # 点数与结束时刻都为空 ⇒ 整段到文件末尾（受 max_points 截断并提示）
    d = load_waveform(cfg, p, t_start=f"{T0 + 3.0:.6f}", n_points=None)
    assert d["n"] == 6400 and not d["truncated"]
    d = load_waveform(cfg, p, n_points=None, max_points=5000)
    assert d["n"] == 5000 and d["truncated"] and any("上限" in n for n in d["notes"])
    # 时间文本写法：日期时间 / 只填时刻
    from elec_tool.timefmt import fmt_local
    d = load_waveform(cfg, p, t_start=fmt_local(T0 + 2.0), n_points=128)
    assert d["n"] == 128 and abs(d["t_first"] - (T0 + 2.0)) < 2e-3
    # 错误
    with pytest.raises(WaveError, match="未知通道"):
        load_waveform(cfg, p, channels=["Zz"])
    with pytest.raises(WaveError, match="点数必须"):
        load_waveform(cfg, p, n_points=0)
    with pytest.raises(WaveError, match="周波数必须"):
        load_waveform(cfg, p, n_cycles=0)
    with pytest.raises(WaveError, match="晚于"):
        load_waveform(cfg, p, t_start=f"{T0 + 2.0:.3f}", t_end=f"{T0 + 1.0:.3f}")
    with pytest.raises(WaveError, match="超出文件范围"):
        load_waveform(cfg, p, t_start=f"{T0 + 100.0:.3f}", n_points=10)


# ---------- ②b 独立基准配置（v0.62） ----------
def test_make_base_independent(cfg, wave_file):
    from elec_tool.wave_preview import base_defaults, load_waveform, make_base, WaveError
    bd = base_defaults(cfg)
    assert bd == {"fs": 6400.0, "f_nom": 50.0, "pt_ct_enabled": True, "pt_ratio": 100.0, "ct_ratio": 15.0, "file_time_utc": False,
                  "custom_time": False, "custom_time_start": "", "custom_time_end": "", "max_points": 20_000_000}   # v0.64 +4
    b = make_base(cfg, fs="6400", f_nom="50", pt_ct_enabled="0", pt_ratio="", ct_ratio=None)
    assert b.transform.enabled is False and b.transform.pt_ratio == 100.0 and b.sampling.fs == 6400.0
    d = load_waveform(b, str(wave_file), n_cycles=2, channels=["Ua"])
    assert abs(np.max(np.abs(d["channels"]["Ua"])) - U_RMS * math.sqrt(2)) / (U_RMS * math.sqrt(2)) < 0.01      # 二次侧
    b2 = make_base(cfg, pt_ct_enabled="1", pt_ratio="50", ct_ratio="10")
    d = load_waveform(b2, str(wave_file), n_cycles=2, channels=["Ua", "Ia"])
    assert abs(np.max(np.abs(d["channels"]["Ua"])) - U_RMS * math.sqrt(2) * 50) / (U_RMS * math.sqrt(2) * 50) < 0.01
    assert abs(np.max(np.abs(d["channels"]["Ia"])) - I_RMS * math.sqrt(2) * 10) / (I_RMS * math.sqrt(2) * 10) < 0.01
    b3 = make_base(cfg, f_nom="60")
    assert load_waveform(b3, str(wave_file), n_cycles=3)["samples_per_cycle"] == 107        # round(6400/60)
    with pytest.raises(WaveError, match="不是数字"):
        make_base(cfg, fs="abc")
    with pytest.raises(WaveError, match="必须 >"):
        make_base(cfg, pt_ratio="0")


# ---------- ③ 逐周波有效值 ----------
def test_rms_curve(cfg, wave_file):
    from elec_tool.wave_preview import rms_curve
    p = str(wave_file)
    d = rms_curve(cfg, p)
    assert d["n"] == 200 and d["agg_cycles"] == 1 and d["cycles_total"] == 200 and d["samples_per_cycle"] == 128
    assert abs(d["t"][0] - T0) < 1e-6 and abs((d["t"][1] - d["t"][0]) - 0.02) < 1e-7
    ua = np.array(d["channels"]["Ua"]); ia = np.array(d["channels"]["Ia"])
    assert np.allclose(ua, U_RMS * 100, rtol=2e-3) and np.allclose(ia, I_RMS * 15, rtol=2e-3)
    # 时间段 + 时长 [起点, 起点+时长)：1 s → 50 个周波；通道子集
    d = rms_curve(cfg, p, t_start=f"{T0 + 1.0:.6f}", duration_s=1.0, channels=["Ia"])
    assert d["n"] == 50 and list(d["channels"]) == ["Ia"] and abs(d["t_first"] - (T0 + 1.0)) < 1e-6
    # 统计窗合并 + 点数上限自动合并
    d = rms_curve(cfg, p, agg_cycles=4)
    assert d["n"] == 50 and d["agg_cycles"] == 4 and np.allclose(d["channels"]["Ub"], U_RMS * 100, rtol=2e-3)
    d = rms_curve(cfg, p, max_points=30)
    assert d["agg_cycles"] == 7 and d["n"] == 28 and any("自动" in n for n in d["notes"])


# ---------- ④ REST ----------
@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r61cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json")); mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    import app.server as srv
    with TestClient(srv.app) as c:
        yield c
    mp.undo()


def test_wave_endpoints(client, wave_file):
    p = str(wave_file)
    r = client.get("/api/process/wave/defaults").json()
    assert r["ok"] and r["methods"] == ["linear", "nearest", "fft"] and r["default_cycles"] == 300 and r["base"]["fs"] == 6400.0
    r = client.get("/api/process/wave/info", params={"path": p}).json()
    assert r["ok"] and r["n_channels"] == 6 and r["fs"] == 6400.0 and r["t_start_local"] and r["t_end_local"] and "side" not in r
    assert abs(r["duration_s"] - r["rows"] / r["fs"]) < 1e-9                                                 # 时长＝点数 / 采样率
    r = client.get("/api/process/wave/load", params={"path": p, "n_cycles": 100}).json()
    assert r["ok"] and r["n"] == 12800 and len(r["channels_loaded"]) == 6
    r = client.get("/api/process/wave/load", params={"path": p}).json()                                      # 不传点数 ⇒ 整段
    assert r["ok"] and r["n"] == 25600
    r = client.get("/api/process/wave/load", params={"path": p, "fs_out": 400, "method": "fft", "channels": "Ia,Ib", "t_start": f"{T0 + 2:.3f}"}).json()
    assert r["ok"] and r["n"] == 800 and r["channels_loaded"] == ["Ia", "Ib"] and r["fs"] == 400.0 and r["method"] == "fft"
    r = client.get("/api/process/wave/load", params={"path": p, "t_start": f"{T0 + 1:.3f}", "t_end": f"{T0 + 1.5:.3f}"}).json()
    assert r["ok"] and r["n"] == 3200
    # 独立基准配置：PT/CT 关 → 二次侧幅值；运行配置不受影响
    r = client.get("/api/process/wave/load", params={"path": p, "n_cycles": 1, "channels": "Ua", "pt_ct_enabled": "0", "pt_ratio": "100", "fs": "6400"}).json()
    assert r["ok"] and abs(max(abs(v) for v in r["channels"]["Ua"]) - U_RMS * math.sqrt(2)) < 2
    assert client.get("/api/config").json()["transform"]["enabled"] is True
    rr = client.get("/api/process/wave/load", params={"path": p, "pt_ratio": "x"})
    assert rr.status_code == 400 and "不是数字" in rr.json()["error"]
    r = client.get("/api/process/wave/rms", params={"path": p, "t_start": f"{T0 + 1:.3f}", "duration_s": 2, "agg_cycles": 2}).json()
    assert r["ok"] and r["n"] == 50 and r["agg_cycles"] == 2 and r["cycles_total"] == 100
    # 错误 → 400 + 中文说明
    for params in ({"path": p, "channels": "Zz"}, {"path": "nope.csv"}, {"path": p, "n": 0}, {"path": p, "method": "cubic", "fs_out": 100}, {"path": p, "n_cycles": 0}):
        rr = client.get("/api/process/wave/load", params=params)
        assert rr.status_code == 400 and rr.json()["ok"] is False and rr.json()["error"], params
    rr = client.get("/api/process/wave/info", params={"path": ""})
    assert rr.status_code == 400 and "路径" in rr.json()["error"]
    # 不改运行配置、不启动引擎
    st = client.get("/api/state").json()
    assert not st["running"] and st["config"]["source"]["path"] != p


# ---------- v0.64：最多加载点数可配（默认 2000 万）/ 自定义时间 / 谐波次数限制放宽 ----------
def test_r64_max_points_custom_time_and_harmonic_relax(cfg, wave_file, client):
    from elec_tool.wave_preview import MAX_POINTS_DEFAULT, file_info, load_waveform, make_base, rms_curve
    p = str(wave_file)
    # 1) 最多加载点数：默认 2000 万；界面可配，超出截断并提示
    assert MAX_POINTS_DEFAULT == 20_000_000
    d = client.get("/api/process/wave/defaults").json()
    assert d["max_points_default"] == 20_000_000 and d["base"]["max_points"] == 20_000_000 and d["base"]["custom_time"] is False
    r = client.get("/api/process/wave/load", params={"path": p}).json()                     # 不传 ⇒ 默认上限，整段 25600 点不截断
    assert r["ok"] and r["n"] == 25600 and not r["truncated"]
    r = client.get("/api/process/wave/load", params={"path": p, "max_points": 1000}).json()
    assert r["ok"] and r["n"] == 1000 and r["truncated"] and any("1000" in n for n in r["notes"])
    r = client.get("/api/process/wave/load", params={"path": p, "max_points": 0})
    assert r.status_code == 400
    # 2) 自定义时间：起始空＝文件数据起始时间；起始给定 → 轴＝起始 + 行号/fs；结束空＝起始 + (行数−1)/fs
    b0 = make_base(cfg)
    i0 = file_info(b0, p)
    b1 = make_base(cfg, custom_time="1")
    i1 = file_info(b1, p)
    assert i1["custom_time"] is True and abs(i1["t_start"] - i0["t_start"]) < 1e-6 and abs(i1["t_end"] - i0["t_end"]) < 1e-6
    b2 = make_base(cfg, custom_time="1", custom_time_start="2026-01-01 00:00:00")
    i2 = file_info(b2, p)
    from elec_tool.config import parse_time_text
    c0 = parse_time_text("2026-01-01 00:00:00")
    assert abs(i2["t_start"] - c0) < 1e-6 and abs(i2["t_end"] - (c0 + (i2["rows"] - 1) / FS)) < 1e-6 and abs(i2["duration_s"] - i2["rows"] / FS) < 1e-9
    w = load_waveform(b2, p, t_start="2026-01-01 00:00:01", t_end="2026-01-01 00:00:01.5")            # 自定义轴上定位
    assert w["n"] == 3200 and abs(w["t_first"] - (c0 + 1.0)) < 1e-6 and w["t_last"] < c0 + 1.5 + 1e-9
    w = load_waveform(b2, p, n_cycles=10)                                                             # 起止空 ⇒ 从自定义起始开始
    assert w["n"] == 1280 and abs(w["t_first"] - c0) < 1e-6
    rm = rms_curve(b2, p, t_start="2026-01-01 00:00:02", t_end="2026-01-01 00:00:03")
    assert rm["n"] == 50 and abs(rm["t_first"] - (c0 + 2.0)) < 1e-6
    # 自定义结束时间：早于按采样率计算的结束 ⇒ 只取到它
    b3 = make_base(cfg, custom_time="1", custom_time_start="2026-01-01 00:00:00", custom_time_end="2026-01-01 00:00:02")
    i3 = file_info(b3, p)
    assert abs(i3["t_end"] - (c0 + 2.0)) < 1e-6 and i3["t_end_custom"] is not None
    w = load_waveform(b3, p)
    assert w["n"] == 12800 and w["t_last"] <= c0 + 2.0 + 1e-9
    with pytest.raises(Exception):
        make_base(cfg, custom_time="1", custom_time_start="2026-01-01 00:00:02", custom_time_end="2026-01-01 00:00:01")
    # REST 透传
    r = client.get("/api/process/wave/info", params={"path": p, "custom_time": "1", "custom_time_start": "2026-01-01 00:00:00"}).json()
    assert r["ok"] and r["custom_time"] is True and r["t_start_local"].startswith("2026-01-01 00:00:00")
    r = client.get("/api/process/wave/load", params={"path": p, "custom_time": "1", "custom_time_start": "2026-01-01 00:00:00",
                                                      "t_start": "2026-01-01 00:00:03", "n_cycles": 5}).json()
    assert r["ok"] and r["n"] == 640 and abs(r["t_first"] - (c0 + 3.0)) < 1e-6
    # 未启用自定义时间：起止空＝文件数据起止（与之前一致），结束时刻按终点裁剪
    w = load_waveform(b0, p, t_start=f"{T0 + 1:.3f}", t_end=f"{T0 + 2:.3f}")
    assert w["n"] == 6400 and w["t_last"] < T0 + 2.0 + 1e-9
    # 3) 基准配置 fs=1000（harmonic.order_max=50 → 2500 Hz ≥ Nyquist 500 Hz）不再报错：次数自动压到 9
    b4 = make_base(cfg, fs=1000)
    assert b4.harmonic.order_max == 9 and b4.harmonic.thd_order_max <= 9
    r = client.get("/api/process/wave/load", params={"path": p, "fs": 1000, "n_cycles": 10}).json()
    assert r["ok"] and r["n"] > 0, r
    b5 = make_base(cfg, fs=200, f_nom=50)                                                             # 极低采样率：order 1 仍合法
    assert b5.harmonic.order_min == 1 and b5.harmonic.order_max == 1
    r = client.get("/api/process/wave/load", params={"path": p, "fs": 80, "f_nom": 50})                 # f_nom ≥ Nyquist 仍是真错误
    assert r.status_code == 400 and "Nyquist" in r.json()["error"]


# ---------- v0.65：采样率按文件数据时间计算（不可改）/ 周波窗 2 瞬时值端点 ----------
def test_r65_fs_from_file_and_nilm_wave_file(cfg, wave_file, client, tmp_path):
    from elec_tool.selftest import HarmSpec, build_signal
    from elec_tool.wave_preview import file_info, load_waveform, make_base, rms_curve
    # 1000 Hz 文件：界面不再上送 fs，采样率按时标推算；读文件 / 周波切分 / 自定义时间轴都按 1000 Hz
    t, u, i = build_signal([HarmSpec(1, U_RMS, I_RMS, phi_deg=0.0)], 1000.0, 2.0, t0=T0)
    p = str(tmp_path / "low.csv"); write_csv(p, t, u, i)
    b = make_base(cfg)                                             # 出厂 fs=6400，不参与
    info = file_info(b, p)
    assert info["fs"] == 1000.0 and info["samples_per_cycle"] == 20 and abs(info["duration_s"] - 2.0) < 1e-9
    w = load_waveform(b, p, n_cycles=5)
    assert w["n"] == 100 and w["fs"] == 1000.0
    r = rms_curve(b, p)
    assert r["samples_per_cycle"] == 20 and r["cycles_total"] == 100
    bc = make_base(cfg, custom_time="1", custom_time_start="2026-01-01 00:00:00")
    ic = file_info(bc, p)
    from elec_tool.config import parse_time_text
    c0 = parse_time_text("2026-01-01 00:00:00")
    assert abs(ic["t_end"] - (c0 + (2000 - 1) / 1000.0)) < 1e-6                     # 自定义轴按 1000 Hz
    w = load_waveform(bc, p, t_start="2026-01-01 00:00:01", n_cycles=5)
    assert w["n"] == 100 and abs(w["t_first"] - (c0 + 1.0)) < 1e-6
    rr = client.get("/api/process/wave/info", params={"path": p}).json()
    assert rr["ok"] and rr["fs"] == 1000.0 and "Nyquist" not in str(rr)
    # 周波窗 2：从当前侧配置的离线文件取 n 个周波的瞬时值（center 模式居中、靠边平移、非离线源 400）
    client.post("/api/engine/stop")
    r = client.put("/api/config", json={"source": {"kind": "csv_file", "path": str(wave_file)}}); assert r.status_code == 200, r.text
    d = client.get("/api/nilm/wave_file", params={"t": f"{T0 + 2:.3f}", "n": 10}).json()
    assert d["ok"] and d["n"] == 1280 and d["source"]["mode"] == "center" and d["source"]["n_cycles"] == 10
    assert abs(d["t_first"] - (T0 + 2 - 0.1)) < 1e-6 and len(d["channels_loaded"]) == 6
    ia = np.array(d["channels"]["Ia"][:128]); assert ia.min() < 0 < ia.max() and abs(ia.max() / np.sqrt(np.mean(ia ** 2)) - np.sqrt(2)) < 0.05   # 瞬时值
    d = client.get("/api/nilm/wave_file", params={"t": f"{T0 + 3.99:.3f}", "n": 10}).json()
    assert d["ok"] and d["n"] == 1280 and d["t_last"] <= T0 + 4.0                 # 靠近末尾整体左移
    d = client.get("/api/nilm/wave_file", params={"n": 3}).json()
    assert d["ok"] and d["source"]["mode"] == "begin" and abs(d["t_first"] - T0) < 1e-6
    client.put("/api/config", json={"source": {"kind": "simulator"}})
    assert client.get("/api/nilm/wave_file", params={"n": 3}).status_code == 400
    client.put("/api/config", json={"source": {"kind": "csv_file", "path": str(wave_file)}})


def test_r68_tod_time_text_in_custom_mode(tmp_path):
    """v0.68：起止时刻写法与数据源页一致——自定义时间模式下也接受只写 HH:MM:SS（＝自定义起始时间当天的该时刻）。"""
    import os
    from elec_tool.config import AppConfig
    from elec_tool.wave_preview import load_waveform, file_info
    path = os.path.join("data", "nilm_bus_mixed.csv")
    if not os.path.isfile(path):
        import pytest
        pytest.skip("样例文件不存在")
    base = AppConfig.from_dict(AppConfig().to_dict())
    base.source.custom_time = True
    base.source.custom_time_start = "2026-10-12 08:00:00"
    info = file_info(base, path)
    fs = float(info["fs"])
    a = load_waveform(base, path, t_start="08:00:01", t_end="08:00:01.5", channels=["Ia"])
    b = load_waveform(base, path, t_start="2026-10-12 08:00:01", t_end="2026-10-12 08:00:01.5", channels=["Ia"])
    assert a["n"] == b["n"] and abs(a["n"] - 0.5 * fs) <= 2
    assert abs(a["t"][0] - b["t"][0]) < 1e-6


def test_r68_tod_time_text_in_file_mode():
    """v0.68：文件时间模式下起止时刻也可只写 HH:MM:SS（与数据源页一致），与完整日期时间结果相同。"""
    import os
    from elec_tool.config import AppConfig
    from elec_tool.timefmt import local_tod_s
    from elec_tool.wave_preview import load_waveform, file_info
    from datetime import datetime
    path = os.path.join("data", "nilm_bus_mixed.csv")
    if not os.path.isfile(path):
        import pytest
        pytest.skip("样例文件不存在")
    base = AppConfig.from_dict(AppConfig().to_dict())
    info = file_info(base, path)
    t0 = float(info["t_start"]); fs = float(info["fs"])
    d0 = datetime.fromtimestamp(t0 - local_tod_s(t0))
    tod = local_tod_s(t0) + 1.0
    hh, mm, ss = int(tod // 3600), int(tod % 3600 // 60), tod % 60
    s_txt = f"{hh:02d}:{mm:02d}:{ss:06.3f}"; e_txt = f"{hh:02d}:{mm:02d}:{ss + 0.5:06.3f}"
    full = lambda x: d0.strftime("%Y-%m-%d ") + x
    a = load_waveform(base, path, t_start=s_txt, t_end=e_txt, channels=["Ia"])
    b = load_waveform(base, path, t_start=full(s_txt), t_end=full(e_txt), channels=["Ia"])
    assert a["n"] == b["n"] and abs(a["n"] - 0.5 * fs) <= 2
    assert abs(a["t"][0] - b["t"][0]) < 1e-6
