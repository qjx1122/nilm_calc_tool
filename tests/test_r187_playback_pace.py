"""第 187 轮：离线 CSV 播放速率——播放耗时不得超过数据时间（倍速按名义生效）。

两个根因（沙盒实测定位，README v0.99.34）：

* **A（主因）** 纯 ``HH:MM:SS[.f]`` 时标不进 v0.82 整秒缓存快路径 → 每行走
  ``datetime.strptime``：30 s/6400 Hz 文件解析耗时 54 s（墙钟**超过**数据时间）、
  8×/4× 倍速全被拖到 ≈1×；且 strptime 基准（1900-01-01，负 epoch）与 ``0/00/00``
  快路径（``_NO_DATE_BASE``）不一致、无日期跨午夜不展开、负 epoch 在 Windows 有
  localtime 风险（F-40）。修复＝纯时间进快路径（np.char.partition 向量化 + 整秒唯一值
  缓存，基准统一 ``_NO_DATE_BASE``、跨午夜展开）。
* **B** ``relative_s``（相对秒）时标**逐块减本块首值** → 时间轴逐块归零：曲线只出
  首尾 2 点（``_due_keys`` 不触发）、节拍钟限速失效、事件时标全错。修复＝
  ``parse_timestamps(relative_base=…)`` 按**文件首行**对齐（``iter_csv_blocks`` 贯通；
  ``_file_time_range`` / ``wave_preview`` 首末段同零点）。

保留的既有语义：时标缺口按数据时间轴等待（两侧同步 / 公共时间段依赖同一时刻口径）。
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from elec_tool.config import AppConfig
from elec_tool.engine import LiveEngine
from elec_tool.pace import PaceClock
from elec_tool.sources import create_source
from elec_tool.sources.parsing import (_parse_slash_clock, _parse_slash_clock_block,
                                       iter_csv_blocks, parse_timestamps)

FS = 6400.0
HDR = "t,ua,ia,ub,ib,uc,ic"


def _sig(n: int, fs: float = FS):
    t = np.arange(n) / fs
    w = 2 * np.pi * 50.0 * t
    u = np.vstack([220 * np.sin(w), 220 * np.sin(w - 2 * np.pi / 3), 220 * np.sin(w + 2 * np.pi / 3)])
    i = np.vstack([10 * np.sin(w - .3), 9 * np.sin(w - 2 * np.pi / 3 - .3), 11 * np.sin(w + 2 * np.pi / 3 - .3)])
    return t, u, i


def _write(path, stamps, u, i):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HDR + "\n")
        for k in range(len(stamps)):
            fh.write(f"{stamps[k]},{u[0,k]:.4f},{i[0,k]:.4f},{u[1,k]:.4f},{i[1,k]:.4f},{u[2,k]:.4f},{i[2,k]:.4f}\n")


def _write_timeonly(path, dur_s: float, fs: float = FS, gap_after: float = 0.0, gap_s: float = 0.0):
    """纯 HH:MM:SS.ffff 时刻列（12:40:00 起），可选在 gap_after 后注入 gap_s 的时标缺口。"""
    n = int(dur_s * fs)
    t, u, i = _sig(n, fs)
    ts = 12 * 3600 + 40 * 60 + t + np.where(t >= gap_after, gap_s, 0.0) if gap_s else 12 * 3600 + 40 * 60 + t
    hh = (ts // 3600).astype(int); mm = ((ts % 3600) // 60).astype(int)
    ss = ts - hh * 3600 - mm * 60
    stamps = [f"{h:02d}:{m:02d}:{s:07.4f}" for h, m, s in zip(hh, mm, ss)]
    _write(path, stamps, u, i)
    return n


def _write_relative(path, dur_s: float, fs: float = FS):
    """纯相对秒（0 起）时刻列——触发 relative_s 模式。"""
    n = int(dur_s * fs)
    t, u, i = _sig(n, fs)
    _write(path, [f"{x:.6f}" for x in t], u, i)
    return n


def _cfg(path: str, speed: float) -> AppConfig:
    cfg = AppConfig()
    cfg.source.kind = "csv_file"
    cfg.source.path = str(path)
    cfg.source.file_speed = speed
    cfg.source.block_samples = 640
    cfg.source.play_start_mode = "begin"
    cfg.validate()
    return cfg


def _play(path, speed: float, tmp_path) -> tuple:
    """引擎 + 节拍钟（与服务端 Runner.start 同接线）回放，返回 (墙钟, state)。"""
    cfg = _cfg(path, speed)
    eng = LiveEngine(cfg, output_root=str(tmp_path))
    clk = PaceClock(speed)
    eng.source.pace_clock = clk
    eng.source.pace_side = "bus"
    eng.source.pace_abort = None
    eng.start()
    t0 = time.perf_counter()
    while True:
        eng.poll_once()
        if eng.state.finished or time.perf_counter() - t0 > 60:
            break
    return time.perf_counter() - t0, eng.state


# ───────────────────────── A：纯时间快路径（等价 / 拒绝 / 基准统一 / 跨午夜） ─────────────────────────
def test_time_only_fast_path_unifies_base_with_slash_prefix():
    """纯 HH:MM:SS.ffff 与 00/00/00 前缀解析出**同一天基**（修复 strptime 1900 负 epoch 漂移）。"""
    a = parse_timestamps(["12:40:00.0000", "12:40:00.0001"], "auto", 0.0)
    b = parse_timestamps(["00/00/00 12:40:00.0000", "00/00/00 12:40:00.0001"], "auto", 0.0)
    assert a.mode == "clock_time" and b.mode == "clock_time"
    assert np.array_equal(a.t, b.t), (a.t, b.t)
    assert a.t[0] > 0                                # 不再是 1900 基准的负 epoch（Windows F-40 风险）


def test_time_only_unwraps_midnight():
    """纯时间跨午夜必须展开（旧 strptime 路径 mode=datetime 不展开 → 23:59→00:00 被判倒流）。"""
    m = parse_timestamps(["23:59:59.5000", "00:00:00.5000"], "auto", 0.0)
    assert m.mode == "clock_time" and m.t[1] > m.t[0], m.t


def test_time_only_block_fast_path_equivalence_and_rejection():
    """快路径与逐值解析逐位一致；骨架外/小数非数字整体退回慢路径（保持既有拒绝语义）。"""
    ts2 = ["12:40:00.0000", "12:40:00.0001", "12:40:01"]
    per = np.array([_parse_slash_clock(s, 8.0)[0] for s in ts2])
    blk, nd, fmt = _parse_slash_clock_block(ts2, 8.0)
    assert np.allclose(blk, per, rtol=0, atol=1e-9)
    assert nd == 3 and "无日期" in fmt
    # 混合带日期/无日期/ISO-T 分隔：仍逐位一致
    ts = ["2026/1/5 8:03:07.5", "0/00/00 23:59:59.9000", "2026-10-13T08:00:01", "00/00/00 00:00:00.0500"]
    per2 = np.array([_parse_slash_clock(s, 8.0)[0] for s in ts])
    blk2, _, _ = _parse_slash_clock_block(ts, 8.0)
    assert np.allclose(blk2, per2, rtol=0, atol=1e-9)
    # 拒绝语义（与旧实现一致）
    assert _parse_slash_clock_block(["1791878400.5"], 0.0) is None       # 纯数字（epoch，应走数值分支）
    assert _parse_slash_clock_block(["not a time"], 0.0) is None
    assert _parse_slash_clock_block(ts2 + ["2026-10-13T08:00:01"], 0.0) is not None
    assert _parse_slash_clock_block(ts2 + ["2026/10/13 08:00:02.5x"], 0.0) is None
    assert _parse_slash_clock_block(["12:40:00.5x"], 0.0) is None


def test_time_only_parse_performance():
    """性能防回归：20 万行纯时间解析 < 2 s（修复前 strptime 逐行 ≈ 5~6 s）。"""
    big = ["12:40:%02d.%04d" % (i % 60, i % 10000) for i in range(200_000)]
    t0 = time.perf_counter()
    parse_timestamps(big, "auto", 0.0)
    dt = time.perf_counter() - t0
    assert dt < 2.0, f"20 万行纯时间解析 {dt:.2f}s（应 <2s；strptime 慢路径 ≈5-6s）"


# ───────────────────────── B：relative_s 跨块同一零点 ─────────────────────────
def test_relative_s_blocks_share_file_base(tmp_path):
    """分块读取的相对秒时间轴按**文件首行**对齐：逐块递增、与整列一次解析逐位一致。"""
    p = tmp_path / "rel.csv"
    n = _write_relative(p, dur_s=3.0)                 # 19200 行，块 640 → 30 块
    cfg = AppConfig()
    cfg.sampling.fs = FS
    cfg.source.kind = "csv_file"; cfg.source.path = str(p); cfg.source.block_samples = 640
    src = create_source(cfg)
    src.open()
    t_parts = []
    while True:
        b = src.read()
        if b is None:
            break
        t_parts.append(b.t)
    assert len(t_parts) == n // 640
    # 逐块首值递增且与 k*640/fs 一致（修复前每块都是 0）
    firsts = np.array([t[0] for t in t_parts])
    assert np.allclose(firsts, np.arange(len(t_parts)) * 640 / FS, atol=1e-9), firsts[:5]
    # 整列连续（文件以 %.6f 写入，量化 1e-6 s ⇒ 容差按写入精度）
    t_all = np.concatenate(t_parts)
    assert np.allclose(np.diff(t_all), 1.0 / FS, atol=1e-6)
    # 与整列一次解析逐位一致
    import csv as _csv
    with open(p, encoding="utf-8") as fh:
        fh.readline()
        col = [row[0] for row in _csv.reader(fh)]
    whole = parse_timestamps(col, "auto", 0.0).t
    assert np.allclose(t_all, whole, rtol=0, atol=1e-12)


def test_relative_s_file_time_range_consistent(tmp_path):
    """公共时间段口径：_file_time_range 首末段同零点（修复前末段自减 → t1≈0、算不出交集）。"""
    from app.server import _file_time_range
    p = tmp_path / "rel2.csv"
    _write_relative(p, dur_s=2.0)
    cfg = AppConfig()
    cfg.source.kind = "csv_file"; cfg.source.path = str(p)
    r = _file_time_range(cfg, str(p))
    assert abs(r["t0"]) < 1e-9, r
    assert r["t1"] > 1.9, r                          # ≈2.0s（修复前 ≈0）
    # 纯时间文件同口径
    p2 = tmp_path / "clock.csv"
    _write_timeonly(p2, dur_s=2.0)
    cfg2 = AppConfig(); cfg2.source.kind = "csv_file"; cfg2.source.path = str(p2)
    r2 = _file_time_range(cfg2, str(p2))
    span = r2["t1"] - r2["t0"]
    assert 1.9 < span < 2.1, r2                      # 时刻列跨度≈数据时长


# ───────────────────────── 端到端：倍速按名义生效、墙钟不超数据时间 ─────────────────────────
def test_named_speed_wall_clock_and_curve_progress(tmp_path):
    """8×（纯时间文件）与 4×（相对秒文件）墙钟≈数据时长/倍速，且曲线正常出点。

    修复前对照：纯时间文件 8× 实测 28s+（≈1×，解析拖死）；相对秒文件时间轴冻结
    （曲线只有首尾点、限速完全失效）。
    """
    p1 = tmp_path / "abs.csv"
    _write_timeonly(p1, dur_s=10.0)
    dt1, st1 = _play(p1, 8.0, tmp_path)
    assert 0.7 <= dt1 < 4.0, f"8× 纯时间文件 wall={dt1:.2f}s（期望≈1.25s；修复前 ≥10s）"
    assert (st1.emits.get("voltage") or 0) >= 9, st1.emits
    assert st1.data_t_end is not None and st1.data_t_end > 9.0, st1.data_t_end

    p2 = tmp_path / "rel.csv"
    _write_relative(p2, dur_s=10.0)
    dt2, st2 = _play(p2, 4.0, tmp_path)
    assert 2.0 <= dt2 < 7.0, f"4× 相对秒文件 wall={dt2:.2f}s（期望≈2.5s；修复前 <1s＝限速失效）"
    assert (st2.emits.get("voltage") or 0) >= 9, st2.emits
    assert st2.data_t_end is not None and st2.data_t_end > 9.0, st2.data_t_end


def test_gap_keeps_timestamp_span_semantics(tmp_path):
    """时标缺口按数据时间轴等待（两侧同步 / 公共时间段同一时刻口径）——保留的既有语义。"""
    p = tmp_path / "gap.csv"
    _write_timeonly(p, dur_s=10.0, gap_after=5.0, gap_s=5.0)   # 数据 10s、时标跨度 15s
    dt, st = _play(p, 4.0, tmp_path)
    # 期望 ≈ 15/4 = 3.75s（按跨度），而非 10/4 = 2.5s（按样本）——缺口等待是有意设计
    assert 2.8 <= dt < 8.0, f"gap 文件 wall={dt:.2f}s（期望≈3.75s）"
    assert st.samples_in == int(10.0 * FS)
