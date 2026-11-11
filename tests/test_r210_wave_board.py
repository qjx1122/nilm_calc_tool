"""第 210 轮（v0.99.51）：数据处理页「波形预览」子界面。

界面上的「波形预览」是一组可增删的预览模块（内部标识 wave-board）；每个模块显示一个文件的曲线：
  * 离线波形 CSV → 电压 / 电流有效值曲线，沿用 /api/process/wave/rms（用例见 tests/test_r61_wave_preview.py，
    这里只验证本子界面用到的那几个参数）；
  * 实时监测输出文件（实时落盘的曲线 CSV）→ 电压 / 电流 / 有功 / 无功 / 功率因数，
    由 elec_tool/monitor_curve.py 读取，接口 /api/process/monitor/files 与 /api/process/monitor/curve。

注意：原先叫「波形预览」的子界面在 v0.99.50 改名为「波形分析」，它的内部标识仍是 wave-preview，与本文件无关。
"""
from __future__ import annotations

import csv
import os
import pathlib
import re
import shutil
import time

import numpy as np
import pytest

from elec_tool.config import CURVE_KEYS
from elec_tool.monitor_curve import (MAX_POINTS_CAP, QUANTITIES, QUANTITY_ORDER, MonitorCurveError, file_kind,
                                     list_curve_files, quantities_of_kind, read_curve_file)

ROOT = pathlib.Path(__file__).resolve().parents[1]
T0 = 1_790_000_000.0
RUN_A, RUN_B, RUN_C = 1_790_000_000_111, 1_790_000_500_222, 1_790_000_900_333      # run_id＝运行启动时的墙钟毫秒

VOLT_HEAD = ["t_epoch_s", "time_local", "source_id", "window_s", "Ua", "Ub", "Uc", "Uab", "Ubc", "Uca", "unbalance_pct", "U1", "run_id"]
POWER_HEAD = ["t_epoch_s", "time_local", "source_id", "window_s", "P", "Q", "S", "Pa", "Pb", "Pc", "Qa", "Qb", "Qc", "Sa", "Sb", "Sc", "run_id"]
PF_HEAD = ["t_epoch_s", "time_local", "source_id", "window_s", "PF", "DPF", "phi1_deg", "PFa", "PFb", "PFc", "run_id"]


def _write(path, head, rows, bom=True):
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(head); w.writerows(rows)
    return str(path)


def _volt_row(t, sid, ua, run, ub=None, uc=None):
    ub = ua + 1 if ub is None else ub; uc = ua + 2 if uc is None else uc
    return [repr(t), "x", sid, 0.2, ua, ub, uc, ua * 1.732, ub * 1.732, uc * 1.732, 0.1, ua, run]


@pytest.fixture()
def mixed_voltage(tmp_path):
    """一个电压文件里混着：总线侧第一次运行 10 点、分路侧 5 点、总线侧第二次运行 20 点（与第一次的数据时间重叠）。"""
    rows = [_volt_row(T0 + k, 0, 100 + k, RUN_A) for k in range(10)]
    rows += [_volt_row(T0 + 100 + k, 1, 300 + k, RUN_C) for k in range(5)]
    rows += [_volt_row(T0 + k, 0, 200 + k, RUN_B) for k in range(20)]
    return _write(tmp_path / "voltage_20261111.csv", VOLT_HEAD, rows)


# --------------------------------------------------------------------------- 读取：来源、运行批次

def test_default_is_bus_side_latest_run(mixed_voltage):
    d = read_curve_file(mixed_voltage)
    assert d["ok"] and d["quantity"] == "voltage" and d["label"] == "电压" and d["unit"] == "V"
    assert d["fields"] == ["Ua", "Ub", "Uc"] and [q["id"] for q in d["quantities"]] == ["voltage"]
    assert d["source_ids"] == [0, 1] and d["source_id"] == 0
    assert d["run_mode"] == "latest" and d["run_id"] == RUN_B and [r["id"] for r in d["run_ids"]] == [RUN_A, RUN_B]
    assert d["run_ids"][0]["rows"] == 10 and d["run_ids"][1]["rows"] == 20
    assert d["n"] == 20 and d["rows_total"] == 35 and d["rows_selected"] == 20 and not d["decimated"]
    assert d["t"] == [T0 + k for k in range(20)] and d["series"]["Ua"] == [200.0 + k for k in range(20)]
    assert d["series"]["Uc"][0] == 202.0 and d["t_first"] == T0 and d["t_last"] == T0 + 19 and d["window_s"] == 0.2
    notes = "；".join(d["notes"])
    assert "总线侧、分路侧" in notes and "当前显示总线侧" in notes, notes
    assert "2 次运行" in notes and "只显示最近一次" in notes, notes


