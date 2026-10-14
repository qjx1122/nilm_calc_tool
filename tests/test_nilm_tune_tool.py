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
