"""v0.89：曲线上标注事件条数限制——「标注全部事件」勾选（默认不勾＝最近 1000 条）。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_api_limit_zero_means_all(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_PERSIST_CONFIG", "0"); monkeypatch.setenv("ELEC_TOOL_AUTOSTART", "")
    from fastapi.testclient import TestClient
    import importlib, app.server as srv
    importlib.reload(srv)
    with TestClient(srv.app) as client:
        for lim in (0, 1, 1000, 999999):
            r = client.get(f"/api/nilm/events?limit={lim}"); assert r.status_code == 200 and r.json()["ok"], lim
        # 直接核对 limit 解析：0 → 不截断；超大 → 5000
        import inspect
        src = inspect.getsource(srv.get_nilm_events)
        assert "10 ** 9 if lim <= 0" in src and "min(lim, 5000)" in src


def test_frontend_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'id="nilm-mark-all"' in html and 'id="nilm-pqs-pool"' in html and "标注全部事件" in html
    assert "const NILM_MARK_LIMIT = 1000" in js and "function nilmMarkPool" in js and "nilmMarkPool(nl)" in js and "nilmMarkPool(NL)" in js
    assert "limit=${nilmMarkAll(side) ? 0 : NILM_MARK_LIMIT}" in js and "on('nilm-mark-all', 'change'" in js
