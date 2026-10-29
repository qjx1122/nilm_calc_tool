"""第 9 轮：间谐波电气量、直流偏置电气量、事件检测（6 类）与 Web 层接入。

覆盖：
  - interharmonic_analysis：175 Hz 注入 → 落在第 3 间谐波组，组有效值/主导频率/相角/TIHD 精确；1 周波窗给出提示
  - dc_analysis / _q_dc：三相直流偏置与中性线直流、相对基波百分比
  - MetricsCalculator 新增两键：ok、曲线标量（TIHD_U/I、Ua_dc…）、History 列
  - EventDetector：基波/谐波/间谐波/频率/ROCOF/功率振荡 6 类的开始、峰值、复归（含频率绝对滞回带、阈值热改后复归）、
    PT/CT 折算、CSV 落盘（start/end 各一行）、clear
  - Web：/api/events、/api/events/clear、PUT /api/config events 热生效、/api/history/{interharmonic,dc}、前端导航/容器
"""
from __future__ import annotations

import csv
import math
import os
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from elec_tool.analysis.harmonic import dc_analysis, interharmonic_analysis
from elec_tool.blocks import SampleBlock
from elec_tool.config import CURVE_KEYS, QUANTITY_KEYS, AppConfig, EventConfig, ConfigError
from elec_tool.events import EVENT_TYPES, EventDetector
from elec_tool.metrics import MetricsCalculator, curve_record

ROOT = Path(__file__).resolve().parents[1]
FS = 6400.0
T0 = 1.79e9


def _blk(t0: float, f: float = 50.0, uamp: float = 57.7, iamp: float = 5.0, ih_u: float = 0.0, ih_f: float = 175.0,
         h5_i: float = 0.0, dc_u=(0, 0, 0), dc_i=(0, 0, 0), dur: float = 1.0, pmod: float = 0.0) -> SampleBlock:
    t = np.arange(int(FS * dur)) / FS
    w = 2 * np.pi * f * t
    u = np.array([uamp * np.sqrt(2) * np.sin(w - k * 2 * np.pi / 3) + ih_u * np.sqrt(2) * np.cos(2 * np.pi * ih_f * t + 0.3) + dc_u[k]
                  for k in range(3)])
    i = np.array([iamp * (1 + pmod) * np.sqrt(2) * np.sin(w - k * 2 * np.pi / 3 - 0.3) + h5_i * np.sqrt(2) * np.sin(5 * w) + dc_i[k]
                  for k in range(3)])
    return SampleBlock(t=t0 + t, u=u, i=i, source="test")


def _cfg(**ev) -> AppConfig:
    cfg = AppConfig()
    cfg.sampling.adaptive_freq = True
    cfg.transform.enabled = False
    for k, v in ev.items():
        setattr(cfg.events, k, v)
    return cfg.validate()


# --------------------------------------------------------------------- 配置

def test_config_has_new_quantities_and_event_config():
    assert QUANTITY_KEYS.index("interharmonic") > QUANTITY_KEYS.index("harmonic")
    assert "dc" in QUANTITY_KEYS and "interharmonic" in CURVE_KEYS and "dc" in CURVE_KEYS
    cfg = AppConfig().validate()
    assert cfg.windows["interharmonic"].length_s == pytest.approx(0.2)        # IEC 61000-4-7：10 周波
    assert cfg.windows["dc"].remove_dc is False                                # 直流量当然不能去直流
    d = cfg.to_dict()
    assert d["events"]["f_high"] == 50.5 and d["events"]["limits_secondary"] is True
    # 旧配置缺 interharmonic/dc 窗与 events 段 → 用默认补齐（向后兼容）
    old = {k: v for k, v in d.items() if k != "events"}
    old["windows"] = {k: v for k, v in d["windows"].items() if k not in ("interharmonic", "dc")}
    cfg2 = AppConfig.from_dict(old).validate()
    assert set(cfg2.windows) == set(QUANTITY_KEYS) and cfg2.events.rocof_limit == 1.0
    with pytest.raises(ConfigError):
        EventConfig(f_low=51, f_high=50).validate()
    with pytest.raises(ConfigError):
        EventConfig(hysteresis=1.2).validate()


# --------------------------------------------------------------------- 算法

