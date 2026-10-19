"""tools/nilm_tune.py：噪声统计与参数建议的自洽性——建议参数在同一噪声水平下「检出已知阶跃、不误报纯噪声」。"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

import numpy as np

from elec_tool.nilm import detect_steps, effective_params

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("nilm_tune", os.path.join(ROOT, "tools", "nilm_tune.py"))
tune = importlib.util.module_from_spec(spec); spec.loader.exec_module(tune)


def test_measure_recovers_sigma_and_suggestions_detect_step_not_noise():
    rng = np.random.default_rng(7)
    sigma, level = 20.0, 5000.0
    bg = level + rng.normal(0, sigma, 3000)
    m = tune.measure(bg)
    assert abs(m["sigma_cycle"] - sigma) / sigma < 0.15 and abs(m["level"] - level) / level < 0.01
    assert not m["has_events_hint"]
    sg = tune.suggest(m, min_load=600.0)
    assert sg["algorithms"]["threshold"]["min_delta_w"] == 300.0        # 最小关心负荷的一半
    # 纯噪声窗：6 种算法 0 误报（300 周波 × 10 窗）
    for w in range(10):
        seg = bg[w * 300:(w + 1) * 300]
        for algo, prm in sg["algorithms"].items():
            eff = effective_params({**prm, "enabled": True}, float(np.median(np.abs(seg))), sg["rel_tol_pct"], sg["min_delta_pct"])
            assert detect_steps(algo, seg, eff) == [], (algo, w)
    # 含 +600 W 阶跃（恰为最小关心负荷）的窗：6 种算法都检出、方向幅值正确
    seg = bg[:300].copy(); seg[150:] += 600.0
    for algo, prm in sg["algorithms"].items():
        eff = effective_params({**prm, "enabled": True}, float(np.median(np.abs(seg))), sg["rel_tol_pct"], sg["min_delta_pct"])
        st = detect_steps(algo, seg, eff)
        assert len(st) == 1 and abs(st[0][0] - 150) <= 2 and abs((st[0][3] - st[0][2]) - 600) < 60, (algo, st)


def test_cli_runs_on_sample(tmp_path):
    sample = os.path.join(ROOT, "data", "nilm_steps.csv")
    if not os.path.exists(sample):
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_nilm_sample.py")], check=True, cwd=ROOT)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_tune.py"), "--file", sample, "--min-load-w", "300000", "--json"],
                       capture_output=True, text=True, cwd=ROOT, check=True)
    import json
    d = json.loads(r.stdout)
    assert d["measure"]["has_events_hint"] and d["suggest"]["algorithms"]["cusum"]["threshold_w"] > 0
    assert set(d["suggest"]["algorithms"]) == {"threshold", "two_window", "cusum", "glr", "steady_state", "median_diff"}


def test_suggest_relative_thresholds_stay_valid_when_base_load_small():
    """v0.22.2：分路侧基荷很小（设备关着时 P≈100 W）而设备很大时，min_delta_pct 曾算出 >100%，
    导致界面「保存参数」/ PUT /api/config 报「nilm.min_delta_pct 必须在 0~100」。"""
    import numpy as np
    from elec_tool.config import AppConfig
    from tools.nilm_tune import measure, suggest
    p = 100 + np.random.default_rng(0).normal(0, 2, 3000)
    sg = suggest(measure(p), 5000)
    assert sg["min_delta_pct"] == 0.0 and 0 <= sg["rel_tol_pct"] <= 50 and "置 0" in sg["note"]
    cfg = AppConfig(); cfg.nilm.rel_tol_pct = sg["rel_tol_pct"]; cfg.nilm.min_delta_pct = sg["min_delta_pct"]
    cfg.nilm.algorithms.update({k: dict(cfg.nilm.algorithms[k], **v) for k, v in sg["algorithms"].items()})
    cfg.validate()
    # 基荷大时仍给出有意义的相对值
    big = suggest(measure(1.5e6 + np.random.default_rng(1).normal(0, 30, 3000)), 300000)
    assert 0 < big["min_delta_pct"] <= 50


def test_measure_suggest_current_unit_gives_a_params_that_detect_step_not_noise():
    """v0.38：I 口径——measure(unit="A") → suggest 给 *_a 参数；经 params_for_current 后 6 算法纯噪声 0 误报、2 A 阶跃全检出。"""
    from elec_tool.nilm import params_for_current
    rng = np.random.default_rng(11)
    sigma, level = 0.02, 6.0
    bg = level + rng.normal(0, sigma, 3000)
    m = tune.measure(bg, "A")
    assert m["unit"] == "A" and abs(m["sigma_cycle"] - sigma) / sigma < 0.15
    sg = tune.suggest(m, 2.0)
    assert sg["unit"] == "A" and sg["quantity"] == "i"
    for algo, prm in sg["algorithms"].items():
        assert not any(k.endswith("_w") for k in prm), (algo, prm)
    assert sg["algorithms"]["threshold"]["min_delta_a"] == 1.0 and sg["algorithms"]["cusum"]["threshold_a"] > sg["algorithms"]["cusum"]["drift_a"]
    # 建议值能通过配置校验
    from elec_tool.config import AppConfig
    cfg = AppConfig(); cfg.nilm.quantity = "i"; cfg.nilm.rel_tol_pct = sg["rel_tol_pct"]; cfg.nilm.min_delta_pct = sg["min_delta_pct"]
    cfg.nilm.algorithms.update({k: dict(cfg.nilm.algorithms[k], **v) for k, v in sg["algorithms"].items()})
    cfg.validate()
    for w in range(10):
        seg = bg[w * 300:(w + 1) * 300]
        for algo, prm in sg["algorithms"].items():
            eff = effective_params(params_for_current({**cfg.nilm.algorithms[algo], "enabled": True}), float(np.median(np.abs(seg))), sg["rel_tol_pct"], sg["min_delta_pct"])
            assert detect_steps(algo, seg, eff) == [], (algo, w)
    seg = bg[:300].copy(); seg[150:] += 2.0
    for algo, prm in sg["algorithms"].items():
        eff = effective_params(params_for_current({**cfg.nilm.algorithms[algo], "enabled": True}), float(np.median(np.abs(seg))), sg["rel_tol_pct"], sg["min_delta_pct"])
        st = detect_steps(algo, seg, eff)
        assert len(st) == 1 and abs(st[0][0] - 150) <= 2 and abs((st[0][3] - st[0][2]) - 2.0) < 0.2, (algo, st)


def test_cli_current_only_auto_picks_i_and_replay_check_roundtrip(tmp_path):
    """v0.38：仅电流样例 → nilm_tune auto 选 I 并给 *_a；--quantity p 明确报错；nilm_replay --params 套用后 6 算法各 2 事件（unit=A）；
    nilm_check 用 --mag-a 按 |ΔI| 归属。"""
    import json
    sample = os.path.join(ROOT, "data", "nilm_steps_i.csv")
    if not os.path.exists(sample):
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_nilm_sample.py"), "--current-only"], check=True, cwd=ROOT)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_tune.py"), "--file", sample, "--min-load-a", "30", "--json"],
                       capture_output=True, text=True, cwd=ROOT, check=True)
    d = json.loads(r.stdout)
    assert d["quantity"] == "i" and d["unit"] == "A" and d["voltage_present"] is False
    assert d["suggest"]["algorithms"]["threshold"]["min_delta_a"] == 15.0 and "min_delta_w" not in d["suggest"]["algorithms"]["threshold"]
    bad = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_tune.py"), "--file", sample, "--quantity", "p"],
                         capture_output=True, text=True, cwd=ROOT)
    assert bad.returncode == 2 and "没有电压" in bad.stderr
    tune_json = tmp_path / "tune.json"; tune_json.write_text(r.stdout, encoding="utf-8")
    out = tmp_path / "ev.csv"
    rp = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_replay.py"), "--file", sample, "--params", str(tune_json), "--out", str(out)],
                        capture_output=True, text=True, cwd=ROOT, check=True)
    assert "nilm.quantity = i" in rp.stdout and "幅值范围(A)" in rp.stdout
    import csv
    rows = list(csv.DictReader(open(out, encoding="utf-8-sig", newline="")))
    assert len(rows) == 12 and all(r_["unit"] == "A" and r_["quantity"] == "i" for r_ in rows)
    ups = sorted(float(r_["magnitude"]) for r_ in rows if r_["direction"] == "up")
    assert all(abs(x - 83.3) < 0.5 for x in ups)
    # 真值表用事件文件里的本地时间文本（与 nilm_check 同一本机时区解释）
    up_local = next(r_["t_start_local"] for r_ in rows if r_["direction"] == "up")
    dn_local = next(r_["t_start_local"] for r_ in rows if r_["direction"] == "down")
    truth = tmp_path / "truth.csv"; truth.write_text(f"时间,动作,备注\n{up_local},开,x\n{dn_local},关,x\n", encoding="utf-8")
    ck = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_check.py"), "--events", str(out), "--truth", str(truth), "--tol-s", "0.5"],
                        capture_output=True, text=True, cwd=ROOT, check=True)
    assert "✅ 6 种算法全部命中且 0 误报" in ck.stdout and "|ΔI| 均值，A" in ck.stdout
    ck2 = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_check.py"), "--events", str(out), "--truth", str(truth), "--tol-s", "0.5",
                          "--mag-a", "83", "--mag-tol-pct", "30"], capture_output=True, text=True, cwd=ROOT)
    assert ck2.returncode == 1 and "幅值带 58.1~107.9 A" in ck2.stdout and "min_delta_a" in ck2.stdout      # 50 A 的切除事件带外 → 记「其它设备」、漏 1
