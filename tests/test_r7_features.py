"""第 7 轮三项功能的回归测试（2026-10-12 用户需求）：

  R7-1 计算出的曲线数据**实时落盘**到 output/realtime/<曲线>_<数据日期>.csv
  R7-2 离线文件可**指定位置**开始播放（row / seconds / percent / time 四种定位方式）
  R7-3 鼠标移到曲线上显示该位置数值（前端契约：hoverInfo/drawHover/绑定事件；端到端见 tools/ui_r7_check.cjs）

每个用例写明「撤销对应实现会怎样失败」。
"""

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from elec_tool.config import AppConfig, ConfigError, CURVE_KEYS, PLAY_START_MODES, parse_play_start, parse_time_text
from elec_tool.engine import LiveEngine
from elec_tool.realtime_writer import RealtimeCurveWriter
from elec_tool.sources import create_source
from elec_tool.sources.parsing import ParseError
from tests.conftest import FS

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")


def _run_engine(cfg):
    eng = LiveEngine(cfg.validate())
    results = list(eng.run())
    return eng, results


def _rows(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


# ===================================================================== R7-1 实时落盘

def test_realtime_writer_appends_one_row_per_curve_point(csv_factory, tmp_path, monkeypatch):
    """撤销 engine._write_realtime → 目录为空；撤销 flush → 文件行数落后于历史点数。"""
    rt = tmp_path / "rt"
    monkeypatch.setenv("ELEC_TOOL_REALTIME_DIR", str(rt))
    d = csv_factory(str(tmp_path / "a.csv"), duration_s=3.0)
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 1280
    eng, _ = _run_engine(cfg)
    files = sorted(p.name for p in rt.glob("*.csv"))
    assert len(files) == 8 and all(re.fullmatch(r"(voltage|current|power|power_factor|fundamental|harmonic|interharmonic|dc)_\d{8}\.csv", f) for f in files), files
    for key in CURVE_KEYS:
        fp = next(rt.glob(f"{key}_*.csv"))
        rows = _rows(fp)
        n_hist = len(eng.calc.history.get(key))
        assert len(rows) - 1 == n_hist == eng.writer.rows_written[key], (key, len(rows) - 1, n_hist)
        assert rows[0][:3] == ["t_epoch_s", "time_local", "window_s"]
    vrows = _rows(next(rt.glob("voltage_*.csv")))
    assert vrows[0][3:6] == ["Ua", "Ub", "Uc"]
    # 文件里的值 == 历史里的值（同一提取规则）
    hist = eng.calc.history.get("voltage")
    assert float(vrows[1][0]) == pytest.approx(hist[0]["t"]) and float(vrows[1][3]) == pytest.approx(hist[0]["Ua"])
    assert float(vrows[-1][3]) == pytest.approx(hist[-1]["Ua"])
    # BOM：Excel 直接打开不乱码
    assert open(next(rt.glob("voltage_*.csv")), "rb").read(3) == b"\xef\xbb\xbf"


def test_realtime_writer_respects_curve_save_and_switch(csv_factory, tmp_path, monkeypatch):
    """未勾选的曲线不落盘；realtime_save=False 一个文件都不写（撤销过滤 → current 文件出现）。"""
    rt = tmp_path / "rt"
    monkeypatch.setenv("ELEC_TOOL_REALTIME_DIR", str(rt))
    d = csv_factory(str(tmp_path / "a.csv"), duration_s=2.0)
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 1280
    cfg.output.curve_save["current"] = False
    cfg.output.curve_save["harmonic"] = False
    _run_engine(cfg)
    names = {p.name.split("_")[0] for p in rt.glob("*.csv")}
    assert "current" not in names and "harmonic" not in names and "voltage" in names, names
    shutil.rmtree(rt)
    cfg.output.realtime_save = False
    eng, _ = _run_engine(cfg)
    assert not rt.exists() or not list(rt.glob("*.csv"))
    assert eng.writer.info()["enabled"] is False


def test_realtime_writer_appends_to_existing_file_without_second_header(csv_factory, tmp_path, monkeypatch):
    """同一天再跑一次 → 续写同一文件、表头只有一行（撤销表头检测 → 文件中部出现第二个表头）。"""
    rt = tmp_path / "rt"
    monkeypatch.setenv("ELEC_TOOL_REALTIME_DIR", str(rt))
    d = csv_factory(str(tmp_path / "a.csv"), duration_s=2.0)
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 1280
    eng1, _ = _run_engine(cfg)
    n1 = eng1.writer.rows_written["power"]
    eng2, _ = _run_engine(cfg)
    rows = _rows(next(rt.glob("power_*.csv")))
    assert len(rows) - 1 == n1 + eng2.writer.rows_written["power"]
    assert sum(1 for r in rows if r and r[0] == "t_epoch_s") == 1
    assert open(next(rt.glob("power_*.csv")), "rb").read().count(b"\xef\xbb\xbf") == 1


def test_realtime_writer_rotates_by_data_date(tmp_path, monkeypatch):
    """按**数据时间**日期分文件：两条相差一天的记录 → 两个文件（撤销 day 判断 → 只有一个文件）。"""
    from elec_tool.metrics import MetricsResult, QuantityResult
    monkeypatch.delenv("ELEC_TOOL_REALTIME_DIR", raising=False)
    cfg = AppConfig()
    cfg.output.realtime_dir = str(tmp_path / "rt")
    w = RealtimeCurveWriter(cfg.validate())
    assert w.dir == str(tmp_path / "rt")
    t0 = parse_time_text("2026-10-12 23:59:59")

    def fake(t):
        q = QuantityResult(key="power", ok=True, values={"p_total": 1.0, "q_total": 2.0, "s_total": 3.0},
                           units={}, window={"length_s_requested": 1.0}, t_ref=t)
        return MetricsResult(t_ref=t, fs=6400.0, f_used=50.0, f_source="test", quantities={"power": q})

    assert w.write(fake(t0)) == 1
    assert w.write(fake(t0 + 2.0)) == 1          # 跨到次日 00:00:01
    names = sorted(p.name for p in (tmp_path / "rt").glob("power_*.csv"))
    assert names == ["power_20261012.csv", "power_20261013.csv"], names
    w.close()


def test_engine_hot_update_rebuilds_writer_with_new_settings(csv_factory, tmp_path, monkeypatch):
    """热更新关掉 realtime_save 后不再写（撤销 update_config 里的重建 → 旧 writer 继续写）。"""
    rt = tmp_path / "rt"
    monkeypatch.setenv("ELEC_TOOL_REALTIME_DIR", str(rt))
    d = csv_factory(str(tmp_path / "a.csv"), duration_s=3.0)
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 1280
    eng = LiveEngine(cfg.validate())
    it = eng.run()
    next(it)                                     # 至少写了 1 行
    n_before = sum(eng.writer.rows_written.values())
    assert n_before >= 1
    cfg2 = AppConfig.from_dict(cfg.to_dict())
    cfg2.output.realtime_save = False
    eng.update_config(cfg2)
    for _ in it:
        pass
    assert eng.writer.enabled is False and sum(eng.writer.rows_written.values()) == 0
    total_rows = sum(len(_rows(p)) - 1 for p in rt.glob("*.csv"))
    assert total_rows == n_before


# ===================================================================== R7-2 播放起点

def test_play_start_modes_enum_and_validation():
    assert PLAY_START_MODES == ("begin", "row", "seconds", "percent", "time")
    assert parse_play_start("begin", "") is None
    assert parse_play_start("row", "120001") == 120001
    assert parse_play_start("seconds", "30") == 30.0
    assert parse_play_start("percent", "50%") == 50.0
    assert parse_play_start("time", "08:00:00") == ("tod", 8 * 3600.0)
    assert parse_play_start("time", "08:00:30.5") == ("tod", 8 * 3600.0 + 30.5)
    kind, v = parse_play_start("time", "2026-10-12 08:00:00")
    assert kind == "abs" and v == pytest.approx(parse_time_text("2026-10-12 08:00:00"))
    for mode, bad in [("row", "0"), ("row", "abc"), ("seconds", "-1"), ("percent", "101"), ("time", "昨天"), ("row", "")]:
        with pytest.raises(ConfigError):
            parse_play_start(mode, bad)
    cfg = AppConfig()
    cfg.source.play_start_mode = "row"
    cfg.source.play_start_value = "abc"
    with pytest.raises(ConfigError, match="播放起点"):
        cfg.validate()                           # 保存配置时就报，而不是启动后
    cfg.source.play_start_mode = "later"
    with pytest.raises(ConfigError, match="play_start_mode"):
        cfg.validate()


def _play(cfg, mode, value):
    cfg.source.play_start_mode, cfg.source.play_start_value = mode, value
    src = create_source(cfg.validate())
    src.open()
    blocks = []
    while True:
        b = src.read()
        if b is None:
            break
        blocks.append(b)
    n = sum(b.n for b in blocks)
    return n, (blocks[0].t[0] if blocks else None), src


def test_play_start_row_seconds_percent(csv_factory, tmp_path):
    """row/seconds 精确到行；percent 按字节对齐到行首（撤销 _seek_rows → 全量 19200）。"""
    d = csv_factory(str(tmp_path / "p.csv"), duration_s=3.0)
    total = len(d["t"])
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 640
    n, t0, _ = _play(cfg, "begin", "")
    assert n == total and t0 == pytest.approx(d["t"][0])
    n, t0, src = _play(cfg, "row", "6401")
    assert n == total - 6400 and t0 == pytest.approx(d["t"][6400])
    assert src.info()["play_seek"] == {"mode": "row", "skipped_rows": 6400, "reached_eof": False}
    assert any("播放起点" in s and "实际跳过 6400 行" in s for s in src.info()["notes"])
    n, t0, _ = _play(cfg, "seconds", "1.5")
    assert n == total - 9600 and t0 == pytest.approx(d["t"][9600])
    n, t0, src = _play(cfg, "percent", "50")
    assert abs(n - total / 2) <= 2 and src.info()["play_seek"]["mode"] == "percent"
    assert src.info()["play_seek"]["start_byte"] > 0
    # percent 对齐到行首：第一块首样本必须是文件里真实存在的某一行（时标恰好落在采样栅格上）
    k = round((t0 - d["t"][0]) * FS)
    assert t0 == pytest.approx(d["t"][k], abs=1e-6)
    n, _, _ = _play(cfg, "percent", "0")
    assert n == total


def test_play_start_time_absolute_and_time_of_day(csv_factory, tmp_path):
    """time：完整时间 → 与文件 epoch 比较；只填 HH:MM:SS → 与当天时刻比较（撤销 _seek_time → 全量）。"""
    d = csv_factory(str(tmp_path / "p.csv"), duration_s=3.0)
    total = len(d["t"])
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 640
    target = d["t"][0] + 1.0
    txt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(target)) + ".%03d" % int((target % 1) * 1000)
    n, t0, src = _play(cfg, "time", txt)
    assert abs(n - (total - 6400)) <= 1 and t0 >= target - 1e-6 and t0 - target < 1 / FS + 1e-6
    assert src.info()["play_seek"]["start_t"] == pytest.approx(t0)
    # 只填时刻（HH:MM:SS，取整秒，确保落在文件范围内）
    tod_target = d["t"][0] + 2.0
    lt = time.localtime(tod_target)
    n2, t02, _ = _play(cfg, "time", f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}")
    assert 0 < n2 <= total - 6400 + 1
    assert time.localtime(t02).tm_sec == lt.tm_sec