def test_source_and_run_can_be_chosen(mixed_voltage):
    d = read_curve_file(mixed_voltage, source_id=1)
    assert d["source_id"] == 1 and d["run_id"] == RUN_C and d["n"] == 5 and d["series"]["Ua"] == [300.0 + k for k in range(5)]
    assert not any("当前显示" in n for n in d["notes"])              # 明确选了来源就不再提示
    d = read_curve_file(mixed_voltage, source_id=0, run=RUN_A)
    assert d["run_mode"] == "one" and d["run_id"] == RUN_A and d["series"]["Ua"] == [100.0 + k for k in range(10)]
    d = read_curve_file(mixed_voltage, source_id=0, run=str(RUN_A))   # 接口传来的是字符串
    assert d["n"] == 10
    # all：两次运行合在一起；同一时刻两行时取后写入的（第二次运行的值）
    d = read_curve_file(mixed_voltage, run="all")
    assert d["run_mode"] == "all" and d["run_id"] is None and d["n"] == 20
    assert d["series"]["Ua"][:10] == [200.0 + k for k in range(10)]
    assert any("2 次运行" in n and "合在一起" in n for n in d["notes"])
    with pytest.raises(MonitorCurveError, match="没有 run_id="):
        read_curve_file(mixed_voltage, source_id=1, run=RUN_A)        # 这次运行属于总线侧
    with pytest.raises(MonitorCurveError, match="运行批次写法不对"):
        read_curve_file(mixed_voltage, run="newest")


def test_file_with_only_one_side_selects_it_without_a_note(tmp_path):
    p = _write(tmp_path / "voltage_20261111.csv", VOLT_HEAD, [_volt_row(T0 + k, 1, 50 + k, RUN_A) for k in range(3)])
    d = read_curve_file(p)
    assert d["source_ids"] == [1] and d["source_id"] == 1 and d["n"] == 3 and d["notes"] == []
    with pytest.raises(MonitorCurveError, match="文件里没有总线侧的数据；文件里有：分路侧"):
        read_curve_file(p, source_id=0)


def test_legacy_file_without_source_and_run_columns(tmp_path):
    """v0.17 之前没有 source_id、v0.32 之前没有 run_id：都算总线侧，不按运行筛选。"""
    head = ["t_epoch_s", "time_local", "window_s", "Ia", "Ib", "Ic", "In", "unbalance_pct"]
    p = _write(tmp_path / "current_20261001.csv", head, [[repr(T0 + k), "x", 1.0, 5 + k, 6 + k, 7 + k, 0.1, 0.2] for k in range(4)], bom=False)
    d = read_curve_file(p)
    assert d["quantity"] == "current" and d["unit"] == "A" and d["fields"] == ["Ia", "Ib", "Ic"]
    assert d["source_ids"] == [0] and d["run_mode"] == "none" and d["run_ids"] == [] and d["run_id"] is None and d["n"] == 4
    assert read_curve_file(p, run="all")["n"] == 4 and read_curve_file(p, run=12345)["n"] == 4   # 没有 run_id 列时这个参数不起作用


# --------------------------------------------------------------------------- 读取：五种量

def test_power_file_offers_active_and_reactive(tmp_path):
    rows = [[repr(T0 + k), "x", 0, 1.0, 900 + k, 300 + k, 950, 300, 300, 300 + k, 100, 100, 100 + k, 316, 316, 316, RUN_A] for k in range(6)]
    p = _write(tmp_path / "power_20261111.csv", POWER_HEAD, rows)
    d = read_curve_file(p)
    assert [q["id"] for q in d["quantities"]] == ["p", "q"] and d["quantity"] == "p"        # 不指定时取文件里的第一种
    assert d["label"] == "有功功率" and d["unit"] == "W" and d["fields"] == ["P", "Pa", "Pb", "Pc"]
    assert d["series"]["P"] == [900.0 + k for k in range(6)] and d["series"]["Pc"][-1] == 305.0
    d = read_curve_file(p, quantity="q")
    assert d["label"] == "无功功率" and d["unit"] == "var" and d["fields"] == ["Q", "Qa", "Qb", "Qc"]
    assert d["series"]["Q"] == [300.0 + k for k in range(6)] and d["series"]["Qc"][0] == 100.0
    assert read_curve_file(p, quantity="Q")["quantity"] == "q"                              # 大小写不敏感
    with pytest.raises(MonitorCurveError, match="没有「电压」的列；它可以显示：有功功率、无功功率"):
        read_curve_file(p, quantity="voltage")
    with pytest.raises(MonitorCurveError, match="不认识的量 'thd'"):
        read_curve_file(p, quantity="thd")


def test_power_factor_file(tmp_path):
    rows = [[repr(T0 + k), "x", 0, 1.0, 0.9, 0.95, 18.2, 0.91, 0.89, "", RUN_A] for k in range(3)]
    p = _write(tmp_path / "power_factor_20261111.csv", PF_HEAD, rows)
    d = read_curve_file(p)
    assert d["quantity"] == "pf" and d["label"] == "功率因数" and d["unit"] == ""
    assert d["fields"] == ["PF", "PFa", "PFb"] and "PFc" not in d["series"]                 # 整列为空的不返回
    assert any("PFc 没有数值" in n for n in d["notes"])
    assert d["series"]["PF"] == [0.9, 0.9, 0.9]


