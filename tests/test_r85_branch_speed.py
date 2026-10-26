"""v0.85：分路侧离线文件播放倍速可单独设置，默认随总线侧（source.file_speed_follow，分路侧专用）。"""
from __future__ import annotations

import time

import pytest

from tests.test_r14_branch import _csv, client  # noqa: F401  复用 r14 的双侧 TestClient 夹具


def test_default_follow_flag():
    from elec_tool.config import AppConfig
    cfg = AppConfig.from_dict({})
    assert cfg.source.file_speed_follow is True
    cfg2 = AppConfig.from_dict({"source": {"file_speed_follow": 0}}); cfg2.validate()
    assert cfg2.source.file_speed_follow is False
    assert "file_speed_follow" in cfg.to_dict()["source"]


def test_branch_speed_follows_bus_by_default_and_can_be_independent(client):  # noqa: F811
    import app.server as srv
    bus_p = _csv(client.dir / "bus85.csv", 4.0, amp_i=7.07)
    br_p = _csv(client.dir / "br85.csv", 4.0, amp_i=1.414)
    client.post("/api/engine/stop")
    client.put("/api/config", json={"branch": {"enabled": True}})
    # 默认：随总线侧 —— 分路侧配置 file_speed=5 被忽略，共用同一只节拍钟、倍速＝总线侧 2
    client.put("/api/branch/config", json={"source": {"kind": "csv_file", "path": br_p, "file_speed": 5}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 2})
    assert r.status_code == 200, r.text
    b = r.json()["branch"]
    assert b["ok"] and b["synced_pace"] is True and b["file_speed"] == 2
    time.sleep(0.3)
    bus_clk = srv.RUNNERS["bus"].engine.source.pace_clock
    br_clk = srv.RUNNERS["branch"].engine.source.pace_clock
    assert br_clk is bus_clk and br_clk.speed == 2
    client.post("/api/engine/stop")
    # 取消随总线侧：分路侧按自己的 5× 独立限速（各自节拍钟）
    client.put("/api/branch/config", json={"source": {"file_speed_follow": False}})
    assert client.get("/api/branch/config").json()["source"]["file_speed_follow"] is False
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": bus_p, "file_speed": 2})
    assert r.status_code == 200, r.text
    b = r.json()["branch"]
    assert b["ok"] and b["synced_pace"] is False and b["file_speed"] == 5
    time.sleep(0.3)
    bus_clk = srv.RUNNERS["bus"].engine.source.pace_clock
    br_clk = srv.RUNNERS["branch"].engine.source.pace_clock
    assert br_clk is not bus_clk and br_clk.speed == 5 and bus_clk.speed == 2
    # 总线侧配置里的 file_speed_follow 不受影响（分路侧专用）
    assert client.get("/api/config").json()["source"]["file_speed_follow"] is True
    client.post("/api/engine/stop")
    client.put("/api/branch/config", json={"source": {"file_speed_follow": True, "kind": "simulator", "path": ""}})
    client.put("/api/config", json={"branch": {"enabled": False}})