def test_interharmonic_groups_exact():
    fs, f = FS, 50.0
    t = np.arange(int(fs * 0.2)) / fs
    x = 100 * np.sqrt(2) * np.sin(2 * np.pi * f * t) + 2 * np.sqrt(2) * np.cos(2 * np.pi * 175 * t + 0.3) + 1.5
    r = interharmonic_analysis(x, fs, f, 50, n_cycles=10)
    assert r["freq_resolution_hz"] == pytest.approx(5.0) and r["n_bins_per_group"] == 9 and r["n_groups"] == 50
    g3 = r["groups"][3]
    assert g3["f_lo"] == 150 and g3["f_hi"] == 200
    assert g3["rms"] == pytest.approx(2.0, abs=1e-9)                     # 组有效值＝注入 RMS
    assert g3["subgroup_rms"] == pytest.approx(2.0, abs=1e-9)            # 175 Hz 不在边缘 bin，子组同值
    assert g3["dom_freq_hz"] == pytest.approx(175.0)
    assert g3["dom_angle_deg"] == pytest.approx(math.degrees(0.3), abs=1e-6)
    assert g3["pct"] == pytest.approx(2.0, abs=1e-9)
    assert r["tihd_pct"] == pytest.approx(2.0, abs=1e-6)
    assert r["max_group"]["h"] == 3 and r["top"][0]["h"] == 3
    others = [g["rms"] for g in r["groups"] if g["h"] != 3]
    assert max(others) < 1e-9                                            # 其余组为 0（无泄漏；直流已去）
    # 1 周波窗：没有可分辨的间谐波 bin → 全 0 + 提示
    r1 = interharmonic_analysis(x[: int(fs / f)], fs, f, 50, n_cycles=1)
    assert r1["n_bins_per_group"] == 0 and r1["tihd_pct"] == 0 and any("1 个周波" in n for n in r1["notes"])


def test_dc_analysis_exact():
    t = np.arange(int(FS)) / FS
    x = 57.7 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t) + 0.3 * np.sqrt(2) * np.sin(2 * np.pi * 250 * t) + 1.25
    r = dc_analysis(x, FS, 50.0, 57.7, 50)
    assert r["dc"] == pytest.approx(1.25, abs=1e-9)
    assert r["dc_pct"] == pytest.approx(100 * 1.25 / 57.7, rel=1e-9)
    assert r["n_cycles"] == 50 and max(abs(v - 1.25) for v in r["per_cycle"]) < 1e-9
    assert r["per_cycle_std"] < 1e-9


def test_metrics_new_quantities_and_curve_scalars():
    cfg = _cfg()
    calc = MetricsCalculator(cfg)
    r = calc.compute(_blk(T0, ih_u=0.5, dc_u=(0.3, -0.2, 0.1), dc_i=(0.1, 0.2, 0.3)))
    qi, qd = r.quantities["interharmonic"], r.quantities["dc"]
    assert qi.ok and qd.ok
    assert qi.values["max_group_u"]["h"] == 3 and qi.values["max_group_u"]["dom_freq_hz"] == pytest.approx(175.0)
    assert qi.values["tihd_u_worst_pct"] == pytest.approx(100 * 0.5 / 57.7, rel=1e-6)
    assert qi.values["tihd_i_worst_pct"] < 1e-6
    assert qd.values["u_dc"]["A"] == pytest.approx(0.3, abs=1e-9) and qd.values["u_dc"]["B"] == pytest.approx(-0.2, abs=1e-9)
    assert qd.values["in_dc"] == pytest.approx(0.6, abs=1e-9)
    assert qd.values["i_dc_pct"]["C"] == pytest.approx(100 * 0.3 / 5.0, rel=1e-6)
    ci = curve_record(r, "interharmonic", qi); cd = curve_record(r, "dc", qd)
    assert set(ci) >= {"TIHD_U", "TIHD_I", "IHmax_U_pct", "IHmax_I_pct"}
    assert set(cd) >= {"Ua_dc", "Ub_dc", "Uc_dc", "Ia_dc", "Ib_dc", "Ic_dc", "In_dc"}
    assert calc.history.count("dc") == 1 and calc.history.count("interharmonic") == 1
    import json; json.dumps(r.to_dict())                                   # 可序列化（WS/REST）


# --------------------------------------------------------------------- 事件检测

def _run(det, calc, blocks):
    out = []
    for b in blocks:
        out += det.process(calc.compute(b))
    return out


