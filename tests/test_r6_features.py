"""第 6 轮四项功能的回归测试（2026-10-12 用户需求）：

  R6-1 离线 CSV 新时间戳格式 ``0/00/00 00:12:40.0000``（无日期、无表头、0.1ms 截断）
  R6-2 趋势曲线＝最近 24h（按数据时间保留；不足则全部；超量抽稀保峰谷）
  R6-3 每条曲线可分别配置「是否保存」，保存/下载时未勾选的曲线不输出
  R6-4 离线播放「自定义时间」：时间轴＝起始时间＋样本序号/fs，起始默认＝文件第 1 条数据时间

每个用例都写明「撤销对应修复会怎样失败」，保证测试真的在约束实现而不是陪跑。
"""

from __future__ import annotations

import math
import os
import re
import shutil
import time
from pathlib import Path

import numpy as np
import time as _time


def _tz_s() -> float:
    """本地时区偏移（秒），与 parsing.local_utc_offset_h 一致；沙盒 UTC 为 0。"""
    return float(_time.localtime().tm_gmtoff)

import pytest

from elec_tool.config import AppConfig, ConfigError, CURVE_KEYS, parse_time_text
from elec_tool.metrics import History
from elec_tool.sources import create_source
from elec_tool.sources.parsing import ParseError, parse_timestamps
from tests.conftest import FS

ROOT = Path(__file__).resolve().parents[1]

USER_LINES = [   # 用户原样给出的三行
    "0/00/00 00:12:40.0000,290.175751,0.014536,-294.450775,-0.663356,-86.006241,-0.007348",
    "0/00/00 00:12:40.0001,297.419373,0.0208,-287.001404,-0.759336,-101.524544,-0.005844",
    "0/00/00 00:12:40.0003,303.946503,0.02684,-278.860626,-0.85684,-116.798264,-0.002928",
]


# ===================================================================== R6-1 时间戳格式

def test_user_clock_format_parses_to_time_of_day():
    """撤销 _parse_slash_clock → ParseError「时间戳 '0/00/00 00:12:40.0000' 无法解析」。"""
    info = parse_timestamps([ln.split(",")[0] for ln in USER_LINES])
    assert info.mode == "clock_time"
    assert info.t[0] == pytest.approx(86400 + 12 * 60 + 40.0)  # 00:12:40 → 基准 1970-01-02 + 760 s（F-40）
    assert np.allclose(np.diff(info.t), [0.0001, 0.0002], atol=1e-9)
    assert any("无日期" in n for n in info.notes)


def test_user_clock_format_estimates_6400hz_despite_0p1ms_truncation(csv_factory, tmp_path):
    """0.1ms 截断 + 6400Hz（间隔 156.25µs）→ 单点间隔在 0.1/0.2ms 间跳动；线性拟合仍应给出 6400Hz。"""
    d = csv_factory(str(tmp_path / "clock.csv"), duration_s=1.0, header=[], ts_mode="clock")
    col = [ln.split(",")[0] for ln in Path(d["path"]).read_text().splitlines()]
    info = parse_timestamps(col)
    assert abs(info.fs_est - FS) / FS < 1e-4, info.fs_est
    assert not any("回退" in n or "无递增" in n for n in info.notes)


def test_clock_format_unwraps_midnight():
    """跨午夜 23:59:59.9999 → 00:00:00.0001 不应判为时标回退（撤销 _unwrap_midnight → diff 为 -86399.9998）。"""
    info = parse_timestamps(["0/00/00 23:59:59.9998", "0/00/00 23:59:59.9999", "0/00/00 00:00:00.0001"])
    assert np.all(np.diff(info.t) > 0)
    assert info.t[-1] - info.t[0] == pytest.approx(0.0003, abs=1e-9)
    assert not any("回退" in n for n in info.notes)


def test_slash_date_without_zero_padding_still_parses():
    info = parse_timestamps(["2026/1/5 8:03:07.5", "2026/1/5 8:03:07.6"])
    assert info.mode == "datetime"
    assert info.t[1] - info.t[0] == pytest.approx(0.1, abs=1e-6)


