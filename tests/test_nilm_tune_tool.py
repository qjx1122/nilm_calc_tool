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
    assert abs(m["sigma_cycle_w"] - sigma) / sigma < 0.15 and abs(m["level_w"] - level) / level < 0.01
    assert not m["has_events_hint"]
    sg = tune.suggest(m, min_load_w=600.0)
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
