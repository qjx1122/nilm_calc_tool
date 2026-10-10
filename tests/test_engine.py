"""引擎与结果层测试：各量独立窗调度（需求⑥）、量纲、连续性检查、热更新、JSON 可序列化。"""

from __future__ import annotations

import copy
import json
import math
import os

import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, QUANTITY_KEYS, SourceConfig, WindowSpec
from elec_tool.engine import LiveEngine
from elec_tool.metrics import MetricsCalculator
from elec_tool.selftest import HarmSpec, build_signal, expected_values
from elec_tool.sources import CsvFileSource, SimulatorSource
from tests.conftest import CT, F_NOM, FS, PT, write_csv


def _engine_from_csv(base_cfg, path, block_samples=1280, windows=None):
    cfg = copy.deepcopy(base_cfg)
    cfg.source = SourceConfig(kind="csv_file", path=path, block_samples=block_samples)
    if windows:
        for k, v in windows.items():
            cfg.windows[k] = WindowSpec(length_s=v)
    cfg.validate()
    return LiveEngine(cfg)


def test_independent_window_scheduling(csv_factory, tmp_path, base_cfg):
    """需求⑥核心：谐波 0.2s 窗应比电压 1s 窗多出约 5 倍的结果。"""
    art = csv_factory(str(tmp_path / "sched.csv"), duration_s=5.0)
    eng = _engine_from_csv(base_cfg, art["path"], block_samples=640,
                           windows={"voltage": 1.0, "harmonic": 0.2, "spectrum": 2.0})
    n_res = 0
    for _ in eng.run():
        n_res += 1
    emits = eng.state.emits
    assert emits["harmonic"] >= 4 * emits["voltage"], emits
    assert emits["spectrum"] <= emits["voltage"], emits
    assert emits["voltage"] >= 4, emits
    assert eng.state.samples_in == art["t"].size
    assert eng.state.finished


def test_window_5s_changes_buffer_and_emits(csv_factory, tmp_path, base_cfg):
    """把电压窗设成 5s：缓冲容量必须随之变大，输出次数必须变少。"""
    art = csv_factory(str(tmp_path / "w5.csv"), duration_s=5.0)
    eng = _engine_from_csv(base_cfg, art["path"], block_samples=640, windows={"voltage": 5.0})
    assert eng.buffer.capacity >= int(5.0 * FS)
    res = list(eng.run())
    assert eng.state.emits["voltage"] <= 2
    assert res, "至少应有一次输出"
    vq = [r for r in res if "voltage" in r.quantities][-1].quantities["voltage"]
    assert vq.window["length_s_requested"] == 5.0
    assert vq.window["n_samples"] <= 5.0 * FS


def test_engine_applies_pt_ct(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "ptct.csv"), duration_s=1.2)
    eng = _engine_from_csv(base_cfg, art["path"])
    res = list(eng.run())[-1]
    exp = art["expected"]
    u_a = res.quantities["voltage"].values["rms"]["A"]
    assert u_a == pytest.approx(exp["u_rms_phase"], rel=2e-3)
    p = res.quantities["power"].values["p_total"]
    assert p == pytest.approx(exp["p_total"], rel=2e-3)
    assert res.meta["pt_ratio"] == PT and res.meta["ct_ratio"] == CT


def test_no_scale_option_uses_secondary(csv_factory, tmp_path, base_cfg):
    cfg = copy.deepcopy(base_cfg)
    cfg.transform.enabled = False
    art = csv_factory(str(tmp_path / "noscale.csv"), duration_s=1.2)
    cfg.source = SourceConfig(kind="csv_file", path=art["path"], block_samples=6400)
    cfg.validate()
    res = list(LiveEngine(cfg).run())[-1]
    exp_sec = expected_values(art["specs"], cfg.transform, FS, F_NOM)
    assert res.quantities["voltage"].values["rms"]["A"] == pytest.approx(exp_sec["u_rms_phase"], rel=2e-3)


