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
    # v0.39：I 口径只能单相——默认配置 channels=[total] → A/B/C 各自检测，6 算法 × 3 相 × 2 事件；A 相 ΔI ≈ 48.1 A（一次侧）
    assert len(rows) == 36 and all(r_["unit"] == "A" and r_["quantity"] == "i" and r_["channel"] in ("A", "B", "C") for r_ in rows)
    ups = sorted(float(r_["magnitude"]) for r_ in rows if r_["direction"] == "up")
    assert all(abs(x - 48.1) < 0.5 for x in ups)
    # 真值表用事件文件里的本地时间文本（与 nilm_check 同一本机时区解释）
    up_local = next(r_["t_start_local"] for r_ in rows if r_["direction"] == "up")
    dn_local = next(r_["t_start_local"] for r_ in rows if r_["direction"] == "down")
    truth = tmp_path / "truth.csv"; truth.write_text(f"时间,动作,备注\n{up_local},开,x\n{dn_local},关,x\n", encoding="utf-8")
    ck0 = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_check.py"), "--events", str(out), "--truth", str(truth), "--tol-s", "0.5"],
                         capture_output=True, text=True, cwd=ROOT)
    assert "请加 --channel" in ck0.stdout and "带内误报" in ck0.stdout                    # 三相事件混在一起 → 提示指定对象
    ck = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_check.py"), "--events", str(out), "--truth", str(truth), "--tol-s", "0.5", "--channel", "A"],
                        capture_output=True, text=True, cwd=ROOT, check=True)
    assert "✅ 6 种算法全部命中且 0 误报" in ck.stdout and "|ΔI| 均值，A" in ck.stdout
    ck2 = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_check.py"), "--events", str(out), "--truth", str(truth), "--tol-s", "0.5", "--channel", "A",
                          "--mag-a", "48", "--mag-tol-pct", "30"], capture_output=True, text=True, cwd=ROOT)
    assert ck2.returncode == 1 and "幅值带 33.6~62.4 A" in ck2.stdout and "min_delta_a" in ck2.stdout      # 28.9 A 的切除事件带外 → 记「其它设备」、漏 1


def test_cli_quantity_defaults_to_config_nilm_quantity(tmp_path):
    """v0.45：配置里 nilm.quantity=i、文件有电压时，不传 --quantity 也应按 I 调参（此前默认 auto 只看电压 → 给出 W 参数）。"""
    import json
    from elec_tool.config import AppConfig
    sample = os.path.join(ROOT, "data", "nilm_steps.csv")
    cfg = AppConfig(); cfg.nilm.quantity = "i"; cfg.nilm.channels = ["A"]
    cfgp = tmp_path / "site.json"; cfg.save(str(cfgp))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_tune.py"), "--file", sample, "--config", str(cfgp), "--json"],
                       capture_output=True, text=True, cwd=ROOT, check=True)
    d = json.loads(r.stdout)
    assert d["quantity"] == "i" and d["quantity_requested"] == "i" and d["voltage_present"] is True and d["unit"] == "A"
    assert "min_delta_a" in d["suggest"]["algorithms"]["threshold"] and "min_delta_w" not in d["suggest"]["algorithms"]["threshold"]
    # 命令行显式 --quantity p 仍可覆盖配置
    r2 = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nilm_tune.py"), "--file", sample, "--config", str(cfgp), "--quantity", "p", "--json"],
                        capture_output=True, text=True, cwd=ROOT, check=True)
    assert json.loads(r2.stdout)["quantity"] == "p"


def test_suggest_enlarges_steady_state_for_soft_start_ramp():
    """v0.56：含 40 s 软启斜坡的分路侧电流 → 量出最长暂态，steady_state.max_transient_cycles / min_steady_cycles 自动放大，
    并给 window_cycles；放大后稳态分段把整条斜坡配成一个事件（1.66 → 4.56 A），默认 100 周波时只报硬跳变。"""
    from elec_tool.nilm import params_for_current
    from elec_tool.config import NILM_ALGO_DEFAULTS, AppConfig
    rng = np.random.default_rng(3)
    x = np.full(9000, 1.66)
    x[2000:2010] += 0.7                                   # 起动冲击
    x[2010:4000] = np.linspace(2.14, 4.56, 1990)          # ≈40 s 斜坡
    x[4000:6000] = 4.56
    x[6000:6500] = np.linspace(4.56, 3.4, 500)            # 10 s 斜坡降
    x[6500:7500] = 3.4
    x[7500:] = 1.73
    x += rng.normal(0, 0.019, x.size)
    m = tune.measure(x, "A")
    sg = tune.suggest(m, 0.42, x)
    tr = sg["transient"]
    assert 1800 <= tr["longest"] <= 2200 and tr["n_transients"] >= 3
    ss = sg["algorithms"]["steady_state"]
    assert ss["max_transient_cycles"] >= 1.5 * tr["longest"] and ss["min_steady_cycles"] > tr["max_pseudo_steady"]
    assert sg["window_cycles"] >= ss["max_transient_cycles"] + 2 * ss["min_steady_cycles"]
    assert "慢启动" in sg["note"]
    lvl = float(np.median(np.abs(x)))

    def run(prm):
        eff = effective_params(params_for_current({**NILM_ALGO_DEFAULTS["steady_state"], **prm, "enabled": True}), lvl, sg["rel_tol_pct"], sg["min_delta_pct"])
        return detect_steps("steady_state", x, eff)
    st = run(ss)
    ramp = [s for s in st if abs(s[2] - 1.66) < 0.1 and abs(s[3] - 4.56) < 0.1]
    assert len(ramp) == 1 and 1900 <= ramp[0][1] - ramp[0][0] <= 2300, st
    st0 = run({**ss, "max_transient_cycles": 100, "min_steady_cycles": 10})
    assert not [s for s in st0 if abs(s[3] - 4.56) < 0.1]           # 默认参数看不到斜坡
    # 套用：window_cycles 只放大不缩小
    from elec_tool.nilm_tuning import apply_nilm_params
    cfg = AppConfig()
    notes = apply_nilm_params(cfg, sg)
    assert cfg.nilm.window_cycles == sg["window_cycles"] and any("window_cycles" in n for n in notes)
    assert cfg.nilm.algorithms["steady_state"]["max_transient_cycles"] == ss["max_transient_cycles"]
    cfg.validate()
    cfg2 = AppConfig(); cfg2.nilm.window_cycles = 99999
    apply_nilm_params(cfg2, sg)
    assert cfg2.nilm.window_cycles == 99999


