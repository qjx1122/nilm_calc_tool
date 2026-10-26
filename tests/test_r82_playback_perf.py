"""v0.82：离线 CSV 播放提速——解析快路径 / 向量化与原逐行逐组实现结果一致；engine.run 不再每块空睡。"""
from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np

from elec_tool.config import AppConfig, ColumnMap, SamplingConfig
from elec_tool.sources.parsing import _parse_slash_clock, _parse_slash_clock_block, parse_rows, parse_timestamps

ROOT = Path(__file__).resolve().parents[1]


def _rows(n=640, bad=None, empty=None, ts="num"):
    rng = np.random.default_rng(0)
    out = []
    for k in range(n):
        t = k / 6400.0
        if ts == "num":
            tcell = f"{1791878400 + t:.6f}"
        else:
            s = int(t); frac = int(round((t - s) * 10000))
            tcell = f"0/00/00 00:00:{s:02d}.{frac:04d}"
        vals = [f"{v:.5f}" for v in rng.normal(0, 1, 6)]
        out.append([tcell] + vals)
    if bad is not None:
        out[bad[0]][bad[1]] = "abc"
    if empty is not None:
        out[empty[0]][empty[1]] = ""
    return out


def test_fast_column_parse_matches_slow_path_and_falls_back():
    cm, sp = ColumnMap(), SamplingConfig()
    rows = _rows()
    blk, info = parse_rows(rows, cm, sp)
    ref = np.array([[float(c) for c in r[1:]] for r in rows])
    assert np.array_equal(blk.u[0], ref[:, 0]) and np.array_equal(blk.i[2], ref[:, 5]) and info["n_bad_cells"] == 0
    # 坏单元 → 退回慢路径：仍报告坏单元并按 nan 插值
    blk2, info2 = parse_rows(_rows(bad=(5, 2)), cm, sp)
    assert info2["n_bad_cells"] == 1 and "非数值" in " ".join(info2["notes"]) and np.isfinite(blk2.i[0]).all()
    # 空单元 → 退回慢路径：n_nan 计数与原来一致
    blk3, info3 = parse_rows(_rows(empty=(7, 1)), cm, sp)
    assert info3["n_nan"] == 1 and info3["n_bad_cells"] == 0 and np.isfinite(blk3.u[0]).all()
    # 短行（列数不足）→ 慢路径
    rows4 = _rows(); rows4[3] = rows4[3][:4]
    blk4, info4 = parse_rows(rows4, cm, sp)
    assert blk4.n == 640 and info4["n_nan"] == 3


def test_slash_clock_block_matches_per_value_and_rejects_mixed():
    ts = [r[0] for r in _rows(3000, ts="clock")]
    per = np.array([_parse_slash_clock(s, 8.0)[0] for s in ts])
    blk, nd, fmt = _parse_slash_clock_block(ts, 8.0)
    assert nd == 3000 and "无日期" in fmt and np.max(np.abs(np.array(blk) - per)) < 1e-9
    ts2 = [s.replace("0/00/00", "2026/10/13") for s in ts]
    per2 = np.array([_parse_slash_clock(s, 8.0)[0] for s in ts2])
    assert np.array_equal(np.array(_parse_slash_clock_block(ts2, 8.0)[0]), per2)
    info = parse_timestamps(ts2, "auto", 8.0)
    assert info.mode == "datetime" and abs(info.fs_est - 6400) < 1 and np.array_equal(info.t, per2)
    assert _parse_slash_clock_block(ts2 + ["2026-10-13T08:00:01"], 0.0) is not None     # 仍是骨架写法
    assert _parse_slash_clock_block(ts2 + ["not a time"], 0.0) is None
    assert _parse_slash_clock_block(["1791878400.5"], 0.0) is None
    assert _parse_slash_clock_block(["2026/10/13 08:00:02.5x"], 0.0) is None            # 小数段非数字 → 慢路径处理/报错
    # 无日期 + 跨午夜仍由 parse_timestamps 展开
    t = parse_timestamps(["0/00/00 23:59:59.9000", "0/00/00 00:00:00.0500"], "auto", 0.0).t
    assert t[1] > t[0]


def test_engine_run_does_not_sleep_per_block_and_results_unchanged():
    from elec_tool.engine import LiveEngine
    sample = ROOT / "data" / "nilm_bus_mixed.csv"
    if not sample.exists():
        import subprocess, sys
        subprocess.run([sys.executable, str(ROOT / "tools" / "gen_nilm_sample.py"), "--bus"], check=True, cwd=ROOT)
    cfg = AppConfig.load(str(ROOT / "configs" / "default.json"))
    cfg.source.kind = "csv_file"; cfg.source.path = str(sample); cfg.source.file_speed = 0.0
    cfg.source.block_samples = 640; cfg.source.poll_interval_s = 0.05
    eng = LiveEngine(cfg, output_root=str(ROOT / "output"))
    t0 = time.perf_counter(); n = 0; last = None
    for r in eng.run():
        n += 1; last = r
    dt = time.perf_counter() - t0
    # 10 s 数据、100 块：旧实现每块空睡 0.05 s ⇒ ≥ 5 s；现在应远快于实时
    assert dt < 6.0 and n >= 50 and eng.state.samples_in == 64000, (dt, n)
    d = last.to_dict()
    assert d["quantities"] and d["f_used"] > 0 and np.isfinite(d["t_ref"])
