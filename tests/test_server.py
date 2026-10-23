"""Web 服务层端到端测试：REST + WebSocket + 静态界面。

对应验收标准：
  ① 软件总体＝电气量计算工具（/api/health、/api/state、页面标题）
  ② 各电气量分到各子界面（index.html 里 7 个 view-* 容器）
  ③ 子界面通过导航条切换（nav 项与 switchView）
  ④ 输入支持实时采集与离线文件两种（simulator / csv_file 两条链路都跑通）
  ⑤ 电气量齐全（三相电压电流、P/Q/PF、基波、谐波 2–50、频谱）
  ⑥ 各量可分别配置时间段（PUT /api/config 改窗长 → 输出次数与 window 字段随之变化）

配置文件通过 ELEC_TOOL_CONFIG_PATH 指向 tmp 目录，**绝不触碰入库的 configs/default.json**。
"""

from __future__ import annotations

import json
import math
import os
import shutil
import time
from pathlib import Path

import pytest

from elec_tool.config import QUANTITY_KEYS
from tests.conftest import CT, F_NOM, FS, HEADER_CN, PT

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------- 夹具

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """同进程内起 ASGI 应用（TestClient）。缺 httpx 时整模块跳过。"""
    pytest.importorskip("httpx", reason="Web 层测试需要 httpx（FastAPI TestClient 依赖）")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient

    cfg_dir = tmp_path_factory.mktemp("webcfg")
    cfg_path = cfg_dir / "cfg.json"
    shutil.copy(ROOT / "configs" / "default.json", cfg_path)

    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(cfg_path))   # 加载与持久化都指向 tmp
    mp.setenv("ELEC_TOOL_AUTOSTART", "")                # 不自动启动，测试自己控制
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "1")

    import app.server as srv
    with TestClient(srv.app) as c:
        c.cfg_path = cfg_path          # type: ignore[attr-defined]
        c.srv = srv                    # type: ignore[attr-defined]
        yield c
    mp.undo()


def _post(client, url, payload):
    r = client.post(url, json=payload)
    return r


def _wait_finished(client, deadline_s: float = 30.0) -> dict:
    """离线源：等到引擎跑完（EOF）或超时。"""
    t0 = time.time()
    st = {}
    while time.time() - t0 < deadline_s:
        st = client.get("/api/state").json()
        if st.get("finished") or (st.get("engine") or {}).get("finished"):
            return st
        if st.get("error"):
            return st
        time.sleep(0.05)
    return st


def _wait_quantity(client, key: str, deadline_s: float = 30.0) -> dict:
    """实时源：等到某个电气量出结果。"""
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        d = client.get("/api/result?full=true").json()
        if d.get("quantities", {}).get(key):
            return d
        time.sleep(0.05)
    return client.get("/api/result?full=true").json()


def _run_offline(client, path, block_samples=6400, windows=None, deadline_s=30.0):
    payload = {"kind": "csv_file", "path": str(path), "block_samples": block_samples}
    if windows:
        payload["windows"] = windows
    r = _post(client, "/api/engine/start", payload)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    st = _wait_finished(client, deadline_s)
    assert not st.get("error"), st.get("error")
    return client.get("/api/result?full=true").json(), st


# --------------------------------------------------------------------- ①②③ 界面结构

def test_health_reports_version_and_running_flag(client):
    d = client.get("/api/health").json()
    assert d["ok"] is True
    assert d["version"]
    assert isinstance(d["running"], bool)


def test_state_lists_all_seven_quantities(client):
    d = client.get("/api/state").json()
    assert set(d["quantities"]) == set(QUANTITY_KEYS)
    assert len(QUANTITY_KEYS) == 9                      # 需求⑤：七类电气量 + 第 9 轮间谐波/直流偏置
    assert d["config"]["sampling"]["fs"] == FS
    assert d["config"]["transform"]["pt_ratio"] == PT
    assert d["config"]["transform"]["ct_ratio"] == CT
    # 配置加载/持久化路径必须落在 tmp（证明没写入库文件）
    assert d["engine"]["config_path"] == str(client.cfg_path)
    assert d["engine"]["config_persist_path"] == str(client.cfg_path)