def test_events_fundamental_harmonic_interharmonic_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_EVENTS_DIR", str(tmp_path / "ev"))
    cfg = _cfg()
    det, calc = EventDetector(cfg), MetricsCalculator(cfg)
    ch = _run(det, calc, [
        _blk(T0),                                              # 正常
        _blk(T0 + 1, uamp=70, ih_u=2.0, h5_i=0.6),             # U1 121%、间谐波 2.857%、HR5=12%/THD_I=12%
        _blk(T0 + 2, uamp=72, ih_u=2.0, h5_i=0.6),             # 持续：峰值更新
        _blk(T0 + 3),                                          # 全部复归
    ])
    started = [e for e in ch if e["status"] == "active"]
    ended = [e for e in ch if e["status"] == "ended"]
    types = {e["type"] for e in started}
    assert types == {"fund_phasor", "harm_phasor", "interharm"}
    u1a = next(e for e in ended if e["subject"] == "U1-A-high")
    assert u1a["start_t"] == pytest.approx(T0 + 1 + 0.5, abs=0.6)         # 数据时间（窗中心/末，容差 1 窗）
    assert u1a["value_start"] == pytest.approx(70, rel=1e-3) and u1a["value_peak"] == pytest.approx(72, rel=1e-3)
    assert u1a["limit"] == pytest.approx(57.74 * 1.1) and u1a["duration_s"] == pytest.approx(2.0, abs=0.01)
    assert {e["subject"] for e in started if e["type"] == "interharm"} == {f"IH_U-{p}-g3" for p in "ABC"}
    assert "175.0 Hz" in next(e for e in started if e["type"] == "interharm")["detail"]
    hr = {e["subject"] for e in started if e["type"] == "harm_phasor"}
    assert hr == {f"HR_I-{p}-h5" for p in "ABC"} | {f"THD_I-{p}" for p in "ABC"}
    assert len(ended) == len(started) and not det.list(active_only=True)
    s = det.summary()
    assert s["counts"]["fund_phasor"] == 3 and s["counts"]["harm_phasor"] == 6 and s["counts"]["interharm"] == 3
    # CSV：start/end 各一行，UTF-8-BOM，文件名按数据日期
    files = list((tmp_path / "ev").glob("events_*.csv"))
    assert len(files) == 1 and re.fullmatch(r"events_\d{8}\.csv", files[0].name)
    rows = list(csv.DictReader(open(files[0], encoding="utf-8-sig")))
    assert len(rows) == 2 * len(started)
    assert {r["status"] for r in rows} == {"start", "end"}
    assert all(r["start_time"] and r["type_name"] for r in rows)
    # clear
    assert det.clear() == len(started) and det.summary()["total"] == 0


def test_events_freq_and_rocof_with_absolute_hysteresis():
    cfg = _cfg()
    det, calc = EventDetector(cfg), MetricsCalculator(cfg)
    ch = _run(det, calc, [_blk(T0, 50.0), _blk(T0 + 1, 50.8), _blk(T0 + 2, 52.0), _blk(T0 + 3, 50.0), _blk(T0 + 4, 50.0)])
    fe = [e for e in ch if e["type"] == "freq"]
    ro = [e for e in ch if e["type"] == "rocof"]
    assert fe[0]["status"] == "active" and fe[0]["value_start"] == pytest.approx(50.8, abs=1e-3)
    # 50.8→52 为 1.2 Hz/s（>1）触发；52→50 为 −2 Hz/s 峰值；50→50 复归
    assert ro[0]["status"] == "active" and ro[0]["value_start"] == pytest.approx(1.2, abs=1e-3)
    assert ro[-1]["status"] == "ended" and ro[-1]["value_peak"] == pytest.approx(2.0, abs=1e-3)
    # 频率复归用绝对滞回带 (1−0.95)×(50.5−49.5)=0.05 Hz，而不是 50.5×0.95（那样永不复归）
    assert fe[-1]["status"] == "ended" and fe[-1]["band"] == pytest.approx(0.05)
    assert not det.list(active_only=True)


def test_events_release_after_limit_raised_and_missing_subject():
    cfg = _cfg()
    det, calc = EventDetector(cfg), MetricsCalculator(cfg)
    ch = _run(det, calc, [_blk(T0, h5_i=0.6)])
    assert any(e["subject"] == "HR_I-A-h5" for e in ch)
    cfg.events.hr_i_limit_pct = 20.0; cfg.events.thd_i_limit_pct = 20.0
    det.update_config(cfg)
    ch = _run(det, calc, [_blk(T0 + 1, h5_i=0.6)])                       # 值未变（12%）但阈值已抬到 20% → 结束
    assert ch and all(e["status"] == "ended" for e in ch) and not det.list(active_only=True)