def test_quantity_table_matches_what_the_realtime_writer_writes():
    """五种量用到的列名必须是实时落盘真正写出的列（metrics 里的提取规则），否则界面永远读不到。"""
    from elec_tool.metrics import _EXTRACTORS

    class _Q:                      # 提取规则只用到 ok / values
        ok = True; values: dict = {}

    class _R:
        f_used = 50.0

    for qid in QUANTITY_ORDER:
        spec = QUANTITIES[qid]
        written = set(_EXTRACTORS[spec["file"]](_R(), _Q()).keys())
        assert set(spec["fields"]) <= written, (qid, spec["fields"], written)
        assert spec["file"] in CURVE_KEYS
    assert [QUANTITIES[q]["label"] for q in QUANTITY_ORDER] == ["电压", "电流", "有功功率", "无功功率", "功率因数"]


# --------------------------------------------------------------------------- 读取：时间、排序、抽稀

def test_time_filters(mixed_voltage):
    d = read_curve_file(mixed_voltage, t_start=T0 + 5, t_end=T0 + 9)
    assert d["t"] == [T0 + k for k in range(5, 10)] and d["series"]["Ua"][0] == 205.0
    d = read_curve_file(mixed_voltage, last_s=3)                                             # 最后 3 秒：T0+16 … T0+19
    assert d["t"] == [T0 + k for k in range(16, 20)]
    d = read_curve_file(mixed_voltage, t_start=T0 + 2, last_s=1000)                          # 两个条件同时起作用
    assert d["t"][0] == T0 + 2 and d["n"] == 18
    with pytest.raises(MonitorCurveError, match="所选时间段内没有数据"):
        read_curve_file(mixed_voltage, t_start=T0 + 1000)
    with pytest.raises(MonitorCurveError, match="必须大于 0"):
        read_curve_file(mixed_voltage, last_s=0)


def test_rows_are_sorted_by_data_time(tmp_path):
    order = [3, 0, 4, 1, 2]
    p = _write(tmp_path / "voltage_20261111.csv", VOLT_HEAD, [_volt_row(T0 + k, 0, 10 + k, RUN_A) for k in order])
    d = read_curve_file(p)
    assert d["t"] == [T0 + k for k in range(5)] and d["series"]["Ua"] == [10.0, 11.0, 12.0, 13.0, 14.0]


def test_decimation_keeps_peaks_of_every_series(tmp_path):
    n = 20000
    ua = np.full(n, 100.0); ub = np.full(n, 101.0); uc = np.full(n, 102.0)
    ua[12345] = 180.0          # A 相一个尖峰
    ub[777] = 20.0             # B 相一个跌落（只在 B 相上有，按“第一条曲线”抽稀会丢掉它）
    rows = [_volt_row(T0 + 0.2 * k, 0, float(ua[k]), RUN_A, ub=float(ub[k]), uc=float(uc[k])) for k in range(n)]
    p = _write(tmp_path / "voltage_20261111.csv", VOLT_HEAD, rows)
    d = read_curve_file(p, max_points=500)
    # 3 条曲线：每段至多 1 + 2×3 个点，500 个点的预算分成 71 段；曲线平坦时各段的峰谷点重合，点数会少于预算
    assert d["decimated"] and d["rows_selected"] == n and 71 <= d["n"] <= 500
    assert max(d["series"]["Ua"]) == 180.0 and min(d["series"]["Ub"]) == 20.0
    assert d["t"][0] == T0 and abs(d["t"][-1] - (T0 + 0.2 * (n - 1))) < 1e-6                 # 首末点保留
    assert all(b > a for a, b in zip(d["t"], d["t"][1:]))
    assert any("已抽稀" in x for x in d["notes"])
    full = read_curve_file(p, max_points=10 ** 9)                                             # 上限封顶，不会原样返回
    assert full["n"] <= MAX_POINTS_CAP and full["n"] == n
    assert read_curve_file(p, max_points=1)["n"] <= 10                                        # 下限 10


def test_only_the_tail_of_a_huge_file_is_read(tmp_path):
    rows = [_volt_row(T0 + k, 0, 100 + k, RUN_A) for k in range(2000)]
    p = _write(tmp_path / "voltage_20261111.csv", VOLT_HEAD, rows)
    d = read_curve_file(p, max_bytes=20_000)
    assert d["truncated"] and d["rows_total"] < 2000 and d["n"] == d["rows_total"]
    assert d["t"][-1] == T0 + 1999 and d["series"]["Ua"][-1] == 2099.0                        # 末尾是完整的
    assert d["series"]["Ua"][0] == 100.0 + (d["t"][0] - T0)                                    # 第一行是完整的一行，不是半行
    assert any("只读取了末尾" in x for x in d["notes"])