def test_suggest_keeps_default_transient_params_for_clean_steps_and_pure_noise():
    rng = np.random.default_rng(5)
    y = np.full(3000, 5000.0); y[1500:] += 600; y += rng.normal(0, 20, 3000)
    sg = tune.suggest(tune.measure(y), 600, y)
    assert sg["transient"]["longest"] <= 100 and sg["transient"]["n_transients"] == 1
    assert sg["algorithms"]["steady_state"]["max_transient_cycles"] == 100 and sg["algorithms"]["steady_state"]["min_steady_cycles"] == 10
    assert "window_cycles" not in sg
    z = 5000 + rng.normal(0, 20, 3000)
    sg = tune.suggest(tune.measure(z), 600, z)
    assert sg["transient"]["n_transients"] == 0 and sg["algorithms"]["steady_state"]["max_transient_cycles"] == 100
    assert tune.suggest(tune.measure(z), 600)["transient"] is None     # 不给序列 → 向后兼容


def test_estimate_min_load_handles_ramps_split_steps_and_ripple():
    """v0.57 复查修复：旧实现按相邻周波 |Δ|>8σ 切段，(a) 软启斜坡切不开 → 斜坡+平台并成一段、中位数无意义、候选错却标可靠；
    (b) 跨周波边界劈成两半的阶跃（每半 <8σ）同样切不开；(c) 纹波时也应稳定。现在与 longest_transient 共用"是否在动"掩码。"""
    from elec_tool.nilm_tuning import estimate_min_load
    rng = np.random.default_rng(3)
    # (a) 现场形状：1.66 → 冲击 → 40 s 斜坡 → 4.56 → 斜坡降 → 3.40 → 1.73；真实最小一次投切 = 1.16 A（4.56→3.40）
    x = np.full(9000, 1.66); x[2000:2010] += 0.7; x[2010:4000] = np.linspace(2.14, 4.56, 1990); x[4000:6000] = 4.56
    x[6000:6500] = np.linspace(4.56, 3.4, 500); x[6500:7500] = 3.4; x[7500:] = 1.73; x += rng.normal(0, 0.019, x.size)
    e = estimate_min_load(x, tune.measure(x, "A")["sigma_cycle"], "A")
    assert e["reliable"] and abs(e["candidate"] - 1.16) < 0.03 and e["candidate_from"] == "step", e
    assert [round(v, 1) for v in e["levels"]] == [1.7, 3.4, 4.6], e["levels"]
    # (b) 300 W 阶跃被劈成 150+150（每半 7.5σ）+ 后面 600 W：候选应是 300（不可靠：< 20σ=400，但数值要对）
    y = np.full(3000, 5000.0); y[1000] = 5150; y[1001:] = 5300; y[2000:] += 600; y += rng.normal(0, 20, 3000)
    e = estimate_min_load(y, tune.measure(y)["sigma_cycle"])
    assert abs(e["candidate"] - 300) < 30 and len(e["levels"]) == 3 and not e["reliable"], e
    # (c) 叠加 30 W / 100 周波的纹波（差分 MAD 低估 σ）：仍只有 2 个台阶、候选 600
    z = 5000 + 30 * np.sin(np.arange(3000) * 2 * np.pi / 100) + rng.normal(0, 20, 3000); z[1500:] += 600
    e = estimate_min_load(z, tune.measure(z)["sigma_cycle"])
    assert e["reliable"] and abs(e["candidate"] - 600) < 30 and len(e["levels"]) == 2, e
    # 两个不相邻状态之差小于任何一次直接投切 → candidate_from=level_gap 并在 note 里说明
    u = np.concatenate([np.full(600, 1.66), np.full(600, 4.56), np.full(600, 3.33), np.full(600, 1.73), np.full(600, 1.30)]) + rng.normal(0, 0.006, 3000)
    e = estimate_min_load(u, 0.006, "A")
    assert e["candidate_from"] == "level_gap" and abs(e["candidate"] - 0.07) < 0.01 and "不相邻状态" in e["note"], e
