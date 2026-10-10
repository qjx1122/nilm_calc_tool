#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四种数据源的**库级**验证工具：同一信号模型下逐源跑 LiveEngine，输出可对账的电气量表。

为什么单独做这个工具：Web 与 CLI 两条入口最终都调 `LiveEngine`＋`create_source`，
所以「四种源都能出正确数」这件事可以在库层一次性证明，且**不需要起服务、不需要真实采集装置**——
本工具会按需自动拉起 `tools/csv_appender.py` / `tools/tcp_feeder.py` 扮演采集侧，跑完即清理。

用法：
    python tools/verify_sources.py                      # 五种配置全跑（4 种源，tcp 含文本/二进制两帧）
    python tools/verify_sources.py --kinds csv_file,simulator
    python tools/verify_sources.py --duration 5 --json  # 机器可读输出
    python tools/verify_sources.py --external-feeders --tcp-port-text 9000 --tcp-port-bin 9001
                                                        # 复用已在跑的喂数器（不再自己拉起）

对账口径（解析解）：合成信号的二次侧基波 U1=100/√3 V、I1=5 A、φ=30°，
经 PT=100 / CT=15 变换后一次侧 U1=5773.503 V、I1=75 A、P₁=3·U1·I1·cos30°=1125.000 kW。
实测 P 略高于 P₁（约 +0.2%）＝谐波功率贡献，属预期；U1 应吻合到 0.01% 量级。
`csv_file` 用的样例文件由 `cli.py gen-sample`（build_signal：三相平衡、谐波电流相角 40°）生成，
与实时源的 SimulatorSource（2% 不平衡、相角跟随 pf_angle）不是同一次实现，故不参与同源对账，
只验证「离线文件链路能算出同量级的正确结果」。

退出码：0＝全部通过（含 SKIP）；1＝有源失败或数值超差；2＝参数/环境错误。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from elec_tool.config import AppConfig, SourceConfig          # noqa: E402
from elec_tool.engine import LiveEngine                       # noqa: E402
from elec_tool.sources.parsing import ParseError              # noqa: E402

PT, CT, FS, F_NOM = 100.0, 15.0, 6400.0, 50.0
U1_SEC, I1_SEC, PHI_DEG = 100.0 / math.sqrt(3.0), 5.0, 30.0
# 解析解（一次侧）
U1_EXP = U1_SEC * PT
I1_EXP = I1_SEC * CT
P1_EXP_W = 3.0 * U1_EXP * I1_EXP * math.cos(math.radians(PHI_DEG))
# THD 解析解：默认谐波比值 3:0.08 5:0.06 7:0.03 11:0.015 13:0.01（SimulatorSource 与 gen-sample 同）
H_RATIOS = (0.08, 0.06, 0.03, 0.015, 0.01)
THD_EXP_PCT = 100.0 * math.sqrt(sum(x * x for x in H_RATIOS))