def test_headerless_user_file_runs_through_csv_source(tmp_path):
    """无表头 + 字符串时标：数据行不得被当表头，时间戳列不得记为「非数值单元格」。"""
    p = tmp_path / "u.csv"
    p.write_text("\n".join(USER_LINES * 10) + "\n", encoding="utf-8")
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", str(p), 1000
    src = create_source(cfg.validate())
    src.open()
    blk = src.read()
    assert blk is not None and blk.n == 30                      # 30 行全是数据
    assert blk.u[0, 0] == pytest.approx(290.175751)
    assert blk.i[2, 2] == pytest.approx(-0.002928)
    assert not any("非数值" in n for n in src.info()["notes"])


# ===================================================================== R6-4 自定义播放时间

def _write_clock_file(csv_factory, path, duration_s=1.0):
    return csv_factory(str(path), duration_s=duration_s, header=[], ts_mode="clock")


def _blocks(cfg):
    src = create_source(cfg.validate())
    src.open()
    out = []
    while True:
        b = src.read()
        if b is None:
            break
        out.append(b)
    return out, src


def test_custom_time_off_keeps_file_timestamps(csv_factory, tmp_path):
    d = _write_clock_file(csv_factory, tmp_path / "a.csv")
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 640
    blocks, src = _blocks(cfg)
    t = np.concatenate([b.t for b in blocks])
    # v0.10：无日期时标按本地时间解释（source.file_time_utc=False 默认）→ epoch = 当天秒 − 本地时区偏移
    assert t[0] == pytest.approx(86400.0 + float(d["t"][0]) % 86400.0 - _tz_s(), abs=1e-4)   # F-40：无日期基准 1970-01-02
    # 文件时标被 0.1ms 截断 → 间隔不是常数（这正是用户要「自定义时间」的原因）
    assert np.unique(np.round(np.diff(t), 5)).size > 1
    assert src.info()["custom_time"] is False


def test_custom_time_default_start_is_first_row_and_uniform(csv_factory, tmp_path):
    """撤销 _apply_custom_time → 时间轴仍是文件的截断时标，diff 不恒等于 1/fs。"""
    d = _write_clock_file(csv_factory, tmp_path / "b.csv")
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 640
    cfg.source.custom_time, cfg.source.custom_time_start = True, ""
    blocks, src = _blocks(cfg)
    t = np.concatenate([b.t for b in blocks])
    first_file_t = 86400.0 + float(d["t"][0]) % 86400.0 - _tz_s()
    assert t[0] == pytest.approx(math.floor(first_file_t * 10000) / 10000, abs=1e-9)   # 文件第 1 条（截断后）
    assert np.allclose(np.diff(t), 1.0 / FS, atol=1e-9)                                # 严格等间隔
    assert t[-1] - t[0] == pytest.approx((t.size - 1) / FS, abs=1e-7)                  # 跨块连续，不重置
    info = src.info()
    assert info["custom_time"] is True and info["custom_time_start_source"] == "文件第 1 条数据时间"
    assert any("自定义播放时间已启用" in n for n in info["notes"])


def test_custom_time_explicit_start_text_and_epoch(csv_factory, tmp_path):
    d = _write_clock_file(csv_factory, tmp_path / "c.csv", duration_s=0.5)
    for start, expect in (("2026-10-12 08:00:00", parse_time_text("2026-10-12 08:00:00")),
                          ("1791800000.5", 1791800000.5)):
        cfg = AppConfig()
        cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 640
        cfg.source.custom_time, cfg.source.custom_time_start = True, start
        blocks, src = _blocks(cfg)
        assert blocks[0].t[0] == pytest.approx(expect, abs=1e-6)
        assert blocks[-1].t[-1] == pytest.approx(expect + (sum(b.n for b in blocks) - 1) / FS, abs=1e-6)
        assert src.info()["custom_time_start_source"] == "配置起始时间"