# --------------------------------------------------------------------------- 读取：不是曲线文件

def test_files_that_are_not_curve_files_are_refused(tmp_path):
    with pytest.raises(MonitorCurveError, match="文件不存在"):
        read_curve_file(str(tmp_path / "nope.csv"))
    wave = _write(tmp_path / "wave.csv", ["时间戳", "A相电压", "A相电流"], [[T0, 1, 2]])
    with pytest.raises(MonitorCurveError, match="表头里没有 t_epoch_s 列"):
        read_curve_file(wave)
    thd = _write(tmp_path / "harmonic_20261111.csv", ["t_epoch_s", "time_local", "source_id", "window_s", "THD_U", "THD_I"], [[T0, "x", 0, 1.0, 1, 2]])
    with pytest.raises(MonitorCurveError, match="没有可以显示的量"):
        read_curve_file(thd)
    empty = _write(tmp_path / "voltage_20261112.csv", VOLT_HEAD, [])
    with pytest.raises(MonitorCurveError, match="只有表头"):
        read_curve_file(empty)
    blank = _write(tmp_path / "voltage_20261113.csv", VOLT_HEAD, [[repr(T0), "x", 0, 0.2, "", "", "", "", "", "", "", "", RUN_A]])
    with pytest.raises(MonitorCurveError, match="都没有数值"):
        read_curve_file(blank)


def test_fast_and_slow_parsers_give_the_same_result(tmp_path):
    """快路径（numpy 只解析用到的列）处理不了引号、列数不齐的行；这时整体退回逐行解析，两条路径的结果必须相同。"""
    from elec_tool import monitor_curve as mc

    def rows(quote_time):
        out = []
        for k in range(50):
            ua = "" if k % 7 == 0 else repr(100.0 + k)                 # 空格子
            ub = "nan" if k % 11 == 0 else repr(101.0 + k)             # 写成 nan 的格子
            tl = '"2026-11-11 10:00:00.200"' if quote_time else "2026-11-11 10:00:00.200"
            out.append(f"{T0 + k!r},{tl},{k % 2},0.2,{ua},{ub},{102.0 + k!r},1,2,3,0.1,,{RUN_A + k % 2}")
        return out

    head = ",".join(VOLT_HEAD)
    plain = tmp_path / "voltage_20261111.csv"; quoted = tmp_path / "voltage_20261112.csv"; short = tmp_path / "voltage_20261113.csv"
    plain.write_bytes(("\ufeff" + head + "\r\n" + "\r\n".join(rows(False)) + "\r\n").encode("utf-8"))       # 实时落盘的写法：BOM + CRLF
    quoted.write_bytes(("\ufeff" + head + "\r\n" + "\r\n".join(rows(True)) + "\r\n").encode("utf-8"))
    short.write_bytes(("\ufeff" + head + "\r\n" + "\r\n".join(rows(False)) + "\r\n" + f"{T0 + 50!r},x,0,0.2,150.0\r\n").encode("utf-8"))   # 多一行比表头短的完整行

    calls = {"n": 0}
    real = mc._num
    def spy(x):
        calls["n"] += 1
        return real(x)
    mc._num = spy
    try:
        a = read_curve_file(str(plain), source_id=0, run="all"); fast_calls = calls["n"]
        b = read_curve_file(str(quoted), source_id=0, run="all"); slow_calls = calls["n"] - fast_calls
        c = read_curve_file(str(short), source_id=0, run="all")
    finally:
        mc._num = real
    assert fast_calls == 0 and slow_calls > 0, (fast_calls, slow_calls)        # 第一个文件走快路径，第二个走慢路径
    for key in ("t", "series", "fields", "n", "rows_total", "source_ids", "run_ids", "window_s"):
        assert a[key] == b[key], key
    assert a["n"] == 25 and a["source_ids"] == [0, 1] and a["series"]["Ua"][0] is None and a["series"]["Ua"][1] == 102.0
    assert a["series"]["Ub"][0] is None and a["series"]["Uc"][0] == 102.0
    assert c["n"] == 26 and c["series"]["Ua"][-1] == 150.0 and c["series"]["Uc"][-1] is None   # 比表头短的完整行：有的格子照用，缺的记为空
    assert c["series"]["Ua"][:25] == a["series"]["Ua"] and not any("已跳过" in x for x in c["notes"])