def test_play_start_time_on_user_clock_format(csv_factory, tmp_path):
    """用户 0/00/00 写法 + 只填时刻：00:12:41 → 跳过前 1 s（6400 行）。"""
    d = csv_factory(str(tmp_path / "c.csv"), duration_s=3.0, header=[], ts_mode="clock")
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 640
    first = Path(d["path"]).read_text().splitlines()[0].split(",")[0]
    m = re.match(r"0/00/00 (\d{2}):(\d{2}):(\d{2})", first)
    assert m, first
    h, mi, s = (int(x) for x in m.groups())
    target = f"{h:02d}:{mi:02d}:{s + 1:02d}"
    n, t0, src = _play(cfg, "time", target)
    assert n == len(d["t"]) - 6400, (n, target)
    import time as _time
    assert t0 == pytest.approx(h * 3600 + mi * 60 + s + 1 - _time.localtime().tm_gmtoff, abs=1e-3)   # v0.10：无日期时标按本地时间解释


def test_play_start_beyond_eof_raises_diagnosable_error(csv_factory, tmp_path):
    """起点超出文件 → ParseError 带「播放起点超出文件范围」（撤销 → 静默跑出 0 样本）。"""
    d = csv_factory(str(tmp_path / "p.csv"), duration_s=1.0)
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path = "csv_file", d["path"]
    for mode, v in [("row", "99999999"), ("seconds", "999"), ("time", "2099-01-01 00:00:00")]:
        cfg.source.play_start_mode, cfg.source.play_start_value = mode, v
        src = create_source(cfg.validate())
        src.open()
        with pytest.raises(ParseError, match="播放起点超出文件范围"):
            src.read()