def test_index_page_has_nav_and_one_subview_per_quantity(client):
    html = client.get("/").text
    assert "负荷辨识工具" in html and "电气量" in html   # v0.25 标题：电力电气量计算与负荷辨识工具
    # 需求③：导航条（每个子界面一个 navitem，data-view 绑定切换）
    assert 'id="navbar"' in html
    assert html.count('class="navitem') >= 11
    # 需求②：每个电气量一个独立子界面容器
    for view in ("overview", "source", "voltage", "current", "power", "power_factor",
                 "fundamental", "harmonic", "spectrum", "windows", "export", "selftest"):
        assert f'id="view-{view}"' in html, f"缺少子界面 view-{view}"
        assert f'data-view="{view}"' in html, f"导航条缺少 {view} 入口"
    # 预览/内网环境无外网：页面不得依赖任何 CDN 或外部资源
    assert "cdn" not in html.lower() and "https://" not in html and "http://" not in html


def test_static_assets_served_without_external_deps(client):
    js = client.get("/static/app.js")
    assert js.status_code == 200
    body = js.text
    assert "mergeResult" in body            # 分量子集推送必须按键合并
    assert "drawLine" in body and "drawBars" in body     # 图表为原生 canvas
    assert "function esc(" in body          # 服务端文本插入 innerHTML 前转义
    css = client.get("/static/style.css")
    assert css.status_code == 200 and css.text.strip()


# --------------------------------------------------------------------- ⑥ 窗口配置

def test_config_put_deep_merges_and_persists(client):
    before = client.get("/api/config").json()
    r = client.put("/api/config", json={"windows": {"voltage": {"length_s": 5.0}}})
    assert r.status_code == 200, r.text
    after = r.json()["config"]
    assert after["windows"]["voltage"]["length_s"] == 5.0
    # 深合并：未提到的量与字段不能被冲掉
    assert after["windows"]["harmonic"]["length_s"] == before["windows"]["harmonic"]["length_s"]
    assert after["windows"]["voltage"]["policy"] == before["windows"]["voltage"]["policy"]
    assert after["transform"]["pt_ratio"] == PT
    # 落盘（tmp 配置）
    on_disk = json.loads(Path(client.cfg_path).read_text())
    assert on_disk["windows"]["voltage"]["length_s"] == 5.0

    r2 = client.put("/api/config", json={"windows": {"voltage": {"length_s": 1.0}}})
    assert r2.json()["config"]["windows"]["voltage"]["length_s"] == 1.0


def test_config_put_rejects_invalid_values(client):
    cases = [
        ({"windows": {"voltage": {"length_s": -1}}}, "length_s"),
        ({"sampling": {"f_min": 70, "f_max": 40}}, "f_min"),
        ({"transform": {"pt_ratio": 0}}, "变比"),
        ({"source": {"kind": "modbus"}}, "kind"),
        ({"power": {"apparent": "foo"}}, "apparent"),
    ]
    good = client.get("/api/config").json()
    disk_before = Path(client.cfg_path).read_bytes()
    for payload, kw in cases:
        r = client.put("/api/config", json=payload)
        assert r.status_code == 400, (payload, r.status_code, r.text)
        d = r.json()
        assert d["ok"] is False and d["error"]
        assert kw in d["error"], d["error"]
    # 非法配置不得污染生效配置与磁盘
    assert client.get("/api/config").json() == good
    # v0.63 起文件只在原文件基础上更新改动键（不再是内存配置的整份转储）→ 对比文件字节未变
    assert Path(client.cfg_path).read_bytes() == disk_before


