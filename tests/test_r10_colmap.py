"""第 10 轮：离线文件列映射开关（columns.mapping_enabled / columns.mapping）。

- 未启用：有可识别表头按表头取列；无表头按默认列序「时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流」
- 启用：只按 mapping 取列（列号从 1 起 / 表头列名）；未映射通道按 0 播放并给提示；时间戳未映射→按 fs 合成连续时间轴
- 校验：列号 <1、重复映射、无任何通道映射、列名不在表头 → ConfigError
- Web：PUT /api/config columns、/api/probe 回显 mapping/unmapped、csv_file 端到端只播放映射列；前端面板与载荷
"""
from __future__ import annotations

import csv
import os
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from elec_tool.config import AppConfig, ColumnMap, ConfigError
from elec_tool.sources.parsing import iter_csv_blocks, parse_rows

ROOT = Path(__file__).resolve().parents[1]
FS = 6400


def _write(path, header, order, n=FS, with_header=True):
    """order: 列内容顺序，元素 ∈ {t,ua,ia,ub,ib,uc,ic,x}；幅值：U 57.7（A/B/C 相角 0/-120/+120），I 5/6/7 A。"""
    t = np.arange(n) / FS
    w = 2 * np.pi * 50 * t
    sig = {"t": 1.79e9 + t, "ua": 57.7 * 1.41421 * np.sin(w), "ub": 57.7 * 1.41421 * np.sin(w - 2.0944),
           "uc": 57.7 * 1.41421 * np.sin(w + 2.0944), "ia": 5 * 1.41421 * np.sin(w), "ib": 6 * 1.41421 * np.sin(w - 2.0944),
           "ic": 7 * 1.41421 * np.sin(w + 2.0944), "x": np.full(n, 9.0)}
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        if with_header:
            wr.writerow(header)
        for k in range(n):
            wr.writerow([f"{sig[c][k]:.6f}" for c in order])
    return path


def _rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def _one(path, cm, cfg):
    return next(iter_csv_blocks(path, cm, cfg.sampling, block_samples=FS))


# ------------------------------------------------------------------ 配置

def test_defaults_and_validation():
    cm = ColumnMap()
    assert cm.mapping_enabled is False and cm.mapping["ic"] == "7"
    assert cm.layout(None) == {k: i for i, k in enumerate(ColumnMap.FIELDS)}          # 默认列序
    cfg = AppConfig(); cfg.columns.mapping_enabled = True
    cfg.columns.mapping = {"timestamp": "1", "ua": "0"}
    with pytest.raises(ConfigError, match="从 1 起"):
        cfg.validate()
    cfg.columns.mapping = {"timestamp": "1"}
    with pytest.raises(ConfigError, match="没有任何电压/电流通道"):
        cfg.validate()
    cfg.columns.mapping = {"timestamp": "1", "ua": "2", "ia": "2"}
    with pytest.raises(ConfigError, match="同一列"):
        cfg.validate()
    cfg.columns.mapping = {"ua": "Ua"}
    cfg.validate()
    with pytest.raises(ConfigError, match="不在表头"):
        cfg.columns.layout(["ts", "Ub"])
    d = cfg.to_dict()["columns"]
    assert d["mapping_enabled"] is True and d["mapping"]["ua"] == "Ua" and d["mapping"]["ic"] == ""
    assert AppConfig.from_dict(cfg.to_dict()).columns.mapping["ua"] == "Ua"


# ------------------------------------------------------------------ 解析

def test_disabled_uses_header_or_default_order(tmp_path):
    cfg = AppConfig().validate()
    # 乱序表头（别名）→ 按表头
    p = _write(tmp_path / "a.csv", ["ts", "Ua", "Ub", "Uc", "Ia", "Ib", "Ic"], ["t", "ua", "ub", "uc", "ia", "ib", "ic"])
    blk, info = _one(str(p), cfg.columns, cfg)
    assert info["columns"]["ia"] == 4 and abs(_rms(blk.i[0]) - 5) < 0.01 and abs(_rms(blk.i[2]) - 7) < 0.01
    # 无表头 → 默认列序 t,ua,ia,ub,ib,uc,ic
    p = _write(tmp_path / "b.csv", None, ["t", "ua", "ia", "ub", "ib", "uc", "ic"], with_header=False)
    blk, info = _one(str(p), cfg.columns, cfg)
    assert info["columns"] == {k: i for i, k in enumerate(ColumnMap.FIELDS)} and abs(_rms(blk.i[1]) - 6) < 0.01
    assert info["unmapped"] == []


