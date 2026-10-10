"""自检与 CLI 端到端测试（真实子进程执行，不是 import 后调函数）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from elec_tool.selftest import run_selftest, summarize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run_cli(*args, expect_code=0, timeout=600):
    cmd = [PY, os.path.join(ROOT, "cli.py"), *args]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if expect_code is not None:
        assert proc.returncode == expect_code, (
            f"命令 {args} 退出码 {proc.returncode}（期望 {expect_code}）\n"
            f"--- stdout ---\n{proc.stdout[-4000:]}\n--- stderr ---\n{proc.stderr[-4000:]}")
    return proc


# ---------------------------------------------------------------- 自检

def test_selftest_all_pass():
    s = summarize(run_selftest(fs=6400.0, f=50.0, pt=100.0, ct=15.0, duration_s=1.0))
    assert s["all_ok"], s["failures"]
    assert s["total"] >= 40
    assert s["worst_rel_err"] < 1e-3


@pytest.mark.parametrize("fs,pt,ct,freq", [(6400.0, 100.0, 15.0, 50.0),
                                           (12800.0, 200.0, 30.0, 50.0),
                                           (6400.0, 100.0, 15.0, 60.0)])
def test_selftest_other_conditions(fs, pt, ct, freq):
    """换采样率/变比/额定频率仍应全通过（证明口径不是硬编码 6400/50）。"""
    if freq == 60.0 and fs == 6400.0:
        pytest.skip("60Hz 下 50 次谐波=3000Hz，接近 6400Hz 的 Nyquist(3200Hz)，另行测试")
    s = summarize(run_selftest(fs=fs, f=freq, pt=pt, ct=ct, duration_s=1.0))
    assert s["all_ok"], s["failures"]


def test_selftest_harmonic_limit_guard():
    """fs=6400、f=50 时最高 63 次；配到 64 次以上必须在配置校验阶段报错。"""
    from elec_tool.config import AppConfig, ConfigError
    cfg = AppConfig()
    cfg.harmonic.order_max = 64
    with pytest.raises(ConfigError):
        cfg.validate()


# ---------------------------------------------------------------- CLI

def test_cli_version_and_help():
    proc = run_cli("--version")
    assert "elec_tool" in proc.stdout
    proc = run_cli("--help")
    for sub in ("init-config", "gen-sample", "selftest", "sources", "compute", "live", "serve"):
        assert sub in proc.stdout


def test_cli_selftest_exit_code():
    proc = run_cli("selftest")
    assert "通过率 100.0%" in proc.stdout
    assert "失败 0" in proc.stdout


def test_cli_selftest_json():
    proc = run_cli("selftest", "--json")
    data = json.loads(proc.stdout)
    assert data["summary"]["all_ok"] is True
    assert len(data["checks"]) >= 40
    assert all("expected" in c and "actual" in c and "rel_err" in c for c in data["checks"])


def test_cli_init_config(tmp_path):
    out = str(tmp_path / "cfg.json")
    proc = run_cli("init-config", "--out", out, "--pt", "200", "--ct", "30", "--fs", "12800")
    assert os.path.isfile(out)
    cfg = json.load(open(out, encoding="utf-8"))
    assert cfg["transform"]["pt_ratio"] == 200.0
    assert cfg["transform"]["ct_ratio"] == 30.0
    assert cfg["sampling"]["fs"] == 12800.0
    assert set(cfg["windows"]) >= {"voltage", "current", "power", "power_factor",
                                   "fundamental", "harmonic", "spectrum"}
    # 覆盖已存在文件需 --force
    proc = run_cli("init-config", "--out", out, expect_code=2)
    assert "已存在" in proc.stderr
    run_cli("init-config", "--out", out, "--force")


def test_cli_gen_sample_and_sources(tmp_path):
    csvp = str(tmp_path / "s.csv")
    proc = run_cli("gen-sample", "--out", csvp, "--duration", "1", "--config", str(tmp_path / "nope.json"))
    assert os.path.isfile(csvp)
    with open(csvp, encoding="utf-8") as fh:
        header = fh.readline().strip()
        rows = sum(1 for _ in fh)
    assert header == "时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流"
    assert rows == 6400
    proc = run_cli("sources", "--file", csvp, "--config", str(tmp_path / "nope.json"))
    assert "列映射" in proc.stdout and "推算采样率" in proc.stdout
    # ISO 时间戳格式同样可用
    csvp2 = str(tmp_path / "s_iso.csv")
    run_cli("gen-sample", "--out", csvp2, "--duration", "0.5", "--ts-format", "iso",
            "--config", str(tmp_path / "nope.json"))
    proc = run_cli("sources", "--file", csvp2, "--config", str(tmp_path / "nope.json"))
    assert "datetime" in proc.stdout


def test_cli_compute_table(tmp_path):
    csvp = str(tmp_path / "c.csv")
    run_cli("gen-sample", "--out", csvp, "--duration", "3", "--config", str(tmp_path / "nope.json"))
    proc = run_cli("compute", "--file", csvp, "--config", str(tmp_path / "nope.json"), "--format", "table")
    for token in ("[voltage]", "[current]", "[power]", "[power_factor]", "[fundamental]",
                  "[harmonic]", "[spectrum]", "有功 P", "功率因数 PF", "THD_U", "各量输出次数"):
        assert token in proc.stdout, f"输出缺少 {token}"
    # 一次侧量纲正确：U1≈5773.5V
    assert "5773" in proc.stdout or "5.773" in proc.stdout


def test_cli_compute_window_override(tmp_path):
    """需求⑥：--set-window 改窗长后，输出次数与窗元信息应随之变化。"""
    csvp = str(tmp_path / "w.csv")
    run_cli("gen-sample", "--out", csvp, "--duration", "4", "--config", str(tmp_path / "nope.json"))
    proc = run_cli("compute", "--file", csvp, "--config", str(tmp_path / "nope.json"),
                   "--set-window", "voltage=2", "--set-window", "harmonic=0.2", "--format", "json")
    lines = [json.loads(l) for l in proc.stdout.splitlines() if l.startswith("{")]
    v_wins = {q["window"]["length_s_requested"] for r in lines for q in [r["quantities"].get("voltage")] if q}
    h_wins = {q["window"]["length_s_requested"] for r in lines for q in [r["quantities"].get("harmonic")] if q}
    assert v_wins == {2.0}
    assert h_wins == {0.2}
    n_v = sum(1 for r in lines if "voltage" in r["quantities"])
    n_h = sum(1 for r in lines if "harmonic" in r["quantities"])
    assert n_h > n_v * 3, (n_h, n_v)


def test_cli_compute_csv_export(tmp_path):
    csvp = str(tmp_path / "e.csv")
    outp = str(tmp_path / "out" / "r.csv")
    run_cli("gen-sample", "--out", csvp, "--duration", "2", "--config", str(tmp_path / "nope.json"))
    run_cli("compute", "--file", csvp, "--config", str(tmp_path / "nope.json"),
            "--format", "csv", "--out", outp)
    assert os.path.isfile(outp)
    with open(outp, encoding="utf-8") as fh:
        head = fh.readline().strip()
        rows = fh.read().strip().splitlines()
    assert head == "t_ref,quantity,metric,value,unit,window_s"
    assert len(rows) > 50
    assert any(",power,p_total," in r for r in rows), rows[:5]
    assert any(",voltage,rms.A," in r for r in rows)
    assert any(",harmonic,thd_u_pct.A," in r for r in rows), rows[:5]
    assert any(",harmonic,u.A.orders_rms.5," in r for r in rows)
    assert any(",fundamental,freq_hz," in r for r in rows)


def test_cli_compute_json_stream(tmp_path):
    csvp = str(tmp_path / "j.csv")
    run_cli("gen-sample", "--out", csvp, "--duration", "2", "--config", str(tmp_path / "nope.json"))
    proc = run_cli("compute", "--file", csvp, "--config", str(tmp_path / "nope.json"),
                   "--format", "json", "--limit", "2")
    objs = [json.loads(l) for l in proc.stdout.splitlines() if l.startswith("{")]
    assert objs, "无 JSON 输出"
    assert objs[0]["meta"]["pt_ratio"] == 100.0
    assert "quantities" in objs[0]


def test_cli_compute_missing_file():
    proc = run_cli("compute", "--file", "data/__nope__.csv", "--config", "configs/__nope__.json",
                   expect_code=None)
    assert proc.returncode != 0
    assert ("不存在" in proc.stderr) or ("不存在" in proc.stdout)


def test_cli_compute_bad_config_exits_2(tmp_path):
    csvp = str(tmp_path / "b.csv")
    run_cli("gen-sample", "--out", csvp, "--duration", "1", "--config", str(tmp_path / "nope.json"))
    proc = run_cli("compute", "--file", csvp, "--config", str(tmp_path / "nope.json"),
                   "--hmax", "200", expect_code=2)
    assert "配置错误" in proc.stderr and "混叠" in proc.stderr


def test_cli_live_simulator(tmp_path):
    proc = run_cli("live", "--source", "simulator", "--config", str(tmp_path / "nope.json"),
                   "--duration", "3", "--pace", "50", "--quantities", "voltage,current,power,fundamental",
                   "--format", "table")
    assert "实时监视" in proc.stdout
    assert ("U=" in proc.stdout) or ("P=" in proc.stdout)
    assert "✓ 结束" in proc.stdout


def test_cli_live_tail(tmp_path):
    """csv_tail 实时链路：一边生成文件一边被工具增量读取。"""
    csvp = str(tmp_path / "live.csv")
    run_cli("gen-sample", "--out", csvp, "--duration", "3", "--config", str(tmp_path / "nope.json"))
    proc = run_cli("live", "--source", "csv_tail", "--path", csvp,
                   "--config", str(tmp_path / "nope.json"), "--duration", "3",
                   "--quantities", "voltage,power", "--format", "table")
    assert "✓ 结束" in proc.stdout


def test_cli_live_tcp_no_server_reports_clearly(tmp_path):
    """TCP 源连不上时必须给出可执行排查提示，而不是抛栈。"""
    proc = run_cli("live", "--source", "tcp", "--host", "127.0.0.1", "--port", "1",
                   "--config", str(tmp_path / "nope.json"), "--duration", "2", expect_code=None)
    assert proc.returncode != 0
    assert "TCP 连接失败" in (proc.stderr + proc.stdout)


def test_cli_live_csv_tail_from_end_and_watch_newest(tmp_path, csv_factory):
    """csv_tail 的两个现场开关（README §3.2/§4.3 记录的行为必须有测试兜底）。"""
    art = csv_factory(str(tmp_path / "live.csv"), duration_s=0.5)

    # 1) --from-end：静态文件启动后没有新增数据 → 输出 0 次，但必须正常结束不报错
    p1 = run_cli("live", "--source", "csv_tail", "--path", art["path"], "--from-end",
                 "--duration", "1", "--config", str(tmp_path / "nope.json"))
    assert "输出 0 次" in p1.stdout and "样本 0" in p1.stdout, p1.stdout[-600:]

    # 2) 默认（tail_from_end=False）：同一文件从头补算 → 必须有输出
    p2 = run_cli("live", "--source", "csv_tail", "--path", art["path"],
                 "--duration", "2", "--config", str(tmp_path / "nope.json"))
    assert "输出 0 次" not in p2.stdout, p2.stdout[-600:]

    # 3) 目录模式：watch_dir_newest=False 时要给**明确中文报错**（非 0 退出，不能是 traceback）
    cfg_path = tmp_path / "cfg_nowatch.json"
    run_cli("init-config", "--out", str(cfg_path))
    c = json.loads(cfg_path.read_text(encoding="utf-8"))
    c["source"]["watch_dir_newest"] = False
    cfg_path.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    p3 = run_cli("live", "--source", "csv_tail", "--path", str(tmp_path), "--duration", "1",
                 "--config", str(cfg_path), expect_code=None)
    assert p3.returncode != 0
    assert "找不到可监视的 CSV" in (p3.stdout + p3.stderr), (p3.stdout[-400:], p3.stderr[-400:])
    assert "Traceback" not in p3.stderr

    # 4) 同一份配置加上 --watch-newest → 自动跟目录内最新 CSV，跑通
    p4 = run_cli("live", "--source", "csv_tail", "--path", str(tmp_path), "--watch-newest",
                 "--duration", "2", "--config", str(cfg_path))
    assert p4.returncode == 0
    assert "输出 0 次" not in p4.stdout, p4.stdout[-600:]