def test_harmonic_order_max_cannot_alias(client):
    """50 次＝2500Hz < Nyquist 3200Hz；配到 200 次必须被拒并说明原因。"""
    r = client.put("/api/config", json={"harmonic": {"order_max": 200}})
    assert r.status_code == 400
    assert "Nyquist" in r.json()["error"] or "混叠" in r.json()["error"]
    ok = client.put("/api/config", json={"harmonic": {"order_max": 50}})
    assert ok.status_code == 200 and ok.json()["config"]["harmonic"]["order_max"] == 50


def test_engine_start_rejects_unknown_source(client):
    r = _post(client, "/api/engine/start", {"kind": "modbus"})
    assert r.status_code == 400
    assert r.json()["ok"] is False and "kind" in r.json()["error"]


# --------------------------------------------------------------------- ④ 离线文件链路

def test_probe_detects_user_csv_format(client, csv_factory, tmp_path):
    art = csv_factory(str(tmp_path / "probe.csv"), duration_s=1.0)
    d = client.get("/api/probe", params={"path": str(art["path"])}).json()
    assert d["ok"] is True
    assert d["header"] == HEADER_CN                       # 用户给定的列格式
    assert d["rows"] == art["t"].size
    assert d["fs_est"] == pytest.approx(FS, rel=1e-3)     # 时间戳反推采样率
    assert abs(d["fs_deviation_pct"]) < 0.1
    assert d["duration_s"] == pytest.approx(1.0, abs=0.01)
    assert d["encoding"]


def test_probe_missing_file_reports_error(client, tmp_path):
    d = client.get("/api/probe", params={"path": str(tmp_path / "nope.csv")}).json()
    assert d["ok"] is False and d.get("error")


def test_files_listing(client):
    d = client.get("/api/files", params={"sub": "data"}).json()
    assert d["ok"] is True and isinstance(d["files"], list)


def test_offline_csv_end_to_end_values(client, csv_factory, tmp_path):
    """离线 CSV → 七类电气量，数值对齐解析解（一次值，已含 PT/CT）。"""
    art = csv_factory(str(tmp_path / "e2e.csv"), duration_s=1.2)
    d, st = _run_offline(client, art["path"])
    exp = art["expected"]
    assert set(d["quantities"]) == set(QUANTITY_KEYS)
    for k in QUANTITY_KEYS:
        assert d["quantities"][k]["ok"] is True, (k, d["quantities"][k].get("error"))
    assert d["meta"]["pt_ratio"] == PT and d["meta"]["ct_ratio"] == CT

    v = d["quantities"]["voltage"]["values"]
    c = d["quantities"]["current"]["values"]
    p = d["quantities"]["power"]["values"]
    pf = d["quantities"]["power_factor"]["values"]
    f = d["quantities"]["fundamental"]["values"]
    h = d["quantities"]["harmonic"]["values"]
    sp = d["quantities"]["spectrum"]["values"]

    assert v["rms"]["A"] == pytest.approx(exp["u_rms_phase"], rel=2e-3)
    assert v["line_rms"]["Uab"] == pytest.approx(exp["u_line"], rel=2e-3)
    assert c["rms"]["A"] == pytest.approx(exp["i_rms_phase"], rel=2e-3)
    assert c["neutral_rms"] == pytest.approx(exp["i_neutral"], rel=5e-3)
    assert p["p_total"] == pytest.approx(exp["p_total"], rel=2e-3)
    assert p["q_total"] == pytest.approx(exp["q_total"], rel=5e-3)
    assert pf["pf_total"] == pytest.approx(exp["pf_arith"], rel=2e-3)
    assert pf["dpf"] == pytest.approx(math.cos(math.radians(30)), rel=2e-3)
    assert f["freq_hz"] == pytest.approx(F_NOM, rel=1e-6)
    assert h["thd_u_pct"]["A"] == pytest.approx(exp["thd_u_pct"], rel=5e-3)
    assert set(h["u"]["A"]["orders_rms"]) == {str(k) for k in range(2, 51)}   # 需求⑤：2–50 次
    assert sp["peak"]["freq_hz"] == pytest.approx(F_NOM, rel=1e-2)
    assert abs(p["p_residual_pct"]) < 0.05            # 时域 P 与 Σ P_h 自洽
    assert st["engine"]["samples_in"] == art["t"].size