def test_enabled_by_number_and_name_with_unmapped_channels(tmp_path):
    cfg = AppConfig()
    cfg.columns.mapping_enabled = True
    # 文件列：t, x, Ic, Ua, Ia（表头名怪异，靠映射）
    p = _write(tmp_path / "m.csv", ["时间", "备用", "C相电流", "电压A", "电流A"], ["t", "x", "ic", "ua", "ia"])
    cfg.columns.mapping = {"timestamp": "1", "ua": "电压A", "ia": "5", "ub": "", "ib": "", "uc": "", "ic": "3"}
    cfg.validate()
    blk, info = _one(str(p), cfg.columns, cfg)
    assert info["columns"] == {"timestamp": 0, "ua": 3, "ia": 4, "ub": None, "ib": None, "uc": None, "ic": 2}
    assert abs(_rms(blk.u[0]) - 57.7) < 0.05 and abs(_rms(blk.i[0]) - 5) < 0.01 and abs(_rms(blk.i[2]) - 7) < 0.01
    assert float(np.abs(blk.u[1]).max()) == 0.0 and float(np.abs(blk.i[1]).max()) == 0.0     # 未映射按 0，不插值
    assert info["unmapped"] == ["ub", "ib", "uc"]
    assert any("未映射字段 B相电压、B相电流、C相电压 不播放" in n for n in info["notes"])
    assert blk.t[0] > 1.7e9                                                               # 时间戳列正常
    # 列号超出文件列数 → 该通道空 → 按 NaN 策略（提示非法/空值），不崩
    cfg.columns.mapping["ub"] = "9"; cfg.validate()
    blk, info = _one(str(p), cfg.columns, cfg)
    assert blk.n == FS


def test_enabled_without_timestamp_synthesizes_continuous_time(tmp_path):
    cfg = AppConfig()
    cfg.columns.mapping_enabled = True
    cfg.columns.mapping = {"timestamp": "", "ua": "2", "ia": "3", "ub": "4", "ib": "5", "uc": "6", "ic": "7"}
    cfg.validate()
    p = _write(tmp_path / "n.csv", None, ["x", "ua", "ia", "ub", "ib", "uc", "ic"], n=3 * 640, with_header=False)
    blocks = list(iter_csv_blocks(str(p), cfg.columns, cfg.sampling, block_samples=640))
    assert len(blocks) == 3
    t = np.concatenate([b.t for b, _ in blocks])
    assert np.allclose(np.diff(t), 1 / FS) and t[0] == 0.0                              # 跨块连续
    assert any("时间轴按配置 fs 合成" in n for n in blocks[0][1]["notes"])
    assert "timestamp" in blocks[0][1]["unmapped"]


def test_header_detection_when_mapping_enabled(tmp_path):
    """启用映射 + 按列号：首行是表头（非数值）必须被跳过；首行是数据必须被保留。"""
    cfg = AppConfig(); cfg.columns.mapping_enabled = True
    cfg.columns.mapping = {"timestamp": "1", "ua": "2", "ia": "3", "ub": "", "ib": "", "uc": "", "ic": ""}
    cfg.validate()
    p1 = _write(tmp_path / "h.csv", ["t", "u", "i"], ["t", "ua", "ia"], n=640)
    p0 = _write(tmp_path / "d.csv", None, ["t", "ua", "ia"], n=640, with_header=False)
    b1, _ = _one(str(p1), cfg.columns, cfg); b0, _ = _one(str(p0), cfg.columns, cfg)
    assert b1.n == 640 and b0.n == 640
    assert cfg.columns.looks_like_header(["t", "u", "i"]) and not cfg.columns.looks_like_header(["1.5", "2", "3"])


