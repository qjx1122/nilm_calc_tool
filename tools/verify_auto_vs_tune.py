#!/usr/bin/env python
"""v0.89.1 核查：负荷辨识「启用自适应算法参数」运行时推导出的各算法参数 vs 数据处理页「负荷辨识调参」给出的参数。

对同一离线文件、同一检测量 / 对象，三套参数并排：
  T  = 调参工具 ``run_tune`` 的 ``suggest.algorithms``（规则：NILM_TUNING_GUIDE §2，min_load 未指定 / 文件估计）
  A  = 调参结果附带的 ``auto_params``（``nilm_auto.auto_params`` 对整段序列一次推导，v0.87 对照）
  R  = 运行时 ``NilmDetector(auto_params=True)`` 回放该文件后 ``summary.auto_last``（最后一个周波窗推导；窗长 nilm.window_cycles）
并把三套参数各自回放到整段逐周波序列（``detect_steps``）看事件数 / 起点，判断差异是否影响结果。

用法：.venv/bin/python tools/verify_auto_vs_tune.py [--file data/nilm_steps.csv ...] [--window 300] [--quantity p|i] [--channel total|A]
     不给 --file 时依次跑 data/nilm_steps.csv、data/nilm_bus_mixed.csv、data/nilm_softstart.csv（缺失时用 tools/gen_nilm_sample.py 生成）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from elec_tool.config import AppConfig, NILM_ALGO_DEFAULTS, NILM_CHANNELS  # noqa: E402
from elec_tool.nilm import NilmDetector, detect_steps, effective_params  # noqa: E402
from elec_tool.nilm_tuning import run_tune  # noqa: E402
from elec_tool.scaling import scale_block  # noqa: E402
from elec_tool.sources import create_source  # noqa: E402
from elec_tool.nilm import CycleFeatures  # noqa: E402

SAMPLES = [("data/nilm_steps.csv", ""), ("data/nilm_bus_mixed.csv", "--bus"), ("data/nilm_softstart.csv", "--soft-start")]
SHOW = {"threshold": ["min_delta", "settle_cycles", "settle_tol", "max_rise_cycles"],
        "median_diff": ["median_cycles", "min_delta", "settle_cycles", "settle_tol", "max_rise_cycles"],
        "two_window": ["pre_cycles", "post_cycles", "min_delta", "k_sigma"],
        "cusum": ["drift", "threshold", "min_delta", "settle_cycles"],
        "glr": ["window_cycles", "threshold", "min_delta", "noise", "settle_cycles"],
        "steady_state": ["tol", "min_steady_cycles", "min_delta", "max_transient_cycles"]}


def _ensure(path: str, flag: str) -> str:
    ap = os.path.join(ROOT, path)
    if not os.path.exists(ap):
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_nilm_sample.py")] + ([flag] if flag else []), check=True, cwd=ROOT)
    return ap


def _base(window: int, quantity: str, channel: str) -> AppConfig:
    cfg = AppConfig()
    cfg.nilm.enabled = True; cfg.nilm.save = False; cfg.nilm.window_cycles = int(window)
    cfg.nilm.quantity = quantity; cfg.nilm.channels = [channel]
    cfg.output.source_id = 0
    cfg.validate()
    return cfg


def _series_and_runtime(cfg: AppConfig, file: str, quantity: str, channel: str):
    """回放文件：返回整段逐周波序列（与 run_tune 同口径）与运行时自适应检测器的 summary / 事件。"""
    c = AppConfig.from_dict(cfg.to_dict()); c.source.kind = "csv_file"; c.source.path = file; c.source.file_speed = 0.0
    c.nilm.auto_params = True; c.validate()
    det = NilmDetector(c); feat = CycleFeatures(c.sampling.fs, c.sampling.f_nom)
    ps, evs = [], []
    with create_source(c) as src:
        while True:
            blk = src.read()
            if blk is None:
                if src.exhausted:
                    break
                continue
            sb = scale_block(blk, c.transform)
            f = feat.push(sb)
            if f["t"].size:
                ps.append(f["p" if quantity == "p" else "i"][NILM_CHANNELS.index(channel)])
            evs += det.ingest(sb)                      # 引擎口径：检测器拿到的是变比折算后的块
    return np.concatenate(ps), det.summary(), evs


def _strip(prm: dict) -> dict:
    """把 *_w / *_a 后缀去掉，便于三套参数同名比较。"""
    return {k[:-2] if k.endswith(("_w", "_a")) else k: v for k, v in prm.items() if k != "enabled"}


def _fmt(v):
    return "—" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))


def compare(file: str, window: int, quantity: str, channel: str, min_load_auto: bool) -> dict:
    cfg = _base(window, quantity, channel)
    tune = run_tune(cfg, file, channel=channel, quantity=quantity, max_cycles=10 ** 7, min_load_auto=min_load_auto)
    p, sm, evs_rt = _series_and_runtime(cfg, file, quantity, channel)
    T = tune["suggest"]["algorithms"]; A = (tune.get("auto_params") or {}).get("algorithms", {})
    R = ((sm.get("auto_last") or {}).get(channel) or {}).get("algorithms", {})
    stA = (tune.get("auto_params") or {}).get("stats", {}); stR = ((sm.get("auto_last") or {}).get(channel) or {}).get("stats", {})
    lvl = float(np.median(p))
    out = {"file": os.path.relpath(file, ROOT), "cycles": int(p.size), "unit": tune["unit"], "level": lvl,
           "tune_sigma": tune["measure"]["sigma_cycle"], "auto_sigma_whole": stA.get("sigma"), "auto_sigma_runtime": stR.get("sigma"),
           "tune_note": tune["suggest"]["note"], "min_load_used": tune["min_load_used"], "stats_whole": stA, "stats_runtime": stR,
           "runtime_events": [(e["algorithm"], round(e["t_start"] - evs_rt[0]["t_start"], 2) if evs_rt else 0, e["direction"]) for e in evs_rt],
           "algos": {}}
    print(f"\n=== {out['file']}  周波 {p.size}  口径 {tune['unit']}  基荷 {lvl:.4g}  σ: 调参 {tune['measure']['sigma_cycle']:.4g} | 自适应整段 {_fmt(stA.get('sigma'))} | 运行时末窗 {_fmt(stR.get('sigma'))}")
    print(f"    调参说明：{tune['suggest']['note'][:160]}")
    print(f"    自适应统计（整段）：{ {k: (round(v, 4) if isinstance(v, float) else v) for k, v in stA.items()} }")
    print(f"    自适应统计（运行时末窗 {window} 周波）：{ {k: (round(v, 4) if isinstance(v, float) else v) for k, v in stR.items()} }")
    for algo in NILM_ALGO_DEFAULTS:
        if algo not in SHOW:
            continue
        t, a, r = _strip(T.get(algo, {})), _strip(A.get(algo, {})), _strip(R.get(algo, {}))
        rows = []
        for k in SHOW[algo]:
            tv, av, rv = t.get(k), a.get(k), r.get(k)
            ratio = (av / tv) if isinstance(tv, (int, float)) and isinstance(av, (int, float)) and tv else None
            rows.append((k, tv, av, rv, ratio))
        # 三套参数各自回放整段序列
        def _run(prm):
            if not prm:
                return None
            eff = effective_params({**prm, "enabled": True}, lvl, 0.0, 0.0)
            st = detect_steps(algo, p, eff)
            return [(int(o), "↑" if d > 0 else "↓", round(float(d), 3 if tune["unit"] == "A" else 0)) for o, _e, _pre, _post, d in st]
        evT, evA, evR = _run(T.get(algo)), _run(A.get(algo)), _run(R.get(algo))
        out["algos"][algo] = {"params": rows, "events_tune": evT, "events_auto_whole": evA, "events_auto_runtime": evR}
        print(f"  [{algo}]")
        print(f"    {'参数':<20}{'调参 T':>14}{'自适应整段 A':>16}{'运行时末窗 R':>16}{'A/T':>8}")
        for k, tv, av, rv, ratio in rows:
            print(f"    {k:<20}{_fmt(tv):>14}{_fmt(av):>16}{_fmt(rv):>16}{(f'{ratio:.2f}' if ratio else '—'):>8}")
        print(f"    事件(起点周波,方向,幅值)  T:{evT}  A:{evA}  R:{evR}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append"); ap.add_argument("--window", type=int, default=300)
    ap.add_argument("--quantity", default="p"); ap.add_argument("--channel", default=None)
    ap.add_argument("--min-load-auto", action="store_true"); ap.add_argument("--json", default="")
    a = ap.parse_args()
    files = [os.path.abspath(f) for f in a.file] if a.file else [_ensure(p, fl) for p, fl in SAMPLES]
    ch = a.channel or ("total" if a.quantity == "p" else "A")
    res = [compare(f, a.window, a.quantity, ch, a.min_load_auto) for f in files]
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
        print("\nJSON →", a.json)


if __name__ == "__main__":
    main()