def test_custom_time_bad_start_rejected_at_validate():
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path = "csv_file", "x.csv"
    cfg.source.custom_time, cfg.source.custom_time_start = True, "昨天早上"
    with pytest.raises(ConfigError, match="起始时间"):
        cfg.validate()
    cfg.source.custom_time = False                               # 未启用时不校验文本
    cfg.validate()


def test_cli_compute_custom_time_start_flag(csv_factory, tmp_path):
    import subprocess
    import sys
    d = _write_clock_file(csv_factory, tmp_path / "cli.csv", duration_s=1.2)
    r = subprocess.run([sys.executable, "cli.py", "compute", "--file", d["path"], "--quantities", "voltage",
                        "--custom-time-start", "2026-10-12 08:00:00", "--format", "table", "--limit", "1"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "2026-10-12 08:00:0" in r.stdout
    assert "自定义播放时间已启用" in r.stdout


# ===================================================================== R6-2 24h 历史

class _Q:
    def __init__(self, t, v):
        self.t_ref = t
        self.ok = True
        self.window = {"length_s_requested": 1.0}
        self.values = {"rms": {"A": v, "B": v + 1.0, "C": v + 2.0}}


class _R:
    f_used = 50.0

    def __init__(self, t, v):
        self.quantities = {"voltage": _Q(t, v)}


def test_history_keeps_only_last_24h_by_data_time():
    """30h、每秒 1 点 → 只应保留最近 24h（±5% 懒修剪余量）；撤销 _trim 的时间分支 → 保留全部 108000 点。"""
    h = History(hours=24.0, max_points=10**6)
    t0 = 1_700_000_000.0
    for k in range(30 * 3600):
        h.push(_R(t0 + k, 5000.0 + (k % 97)))
    a, b = h.span("voltage")
    assert 24.0 <= (b - a) / 3600.0 <= 24.0 * 1.06
    assert len(h.get("voltage", hours=24.0)) == 24 * 3600 + 1
    assert h.stats()["voltage"]["dropped"] > 0


def test_history_shorter_than_24h_keeps_everything():
    h = History(hours=24.0)
    for k in range(500):
        h.push(_R(1_700_000_000.0 + k * 0.2, 1.0))
    assert h.count("voltage") == 500
    assert len(h.get("voltage")) == 500


def test_history_max_points_is_memory_cap():
    h = History(hours=24.0, max_points=1000)
    for k in range(5000):
        h.push(_R(1_700_000_000.0 + k, 1.0))
    assert h.count("voltage") <= 1000 * 1.06


def test_history_decimation_keeps_extremes_and_last_point():
    h = History(hours=24.0)
    n = 20000
    for k in range(n):
        v = 100.0 + (50.0 if k == 12345 else 0.0) - (50.0 if k == 777 else 0.0)   # 一个尖峰、一个深谷
        h.push(_R(1_700_000_000.0 + k, v))
    pts = h.get("voltage", max_points=1500)
    assert len(pts) <= 1500 + 2
    vals = [p["Ua"] for p in pts]
    assert max(vals) == 150.0 and min(vals) == 50.0           # 峰谷保形
    assert pts[-1]["t"] == 1_700_000_000.0 + n - 1              # 最后一点永远保留
    assert len(h.get("voltage", n=400)) == 400                  # 旧接口 n 仍可用


def test_engine_hot_update_preserves_history(csv_factory, tmp_path):
    """撤销 engine.update_config 的 history 搬运 → 热更新后 count 归 0。"""
    from elec_tool.engine import LiveEngine
    d = csv_factory(str(tmp_path / "h.csv"), duration_s=3.0)
    cfg = AppConfig()
    cfg.source.kind, cfg.source.path, cfg.source.block_samples = "csv_file", d["path"], 1280
    eng = LiveEngine(cfg.validate())
    eng.start()
    for _ in range(40):
        eng.poll_once()
    before = eng.calc.history.count("voltage")
    assert before >= 2
    cfg2 = AppConfig.from_dict(cfg.to_dict())
    cfg2.output.curve_save["current"] = False
    eng.update_config(cfg2)
    assert eng.calc.history.count("voltage") == before
    assert eng.calc.history.hours == 24.0


# ===================================================================== R6-3 曲线保存配置 + Web 端到端

def test_output_config_curve_save_defaults_and_validation():
    cfg = AppConfig()
    assert cfg.output.curve_save == {k: True for k in CURVE_KEYS}
    assert cfg.output.history_hours == 24.0
    d = cfg.to_dict()
    d["output"]["curve_save"] = {"voltage": False}              # 只给一个键：其余补 True
    c2 = AppConfig.from_dict(d)
    assert c2.output.curve_save["voltage"] is False and c2.output.curve_save["harmonic"] is True
    d["output"]["curve_save"] = {"spectrum": True}              # 频谱不是趋势曲线
    with pytest.raises(ConfigError, match="curve_save"):
        AppConfig.from_dict(d)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    cfg_dir = tmp_path_factory.mktemp("r6cfg")
    cfg_path = cfg_dir / "cfg.json"
    shutil.copy(ROOT / "configs" / "default.json", cfg_path)
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(cfg_path))
    mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "1")
    import app.server as srv
    out_dir = tmp_path_factory.mktemp("r6out")
    with TestClient(srv.app) as c:
        # 导出目录指到 tmp：测试不往仓库 output/ 写文件
        c.put("/api/config", json={"output": {"export_dir": str(out_dir)}})
        c.cfg_path = cfg_path            # type: ignore[attr-defined]
        c.out_dir = out_dir              # type: ignore[attr-defined]
        yield c
    mp.undo()