def test_gap_detection(tmp_path, base_cfg):
    """数据时间跳变必须被检出（丢点会让窗结果失真，不能静默）。"""
    specs = [HarmSpec(1, 57.735, 5.0, 30.0)]
    t1, u1, i1 = build_signal(specs, FS, 0.5, F_NOM, t0=1_760_000_000.0)
    t2, u2, i2 = build_signal(specs, FS, 0.5, F_NOM, t0=t1[-1] + 0.37)      # 跳变 0.37s
    t = np.concatenate([t1, t2]); u = np.concatenate([u1, u2], axis=1); i = np.concatenate([i1, i2], axis=1)
    p = write_csv(str(tmp_path / "gap.csv"), t, u, i)
    eng = _engine_from_csv(base_cfg, p, block_samples=640)
    list(eng.run())
    assert eng.state.gaps, "未检出时间跳变"
    assert eng.state.gaps[0]["gap_s"] == pytest.approx(0.37, abs=0.01)
    assert any("跳变" in n for n in eng.state.notes)


def test_hot_config_update(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "hot.csv"), duration_s=2.0)
    eng = _engine_from_csv(base_cfg, art["path"], block_samples=640)
    eng.start()
    for _ in range(5):
        eng.poll_once()
    fill_before = len(eng.buffer)
    new_cfg = copy.deepcopy(eng.cfg)
    new_cfg.windows["voltage"] = WindowSpec(length_s=3.0)
    new_cfg.transform.pt_ratio = 200.0
    eng.update_config(new_cfg)
    assert eng.cfg.transform.pt_ratio == 200.0
    assert eng.buffer.capacity >= int(3.0 * FS)
    assert len(eng.buffer) > 0                       # 已有数据被保留
    assert eng.state.emits == {} or all(v >= 0 for v in eng.state.emits.values())
    eng.stop()
    assert fill_before > 0


def test_result_json_serializable(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "json.csv"), duration_s=1.2)
    eng = _engine_from_csv(base_cfg, art["path"], block_samples=6400)
    res = list(eng.run())[-1]
    d = res.to_dict()
    s = json.dumps(d, ensure_ascii=False, allow_nan=False)      # allow_nan=False 强制检查 NaN
    assert "NaN" not in s and "Infinity" not in s
    back = json.loads(s)
    assert set(back["quantities"]) <= set(QUANTITY_KEYS)
    for key in ("voltage", "current", "power", "power_factor", "fundamental", "harmonic", "spectrum"):
        q = back["quantities"][key]
        assert q["ok"] is True, (key, q.get("error"))
        assert q["window"]["n_samples"] > 0
        assert isinstance(q["units"], dict)


def test_all_quantities_present_and_sane(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "all.csv"), duration_s=1.2)
    eng = _engine_from_csv(base_cfg, art["path"], block_samples=6400)
    res = list(eng.run())[-1]
    assert set(res.quantities) == set(QUANTITY_KEYS)
    exp = art["expected"]
    v = res.quantities["voltage"].values
    c = res.quantities["current"].values
    p = res.quantities["power"].values
    pf = res.quantities["power_factor"].values
    f = res.quantities["fundamental"].values
    h = res.quantities["harmonic"].values
    sp = res.quantities["spectrum"].values
    assert v["rms"]["A"] == pytest.approx(exp["u_rms_phase"], rel=2e-3)
    assert v["line_rms"]["Uab"] == pytest.approx(exp["u_line"], rel=2e-3)
    assert c["rms"]["A"] == pytest.approx(exp["i_rms_phase"], rel=2e-3)
    assert c["neutral_rms"] == pytest.approx(exp["i_neutral"], rel=5e-3)
    assert p["p_total"] == pytest.approx(exp["p_total"], rel=2e-3)
    assert p["q_total"] == pytest.approx(exp["q_total"], rel=5e-3)
    assert pf["pf_total"] == pytest.approx(exp["pf_arith"], rel=2e-3)
    assert pf["dpf"] == pytest.approx(math.cos(math.radians(30)), rel=2e-3)
    assert f["freq_hz"] == pytest.approx(F_NOM, rel=1e-6)
    assert f["phase_sequence"] == "正序(ABC)"
    assert h["thd_u_pct"]["A"] == pytest.approx(exp["thd_u_pct"], rel=5e-3)
    assert set(h["u"]["A"]["orders_rms"]) == {str(k) for k in range(2, 51)}
    assert sp["peak"]["freq_hz"] == pytest.approx(F_NOM, rel=1e-2)