def test_offline_window_length_changes_output_count(client, csv_factory, tmp_path):
    """需求⑥：同一份数据，电压窗 1s vs 5s，输出次数必须差 ~5 倍。"""
    art = csv_factory(str(tmp_path / "w.csv"), duration_s=5.0)
    _, st1 = _run_offline(client, art["path"], block_samples=640,
                          windows={"voltage": 1.0, "harmonic": 0.2})
    e1 = st1["engine"]["emits"]
    assert e1["voltage"] >= 4 and e1["harmonic"] >= 4 * e1["voltage"]

    d2, st2 = _run_offline(client, art["path"], block_samples=640,
                           windows={"voltage": 5.0, "harmonic": 0.2})
    e2 = st2["engine"]["emits"]
    assert e2["voltage"] <= 2, e2
    assert e2["harmonic"] >= 4 * max(e2["voltage"], 1), e2
    assert d2["quantities"]["voltage"]["window"]["length_s_requested"] == 5.0
    assert st2["engine"]["buffer_capacity"] >= int(5.0 * FS)   # 缓冲按需扩容
    # 每次运行是独立数据集：重启后历史不得把两次运行混在一起
    assert st2["engine"]["samples_in"] == art["t"].size


def test_history_is_per_quantity_and_non_decreasing(client, csv_factory, tmp_path):
    art = csv_factory(str(tmp_path / "hist.csv"), duration_s=3.0)
    _run_offline(client, art["path"], block_samples=640,
                 windows={"voltage": 1.0, "harmonic": 0.2})
    for key in ("voltage", "harmonic"):
        d = client.get(f"/api/history/{key}", params={"n": 50}).json()
        assert d["quantity"] == key
        pts = d["points"]
        assert pts, key
        ts = [p["t"] for p in pts]
        # 收尾 flush 可能与最后一次调度共用同一 t_ref：只保证非递减
        assert all(b >= a for a, b in zip(ts, ts[1:])), ts
    bad = client.get("/api/history/not_a_quantity")
    assert bad.status_code in (400, 404)


def test_export_csv_and_json(client, csv_factory, tmp_path):
    art = csv_factory(str(tmp_path / "exp.csv"), duration_s=1.2)
    _run_offline(client, art["path"])
    csv_resp = client.get("/api/export", params={"fmt": "csv"})
    assert csv_resp.status_code == 200
    lines = csv_resp.text.strip().splitlines()
    assert lines[0].strip() == "source_id,t_ref,quantity,metric,value,unit,window_s"
    assert len(lines) > 200
    assert any("harmonic,thd_u_pct.A," in ln for ln in lines)
    assert any("fundamental,freq_hz," in ln for ln in lines)

    j = client.get("/api/export", params={"fmt": "json"}).json()
    assert isinstance(j, list) and j                     # 顶层就是结果列表
    assert set(j[-1]["quantities"]) == set(QUANTITY_KEYS)
    one = client.get("/api/export", params={"fmt": "csv", "quantity": "harmonic"}).text
    assert "harmonic,thd_u_pct.A," in one and "voltage,rms.A," not in one
    bad = client.get("/api/export", params={"fmt": "xlsx"})
    assert bad.status_code in (400, 422)


# --------------------------------------------------------------------- ④ 实时链路