def free_port() -> int:
    """向内核要一个空闲端口：避免与用户已在跑的喂数器/服务撞端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def spawn(cmd: list[str], wait_port: int | None = None, timeout: float = 15.0) -> subprocess.Popen:
    """拉起采集侧扮演进程；wait_port 给定时等到它真的开始监听（否则客户端会连接失败）。"""
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    if wait_port:
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                with socket.create_connection(("127.0.0.1", wait_port), timeout=0.5):
                    return proc
            except OSError:
                if proc.poll() is not None:
                    raise RuntimeError(f"喂数器启动即退出：{' '.join(cmd)}")
                time.sleep(0.15)
        raise RuntimeError(f"喂数器 {wait_port} 端口未在 {timeout}s 内监听")
    time.sleep(0.6)          # 文件模式：等首个分片落盘
    return proc


def build_cfg(kind: str, over: dict) -> AppConfig:
    """按用户给定工况建配置：fs=6400、PT=100、CT=15、50Hz，窗长用默认（1s／基波谐波 0.2s）。"""
    cfg = AppConfig()
    cfg.sampling.fs = FS
    cfg.sampling.f_nom = F_NOM
    cfg.transform.pt_ratio = PT
    cfg.transform.ct_ratio = CT
    cfg.source = SourceConfig(kind=kind, **over)
    cfg.validate()
    return cfg


def run_case(cfg: AppConfig, duration_s: float, max_ticks: int) -> dict:
    """跑一个源：engine.start() → run() 迭代 → stop()，回收结果与诊断。"""
    engine = LiveEngine(cfg)
    engine.start()
    t0 = time.time()
    n_out = 0
    # 关键：引擎按各量窗长**错峰**输出（1s 窗与 0.2s 窗不同拍），最后一个结果往往只含
    # fundamental/harmonic。必须像前端 mergeResult 那样按键合并，否则 voltage/power 读成 0。
    merged: dict = {}
    last = None
    try:
        for res in engine.run(duration_s=duration_s, max_ticks=max_ticks):
            last, n_out = res, n_out + 1
            for k, q in (res.quantities or {}).items():
                merged[k] = q
    finally:
        engine.stop()
    st = engine.state.to_dict()
    info = engine.source.info()
    out = {
        "kind": cfg.source.kind,
        "outputs": n_out,
        "samples_in": st.get("samples_in"),
        "data_duration_s": round(float(st.get("data_duration_s") or 0.0), 2),
        "rate_samples_per_s": round(float(st.get("rate_samples_per_s") or 0.0)),
        "n_gaps": st.get("n_gaps"),
        "emits": st.get("emits"),
        "wall_s": round(time.time() - t0, 2),
        "source_notes": [str(x) for x in (info.get("notes") or [])][-4:],
        "info_keys": sorted(info.keys()),
    }
    if merged:
        v, pw, hm, fu = merged.get("voltage"), merged.get("power"), merged.get("harmonic"), merged.get("fundamental")
        def gv(obj, key, default=None):
            return (obj.values.get(key, default) if obj is not None else default)
        rms = gv(v, "rms") or {}
        def three(x):
            if isinstance(x, dict):
                return [x.get(k) for k in ("A", "B", "C") if x.get(k) is not None]
            return list(x or [])
        out.update({
            "t_ref": float(last.t_ref if last is not None else float("nan")),
            "f_used": round(float(getattr(last, "f_used", F_NOM)), 4),
            "f_source": getattr(last, "f_source", "?"),
            "U_abc": [round(float(x), 1) for x in three(rms)],
            "U_line": [round(float(x), 1) for x in three(gv(v, "line_rms"))][:3],
            "U1_abc": [round(float(x), 2) for x in three(gv(fu, "u1_rms"))][:3],
            "I1_abc": [round(float(x), 3) for x in three(gv(fu, "i1_rms"))][:3],
            "P_kW": round(float(gv(pw, "p_total", 0.0)) / 1e3, 3),
            "Q_kvar": round(float(gv(pw, "q_total", 0.0)) / 1e3, 3),
            "PF": round(float(gv(pw, "pf_total", 0.0)), 4),
            "THDu_pct": [round(float(x), 3) for x in three(gv(hm, "thd_u_pct"))][:3],
            "unbalance_u_pct": round(float(gv(v, "rms_unbalance_pct", 0.0)), 4),
            "window": {k: (merged[k].window.get("length_s_actual"), merged[k].window.get("n_cycles"))
                       for k in ("voltage", "harmonic") if k in merged},
        })
    return out


def judge(case: str, r: dict) -> tuple[str, str]:
    """判定：SKIP／PASS／FAIL＋理由（数值口径见模块 docstring）。"""
    if r.get("status") == "skip":
        return "SKIP", r.get("reason", "")
    if r.get("error"):
        return "FAIL", str(r["error"])[:200]
    if not r.get("outputs"):
        return "FAIL", "没有任何输出（源未产出数据或窗长未满足）"
    if r.get("n_gaps"):
        return "FAIL", f"检测到 {r['n_gaps']} 处数据时间跳变（丢点/时标退化）"
    missing = [k for k in ("U1_abc", "P_kW", "THDu_pct") if not r.get(k)]
    if missing:
        return "FAIL", (f"未取到 {missing}：跑得太短（1s 窗需要 >1s 数据）或该量未启用；"
                        f"请加大 --duration（建议 ≥2.5s）")
    u1s = r.get("U1_abc") or []
    # 合成信号含 2% 不平衡，单相值本就偏离 U1_EXP，故用**三相均值**对账
    u1 = sum(u1s) / len(u1s) if u1s else 0.0
    thd = r.get("THDu_pct") or []
    dev_u1 = abs(u1 - U1_EXP) / U1_EXP
    dev_p = abs(r["P_kW"] * 1e3 - P1_EXP_W) / P1_EXP_W
    dev_thd = abs((sum(thd) / len(thd)) - THD_EXP_PCT) if thd else 99.0
    why = (f"U1均={u1:.2f}V 偏差 {dev_u1 * 1e4:.2f}‱（解析解 {U1_EXP:.3f}V）；"
           f"P={r.get('P_kW')}kW 偏差 {dev_p * 1e2:.3f}%（基波解析解 {P1_EXP_W / 1e3:.3f}kW，"
           f"含谐波功率应略高）；THDu 偏差 {dev_thd:.3f} 百分点（解析解 {THD_EXP_PCT:.3f}%）；"
           f"f={r.get('f_used')}Hz")
    if case.startswith("csv_file"):
        # 样例文件是另一次实现（三相平衡、谐波电流相角 40°）：U1/THD 可对账，P 只校量级
        ok = dev_u1 < 5e-4 and dev_thd < 0.05 and 0.9e6 < (r.get("P_kW") or 0) * 1e3 < 1.3e6
        return ("PASS" if ok else "FAIL"), why + "；（样例文件为独立实现，P 只校量级）"
    ok = dev_u1 < 5e-4 and dev_p < 5e-3 and dev_thd < 0.05 and abs(r["f_used"] - F_NOM) < 5e-3
    return ("PASS" if ok else "FAIL"), why


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="四种数据源的库级验证（自动扮演采集侧）")
    ap.add_argument("--kinds", default="csv_file,csv_tail,tcp_text,tcp_binary,simulator",
                    help="要跑的用例，逗号分隔（默认全跑）")
    ap.add_argument("--duration", type=float, default=3.0, help="每个实时源跑多少秒（默认 3）")
    ap.add_argument("--max-ticks", type=int, default=4000, help="引擎最大轮数（默认 4000）")
    ap.add_argument("--csv", default="data/sample_6400hz.csv", help="离线样例 CSV（缺失时自动 gen-sample）")
    ap.add_argument("--tail-path", default="", help="csv_tail 目标文件（默认临时文件，跑完删除）")
    ap.add_argument("--rate", type=float, default=4.0, help="扮演采集侧的速率倍数（默认 4）")
    ap.add_argument("--external-feeders", action="store_true", help="复用已在跑的喂数器，不自己拉起")
    ap.add_argument("--tcp-host", default="127.0.0.1")
    ap.add_argument("--tcp-port-text", type=int, default=0, help="text_csv 喂数器端口（0＝自动选空闲端口）")
    ap.add_argument("--tcp-port-bin", type=int, default=0, help="binary 喂数器端口（0＝自动选空闲端口）")
    ap.add_argument("--struct-fmt", default="<7d", help="二进制帧格式（默认 <7d＝小端 7 个 double）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（便于入库/比对）")
    args = ap.parse_args(argv)

    wanted = [k.strip() for k in args.kinds.split(",") if k.strip()]
    py = sys.executable
    results: list[dict] = []
    procs: list[subprocess.Popen] = []
    tmp_files: list[Path] = []

    try:
        for case in wanted:
            r: dict = {"case": case}
            try:
                if case == "csv_file":
                    csv_path = Path(args.csv)
                    if not csv_path.is_absolute():
                        csv_path = ROOT / csv_path
                    if not csv_path.exists():
                        subprocess.run([py, "cli.py", "gen-sample", "--out", str(csv_path),
                                        "--duration", "5"], cwd=str(ROOT), check=True,
                                       stdout=subprocess.DEVNULL)
                        r["note"] = f"样例文件不存在，已自动 gen-sample：{csv_path}"
                    cfg = build_cfg("csv_file", {"path": str(csv_path), "block_samples": 640})
                    r.update(run_case(cfg, args.duration, args.max_ticks))

                elif case == "csv_tail":
                    if args.tail_path:
                        target = Path(args.tail_path)
                    else:
                        target = Path("/tmp") / f"verify_tail_{os.getpid()}.csv"
                        tmp_files.append(target)
                    if not args.external_feeders:
                        procs.append(spawn([py, "tools/csv_appender.py", "--out", str(target),
                                            "--rate", str(args.rate),
                                            "--duration", str(args.duration + 10)]))
                    cfg = build_cfg("csv_tail", {"path": str(target), "block_samples": 640,
                                                 "poll_interval_s": 0.05, "tail_from_end": False})
                    r.update(run_case(cfg, args.duration, args.max_ticks))

                elif case in ("tcp_text", "tcp_binary"):
                    is_text = case == "tcp_text"
                    port = (args.tcp_port_text if is_text else args.tcp_port_bin) or free_port()
                    if not args.external_feeders:
                        procs.append(spawn(
                            [py, "tools/tcp_feeder.py", "--port", str(port),
                             "--mode", "text_csv" if is_text else "binary",
                             "--rate", str(args.rate), "--duration", str(args.duration + 10)]
                            + (["--header"] if is_text else ["--struct-fmt", args.struct_fmt]),
                            wait_port=port))
                    over = {"host": args.tcp_host, "port": port, "block_samples": 640,
                            "frame": "text_csv" if is_text else "binary"}
                    if not is_text:
                        over["struct_fmt"] = args.struct_fmt
                        over["struct_fields"] = "t,ua,ia,ub,ib,uc,ic"
                    r["port"] = port
                    cfg = build_cfg("tcp", over)
                    r.update(run_case(cfg, args.duration, args.max_ticks))

                elif case == "simulator":
                    cfg = build_cfg("simulator", {"block_samples": 640, "sim_speed": args.rate})
                    r.update(run_case(cfg, args.duration, args.max_ticks))

                else:
                    print(f"未知用例：{case}（可选 csv_file,csv_tail,tcp_text,tcp_binary,simulator）",
                          file=sys.stderr)
                    return 2
            except ParseError as exc:
                if "TCP 连接失败" in str(exc):
                    r.update(status="skip",
                             reason="没有可连的喂数器；先跑 python tools/tcp_feeder.py --port <端口>"
                                    " 或去掉 --external-feeders 让本工具自动拉起")
                else:
                    r.update(error=str(exc))
            except Exception as exc:                    # 单个用例失败不应中断其余用例
                r.update(error=f"{type(exc).__name__}: {exc}")
            verdict, why = judge(case, r)
            r["verdict"], r["why"] = verdict, why
            results.append(r)
    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        for f in tmp_files:
            try:
                f.unlink()
            except OSError:
                pass

    if args.json:
        print(json.dumps({"analytic": {"U1_V": round(U1_EXP, 3), "I1_A": I1_EXP,
                                       "P1_kW": round(P1_EXP_W / 1e3, 3),
                                       "THDu_pct": round(THD_EXP_PCT, 3),
                                       "phi_deg": PHI_DEG, "pt": PT, "ct": CT, "fs": FS},
                          "cases": results}, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"● 库级四源验证　解析解：U1={U1_EXP:.3f}V  I1={I1_EXP:.1f}A  "
              f"P₁={P1_EXP_W / 1e3:.3f}kW  THDu={THD_EXP_PCT:.3f}%"
              f"（φ={PHI_DEG:.0f}°, PT={PT:.0f}, CT={CT:.0f}, fs={FS:.0f}Hz）")
        for r in results:
            print("-" * 78)
            print(f"[{r['verdict']}] {r['case']}　{r.get('why', '')}")
            if r["verdict"] == "SKIP":
                results_row_done = True          # SKIP 用例没有数值，不打印一堆 None
            if r.get("U_abc"):
                print(f"    U(A/B/C)={r['U_abc']}V  U线={r.get('U_line')}V  "
                      f"U1={r.get('U1_abc')}V  I1={r.get('I1_abc')}A")
                print(f"    P={r['P_kW']}kW  Q={r['Q_kvar']}kvar  PF={r['PF']}  "
                      f"f={r['f_used']}Hz({r.get('f_source')})  THDu={r['THDu_pct']}%  "
                      f"不平衡={r.get('unbalance_u_pct')}%")
            if r.get("outputs") is not None:
                print(f"    输出 {r.get('outputs')} 次  样本 {r.get('samples_in')}  "
                      f"数据时长 {r.get('data_duration_s')}s  速率 {r.get('rate_samples_per_s')} 样本/s  "
                      f"缺口 {r.get('n_gaps')}  墙钟 {r.get('wall_s')}s")
            if r.get("window"):
                print(f"    窗长(实际s, 周期数)：{r['window']}")
            for n in r.get("source_notes") or []:
                print(f"    · 源：{n[:150]}")
            if r.get("note"):
                print(f"    · {r['note']}")
        print("-" * 78)
        n_pass = sum(1 for r in results if r["verdict"] == "PASS")
        n_skip = sum(1 for r in results if r["verdict"] == "SKIP")
        n_fail = sum(1 for r in results if r["verdict"] == "FAIL")
        print(f"✓ 结果：PASS {n_pass} / SKIP {n_skip} / FAIL {n_fail}（共 {len(results)} 例）")
    return 1 if any(r["verdict"] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