def test_history_per_quantity_independent(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "hist.csv"), duration_s=3.0)
    eng = _engine_from_csv(base_cfg, art["path"], block_samples=640,
                           windows={"voltage": 1.0, "harmonic": 0.2})
    list(eng.run())
    hist = eng.calc.history
    hv = hist.get("voltage"); hh = hist.get("harmonic")
    assert len(hh) > len(hv) >= 2
    assert all(rec["Ua"] is not None for rec in hv)     # 不得有 None 空点
    assert all(rec["THD_U"] is not None for rec in hh)
    # 收尾 flush_all 可能与最后一次调度同一数据时刻 → 只要求非递减，且严格递增占多数
    dv = np.diff([r["t"] for r in hv])
    assert np.all(dv >= 0) and (dv > 0).sum() >= max(1, len(dv) - 1)


def test_snapshot_full_does_not_consume(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "snap.csv"), duration_s=1.2)
    eng = _engine_from_csv(base_cfg, art["path"], block_samples=6400)
    eng.start()
    eng.poll_once()
    before = eng.state.samples_in
    snap = eng.snapshot_full()
    assert snap is not None and set(snap.quantities) == set(QUANTITY_KEYS)
    assert eng.state.samples_in == before            # snapshot 不推进数据


def test_empty_buffer_handled(base_cfg):
    cfg = copy.deepcopy(base_cfg)
    cfg.source = SourceConfig(kind="simulator", block_samples=640)
    cfg.validate()
    eng = LiveEngine(cfg)
    res = eng.calc.compute_from_buffer(eng.buffer)
    assert res.meta["ok"] is False
    assert eng.snapshot_full() is None


def test_live_engine_with_simulator(base_cfg):
    """实时链路端到端：模拟器 → 引擎 → 结果（不依赖真实采集装置）。"""
    cfg = copy.deepcopy(base_cfg)
    cfg.source = SourceConfig(kind="simulator", block_samples=640, sim_speed=50.0)
    cfg.validate()
    eng = LiveEngine(cfg, source=SimulatorSource(cfg, realtime_pace=False, block_samples=640))
    out = []
    for res in eng.run(duration_s=3.0, max_ticks=40):
        out.append(res)
        if len(out) >= 3:
            break
    eng.stop()
    assert out, "实时链路无输出"
    last = out[-1]
    assert last.quantities["fundamental"].values["freq_hz"] == pytest.approx(F_NOM, rel=1e-3)
    assert last.quantities["voltage"].values["rms"]["A"] == pytest.approx(
        100 / math.sqrt(3) * PT, rel=2e-2)
    st = eng.state.to_dict()
    assert st["samples_in"] > 0 and st["source_kind"] == "simulator"


def test_metrics_calculator_rejects_unscaled_block_with_note(base_cfg):
    """未按一次侧送入时必须给出显式提示（防止把二次值当一次值报给领导）。"""
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, 30.0)], FS, 1.0, F_NOM)
    blk = SampleBlock(t=t, u=u, i=i, scaled=False, source="x")
    res = MetricsCalculator(base_cfg).compute(blk, with_history=False)
    assert any("PT/CT" in n for n in res.meta["notes"])
