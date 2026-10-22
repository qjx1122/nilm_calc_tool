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
    assert abs(d["t_start"] - T0) < 1e-6 and abs(d["t_end"] - (T0 + 4.0 - 1 / FS)) < 1e-3
    assert d["pt_ct"]["enabled"] and d["pt_ct"]["pt_ratio"] == 100.0
    with pytest.raises(WaveError, match="文件不存在"):
        file_info(cfg, str(wave_file.parent / "nope.csv"))


# ---------- ② 原始波形 ----------
def test_load_waveform_defaults_and_options(cfg, wave_file):
    from elec_tool.wave_preview import load_waveform, WaveError
    p = str(wave_file)
    # 默认：起点起 1000 点、原采样率、全部通道、一次侧口径
    d = load_waveform(cfg, p)
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
    # 指定时间段（结束时刻优先于点数）
    d = load_waveform(cfg, p, t_start=f"{T0 + 1.0:.6f}", t_end=f"{T0 + 1.5:.6f}", n_points=10)
    assert d["n"] == 3200 and abs(d["t_first"] - (T0 + 1.0)) < 1e-6 and d["t_last"] < T0 + 1.5
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
    with pytest.raises(WaveError, match="晚于"):
        load_waveform(cfg, p, t_start=f"{T0 + 2.0:.3f}", t_end=f"{T0 + 1.0:.3f}")
    with pytest.raises(WaveError, match="超出文件范围"):
        load_waveform(cfg, p, t_start=f"{T0 + 100.0:.3f}", n_points=10)


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
    r = client.get("/api/process/wave/info", params={"path": p}).json()
    assert r["ok"] and r["n_channels"] == 6 and r["fs"] == 6400.0 and r["t_start_local"] and r["t_end_local"] and r["side"] == "bus"
    r = client.get("/api/process/wave/load", params={"path": p}).json()
    assert r["ok"] and r["n"] == 1000 and len(r["channels_loaded"]) == 6
    r = client.get("/api/process/wave/load", params={"path": p, "n": "", "fs": 400, "channels": "Ia,Ib", "t_start": f"{T0 + 2:.3f}"}).json()
    assert r["ok"] and r["n"] == 800 and r["channels_loaded"] == ["Ia", "Ib"] and r["fs"] == 400.0          # n= ⇒ 到文件末尾
    r = client.get("/api/process/wave/load", params={"path": p, "n": "", "t_start": f"{T0 + 1:.3f}", "t_end": f"{T0 + 1.5:.3f}"}).json()
    assert r["ok"] and r["n"] == 3200
    r = client.get("/api/process/wave/load", params={"path": p, "side": "branch", "n": 64}).json()          # 分路侧基准配置
    assert r["ok"] and r["n"] == 64
    r = client.get("/api/process/wave/rms", params={"path": p, "t_start": f"{T0 + 1:.3f}", "duration_s": 2, "agg_cycles": 2}).json()
    assert r["ok"] and r["n"] == 50 and r["agg_cycles"] == 2 and r["cycles_total"] == 100
    # 错误 → 400 + 中文说明
    for params in ({"path": p, "channels": "Zz"}, {"path": "nope.csv"}, {"path": p, "n": 0}, {"path": p, "side": "x"}):
        rr = client.get("/api/process/wave/load", params=params)
        assert rr.status_code == 400 and rr.json()["ok"] is False and rr.json()["error"], params
    rr = client.get("/api/process/wave/info", params={"path": ""})
    assert rr.status_code == 400 and "路径" in rr.json()["error"]
    # 不改运行配置、不启动引擎
    st = client.get("/api/state").json()
    assert not st["running"] and st["config"]["source"]["path"] != p