def test_events_limits_scaled_by_pt_ct():
    from elec_tool.scaling import scale_block
    cfg = _cfg()
    cfg.transform.enabled = True; cfg.transform.pt_ratio = 100.0; cfg.transform.ct_ratio = 15.0   # v0.99.23：_cfg 的 enabled=False 已被 validate 折算为 1/1，这里显式设 100/15 → 一次值
    det, calc = EventDetector(cfg), MetricsCalculator(cfg)
    sc = lambda b: scale_block(b, cfg.transform)                           # 引擎在 _ingest 里做的折算
    ch = _run(det, calc, [sc(_blk(T0))])                                   # 57.7×100 V、5×15 A：正常，不应报
    assert not [e for e in ch if e["type"] == "fund_phasor"]
    s = det.summary()
    assert s["limit_scale"] == {"u": 100.0, "i": 15.0} and s["effective_limits"]["i1_high_a"] == pytest.approx(90.0)
    ch = _run(det, calc, [sc(_blk(T0 + 1, iamp=6.5))])                    # 97.5 A > 90 A
    assert {e["subject"] for e in ch} == {f"I1-{p}-high" for p in "ABC"}
    cfg.events.limits_secondary = False; det.update_config(cfg)            # 直接按一次值填：6 A 上限 → 立即超
    assert det.summary()["effective_limits"]["i1_high_a"] == 6.0


def test_events_power_oscillation():
    cfg = _cfg(osc_window_s=6.0, osc_min_points=6, osc_limit_pct=5.0)
    cfg.windows["power"].length_s = 0.5
    det, calc = EventDetector(cfg), MetricsCalculator(cfg)
    ch = []
    for k in range(16):                                                     # P 以 0.5 Hz、±10% 调制，步长 0.5 s
        ch += det.process(calc.compute(_blk(T0 + 0.5 * k, dur=0.5, pmod=0.10 * np.sin(2 * np.pi * 0.5 * 0.5 * k))))
    osc = [e for e in ch if e["type"] == "power_osc"]
    assert osc and osc[0]["status"] == "active"
    info = det.summary()["osc"]
    assert info["dom_freq_hz"] == pytest.approx(0.5, abs=0.15)
    assert 14 < info["amp_pp_pct"] < 26                                     # ±10% → 峰峰 20%（hann 泄漏/短窗容差）
    for k in range(16, 32):                                                 # 调制消失 → 复归
        ch += det.process(calc.compute(_blk(T0 + 0.5 * k, dur=0.5)))
    assert [e for e in ch if e["type"] == "power_osc"][-1]["status"] == "ended"


def test_events_disabled_and_nominal_freq_note():
    cfg = _cfg(enabled=False)
    det, calc = EventDetector(cfg), MetricsCalculator(cfg)
    assert _run(det, calc, [_blk(T0, uamp=80)]) == []
    cfg2 = _cfg(); cfg2.sampling.adaptive_freq = False
    assert any("adaptive_freq" in n for n in EventDetector(cfg2).summary()["notes"])


# --------------------------------------------------------------------- 引擎 + Web

def test_engine_runs_detector_and_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_EVENTS_DIR", str(tmp_path / "ev"))
    from elec_tool.engine import LiveEngine
    from elec_tool.sources.base import DataSource

    class Src(DataSource):
        kind = "test"
        def __init__(self):
            self.k = 0
        def open(self): pass
        def close(self): pass
        def read(self):
            if self.k >= 3:
                return None
            b = _blk(T0 + self.k, uamp=70 if self.k == 1 else 57.7)
            self.k += 1
            return b
        def exhausted(self):
            return self.k >= 3
        def info(self):
            return {"kind": "test"}

    cfg = _cfg()
    eng = LiveEngine(cfg, source=Src())
    pushed = []
    eng.on_event = lambda ch: pushed.extend(ch)
    eng.start()
    for _ in range(6):
        eng.poll_once()
    eng.flush_all(); eng.stop()
    st = eng.state.to_dict()
    assert st["events_total"] == 3 and {e["subject"] for e in pushed} >= {"U1-A-high"}
    assert eng.info()["events"]["counts"]["fund_phasor"] == 3


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    cfg_dir = tmp_path_factory.mktemp("r9cfg")
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
        yield c
    mp.undo()