def _wait_finished(client, deadline_s=30.0):
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        st = client.get("/api/state").json()
        if st.get("finished") or st.get("error"):
            break
        time.sleep(0.05)
    time.sleep(0.3)        # finished 置位后运行线程还要 flush_all 一次（收尾强算 + 入历史），等它做完再读计数
    return client.get("/api/state").json()


def test_web_probe_accepts_headerless_clock_file(client, tmp_path):
    p = tmp_path / "probe.csv"
    p.write_text("\n".join(USER_LINES * 50) + "\n", encoding="utf-8")
    d = client.get("/api/probe", params={"path": str(p)}).json()
    assert d["ok"] is True, d
    assert d["has_header"] is False and d["rows"] == 150        # 第一行是数据，不是表头
    assert d["ts_mode"] == "clock_time" and d["t_first_text"] == "0/00/00 00:12:40.0000"


def test_web_start_with_custom_time_and_history_window(client, csv_factory, tmp_path):
    d = csv_factory(str(tmp_path / "web.csv"), duration_s=3.0, header=[], ts_mode="clock")
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "block_samples": 1280,
                                               "custom_time": True, "custom_time_start": "2026-10-12 08:00:00"})
    assert r.status_code == 200, r.text
    assert r.json()["config"]["source"]["custom_time"] is True   # 白名单放行（撤销 → 回显 False）
    st = _wait_finished(client)
    assert not st.get("error"), st.get("error")
    src = st["source"]
    assert src["custom_time"] is True and src["custom_time_start_source"] == "配置起始时间"
    assert src["custom_time_start"] == pytest.approx(parse_time_text("2026-10-12 08:00:00"))
    assert st["history"]["voltage"]["count"] >= 2
    h = client.get("/api/history/voltage", params={"max_points": 1500}).json()
    assert h["hours"] == 24.0 and h["count"] == h["count_total"] >= 2 and h["decimated"] is False
    assert h["t_first"] >= parse_time_text("2026-10-12 08:00:00")
    assert {"t", "Ua", "Ub", "Uc"} <= set(h["points"][0])
    assert client.get("/api/history/voltage", params={"n": 1}).json()["count"] == 1   # 旧参数兼容


