"""F-40（用户回报）：Windows 下 `time.localtime(负 epoch)` 抛 OSError → `/api/nilm/events` 500。

根因：无日期时标 `0/00/00 HH:MM:SS` 的基准为 1970-01-01，按本地时间解释（UTC+8）后 epoch 为负。
修法：① 基准改 1970-01-02；② 所有本地时间文本出口走 `elec_tool.timefmt`（localtime 失败时手工换算）。
本用例用 monkeypatch 模拟 Windows 行为（负值 / 极小值抛 OSError）。
"""
from __future__ import annotations

import csv
import time

import numpy as np
import pytest

from elec_tool import timefmt
from elec_tool.config import AppConfig
from elec_tool.engine import LiveEngine
from elec_tool.sources.parsing import _NO_DATE_BASE, parse_timestamps

FS = 6400


@pytest.fixture
def windows_like_localtime(monkeypatch):
    real = time.localtime

    def fake(t=None):
        if t is not None and float(t) < 0:
            raise OSError(22, "Invalid argument")
        return real(t)
    monkeypatch.setattr(time, "localtime", fake)
    monkeypatch.setenv("TZ", "Asia/Shanghai"); time.tzset()
    yield
    monkeypatch.delenv("TZ", raising=False); time.tzset()


def test_timefmt_never_raises(windows_like_localtime):
    with pytest.raises(OSError):
        time.localtime(-100)                                   # 模拟生效
    assert timefmt.fmt_local(-28800 + 740) == "1970-01-01 00:12:20.000"      # 东八区：负 epoch 仍能格式化
    assert timefmt.local_day(-1) == "19700101" and timefmt.local_tod_s(-28800 + 5.25) == pytest.approx(5.25)
    assert timefmt.fmt_local(1791878400.0, ms=False) == "2026-10-13 16:00:00"      # 东八区
    assert timefmt.fmt_local(None) == "" and timefmt.local_day(float("nan")) == "unknown"


def test_no_date_stamps_are_positive_in_any_timezone(windows_like_localtime):
    info = parse_timestamps(["0/00/00 00:12:40.0000", "0/00/00 00:12:40.0002"], "auto", tz_offset_h=8.0)
    assert _NO_DATE_BASE == 86400.0 and info.t[0] > 0
    assert timefmt.fmt_local(float(info.t[0]), ms=False, date=False) == "00:12:40"          # 本地显示＝文件时刻
    info14 = parse_timestamps(["0/00/00 00:00:00.0000"], "auto", tz_offset_h=14.0)
    assert info14.t[0] > 0                                                                 # UTC+14 也为正


def test_nilm_and_events_listing_with_clock_file(windows_like_localtime, tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))
    monkeypatch.setenv("ELEC_TOOL_EVENTS_DIR", str(tmp_path / "ev"))
    monkeypatch.setenv("ELEC_TOOL_REALTIME_DIR", str(tmp_path / "rt"))
    n = 3 * FS; t = np.arange(n) / FS; w = 2 * np.pi * 50 * t
    P = np.full(n, 1000.0); P[t >= 1.5] += 600
    p = tmp_path / "clk.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(n):
            tod = 12 * 60 + 40 + t[k]
            row = [f"0/00/00 00:{int(tod // 60):02d}:{tod % 60:07.4f}"]
            for ph in (0, -2.0944, 2.0944):
                row += [f"{57.74 * 1.41421 * np.sin(w[k] + ph):.4f}", f"{(P[k] / 3) / 57.74 * 1.41421 * np.sin(w[k] + ph):.5f}"]
            wr.writerow(row)
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = str(p); cfg.validate()
    eng = LiveEngine(cfg)
    for _ in eng.run():
        pass
    evs = eng.nilm.list(limit=50)                      # 修复前：OSError
    assert evs and all(e["t_start"] > 0 for e in evs)
    assert any(e["t_start_local"].endswith("00:12:41.500") for e in evs), [e["t_start_local"] for e in evs]
    assert eng.detector.list(limit=10) is not None
    assert eng.nilm.writer.rows_written == len(evs) and list((tmp_path / "nilm").glob("nilm_events_19700102.csv"))
