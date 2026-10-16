"""v0.22：现场实施手册配套脚本 tools/nilm_replay.py（离线回放）与 tools/nilm_check.py（真值对账）。"""
from __future__ import annotations

import csv
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
SAMPLE = ROOT / "data" / "nilm_steps.csv"


def _run(*args, check=True):
    r = subprocess.run([PY, *args], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    if check:
        assert r.returncode == 0, r.stdout + r.stderr
    return r


@pytest.fixture(scope="module")
def sample():
    if not SAMPLE.is_file():
        _run("tools/gen_nilm_sample.py")
    return SAMPLE


@pytest.fixture()
def truth(tmp_path):
    p = tmp_path / "truth.csv"
    # 样例：2.0 s 投入、4.4 s 切除；第二行只写时刻（按事件文件日期补齐）
    p.write_text("时间,动作,备注\n2026-10-13 08:00:02,开,样例\n08:00:04.4,关,样例\n", encoding="utf-8-sig")
    return p


def test_replay_default_params_and_check(sample, truth, tmp_path):
    out = tmp_path / "ev.csv"
    r = _run("tools/nilm_replay.py", "--file", str(sample), "--out", str(out))
    assert "各算法事件数" in r.stdout and out.is_file()
    rows = list(csv.DictReader(open(out, encoding="utf-8-sig")))
    assert rows and set(rows[0]) >= {"source_id", "algorithm", "t_start", "direction", "magnitude_w"}
    assert {x["algorithm"] for x in rows} >= {"threshold", "cusum", "glr", "steady_state", "median_diff", "two_window"}
    # 对账：默认参数下 two_window 把 3.0 s 的尖峰误报 1 条，其余 5 种全部命中 0 误报 → 总结论可上线（exit 0）
    detail = tmp_path / "check.csv"
    r = _run("tools/nilm_check.py", "--events", str(out), "--truth", str(truth), "--tol-s", "0.5", "--out", str(detail))
    assert "✅ 可上线" in r.stdout and "two_window" in r.stdout and "误报" in r.stdout
    assert "种算法全部命中且 0 误报" in r.stdout
    det = list(csv.DictReader(open(detail, encoding="utf-8-sig")))
    assert any(d["算法"] == "two_window" and d["结果"] == "误报" for d in det)
    assert sum(1 for d in det if d["算法"] == "threshold" and d["结果"] == "命中") == 2


def test_tune_replay_check_loop(sample, truth, tmp_path):
    tune = tmp_path / "tune.json"
    r = _run("tools/nilm_tune.py", "--file", str(sample), "--min-load-w", "300000", "--json")
    tune.write_text(r.stdout, encoding="utf-8")
    assert "suggest" in json.loads(r.stdout)
    out = tmp_path / "ev.csv"; site = tmp_path / "site.json"
    r = _run("tools/nilm_replay.py", "--file", str(sample), "--params", str(tune), "--set", "glr.enabled=0",
             "--set", "nilm.min_gap_cycles=25", "--save-config", str(site), "--out", str(out))
    assert "glr             (关闭)" in r.stdout or "(关闭)" in r.stdout
    cfg = json.load(open(site, encoding="utf-8"))
    assert cfg["nilm"]["algorithms"]["glr"]["enabled"] is False and cfg["nilm"]["min_gap_cycles"] == 25
    assert cfg["nilm"]["algorithms"]["threshold"]["min_delta_w"] == json.loads(tune.read_text(encoding="utf-8"))["suggest"]["algorithms"]["threshold"]["min_delta_w"]
    assert not any(x["algorithm"] == "glr" for x in csv.DictReader(open(out, encoding="utf-8-sig")))
    # 建议参数下：尖峰不再误报，5 种启用算法全部 ✅
    r = _run("tools/nilm_check.py", "--events", str(out), "--truth", str(truth), "--tol-s", "0.5")
    assert "5 种算法全部命中且 0 误报" in r.stdout, r.stdout


def test_check_detects_miss_and_exit_code(sample, truth, tmp_path):
    out = tmp_path / "ev.csv"
    # 门槛抬到 2 MW：全部漏报 → 结论 ✗、退出码 1
    _run("tools/nilm_replay.py", "--file", str(sample), "--set", "nilm.min_delta_pct=80", "--out", str(out), "--quiet")
    r = _run("tools/nilm_check.py", "--events", str(out), "--truth", str(truth), check=False)
    assert r.returncode == 1 and "没有算法达标" in r.stdout


def test_check_bad_action_message(sample, tmp_path):
    out = tmp_path / "ev.csv"
    _run("tools/nilm_replay.py", "--file", str(sample), "--out", str(out), "--quiet")
    bad = tmp_path / "bad.csv"; bad.write_text("时间,动作\n2026-10-13 08:00:02,打开\n", encoding="utf-8")
    r = _run("tools/nilm_check.py", "--events", str(out), "--truth", str(bad), check=False)
    assert r.returncode != 0 and "不认识" in (r.stdout + r.stderr)


def test_guide_mentions_scripts_and_steps():
    md = (ROOT / "NILM_TUNING_GUIDE.md").read_text(encoding="utf-8")
    for s in ("nilm_tune.py", "nilm_replay.py", "nilm_check.py", "truth.csv", "--save-config", "/api/branch/config",
              "Invoke-RestMethod", "✅ 可上线", "打勾清单", "--set threshold.min_delta_w", "--mag-w", "--signature-from", "其它设备", "检测 ≠ 归属"):
        assert s in md, s


# ---------------------------------------------------------------- v0.22.1：总线上还有其它设备启停
BUS = ROOT / "data" / "nilm_bus_mixed.csv"


@pytest.fixture(scope="module")
def bus_sample():
    if not BUS.is_file():
        _run("tools/gen_nilm_sample.py", "--bus")
    return BUS


def test_mixed_bus_other_devices_are_not_false_alarms(bus_sample, tmp_path):
    truth = tmp_path / "truth.csv"
    truth.write_text("时间,动作,备注\n2026-10-13 08:00:02,开,待检\n08:00:06,关,待检\n", encoding="utf-8-sig")
    ev = tmp_path / "ev.csv"
    _run("tools/nilm_replay.py", "--file", str(bus_sample), "--out", str(ev), "--quiet")
    # 不带指纹：其它设备的 3 次动作全被算成误报 → 没有算法 ✅
    r = _run("tools/nilm_check.py", "--events", str(ev), "--truth", str(truth), "--tol-s", "0.5", check=False)
    assert r.returncode == 1 and "带内误报" in r.stdout and "没有算法达标" in r.stdout
    # 带幅值指纹（500 W 二次侧 × PT·CT 1500 = 750 kW）：带外事件归「其它设备」，6 种全 ✅
    r = _run("tools/nilm_check.py", "--events", str(ev), "--truth", str(truth), "--tol-s", "0.5", "--mag-w", "750000", "--mag-tol-pct", "30",
             "--out", str(tmp_path / "d.csv"))
    assert "6 种算法全部命中且 0 误报" in r.stdout and "不计误报" in r.stdout, r.stdout
    det = list(csv.DictReader(open(tmp_path / "d.csv", encoding="utf-8-sig")))
    assert sum(1 for d in det if d["算法"] == "threshold" and d["结果"].startswith("其它设备")) == 3
    assert not any(d["结果"] == "误报" for d in det)
    # 真值表登记「其它」行：同样不算误报
    truth2 = tmp_path / "truth2.csv"
    truth2.write_text("时间,动作,备注\n2026-10-13 08:00:02,开,待检\n08:00:06,关,待检\n08:00:03.5,其它,大设备\n08:00:08,其它,大设备\n08:00:05,其它,小设备\n", encoding="utf-8-sig")
    r = _run("tools/nilm_check.py", "--events", str(ev), "--truth", str(truth2), "--tol-s", "0.5")
    assert "6 种算法全部命中且 0 误报" in r.stdout
    # 指纹来自设备侧回放文件（时刻用设备侧自己的真值表）
    dev_ev = tmp_path / "dev.csv"
    _run("tools/nilm_replay.py", "--file", str(ROOT / "data" / "nilm_steps.csv"), "--out", str(dev_ev), "--quiet")
    dev_truth = tmp_path / "dev_truth.csv"; dev_truth.write_text("时间,动作\n2026-10-13 08:00:02,开\n", encoding="utf-8")
    r = _run("tools/nilm_check.py", "--events", str(ev), "--truth", str(truth), "--tol-s", "0.5",
             "--signature-from", str(dev_ev), "--signature-truth", str(dev_truth))
    assert "设备指纹" in r.stdout and "6 种算法全部命中且 0 误报" in r.stdout
    # 指纹给错（1500 W 大设备的 2.25 MW）：待检设备被判带外 → 全漏
    r = _run("tools/nilm_check.py", "--events", str(ev), "--truth", str(truth), "--tol-s", "0.5", "--mag-w", "2250000", check=False)
    assert r.returncode == 1 and "全漏" in r.stdout
