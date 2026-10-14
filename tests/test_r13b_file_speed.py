"""v0.12.2（F-42）：离线文件播放倍速 `source.file_speed` 与暂停的可用性。

用户回报「界面上暂停播放没有生效」：服务端日志里 /api/engine/pause 全是 400——离线文件不限速时 5 s 样例 2 s 就播完，
按钮还亮着、点下去已是「已播放完毕」。修：① csv_file 增 file_speed（1×＝真实速率，0＝不限速），界面默认 1×；
② 限速按相邻两块间隔计，暂停后恢复不突发追赶；③ 静态资源带版本号 + no-cache，杜绝旧 app.js。
"""
from __future__ import annotations

import csv
import pathlib
import time

import numpy as np
import pytest

from elec_tool.config import AppConfig, ConfigError
from elec_tool.sources import create_source

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400


def _csv(path, dur):
    n = int(dur * FS); t = np.arange(n) / FS; w = 2 * np.pi * 50 * t
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(n):
            row = [f"{1_700_000_000 + t[k]:.6f}"]
            for ph in (0, -2.0944, 2.0944):
                row += [f"{81.65 * np.sin(w[k] + ph):.4f}", f"{7.07 * np.sin(w[k] + ph):.5f}"]
            wr.writerow(row)
    return str(path)


def test_file_speed_paces_blocks_and_does_not_catch_up(tmp_path):
    p = _csv(tmp_path / "a.csv", 1.0)                       # 1 s 数据 = 10 块 × 640
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = p; cfg.source.block_samples = 640
    # 不限速：瞬间读完
    cfg.source.file_speed = 0.0
    with create_source(cfg) as src:
        t0 = time.monotonic(); n = 0
        while src.read() is not None:
            n += 1
        assert n == 10 and time.monotonic() - t0 < 0.8
    # 4×：1 s 数据 ≈ 0.25 s 墙钟（首块不等待）
    cfg.source.file_speed = 4.0
    with create_source(cfg) as src:
        t0 = time.monotonic(); n = 0
        while src.read() is not None:
            n += 1
        el = time.monotonic() - t0
        assert n == 10 and 0.18 <= el <= 0.6, el
    # 模拟「暂停 0.5 s 后恢复」：下一块不补偿、之后仍按间隔限速
    cfg.source.file_speed = 4.0
    with create_source(cfg) as src:
        src.read(); src.read()
        time.sleep(0.5)
        t0 = time.monotonic(); src.read()
        assert time.monotonic() - t0 < 0.05                 # 恢复后的第一块立即返回
        t0 = time.monotonic(); src.read()
        assert time.monotonic() - t0 >= 0.02                # 第二块仍按 0.1 s / 4 ≈ 25 ms 间隔
        assert src.info()["file_speed"] == 4.0


def test_file_speed_validation():
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = "x.csv"
    cfg.source.file_speed = -1
    with pytest.raises(ConfigError):
        cfg.validate()
    d = AppConfig().to_dict(); d["source"]["file_speed"] = 2.5
    assert AppConfig.from_dict(d).source.file_speed == 2.5


def test_index_has_asset_version_and_no_cache(tmp_path):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    mp = MonkeyPatch(); mp.setenv("ELEC_TOOL_AUTOSTART", ""); mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    import app.server as srv
    with TestClient(srv.app) as c:
        r = c.get("/")
        assert r.status_code == 200 and "no-store" in r.headers["cache-control"]
        v = r.headers["x-asset-version"]
        assert f'/static/app.js?v={v}' in r.text and f'/static/style.css?v={v}' in r.text
        r2 = c.get(f"/static/app.js?v={v}")
        assert r2.status_code == 200 and "no-cache" in r2.headers["cache-control"]
        # 启动接口接受 file_speed
        p = _csv(tmp_path / "b.csv", 0.5)
        r3 = c.post("/api/engine/start", json={"kind": "csv_file", "path": p, "file_speed": 3})
        assert r3.status_code == 200 and r3.json()["config"]["source"]["file_speed"] == 3
        c.post("/api/engine/stop")
    mp.undo()


def test_frontend_has_speed_selector_and_guarded_toggle():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'id="src-file-speed"' in html and 'value="0">不限速' in html
    assert "p.file_speed = parseFloat($('#src-file-speed').value)" in js
    assert "暂停/恢复仅支持离线文件（csv_file）源" in js and "离线文件未在播放，无法暂停" in js