def test_a_line_still_being_written_is_not_read(tmp_path):
    """最后一行没有换行符＝还在写入：最后一个格子可能是被截断的数字，整行不能用。

    这里截断的是 run_id（1794371583469 只写出了 1794371）。如果把这一行读进来，它会被当成另一次运行，
    而“最近一次运行”取的正是文件里最后写入的那一行 —— 曲线就只剩这一个点。
    """
    lines = [f"{T0 + k!r},2026-11-11 10:00:00.200,0,0.2,{100.0 + k!r},{101.0 + k!r},{102.0 + k!r},1,2,3,0.1,,{RUN_A}" for k in range(20)]
    done = tmp_path / "voltage_20261111.csv"; writing = tmp_path / "voltage_20261112.csv"; cut_value = tmp_path / "voltage_20261113.csv"
    head = "\ufeff" + ",".join(VOLT_HEAD) + "\r\n"
    done.write_bytes((head + "\r\n".join(lines) + "\r\n").encode("utf-8"))
    writing.write_bytes((head + "\r\n".join(lines) + "\r\n" + f"{T0 + 20!r},2026-11-11 10:00:00.200,0,0.2,120.0,121.0,122.0,1,2,3,0.1,,1794371").encode("utf-8"))
    cut_value.write_bytes((head + "\r\n".join(lines) + "\r\n" + f"{T0 + 20!r},2026-11-11 10:00:00.200,0,0.2,12").encode("utf-8"))   # Ua 本该是 120.0
    a = read_curve_file(str(done)); b = read_curve_file(str(writing)); c = read_curve_file(str(cut_value))
    for d in (b, c):
        assert d["n"] == 20 and d["t"] == a["t"] and d["series"] == a["series"]
        assert [r["id"] for r in d["run_ids"]] == [RUN_A] and d["run_id"] == RUN_A and d["rows_total"] == 20
    # 只有表头加一行没写完的数据：报错里说明原因
    only = tmp_path / "current_20261111.csv"
    only.write_bytes(("\ufefft_epoch_s,time_local,source_id,window_s,Ia,Ib,Ic,run_id\r\n" + f"{T0!r},x,0,0.2,1.0,2.0").encode("utf-8"))
    with pytest.raises(MonitorCurveError, match="没有完整的数据行.*最后一行没有换行符"):
        read_curve_file(str(only))


def test_glued_lines_and_impossible_times_are_skipped(tmp_path):
    """程序被杀时只写了半行、重启后接着写，两行会粘成一行：列数比表头多，各格子已经错位，整行跳过并在说明里写明。

    半行断在第一个格子里时，粘出来的行列数是对的，但“时间”成了两个时间拼起来的天文数字，同样不能用。
    """
    def line(k, run=RUN_A):
        return f"{T0 + k!r},2026-11-11 10:00:00.200,0,0.2,{100.0 + k!r},{101.0 + k!r},{102.0 + k!r},1,2,3,0.1,,{run}"
    good = [line(k) for k in range(10)]
    head = "\ufeff" + ",".join(VOLT_HEAD) + "\r\n"
    glued = tmp_path / "voltage_20261111.csv"
    #   第 10 行只写到 Ua 的一半（"110"），紧接着是重启后写的第 11 行
    glued.write_bytes((head + "\r\n".join(good) + "\r\n" + f"{T0 + 10!r},2026-11-11 10:00:00.200,0,0.2,110" + line(11, RUN_B) + "\r\n"
                       + line(12, RUN_B) + "\r\n").encode("utf-8"))
    d = read_curve_file(str(glued), run="all")
    assert d["n"] == 11 and d["t"] == [T0 + k for k in range(10)] + [T0 + 12] and d["series"]["Ua"][-1] == 112.0
    assert d["rows_total"] == 11 and any("有 1 行格式不对" in x and "已跳过" in x for x in d["notes"]), d["notes"]
    assert all(v is not None and 100.0 <= v <= 112.0 for v in d["series"]["Ua"]) and all(v is not None and 102.0 <= v <= 114.0 for v in d["series"]["Uc"])
    #   半行断在时间格子里："1790000" + 下一行 → 列数没变，时间是 1790000179… 这样的数
    bigt = tmp_path / "voltage_20261112.csv"
    bigt.write_bytes((head + "\r\n".join(good) + "\r\n" + "17900" + line(11) + "\r\n" + line(12) + "\r\n").encode("utf-8"))
    e = read_curve_file(str(bigt), run="all")
    assert e["n"] == 11 and e["t_last"] == T0 + 12 and max(e["t"]) < 2e9 and any("有 1 行格式不对" in x for x in e["notes"]), (e["t"][-3:], e["notes"])


# --------------------------------------------------------------------------- 文件清单