def test_play_start_with_custom_time_counts_from_played_rows(csv_factory, tmp_path):
    """播放起点 + 自定义时间：时间轴从**起点处**的样本开始等间隔推算（起始留空＝起点行的文件时标）。"""
    d = csv_factory(str(tmp_path / "p.csv"), duration_s=2.0)
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 640
    cfg.source.custom_time = True
    n, t0, src = _play(cfg, "row", "6401")
    assert n == len(d["t"]) - 6400
    assert t0 == pytest.approx(d["t"][6400]) and src.info()["custom_time_start_source"] == "文件第 1 条数据时间"


def test_cli_play_from_flag(csv_factory, tmp_path):
    """CLI --play-from sec:2 → 摄入样本 = 总数 − 12800；--realtime-dir 指到 tmp 并写出文件；非法写法退出码非 0。"""
    d = csv_factory(str(tmp_path / "cli.csv"), duration_s=3.0)
    rt = tmp_path / "rt"
    cmd = [sys.executable, str(ROOT / "cli.py"), "compute", "--file", d["path"], "--play-from", "sec:2",
           "--realtime-dir", str(rt), "--format", "json"]
    env = dict(os.environ)
    env.pop("ELEC_TOOL_REALTIME_DIR", None)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), env=env, timeout=120)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "跳过开头 2 s" in r.stdout and "实际跳过 12800 行" in r.stdout and "实时落盘" in r.stdout
    assert list(rt.glob("*.csv")), "CLI 未写出实时落盘文件"
    r2 = subprocess.run(cmd[:-4] + ["--play-from", "nonsense", "--realtime-save", "off", "--format", "json"],
                        capture_output=True, text=True, cwd=str(ROOT), env=env, timeout=60)
    assert r2.returncode != 0 and "play-from" in (r2.stdout + r2.stderr)