def test_web_curve_save_toggle_persists_and_keeps_history(client):
    before = client.get("/api/history/voltage").json()["count_total"]
    assert before >= 2
    r = client.put("/api/config", json={"output": {"curve_save": {"current": False, "harmonic": False}}})
    assert r.status_code == 200, r.text
    cs = client.get("/api/config").json()["output"]["curve_save"]
    assert cs["current"] is False and cs["harmonic"] is False and cs["voltage"] is True
    # 已结束的离线引擎做热更新 → 历史与结果都必须还在（撤销 set_cfg 修复 → count 变 0 / result 409）
    assert client.get("/api/history/voltage").json()["count_total"] == before
    assert client.get("/api/result").status_code == 200
    import json
    on_disk = json.loads(client.cfg_path.read_text(encoding="utf-8"))
    assert on_disk["output"]["curve_save"]["current"] is False  # 写入了配置文件


def test_web_curves_save_skips_unchecked(client):
    r = client.post("/api/curves/save", json={})
    assert r.status_code == 200, r.text
    d = r.json()
    saved = {f["quantity"] for f in d["files"]}
    assert saved == {"voltage", "power", "power_factor", "fundamental", "interharmonic", "dc"}   # R9：八条曲线
    assert set(d["skipped"]) == {"current", "harmonic"}
    out = Path(d["dir"]) if os.path.isabs(d["dir"]) else ROOT / d["dir"]
    assert out.is_relative_to(client.out_dir)                   # 写到了 export_dir，而不是仓库 output/
    files = sorted(p.name for p in out.glob("*.csv"))
    assert "current.csv" not in files and "voltage.csv" in files
    text = (out / "voltage.csv").read_text(encoding="utf-8-sig")
    head = text.splitlines()[0]
    assert head.startswith("t_epoch_s,time_local,quantity,") and ",Ua," in head
    assert re.search(r"\n\d+\.\d+,2026-10-12 08:00:0\d\.\d{3},voltage,", text)


def test_web_curves_export_respects_selection(client):
    assert client.get("/api/curves/export", params={"quantity": "current"}).status_code == 403
    r = client.get("/api/curves/export", params={"quantity": "voltage"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    merged = client.get("/api/curves/export").text
    kinds = {ln.split(",")[2] for ln in merged.splitlines()[1:] if ln}
    assert kinds == {"voltage", "power", "power_factor", "fundamental", "interharmonic", "dc"}
    client.put("/api/config", json={"output": {"curve_save": {k: False for k in CURVE_KEYS}}})
    assert client.post("/api/curves/save", json={}).status_code == 400
    client.put("/api/config", json={"output": {"curve_save": {k: True for k in CURVE_KEYS}}})


def test_web_openapi_has_curve_endpoints(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {"/api/curves/save", "/api/curves/export"} <= paths


# ===================================================================== 前端契约（静态）

HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
APPJS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
SERVER = (ROOT / "app/server.py").read_text(encoding="utf-8")


def test_frontend_has_custom_time_controls_wired():
    for el in ("src-customtime", "src-customstart"):
        assert f'id="{el}"' in HTML
    # v0.16：表单按前缀参数化，字段名 customtime / customstart 经 srcEl(pre, name) 取用
    assert "chk('customtime', src.custom_time)" in APPJS and "set('customstart', src.custom_time_start || '')" in APPJS
    assert "custom_time_start" in APPJS and '"custom_time", "custom_time_start"' in SERVER   # start 白名单


def test_frontend_has_one_save_checkbox_per_curve():
    boxes = re.findall(r'class="curve-save" data-curve="([a-z_]+)"(?! data-side="branch")', HTML)
    assert sorted(boxes) == sorted(CURVE_KEYS)                   # 总线侧每条趋势曲线各一个、不多不少（分路侧另计）
    assert 'id="curve-save-list"' in HTML and 'id="btn-save-curves"' in HTML
    assert "/api/curves/save" in APPJS and "curve_save" in APPJS


def test_frontend_requests_24h_history_not_fixed_400():
    assert "?n=400" not in APPJS
    assert "max_points=${HIST_MAX_POINTS}" in APPJS
