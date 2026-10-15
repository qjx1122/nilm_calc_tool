"""v0.16：数据源与控制页两列布局 / 分路侧 4 种输入方式 / 曲线分线显示开关持久化 / 总览分路侧曲线状态栏。

界面行为由 tools/ui_r16_check.cjs（jsdom）覆盖；这里只验证静态结构与服务端契约。
"""
from __future__ import annotations

import pathlib
import re
import shutil

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
APPJS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


def _options(select_id: str):
    m = re.search(r'<select id="%s"[^>]*>(.*?)</select>' % re.escape(select_id), HTML, re.S)
    assert m, select_id
    return re.findall(r'<option value="([^"]*)"', m.group(1))


def test_source_view_two_columns_same_row():
    sec = HTML[HTML.index('id="view-source"'):HTML.index("<!-- 三相电压 -->")]
    grid = sec[sec.index('id="srcgrid"'):sec.index("</section>")]
    cols = re.findall(r'<div class="panel (col-bus|col-br)"', grid)
    # 4 行 × 2 列：总线侧在左、分路侧在右，交替出现
    assert cols == ["col-bus", "col-br"] * 4
    # 未启用分路侧：右列隐藏（CSS 规则存在 + 初始类名 no-branch）
    css = (ROOT / "app" / "static" / "style.css").read_text(encoding="utf-8")
    assert ".srcgrid.no-branch .col-br{display:none}" in css
    assert 'class="srcgrid no-branch" id="srcgrid"' in HTML


def test_branch_source_has_same_four_kinds_and_fields():
    assert _options("br-kind") == _options("src-kind") == ["csv_file", "csv_tail", "tcp", "simulator"]
    assert _options("br-playmode") == _options("src-playmode")
    assert _options("br-file-speed") == _options("src-file-speed")
    for n in ("path", "host", "port", "frame", "fmt", "fields", "customtime", "utc", "customstart",
              "playmode", "playvalue", "tailend", "newest", "block", "speed", "file-speed"):
        assert f'id="src-{n}"' in HTML and f'id="br-{n}"' in HTML, n
    # 两侧共用同一套表单函数（前缀参数化），分路侧不再写死 csv_file
    assert "function collectSourceFields(pre)" in APPJS and "function fillSourceFields(pre, src)" in APPJS
    assert "kind: 'csv_file', path: $('#br-path')" not in APPJS


def test_overview_branch_curve_header_matches_bus():
    for k in ("voltage", "current", "power", "harmonic"):
        assert f'class="curve-save" data-curve="{k}" data-side="branch"' in HTML, k
        assert f'class="curvespan" data-curve="{k}" data-side="branch"' in HTML, k


def test_series_hidden_config_validation():
    from elec_tool.config import AppConfig, ConfigError
    cfg = AppConfig.from_dict({"output": {"series_hidden": {"ov-u": ["Ub", ""], "ov-p": [], "x": None}}})
    cfg.validate()
    assert cfg.output.series_hidden == {"ov-u": ["Ub"]}          # 空列表 / None / 空名被清理
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"output": {"series_hidden": {"ov-u": "Ub"}}}).validate()
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"output": {"series_hidden": ["Ub"]}}).validate()


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r16")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json"))
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "1")
    import app.server as srv
    with TestClient(srv.app) as c:
        c.dir = d  # type: ignore[attr-defined]
        yield c
    mp.undo()


def test_series_hidden_roundtrip_and_persist(client):
    import json
    r = client.put("/api/config", json={"output": {"series_hidden": {"ov-u": ["Ub"]}}})
    assert r.status_code == 200 and r.json()["config"]["output"]["series_hidden"] == {"ov-u": ["Ub"]}
    # 另一张图的开关不影响已有项（深合并）
    client.put("/api/config", json={"output": {"series_hidden": {"ov-p": ["Q", "S"]}}})
    assert client.get("/api/config").json()["output"]["series_hidden"] == {"ov-u": ["Ub"], "ov-p": ["Q", "S"]}
    # 全部重新勾选 → 送空列表 → 该项消失
    client.put("/api/config", json={"output": {"series_hidden": {"ov-u": []}}})
    assert client.get("/api/config").json()["output"]["series_hidden"] == {"ov-p": ["Q", "S"]}
    # 已落盘（重开页面/重启服务仍保持）
    assert json.loads((client.dir / "cfg.json").read_text(encoding="utf-8"))["output"]["series_hidden"] == {"ov-p": ["Q", "S"]}
    # 分路侧配置独立
    client.put("/api/branch/config", json={"output": {"series_hidden": {"ov-u-br": ["Ua"]}, "curve_save": {"voltage": False}}})
    b = client.get("/api/branch/config").json()["output"]
    assert b["series_hidden"] == {"ov-u-br": ["Ua"]} and b["curve_save"]["voltage"] is False
    assert client.get("/api/config").json()["output"]["curve_save"]["voltage"] is True
