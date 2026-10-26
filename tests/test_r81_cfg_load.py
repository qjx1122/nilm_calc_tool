"""v0.81：数据源与控制界面「从文件加载本侧配置」——POST /api/config/load_file、/api/branch/config/load_file、GET /api/config/file。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r81cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "1"); mp.setenv("ELEC_TOOL_EVENTS_DIR", str(d / "ev"))
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(d / "rt")); mp.setenv("ELEC_TOOL_NILM_DIR", str(d / "nilm"))
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json"))
    shutil.copy(ROOT / "configs" / "default.json", d / "branch.json")
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


def test_config_file_default_paths(client):
    b = client.get("/api/config/file").json()
    br = client.get("/api/branch/config/file").json()
    assert b["ok"] and b["side"] == "bus" and b["path"].endswith("cfg.json") and b["exists"]
    assert br["ok"] and br["side"] == "branch" and br["path"].endswith("branch.json") and br["exists"]


def test_load_file_bus_hot_update_without_persist(client):
    d = client.dir
    doc = json.loads((ROOT / "configs" / "default.json").read_text(encoding="utf-8"))
    doc["transform"]["pt_ratio"] = 123.0
    doc["nilm"] = {"algorithms": {"glr": {"threshold": 33.0}}}
    (d / "other.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    before = (d / "cfg.json").read_text(encoding="utf-8")
    r = client.post("/api/config/load_file", json={"path": str(d / "other.json")}).json()
    assert r["ok"] and r["side"] == "bus" and r["loaded_from"].endswith("other.json") and r["config_file_updated"] is False
    assert r["config"]["transform"]["pt_ratio"] == 123.0 and r["config"]["nilm"]["algorithms"]["glr"]["threshold"] == 33.0
    assert r["config"]["output"]["source_id"] == 0                    # 侧别强制项不被文件覆盖
    assert client.get("/api/config").json()["transform"]["pt_ratio"] == 123.0
    assert (d / "cfg.json").read_text(encoding="utf-8") == before      # 默认不写配置文件
    # 分路侧不受影响
    assert client.get("/api/branch/config").json()["transform"]["pt_ratio"] != 123.0


def test_load_file_persist_writes_only_diff(client):
    d = client.dir
    doc = json.loads((ROOT / "configs" / "default.json").read_text(encoding="utf-8"))
    doc["transform"]["ct_ratio"] = 77.0
    (d / "ct77.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    base_before = json.loads((d / "cfg.json").read_text(encoding="utf-8"))
    r = client.post("/api/config/load_file", json={"path": str(d / "ct77.json"), "persist": True}).json()
    assert r["ok"] and r["config_file_updated"] is True and r["config_file"].endswith("cfg.json")
    assert "transform.ct_ratio" in r["config_file_changes"]
    after = json.loads((d / "cfg.json").read_text(encoding="utf-8"))
    assert after["transform"]["ct_ratio"] == 77.0
    # 除了本次差异（ct_ratio，以及上一测试加载到运行配置但未落盘、本次随整份配置一起成为差异的 pt_ratio / glr.threshold）其它键不变
    changed = set(r["config_file_changes"])
    assert changed <= {"transform.ct_ratio", "transform.pt_ratio", "nilm.algorithms.glr.threshold"}, changed
    for k in ("sampling", "columns", "source", "windows", "harmonic", "power"):
        assert after[k] == base_before[k], k


def test_load_file_default_path_and_branch(client):
    d = client.dir
    # 分路侧：路径空＝现有路径（branch.json）；先改文件再加载应生效
    doc = json.loads((d / "branch.json").read_text(encoding="utf-8"))
    doc["transform"]["pt_ratio"] = 55.0
    (d / "branch.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    r = client.post("/api/branch/config/load_file", json={"path": ""}).json()
    assert r["ok"] and r["side"] == "branch" and r["loaded_from"].endswith("branch.json")
    assert r["config"]["transform"]["pt_ratio"] == 55.0 and r["config"]["output"]["source_id"] == 1
    assert client.get("/api/branch/config").json()["transform"]["pt_ratio"] == 55.0
    assert client.get("/api/config").json()["transform"]["pt_ratio"] != 55.0     # 总线侧不受影响
    # 总线侧：无 body ＝ 现有路径
    r2 = client.post("/api/config/load_file", json={}).json()
    assert r2["ok"] and r2["loaded_from"].endswith("cfg.json") and r2["same_as_config_file"]


def test_load_file_errors(client):
    d = client.dir
    assert client.post("/api/config/load_file", json={"path": str(d / "nope.json")}).status_code == 400
    (d / "bad.json").write_text("{not json", encoding="utf-8")
    r = client.post("/api/config/load_file", json={"path": str(d / "bad.json")})
    assert r.status_code == 400 and "合法 JSON" in r.json()["error"]
    (d / "list.json").write_text("[1,2]", encoding="utf-8")
    assert client.post("/api/config/load_file", json={"path": str(d / "list.json")}).status_code == 400
    doc = json.loads((ROOT / "configs" / "default.json").read_text(encoding="utf-8")); doc["sampling"]["fs"] = 0
    (d / "fs0.json").write_text(json.dumps(doc), encoding="utf-8")
    r = client.post("/api/config/load_file", json={"path": str(d / "fs0.json")})
    assert r.status_code == 400 and "fs" in r.json()["error"]
    # 非法文件不改变运行配置
    assert client.get("/api/config").json()["sampling"]["fs"] > 0


def test_ui_has_load_rows():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8"); js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert all(x in html for x in ('id="src-cfgload-path"', 'id="btn-src-cfgload"', 'id="src-cfgload-persist"',
                                   'id="br-cfgload-path"', 'id="btn-br-cfgload"', 'id="br-cfgload-persist"',
                                   '从文件加载总线侧配置', '从文件加载分路侧配置'))
    assert "/api/config/load_file" in js and "function loadCfgFromFile(" in js and "/api/config/file" in js