def test_file_kind_and_listing(tmp_path):
    assert file_kind("voltage_20261111.csv") == "voltage" and file_kind("/x/y/power_factor_20261111.csv") == "power_factor"
    assert file_kind("power_20261111.csv") == "power" and file_kind("current.csv") == "current"      # 「保存曲线数据」没有日期
    for other in ("harmonic_20261111.csv", "voltage_20261111.v016.csv", "voltage_20261111.pre-v032.csv", "voltage_2026.csv", "events_20261111.csv"):
        assert file_kind(other) is None, other
    assert quantities_of_kind("power") == ["p", "q"] and quantities_of_kind("voltage") == ["voltage"] and quantities_of_kind(None) == []

    rt = tmp_path / "realtime"; rt.mkdir()
    run = tmp_path / "20261111_101010" / "realtime"; run.mkdir(parents=True)
    now = time.time()
    for k, name in enumerate(["voltage_20261110.csv", "current_20261110.csv", "power_20261110.csv", "power_factor_20261110.csv",
                              "harmonic_20261110.csv", "voltage_20261110.v016.csv"]):
        (rt / name).write_text("t_epoch_s\n", encoding="utf-8"); os.utime(rt / name, (now - 100 + k, now - 100 + k))
    (run / "voltage_20261111.csv").write_text("t_epoch_s\n", encoding="utf-8"); os.utime(run / "voltage_20261111.csv", (now, now))
    files = list_curve_files([("实时落盘目录", str(rt)), ("运行目录", str(run)), ("重复", str(rt)), ("不存在", str(tmp_path / "none"))])
    assert [f["name"] for f in files] == ["voltage_20261111.csv", "power_factor_20261110.csv", "power_20261110.csv",
                                          "current_20261110.csv", "voltage_20261110.csv"]              # 新的在前；谐波和备份文件不列
    assert files[0]["dir_label"] == "运行目录" and files[0]["kind"] == "voltage" and files[0]["day"] == "20261111"
    assert files[2]["quantities"] == ["p", "q"] and files[1]["quantities"] == ["pf"]
    assert len(list_curve_files([("a", str(rt))], limit=2)) == 2


# --------------------------------------------------------------------------- 接口：对着真实运行写出的文件

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    d = tmp_path_factory.mktemp("r210cfg")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(d / "cfg.json")); mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json")); mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "0")
    import app.server as srv
    with TestClient(srv.app) as c:
        yield c
        c.post("/api/engine/stop")
    mp.undo()


def _wait_finished(client, deadline_s=30.0):
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        st = client.get("/api/state").json()
        if st.get("finished") or st.get("error"):
            break
        time.sleep(0.05)
    time.sleep(0.4)                              # finished 之后运行线程还会 flush_all 一次
    return client.get("/api/state").json()


def _play(client, csv_factory, tmp_path, name="w.csv"):
    d = csv_factory(str(tmp_path / name), duration_s=3.0)
    client.put("/api/config", json={"output": {"realtime_save": True, "curve_save": {k: True for k in CURVE_KEYS}}})
    r = client.post("/api/engine/start", json={"kind": "csv_file", "path": d["path"], "block_samples": 1280, "play_start_mode": "begin"})
    assert r.status_code == 200, r.text
    st = _wait_finished(client)
    assert st.get("finished") and not st.get("error"), st
    return d


def test_monitor_endpoints_read_what_a_real_run_wrote(client, csv_factory, tmp_path):
    """真实引擎播放一份 3 秒的离线文件 → 实时落盘 → 两个接口读回来，数值与信号的解析值一致。"""
    d = _play(client, csv_factory, tmp_path)
    listing = client.get("/api/process/monitor/files").json()
    assert listing["ok"] and [q["id"] for q in listing["quantities"]] == list(QUANTITY_ORDER)
    by_kind = {f["kind"]: f for f in listing["files"]}
    assert set(by_kind) == {"voltage", "current", "power", "power_factor"}, listing["files"]        # 谐波、基波等文件不列
    assert all(f["dir_label"] and f["mtime_local"] and f["size_bytes"] > 0 for f in listing["files"])
    assert by_kind["power"]["quantities"] == ["p", "q"]

    exp = d["expected"]                                                                              # 夹具按 PT 100 / CT 15 算，这里是出厂 1 / 1
    u_rms = float(exp["u_rms_phase"]) / 100.0; i_rms = float(exp["i_rms_phase"]) / 15.0
    v = client.get("/api/process/monitor/curve", params={"path": by_kind["voltage"]["path"]})
    assert v.status_code == 200, v.text
    v = v.json()
    assert v["ok"] and v["quantity"] == "voltage" and v["fields"] == ["Ua", "Ub", "Uc"] and v["n"] >= 2
    assert v["source_id"] == 0 and v["source_ids"] == [0] and v["run_mode"] == "latest" and len(v["run_ids"]) == 1
    assert v["path_display"] and v["t_first_local"] and v["t_last_local"] and v["run_ids"][0]["started_local"]
    assert d["t"][0] <= v["t_first"] <= v["t_last"] <= d["t"][-1] + 1e-3                             # 行里的时间是数据时间
    assert all(abs(x - u_rms) / u_rms < 0.01 for x in v["series"]["Ua"]), (v["series"]["Ua"][:3], u_rms)
    c = client.get("/api/process/monitor/curve", params={"path": by_kind["current"]["path"], "quantity": "current"}).json()
    assert c["unit"] == "A" and all(abs(x - i_rms) / i_rms < 0.01 for x in c["series"]["Ia"])
    p = client.get("/api/process/monitor/curve", params={"path": by_kind["power"]["path"], "quantity": "p"}).json()
    q = client.get("/api/process/monitor/curve", params={"path": by_kind["power"]["path"], "quantity": "q"}).json()
    p_exp = float(exp["p_total"]) / 1500.0; q_exp = float(exp["q_total"]) / 1500.0
    assert p["fields"][0] == "P" and all(abs(x - p_exp) / p_exp < 0.01 for x in p["series"]["P"]), (p["series"]["P"][:3], p_exp)
    assert q["fields"][0] == "Q" and all(abs(x - q_exp) / abs(q_exp) < 0.01 for x in q["series"]["Q"]), (q["series"]["Q"][:3], q_exp)
    assert abs(sum(p["series"][k][0] for k in ("Pa", "Pb", "Pc")) - p["series"]["P"][0]) < 1e-3 * abs(p["series"]["P"][0])
    f = client.get("/api/process/monitor/curve", params={"path": by_kind["power_factor"]["path"]}).json()
    assert f["quantity"] == "pf" and all(abs(x - float(exp["pf_arith"])) < 0.01 for x in f["series"]["PF"]), f["series"]["PF"][:3]
    # 时间筛选走同一个接口；时刻写法与其他时间输入相同（epoch 秒或日期时间）
    half = client.get("/api/process/monitor/curve", params={"path": by_kind["voltage"]["path"], "t_start": repr(v["t"][1])}).json()
    assert half["n"] == v["n"] - 1 and half["t"][0] == v["t"][1]
    last = client.get("/api/process/monitor/curve", params={"path": by_kind["voltage"]["path"], "last_s": "0.001"}).json()
    assert last["n"] == 1 and last["t"][0] == v["t"][-1]