def test_realtime_simulator_streams_and_schedules_per_quantity(client):
    """实时源：模拟器按 6400 点/s 推进，各量按自己的窗长独立出结果。"""
    r = _post(client, "/api/engine/start",
              {"kind": "simulator", "block_samples": 640, "sim_speed": 40.0,
               "poll_interval_s": 0.01})
    assert r.status_code == 200 and r.json()["ok"] is True

    # 首帧结果允许「缩窗」（数据不足一个窗长时按可用数据的整数周期计算），
    # 因此先拿到首次结果，再等数据积累超过一个完整窗长后断言满窗。
    _wait_quantity(client, "voltage", deadline_s=25.0)
    t0 = time.time()
    st = client.get("/api/state").json()
    while time.time() - t0 < 25.0 and st["engine"]["data_duration_s"] < 1.2:
        time.sleep(0.05)
        st = client.get("/api/state").json()
    d = client.get("/api/result", params={"full": "true"}).json()
    assert st["running"] is True or st["engine"]["samples_in"] > 0
    assert st["source"]["kind"] == "simulator"
    assert st["engine"]["samples_in"] >= FS                    # 至少 1s 数据
    assert st["engine"]["rate_samples_per_s"] > 0
    wv = d["quantities"]["voltage"]["window"]
    assert wv["length_s_requested"] == 1.0
    assert wv["n_samples"] == pytest.approx(FS, rel=1e-6)      # 满窗，不再缩窗

    v = d["quantities"]["voltage"]["values"]
    p = d["quantities"]["power"]["values"]
    f = d["quantities"]["fundamental"]["values"]
    h = d["quantities"]["harmonic"]["values"]
    # 模拟器二次侧额定：相电压 100/√3 V → 一次 5773.5 V
    assert v["rms"]["A"] == pytest.approx(100.0 / math.sqrt(3) * PT, rel=5e-2)
    assert f["freq_hz"] == pytest.approx(F_NOM, rel=1e-3)
    assert 0.3 < p["pf_total"] <= 1.0
    assert p["q_total"] > 0                                    # 电流滞后 → 感性
    assert h["thd_u_pct"]["A"] > 0                             # 注入了谐波
    assert d["quantities"]["harmonic"]["window"]["leakage_risk"] is False

    emits = st["engine"]["emits"]
    assert emits["fundamental"] >= 2 * max(emits["voltage"], 1), emits   # 0.2s vs 1s 窗

    r2 = _post(client, "/api/engine/stop", {})
    assert r2.status_code == 200
    time.sleep(0.2)
    assert client.get("/api/state").json()["running"] is False
    # 停止后仍可导出/回看结果
    assert client.get("/api/result").json()["quantities"]


def test_result_full_flag_recomputes_all_quantities(client, csv_factory, tmp_path):
    """full=true＝强制把七类量都算一遍（首屏/切换视图用）；full=false＝取最近缓存。"""
    art = csv_factory(str(tmp_path / "full.csv"), duration_s=1.2)
    _run_offline(client, art["path"])
    full = client.get("/api/result", params={"full": "true"}).json()
    cached = client.get("/api/result", params={"full": "false"}).json()
    assert set(full["quantities"]) == set(QUANTITY_KEYS)
    assert set(cached["quantities"]) == set(QUANTITY_KEYS)
    assert cached["t_ref"] == pytest.approx(full["t_ref"], rel=1e-9)
    # 谐波必须给到 2~50 次全序列，频谱必须给频率轴
    h = full["quantities"]["harmonic"]["values"]
    assert len(h["u"]["A"]["orders_rms"]) == 49
    # 频谱曲线在 quantity.series.channels 下（前端 renderSpectrum 用的就是这条路径）
    sp = full["quantities"]["spectrum"]
    ch = sp["series"]["channels"]["Ua"]
    assert len(ch["freqs"]) == len(ch["amp_rms"]) == len(ch["amp_db"]) > 100
    assert max(ch["freqs"]) <= sp["values"]["nyquist_hz"]


# --------------------------------------------------------------------- 自检与 WebSocket

def test_selftest_endpoint_all_pass(client):
    d = client.get("/api/selftest").json()
    assert d["total"] == d["passed"] and d["failed"] == 0
    assert d["pass_rate_pct"] == 100.0
    assert d["worst_rel_err"] < 1e-3
    assert d["conditions"]["fs"] == FS
    assert d["conditions"]["pt"] == PT and d["conditions"]["ct"] == CT
    assert d["all_ok"] is True and d["failures"] == []
    assert len(d["checks"]) == d["total"] and all(c["ok"] for c in d["checks"])
    # 自检项必须覆盖七类量（S1 电压电流 / S2 功率 / S3 谐波 / S4 频谱 / S5 窗长 / S6 变比 ...）
    ids = {c["id"].split("-")[0] for c in d["checks"]}
    assert {"S1", "S2", "S3", "S4", "S5", "S6"} <= ids, sorted(ids)


