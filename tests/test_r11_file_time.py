"""第 11 轮：离线文件时标的 UTC 开关 source.file_time_utc（custom_time=False 时决定曲线时间）。

- 默认 False：文件里的 "2026-10-12 08:00:00" / "0/00/00 00:12:40.0000" 按本机本地时间解释 → 本地显示＝文件时间
- True：按 UTC 解释 → 本地显示＝文件时间 + 时区偏移（旧行为）
- epoch 数字时标不受影响；create_source/engine 默认按配置取偏移；/api/probe、/api/engine/start 透传
"""
from __future__ import annotations

import csv
import os
import shutil
import time
from pathlib import Path

import numpy as np
import pytest

from elec_tool.config import AppConfig
from elec_tool.sources import create_source
from elec_tool.sources.parsing import file_tz_offset_h, iter_csv_blocks, local_utc_offset_h

ROOT = Path(__file__).resolve().parents[1]
FS = 6400


@pytest.fixture
def beijing(monkeypatch):
    """把进程时区切到东八区（沙盒默认 UTC，否则偏移为 0 看不出差别）。"""
    monkeypatch.setenv("TZ", "Asia/Shanghai")
    time.tzset()
    yield 8.0
    monkeypatch.delenv("TZ", raising=False)
    time.tzset()


def _write(path, stamps):
    t = np.arange(len(stamps)) / FS
    w = 2 * np.pi * 50 * t
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k, s in enumerate(stamps):
            wr.writerow([s] + [f"{81.6 * np.sin(w[k] + ph):.4f}" if j % 2 == 0 else f"{7.07 * np.sin(w[k] + ph):.4f}"
                               for j, ph in enumerate((0, 0, -2.0944, -2.0944, 2.0944, 2.0944))])
    return str(path)


def _local_text(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def test_offset_helpers(beijing):
    assert local_utc_offset_h() == 8.0
    cfg = AppConfig()
    assert cfg.source.file_time_utc is False and file_tz_offset_h(cfg) == 8.0
    cfg.source.file_time_utc = True
    assert file_tz_offset_h(cfg) == 0.0
    assert AppConfig.from_dict(cfg.to_dict()).source.file_time_utc is True


def test_datetime_text_matches_file_when_not_utc(beijing, tmp_path):
    stamps = [f"2026-10-12 08:00:{k / FS:09.6f}" for k in range(640)]
    p = _write(tmp_path / "dt.csv", stamps)
    cfg = AppConfig().validate()
    cfg.source.kind = "csv_file"; cfg.source.path = p
    # 默认（不按 UTC）：本地显示 == 文件时间
    blk, info = next(iter_csv_blocks(p, cfg.columns, cfg.sampling, block_samples=640, tz_offset_h=file_tz_offset_h(cfg)))
    assert _local_text(blk.t[0]) == "2026-10-12 08:00:00"
    assert any("本地时间（UTC+8）" in n for n in info["notes"])
    # 按 UTC：本地显示 = 文件时间 + 8 h
    cfg.source.file_time_utc = True
    blk2, info2 = next(iter_csv_blocks(p, cfg.columns, cfg.sampling, block_samples=640, tz_offset_h=file_tz_offset_h(cfg)))
    assert _local_text(blk2.t[0]) == "2026-10-12 16:00:00"
    assert blk2.t[0] - blk.t[0] == pytest.approx(8 * 3600.0)
    assert any("按UTC解释" in n for n in info2["notes"])


def test_slash_clock_and_epoch(beijing, tmp_path):
    # 0/00/00 当天时刻写法：不按 UTC → 本地显示 00:12:40
    p = _write(tmp_path / "clk.csv", [f"0/00/00 00:12:{40 + k / FS:07.4f}" for k in range(640)])
    cfg = AppConfig().validate()
    blk, _ = next(iter_csv_blocks(p, cfg.columns, cfg.sampling, block_samples=640, tz_offset_h=file_tz_offset_h(cfg)))
    assert time.strftime("%H:%M:%S", time.localtime(blk.t[0])) == "00:12:40"
    # epoch 数字：两种设置结果一致
    p2 = _write(tmp_path / "ep.csv", [f"{1791800000 + k / FS:.6f}" for k in range(640)])
    a, _ = next(iter_csv_blocks(p2, cfg.columns, cfg.sampling, block_samples=640, tz_offset_h=0.0))
    b, _ = next(iter_csv_blocks(p2, cfg.columns, cfg.sampling, block_samples=640, tz_offset_h=8.0))
    assert a.t[0] == b.t[0] == pytest.approx(1791800000.0)


def test_create_source_uses_config_offset(beijing, tmp_path):
    p = _write(tmp_path / "s.csv", [f"2026-10-12 08:00:{k / FS:09.6f}" for k in range(640)])
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = p; cfg.validate()
    src = create_source(cfg)
    assert src.tz_offset_h == 8.0
    src.open(); blk = src.read(); src.close()
    assert _local_text(blk.t[0]) == "2026-10-12 08:00:00"
    cfg.source.file_time_utc = True
    assert create_source(cfg).tz_offset_h == 0.0
    assert create_source(cfg, tz_offset_h=3.0).tz_offset_h == 3.0          # 显式传入仍优先


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r11cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0"); mp.setenv("ELEC_TOOL_EVENTS_DIR", str(d / "ev"))
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(d / "rt"))
    mp.setenv("TZ", "Asia/Shanghai"); time.tzset()
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo(); time.tzset()


def test_web_probe_and_start_passthrough(client):
    p = _write(client.dir / "w.csv", [f"2026-10-12 08:00:{k / FS:09.6f}" for k in range(2 * 640)])
    client.post("/api/engine/stop")
    client.put("/api/config", json={"source": {"file_time_utc": False, "custom_time": False}})
    pr = client.get(f"/api/probe?path={p}").json()
    assert pr["ok"] and pr["file_time_utc"] is False and pr["tz_offset_h"] == 8.0 and pr["t_first_local"] == "2026-10-12 08:00:00"
    client.put("/api/config", json={"source": {"file_time_utc": True}})
    pr = client.get(f"/api/probe?path={p}").json()
    assert pr["file_time_utc"] is True and pr["t_first_local"] == "2026-10-12 16:00:00"
    # 启动时顶层 file_time_utc 覆盖
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": str(p), "realtime": False, "file_time_utc": False})
    assert r.status_code == 200, r.text
    deadline = time.time() + 10
    while time.time() < deadline:
        st = client.get("/api/state").json()
        if st.get("finished") or st.get("error"):
            break
        time.sleep(0.2)
    assert st["source"]["file_time_utc"] is False and st["source"]["tz_offset_h"] == 8.0
    assert _local_text(st["source"]["t_start"]) == "2026-10-12 08:00:00"
    assert st["config"]["source"]["file_time_utc"] is False
    client.post("/api/engine/stop")


def test_frontend_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'id="src-utc"' in html
    assert "chk('utc', src.file_time_utc)" in js and "p.file_time_utc" in js
    assert "'utc': (kind === 'csv_file' && !ct) || kind === 'csv_tail'" in js
