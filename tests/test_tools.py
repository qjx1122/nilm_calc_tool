#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ 下两个联调工具的防腐测试。

为什么要有：`tools/csv_appender.py`（模拟采集器写文件）与 `tools/verify_sources.py`（库级四源验证）
是**交付物的一部分**——用户没有真实采集装置时靠它们复现验证。工具一旦悄悄坏掉，
README/REPORT_TEST 里的验证步骤就成了空头承诺，所以这里钉住它们的关键行为。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.conftest import HEADER_CN

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def _run(args: list[str], timeout: float = 180.0) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *args], cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def test_csv_appender_writes_user_column_format(tmp_path):
    """追加器必须按用户给定的列格式落盘：`时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流`。"""
    out = tmp_path / "live.csv"
    r = _run(["tools/csv_appender.py", "--out", str(out), "--rate", "20",
              "--block", "640", "--duration", "0.3"])
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == HEADER_CN, f"表头与用户约定不符：{lines[0]}"
    assert len(lines) > 640, "0.3s×20 倍速应写出数千行"
    cells = lines[1].split(",")
    assert len(cells) == 7
    vals = [float(c) for c in cells]                 # 全部可解析为数值
    assert vals[0] > 1.7e9, "时间戳应是 epoch 秒"
    assert 40.0 < vals[1] < 80.0, f"A 相电压应在二次侧 57.7V 附近，实得 {vals[1]}"
    assert "✓ 结束" in r.stdout


def test_csv_appender_no_header_and_rotate(tmp_path):
    """--no-header 验证无表头解析路径；--rotate-every 验证分片轮转（目录模式的采集侧）。"""
    d = tmp_path / "shards"
    r = _run(["tools/csv_appender.py", "--out", str(d), "--rotate-every", "2",
              "--rate", "20", "--block", "640", "--duration", "0.3", "--no-header"])
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
    shards = sorted(d.glob("part_*.csv"))
    assert len(shards) >= 2, "按 2 块轮转应产生多个分片"
    first = shards[0].read_text(encoding="utf-8").splitlines()
    cells = first[0].split(",")
    assert len(cells) == 7
    assert float(cells[0]) > 1.7e9, "--no-header 时首行应直接是数据（epoch 秒），不是表头"
    assert "↻ 轮转到新文件" in r.stdout


def test_verify_sources_simulator_passes_and_matches_analytic():
    """验证工具自身必须能跑通并 PASS，且解析解常量与用户工况一致（PT=100/CT=15/fs=6400）。"""
    # --duration 必须 >最长窗（1s）＋余量，否则 voltage/power 还没出结果
    r = _run(["tools/verify_sources.py", "--kinds", "simulator", "--duration", "2.5", "--json"])
    assert r.returncode == 0, r.stdout[-1200:] + r.stderr[-600:]
    d = json.loads(r.stdout)
    assert abs(d["analytic"]["U1_V"] - 100.0 / 3 ** 0.5 * 100.0) < 0.01
    assert d["analytic"]["I1_A"] == 75.0 and d["analytic"]["pt"] == 100.0 and d["analytic"]["ct"] == 15.0
    case = d["cases"][0]
    assert case["verdict"] == "PASS", case.get("why")
    assert case["n_gaps"] == 0 and case["outputs"] >= 1
    assert abs(sum(case["U1_abc"]) / 3 - d["analytic"]["U1_V"]) / d["analytic"]["U1_V"] < 5e-4
    assert abs(case["f_used"] - 50.0) < 5e-3


def test_verify_sources_tcp_without_feeder_skips_with_hint():
    """没有采集侧时必须是 SKIP＋可操作提示（退出码 0），不能崩成 traceback。"""
    r = _run(["tools/verify_sources.py", "--kinds", "tcp_text", "--external-feeders",
              "--tcp-port-text", "1", "--duration", "1", "--json"])
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    case = json.loads(r.stdout)["cases"][0]
    assert case["verdict"] == "SKIP"
    assert "tcp_feeder" in case["reason"]


def test_verify_sources_rejects_unknown_case():
    """参数错误用退出码 2 区分于验证失败（1），便于脚本编排。"""
    r = _run(["tools/verify_sources.py", "--kinds", "not_a_source"])
    assert r.returncode == 2