def test_web_events_api_and_new_quantities(client):
    import time
    client.post("/api/engine/stop"); client.post("/api/events/clear")        # RUNNER 为进程级单例：清掉其他模块留下的事件
    d = client.get("/api/events").json()
    assert d["ok"] and d["summary"]["types"] == EVENT_TYPES and d["events"] == []
    # 事件阈值热更新 + 未知字段/非法值
    r = client.put("/api/config", json={"events": {"thd_u_limit_pct": 3.0, "f_high": 50.2}})
    assert r.status_code == 200 and r.json()["config"]["events"]["thd_u_limit_pct"] == 3.0
    assert client.put("/api/config", json={"events": {"f_low": 60}}).status_code == 400
    # 跑仿真源（含 3/5 次谐波）→ 新量有结果、谐波事件出现
    r = client.post("/api/engine/start", json={"source": {"kind": "simulator", "duration_s": 3.0}})
    assert r.status_code == 200, r.text
    deadline = time.time() + 15
    while time.time() < deadline:
        res = client.get("/api/result?full=true")
        if res.status_code == 200 and {"interharmonic", "dc"} <= set(res.json()["quantities"]):
            break
        time.sleep(0.3)
    qs = res.json()["quantities"]
    assert qs["interharmonic"]["ok"] and qs["dc"]["ok"], (qs["interharmonic"].get("error"), qs["dc"].get("error"))
    assert "tihd_u_worst_pct" in qs["interharmonic"]["values"] and "in_dc" in qs["dc"]["values"]
    time.sleep(1.5)
    d = client.get("/api/events?limit=50").json()
    assert d["summary"]["total"] >= 1
    assert all(set(e) >= {"id", "type", "type_name", "subject", "start_t", "value_peak", "limit", "active"} for e in d["events"])
    one = d["events"][0]["type"]
    assert all(e["type"] == one for e in client.get(f"/api/events?types={one}").json()["events"])
    act = client.get("/api/events?active=1").json()["events"]
    assert all(e["active"] for e in act)
    client.post("/api/engine/stop")
    for k in ("interharmonic", "dc"):
        h = client.get(f"/api/history/{k}?max_points=50").json()
        assert h["quantity"] == k and h["count"] >= 1
    assert "dc" in client.get("/api/state").json()["quantities"]
    r = client.post("/api/events/clear").json()
    assert r["ok"] and r["summary"]["total"] == 0 and client.get("/api/events").json()["events"] == []


def test_frontend_has_new_views_and_wiring():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    for v in ("interharmonic", "dc", "events"):
        assert f'data-view="{v}"' in html and f'id="view-{v}"' in html
    for i in ("ih-bar-u", "ih-table-i", "ih-trend", "dc-cards", "dc-trend", "ev-active", "ev-table", "ev-form", "btn-ev-save", "btn-ev-clear"):
        assert f'id="{i}"' in html, i
    boxes = re.findall(r'class="curve-save" data-curve="([a-z_]+)"(?! data-side="branch")', html)
    assert set(boxes) == set(CURVE_KEYS) and boxes.count("harmonic") == 2   # 总线侧每条曲线至少一个（v0.28 谐波页 THD 趋势再加一个，与总览共用同一保存开关）；分路侧（data-side=branch）另计
    for f in ("renderInterharmonic", "renderDC", "renderEvents", "saveEventConfig", "onEventPush", "/api/events"):
        assert f in js
    assert "'interharmonic', 'dc'" in js                                    # CURVE_KEYS 同步
    # F-32：事件到达不再逐条弹 toast（事件多时刷屏）；只更新徽标 + 事件页
    body = js[js.index("function onEventPush"):]
    body = body[: body.index("\n}")]
    assert "toast(" not in body and "setEventBadge(" in body
    js_fields = set(re.findall(r"id=\"ev-([a-z0-9_]+)\"", html)) - {"enabled", "save", "filter", "only-active", "cards", "active",
                                                                     "table", "total", "form", "notes", "form-note"}
    assert js_fields <= set(EventConfig.__dataclass_fields__), js_fields - set(EventConfig.__dataclass_fields__)