def test_websocket_sends_hello_then_snapshot(client):
    with client.websocket_connect("/ws") as ws:
        m1 = ws.receive_json()
        assert m1["type"] == "hello" and m1["data"]["version"]
        m2 = ws.receive_json()
        assert m2["type"] in ("snapshot", "state", "result")
        if m2["type"] == "snapshot":
            assert "quantities" in m2["data"]


def test_openapi_documents_all_endpoints(client):
    spec = client.get("/openapi.json").json()
    paths = set(spec["paths"])
    for p in ("/api/health", "/api/state", "/api/config", "/api/engine/start",
              "/api/engine/stop", "/api/result", "/api/export", "/api/selftest",
              "/api/probe", "/api/files"):
        assert p in paths, sorted(paths)
    assert any(p.startswith("/api/history") for p in paths)


# --------------------------------------------------------------------- v0.71 三相电压/电流/功率页「周波窗」离线文件接口

def test_elec_cycles_file_matches_nilm_cycles(client, csv_factory, tmp_path):
    """/api/elec/cycles_file（U/I/P/Q/S 逐周波）与 /api/nilm/cycles_file（负荷辨识口径）同段同值；
    t 空＝数据起点起 n 个周波，t 给定＝居中；非 csv_file 源 400。"""
    path = tmp_path / "ew.csv"
    csv_factory(str(path), duration_s=1.0, header=HEADER_CN, ts_mode="epoch")
    _run_offline(client, path)
    r = client.get("/api/elec/cycles_file?n=10")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True and d["n_cycles"] == 10 and d["n_cycle_samples"] == int(round(FS / F_NOM))
    assert len(d["t"]) == 10
    for grp, keys in (("U", "ABC"), ("I", "ABC"), ("P", "ABC"), ("Q", "ABC"), ("S", "ABC")):
        for k in keys:
            assert len(d[grp][k]) == 10, (grp, k)
    assert len(d["I"]["total"]) == 10 and len(d["P"]["total"]) == 10
    # 与负荷辨识周波窗接口对齐（同起点、同 P/Q/I）
    n = client.get("/api/nilm/cycles_file?n=10").json()
    assert n["ok"] is True
    assert n["t"][0] == pytest.approx(d["t"][0], abs=1e-6)
    ch = n["channels"]["total"] if "total" in n["channels"] else next(iter(n["channels"].values()))
    for a, b in zip(ch["p"], d["P"]["total"]):
        assert a == pytest.approx(b, rel=1e-9, abs=1e-6)
    for a, b in zip(ch["q"], d["Q"]["total"]):
        assert a == pytest.approx(b, rel=1e-9, abs=1e-6)
    for a, b in zip(ch["i"], d["I"]["total"]):
        assert a == pytest.approx(b, rel=1e-9, abs=1e-9)
    # 居中装载：中心时刻落在窗内中部
    tc = d["t"][0] + 0.5
    c = client.get(f"/api/elec/cycles_file?n=20&t={tc}").json()
    assert c["ok"] is True and c["n_cycles"] == 20
    assert c["t"][0] < tc < c["t"][-1] + 1.0 / F_NOM
    assert abs((c["t"][0] + c["t"][-1]) / 2 - tc) < 2.0 / F_NOM
    # 非文件源：400
    _post(client, "/api/engine/start", {"kind": "simulator"})
    try:
        r = client.get("/api/elec/cycles_file?n=10")
        assert r.status_code == 400
        assert "离线文件" in r.json()["error"]
    finally:
        _post(client, "/api/engine/stop", {})