def test_parse_rows_positional_for_tail(tmp_path):
    rows = [[f"{1.79e9 + k / FS:.6f}", "1", "2", "3", "4", "5", "6"] for k in range(640)]
    blk, info = parse_rows(rows, ColumnMap(), AppConfig().validate().sampling)
    assert blk.u[2][0] == 5.0 and blk.i[2][0] == 6.0 and info["columns"]["ic"] == 6


# ------------------------------------------------------------------ Web

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    cfg_dir = tmp_path_factory.mktemp("r10cfg")
    cfg_path = cfg_dir / "cfg.json"
    shutil.copy(ROOT / "configs" / "default.json", cfg_path)
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(cfg_path))
    mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    mp.setenv("ELEC_TOOL_EVENTS_DIR", str(cfg_dir / "events"))
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(cfg_dir / "rt"))
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = cfg_dir      # type: ignore[attr-defined]
        yield c
    mp.undo()


def test_web_mapping_config_probe_and_playback(client):
    import time
    p = _write(client.dir / "map.csv", ["ts", "Ia", "Ua", "junk"], ["t", "ia", "ua", "x"], n=2 * FS)
    client.post("/api/engine/stop")
    # 未启用：表头 ts/Ia/Ua/junk 缺 B/C 相 → 名字识别失败但首行非数值仍判为表头 → 默认列序（第 4 列 junk 当 B 相电压）
    r = client.put("/api/config", json={"columns": {"mapping_enabled": False}}); assert r.status_code == 200
    pr = client.get(f"/api/probe?path={p}").json()
    assert pr["ok"] and pr["mapping_enabled"] is False and pr["columns"]["ub"] == 3
    # 启用：只映射 t/Ua/Ia
    r = client.put("/api/config", json={"columns": {"mapping_enabled": True,
                                                    "mapping": {"timestamp": "ts", "ua": "Ua", "ia": "Ia", "ub": "", "ib": "", "uc": "", "ic": ""}}})
    assert r.status_code == 200, r.text
    assert r.json()["config"]["columns"]["mapping"]["ua"] == "Ua"
    assert client.put("/api/config", json={"columns": {"mapping": {"ua": "", "ia": ""}}}).status_code == 400   # 无通道
    pr = client.get(f"/api/probe?path={p}").json()
    assert pr["ok"] and pr["mapping_enabled"] is True and pr["columns"] == {"timestamp": 0, "ua": 2, "ia": 1, "ub": None, "ib": None, "uc": None, "ic": None}
    assert pr["unmapped"] == ["B相电压", "B相电流", "C相电压", "C相电流"] and pr["ncols"] == 4
    # 列名不在表头 → 探查给出可读错误
    client.put("/api/config", json={"columns": {"mapping": {"ic": "不存在的列"}}})
    assert "不在表头" in client.get(f"/api/probe?path={p}").json()["error"]
    client.put("/api/config", json={"columns": {"mapping": {"ic": ""}}})
    # 端到端播放：只有 A 相有值
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(p), "realtime": False})
    assert r.status_code == 200, r.text
    deadline = time.time() + 15
    while time.time() < deadline:
        st = client.get("/api/state").json()
        if st.get("finished") or st.get("error"):
            break
        time.sleep(0.2)
    res = client.get("/api/result?full=true").json()
    v = res["quantities"]["voltage"]["values"]
    assert abs(v["rms"]["A"] - 5770) < 10 and v["rms"]["B"] == 0 and v["rms"]["C"] == 0     # PT=100；B/C 未映射＝0
    assert any("未映射" in n for n in st["source"].get("notes", [])), st["source"].get("notes")
    client.post("/api/engine/stop")
    client.put("/api/config", json={"columns": {"mapping_enabled": False}})


def test_frontend_colmap_panel():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'id="cfg-mapen"' in html and 'id="btn-map-fromprobe"' in html
    for k in ColumnMap.FIELDS:
        assert f'id="cfg-map-{k}"' in html, k
    assert "collectColumnsPayload" in js and "columns: collectColumnsPayload()" in js
    assert "fillColumnsForm('bus', cfg.columns)" in js and "syncColmapForm" in js      # R15：两侧列映射共用一套按前缀寻址的表单函数
    for k in ColumnMap.FIELDS:
        assert f'id="br-map-{k}"' in html, k                                               # 分路侧独立列映射