# ===================================================================== Web 层

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    cfg_dir = tmp_path_factory.mktemp("r7cfg")
    cfg_path = cfg_dir / "cfg.json"
    shutil.copy(ROOT / "configs" / "default.json", cfg_path)
    rt_dir = tmp_path_factory.mktemp("r7rt")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(cfg_path))
    mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "1")
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(rt_dir))
    import app.server as srv
    with TestClient(srv.app) as c:
        c.rt_dir = rt_dir                # type: ignore[attr-defined]
        yield c
    mp.undo()


def _wait_finished(client, deadline_s=30.0):
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        st = client.get("/api/state").json()
        if st.get("finished") or st.get("error"):
            break
        time.sleep(0.05)
    time.sleep(0.4)                              # finished 后运行线程还会 flush_all 一次
    return client.get("/api/state").json()


def test_web_start_whitelists_play_start_and_reports_seek(client, csv_factory, tmp_path):
    """/api/engine/start 放行 play_start_mode/value（撤销白名单 → 全量摄入）；source 信息含 play_seek。"""
    d = csv_factory(str(tmp_path / "w.csv"), duration_s=3.0)
    total = len(d["t"])
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "block_samples": 1280,
                                               "play_start_mode": "row", "play_start_value": "6401"})
    assert r.status_code == 200, r.text
    assert r.json()["config"]["source"]["play_start_mode"] == "row"
    st = _wait_finished(client)
    assert not st.get("error"), st.get("error")
    assert st["engine"]["samples_in"] == total - 6400
    assert st["source"]["play_seek"]["skipped_rows"] == 6400
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "play_start_mode": "row", "play_start_value": "x"})
    assert r.status_code == 400 and "播放起点" in r.json()["error"]
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "play_start_mode": "time", "play_start_value": "23:59:59"})
    assert r.status_code == 200
    st = _wait_finished(client)
    assert "播放起点超出文件范围" in (st.get("error") or ""), st.get("error")


def test_web_realtime_endpoint_and_toggle(client, csv_factory, tmp_path):
    """GET /api/realtime 列出文件与行数；PUT realtime_save=false 后不再写（撤销热更新重建 → 行数继续增长）。"""
    d = csv_factory(str(tmp_path / "w.csv"), duration_s=2.0)
    client.put("/api/config", json={"output": {"realtime_save": True, "curve_save": {k: True for k in CURVE_KEYS}}})
    client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "block_samples": 1280,
                                           "play_start_mode": "begin"})
    _wait_finished(client)
    rt = client.get("/api/realtime").json()
    assert rt["enabled"] is True and rt["rows_written"]["voltage"] >= 1
    assert {re.sub(r"_\d{8}\.csv$", "", f["name"]) for f in rt["dir_files"]} == set(CURVE_KEYS)
    vfile = next(Path(rt["dir"]).glob("voltage_*.csv"))      # 目录以服务端回显为准（autouse 夹具按用例改写 env）
    n1 = len(_rows(vfile)) - 1
    assert n1 == rt["rows_written"]["voltage"]
    r = client.put("/api/config", json={"output": {"realtime_save": False}})
    assert r.status_code == 200 and r.json()["config"]["output"]["realtime_save"] is False
    client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "block_samples": 1280})
    _wait_finished(client)
    assert len(_rows(vfile)) - 1 == n1
    assert client.get("/api/realtime").json()["enabled"] is False
    client.put("/api/config", json={"output": {"realtime_save": True}})