def test_saved_curve_files_can_also_be_read(client, csv_factory, tmp_path):
    """「保存曲线数据」写出的 curves_<时间>/<曲线>.csv 没有日期后缀、没有 run_id 列，多一列 quantity：手填路径时也能显示，
    读到的点与同一次运行的实时落盘文件一致。"""
    _play(client, csv_factory, tmp_path)
    before = client.get("/api/config").json()["output"]["export_dir"]
    client.put("/api/config", json={"output": {"export_dir": str(tmp_path / "exp")}})
    try:
        saved = client.post("/api/curves/save", json={"quantities": ["voltage", "power", "power_factor"], "with_branch": False})
        assert saved.status_code == 200, saved.text
        paths = {f["quantity"]: f["path"] for f in saved.json()["files"]}
    finally:
        client.put("/api/config", json={"output": {"export_dir": before}})
    assert set(paths) == {"voltage", "power", "power_factor"} and os.path.basename(paths["voltage"]) == "voltage.csv", paths
    head = open(paths["voltage"], encoding="utf-8-sig").readline().strip().split(",")
    assert "run_id" not in head and head[:5] == ["t_epoch_s", "time_local", "source_id", "quantity", "window_s"], head

    rt = {f["kind"]: f["path"] for f in client.get("/api/process/monitor/files").json()["files"]}
    for kind, quantity, field in (("voltage", "voltage", "Ua"), ("power", "p", "P"), ("power", "q", "Qa"), ("power_factor", "pf", "PF")):
        a = client.get("/api/process/monitor/curve", params={"path": paths[kind], "quantity": quantity})
        assert a.status_code == 200, a.text
        a = a.json()
        b = client.get("/api/process/monitor/curve", params={"path": rt[kind], "quantity": quantity}).json()
        assert a["quantity"] == quantity and a["fields"] == b["fields"] and a["source_id"] == 0, (kind, a["fields"], b["fields"])
        assert a["run_mode"] == "none" and a["run_ids"] == [] and a["window_s"] == b["window_s"], (a["run_mode"], a["run_ids"], a["window_s"])
        assert a["n"] >= 2 and a["t"] == b["t"], (kind, a["t"], b["t"])                      # 同一批曲线点
        assert a["series"][field] == pytest.approx(b["series"][field], rel=1e-9), (kind, field)


def test_monitor_curve_separates_repeated_runs_of_the_same_file(client, csv_factory, tmp_path):
    """同一份离线文件播放两次：两次的数据时间完全重叠，默认只显示最近一次，也可以指定某一次或全部。"""
    _play(client, csv_factory, tmp_path)
    _play(client, csv_factory, tmp_path)
    vfile = next(f for f in client.get("/api/process/monitor/files").json()["files"] if f["kind"] == "voltage")
    d = client.get("/api/process/monitor/curve", params={"path": vfile["path"]}).json()
    assert len(d["run_ids"]) == 2 and d["run_id"] == d["run_ids"][-1]["id"] and d["run_mode"] == "latest"
    # 每次运行收尾时会把最后一个点再写一遍（时刻相同），所以文件行数比点数多；读出来的曲线里同一时刻只留一个点
    assert d["run_ids"][0]["rows"] == d["run_ids"][1]["rows"] >= d["n"] and d["rows_total"] == 2 * d["run_ids"][0]["rows"]
    assert all(b > a for a, b in zip(d["t"], d["t"][1:]))
    first = client.get("/api/process/monitor/curve", params={"path": vfile["path"], "run": str(d["run_ids"][0]["id"])}).json()
    assert first["run_id"] == d["run_ids"][0]["id"] and first["t"] == d["t"]
    both = client.get("/api/process/monitor/curve", params={"path": vfile["path"], "run": "all"}).json()
    assert both["run_mode"] == "all" and both["t"] == d["t"]


def test_monitor_files_lists_run_directories(client, csv_factory, tmp_path, monkeypatch):
    """离线文件播放默认写到运行目录 output/<时间>/realtime/，文件下拉要能列出来。"""
    monkeypatch.setenv("ELEC_TOOL_RUN_DIRS", "1"); monkeypatch.setenv("ELEC_TOOL_OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.delenv("ELEC_TOOL_REALTIME_DIR", raising=False)
    _play(client, csv_factory, tmp_path)
    runs = [p for p in (tmp_path / "out").iterdir() if re.match(r"^\d{8}_\d{6}", p.name)]
    assert len(runs) == 1 and (runs[0] / "realtime").is_dir()
    files = client.get("/api/process/monitor/files").json()["files"]
    here = [f for f in files if runs[0].name in f["path"]]
    assert {f["kind"] for f in here} == {"voltage", "current", "power", "power_factor"}, files
    d = client.get("/api/process/monitor/curve", params={"path": here[0]["path"]}).json()
    assert d["ok"] and d["n"] >= 2


def test_monitor_curve_errors_are_400_with_a_readable_message(client, tmp_path, mixed_voltage):
    def err(**params):
        r = client.get("/api/process/monitor/curve", params=params)
        assert r.status_code == 400, (params, r.status_code, r.text)
        body = r.json(); assert body["ok"] is False
        return body["error"]

    assert "未填写" in err()
    assert "文件不存在" in err(path=str(tmp_path / "nope.csv"))
    assert "没有「功率因数」的列" in err(path=mixed_voltage, quantity="pf")
    assert "数据来源只能是 0" in err(path=mixed_voltage, source_id="2")
    assert "运行批次写法不对" in err(path=mixed_voltage, run="newest")
    assert "必须是数字" in err(path=mixed_voltage, last_s="abc")
    assert "结束时刻必须晚于起始时刻" in err(path=mixed_voltage, t_start=repr(T0 + 5), t_end=repr(T0 + 1))
    assert err(path=mixed_voltage, t_start="昨天").startswith("起始时刻：时间 '昨天' 无法解析")
    msg = err(path=mixed_voltage, t_end="08:00:00")                 # 报错要说清是哪个输入框，不能把结束时刻说成“起始时间”
    assert msg.startswith("结束时刻：时间 '08:00:00' 无法解析") and "起始时间" not in msg and "2026-10-12 08:00:00" in msg
    ok = client.get("/api/process/monitor/curve", params={"path": mixed_voltage, "source_id": "1", "max_points": 3})
    assert ok.status_code == 200 and ok.json()["source_id"] == 1


def test_offline_csv_modules_use_the_existing_rms_endpoint(client, csv_factory, tmp_path):
    """离线波形 CSV 模块的三项配置（文件路径、时间段、每点周波数）就是 /api/process/wave/rms 的参数。"""
    d = csv_factory(str(tmp_path / "w.csv"), duration_s=3.0)                                        # 150 个周波
    t0 = float(d["t"][0])
    full = client.get("/api/process/wave/rms", params={"path": d["path"], "agg_cycles": 1}).json()
    assert full["ok"] and full["n"] == 150 and full["agg_cycles"] == 1 and set(full["channels"]) == {"Ua", "Ub", "Uc", "Ia", "Ib", "Ic"}
    ten = client.get("/api/process/wave/rms", params={"path": d["path"], "agg_cycles": 10}).json()
    assert ten["n"] == 15 and ten["agg_cycles"] == 10 and abs((ten["t"][1] - ten["t"][0]) - 0.2) < 1e-6   # 每点 10 个周波＝0.2 s
    seg = client.get("/api/process/wave/rms", params={"path": d["path"], "agg_cycles": 5, "t_start": repr(t0 + 1.0), "t_end": repr(t0 + 2.0)}).json()
    assert seg["n"] == 10 and abs(seg["t_first"] - (t0 + 1.0)) < 1e-3 and seg["t_last"] < t0 + 2.0
    only_u = client.get("/api/process/wave/rms", params={"path": d["path"], "channels": "Ua,Ub,Uc", "pt_ratio": "100", "pt_ct_enabled": "1"}).json()
    assert set(only_u["channels"]) == {"Ua", "Ub", "Uc"}
    assert abs(only_u["channels"]["Ua"][0] / full["channels"]["Ua"][0] - 100.0) < 1e-6              # PT 变比按模块里填的值换算
    r = client.get("/api/process/wave/rms", params={"path": str(tmp_path / "nope.csv")})
    assert r.status_code == 400 and "文件不存在" in r.json()["error"]