def test_web_openapi_has_realtime_endpoint(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/realtime" in paths


# ===================================================================== R7-3 前端契约

def test_frontend_play_start_select_matches_backend_modes():
    """下拉框选项 == PLAY_START_MODES（撤销 → 选了后端不认）；取值框存在且随模式联动。"""
    m = re.search(r'<select id="src-playmode"[^>]*>(.*?)</select>', INDEX, re.S)
    assert m, "index.html 缺少 #src-playmode"
    opts = re.findall(r'value="([^"]+)"', m.group(1))
    assert opts == list(PLAY_START_MODES), opts
    assert 'id="src-playvalue"' in INDEX
    assert "'src-playmode': kind === 'csv_file'" in APP_JS
    assert "'src-playvalue': kind === 'csv_file' && $('#src-playmode').value !== 'begin'" in APP_JS
    assert "p.play_start_mode = $('#src-playmode').value" in APP_JS
    assert "$('#src-playmode').addEventListener('change'" in APP_JS
    for mode in PLAY_START_MODES:
        assert re.search(rf"\b{mode}: '", APP_JS.split("const PLAY_PLACEHOLDER")[1].split("};")[0]), f"缺 {mode} 的占位说明"


def test_frontend_realtime_panel_wired():
    for el in ("rt-enable", "rt-dir", "btn-rt-save", "btn-rt-refresh", "rt-out"):
        assert f'id="{el}"' in INDEX, el
    assert "api('/api/realtime')" in APP_JS
    assert "realtime_save: on" in APP_JS
    assert "$('#btn-rt-save').addEventListener('click', saveRealtime)" in APP_JS
    assert "!S.rtDirty" in APP_JS            # 用户编辑中不被实时推送覆盖


def test_frontend_hover_tooltip_contract():
    """drawLine 必须：挂 __chart、绑定 mousemove/mouseleave 一次、重绘末尾叠加悬停（撤销任一 → 悬停失效或被刷新抹掉）。"""
    body = APP_JS.split("function drawLine(")[1].split("\nfunction drawBars(")[0]
    assert "bindHover(cv)" in body and "cv.__redraw = () => drawLine(cv, series, opt)" in body
    assert "cv.__chart = { ctx, w, h, pad, pts, xmin, xmax, ymin, ymax, X, Y, opt }" in body
    assert body.rstrip().endswith("drawHover(cv);\n}")
    assert "cv.addEventListener('mousemove'" in APP_JS and "cv.addEventListener('mouseleave'" in APP_JS
    assert "if (cv.__hoverBound) return;" in APP_JS
    # 趋势图的提示用完整时刻（含毫秒），而不是刻度上的 HH:MM:SS
    assert APP_JS.count("fmtTip: x => ts(x + ") == 9                      # 6 条原趋势 + R9 的 TIHD / 直流趋势 + R12 负荷辨识周波窗
    assert "fmtTip: x => x.toFixed(2) + ' Hz'" in APP_JS
    # 最近点查找：有序二分
    assert "function nearestIdx(data, x)" in APP_JS and "while (hi - lo > 1)" in APP_JS


def test_ws_pushes_state_periodically_during_continuous_playback(client, csv_factory, tmp_path):
    """F-23（用户回报）：离线文件播放时 result 连续不断，旧实现只在队列空闲 1s 才发 state，
    顶栏「样本」/「数据源状态」汇总冻结在启动瞬间、需手动刷新。要求：result 流中每 ~1s 必有 state，
    且其中 engine.samples_in 单调增长。"""
    d = csv_factory(str(tmp_path / "ws.csv"), duration_s=60.0)     # 离线全速播放，足够跑满 3s 以上
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        r = client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "block_samples": 640})
        assert r.json().get("ok"), r.json()
        t0 = time.time(); kinds = []; samples = []
        while time.time() - t0 < 3.2:
            m = ws.receive_json()
            kinds.append(m["type"])
            if m["type"] == "state" and (m["data"].get("engine") or {}).get("running"):
                samples.append(m["data"]["engine"]["samples_in"])
            if m["type"] == "state" and m["data"].get("finished"):
                break
    client.post("/api/engine/stop")
    assert kinds.count("result") >= 5, kinds[:20]                     # 的确是连续 result 流
    assert kinds.count("state") >= 2, (kinds.count("state"), kinds[:40])  # 流中仍定期有 state
    assert samples == sorted(samples) and samples[-1] > samples[0], samples
