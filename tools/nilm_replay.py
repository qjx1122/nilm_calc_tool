#!/usr/bin/env python
"""负荷辨识离线回放：用一份配置（可叠加 nilm_tune.py 的建议参数）跑一个离线 CSV，把 6 种算法检出的事件写成一个 CSV。

用法（仓库根目录、已激活 .venv）：
    python tools/nilm_replay.py --file data/设备启停.csv --config configs/site.json --out output/replay_events.csv
    python tools/nilm_replay.py --file data/设备启停.csv --params output/tune.json          # 叠加 nilm_tune --json 的建议
    python tools/nilm_replay.py --file data/设备启停.csv --params output/tune.json --save-config configs/site.json
    python tools/nilm_replay.py --file data/设备启停.csv --set threshold.min_delta_w=300 --set nilm.rel_tol_pct=0.2

- 不启动 Web、不写 output/nilm/，只写 --out 指定的事件文件（表头与 nilm_events_*.csv 相同）。
- 结束时打印每种算法的事件数、投入(up)/切除(down) 数与幅值范围，供 nilm_check.py 对账。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from elec_tool.config import ConfigError, NILM_ALGO_DEFAULTS, AppConfig, load_or_default   # noqa: E402
from elec_tool.nilm_tuning import apply_nilm_params                              # noqa: E402
from elec_tool.nilm import _CSV_FIELDS, NILM_ALGO_NAMES, NilmDetector           # noqa: E402
from elec_tool.scaling import scale_block                                        # noqa: E402
from elec_tool.sources import create_source                                      # noqa: E402


def apply_params(cfg: AppConfig, params: Dict[str, Any]) -> List[str]:
    """把 nilm_tune --json 的输出叠加到 cfg.nilm（v0.50 起实现在 elec_tool.nilm_tuning，与 nilm_tune --apply / API 共用）。"""
    return apply_nilm_params(cfg, params)


def apply_set(cfg: AppConfig, items: List[str]) -> List[str]:
    """--set 算法.参数=值 / --set nilm.参数=值 / --set 算法.enabled=0"""
    notes: List[str] = []
    for it in items:
        key, _, val = it.partition("=")
        head, _, name = key.strip().partition(".")
        v: Any
        try:
            v = float(val)
        except ValueError:
            v = val.strip().lower() in ("1", "true", "on", "yes", "y")
        if head == "nilm":
            setattr(cfg.nilm, name, (val.strip() if name in ("quantity", "profile_path") else v))   # v0.91：字符串字段原样
        elif head in NILM_ALGO_DEFAULTS:
            cur = dict(cfg.nilm.algorithms.get(head) or {})
            cur[name] = (bool(v) if name == "enabled" else v)
            cfg.nilm.algorithms[head] = cur
        else:
            raise SystemExit(f"--set 不认识的键：{key}（应为 nilm.xxx 或 <算法>.xxx，算法 = {list(NILM_ALGO_DEFAULTS)}）")
        notes.append(f"{key} = {val.strip() if (head == 'nilm' and name in ('quantity', 'profile_path')) else v}")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="离线 CSV（含设备启停）")
    ap.add_argument("--config", default=None, help="配置文件（PT/CT、fs、nilm 参数；默认 configs/default.json）")
    ap.add_argument("--params", default=None, help="nilm_tune.py --json 的输出文件，叠加其建议参数")
    ap.add_argument("--set", action="append", default=[], metavar="键=值", help="单项覆盖，如 threshold.min_delta_w=300、threshold.min_delta_a=0.5、glr.enabled=0、nilm.rel_tol_pct=0.2")
    ap.add_argument("--quantity", default=None, choices=("auto", "p", "i"), help="检测量（覆盖配置 nilm.quantity）：p 有功 / i 电流有效值 / auto")
    ap.add_argument("--out", default=os.path.join("output", "replay_events.csv"), help="事件输出 CSV")
    ap.add_argument("--save-config", default=None, help="把最终生效的配置另存到该路径（给 Web 用）")
    ap.add_argument("--custom-time-start", default=None, help="文件时标不可靠时：自定义时间轴起点，如 '2026-10-15 08:00:00'")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    try:
        cfg = load_or_default(a.config, strict=True)
    except ConfigError as exc:
        print(f"错误：{exc}", file=sys.stderr); return 2
    cfg.source.kind = "csv_file"; cfg.source.path = a.file; cfg.source.file_speed = 0.0
    cfg.source.play_window = False; cfg.source.play_start_mode = "begin"; cfg.source.play_start_value = ""
    if a.custom_time_start:
        cfg.source.custom_time = True; cfg.source.custom_time_start = a.custom_time_start
    cfg.nilm.enabled = True; cfg.nilm.save = False
    notes: List[str] = []
    if a.params:
        with open(a.params, encoding="utf-8") as fh:
            notes += apply_params(cfg, json.load(fh))
    notes += apply_set(cfg, a.set)
    if a.quantity:
        cfg.nilm.quantity = a.quantity; notes.append(f"nilm.quantity = {a.quantity}")
    cfg.validate()
    if a.save_config:
        cfg.save(a.save_config)

    det = NilmDetector(cfg, root=ROOT)
    events: List[Dict[str, Any]] = []
    n_samples = 0
    with create_source(cfg) as src:
        while True:
            blk = src.read()
            if blk is None:
                if src.exhausted:
                    break
                continue
            n_samples += blk.n
            events += det.ingest(scale_block(blk, cfg.transform))
    det.close()

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sid = int(getattr(cfg.output, "source_id", 0) or 0)
    with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(_CSV_FIELDS)
        for ev in events:
            w.writerow([sid] + [ev.get(k, "") for k in _CSV_FIELDS[1:]])

    if not a.quiet:
        qty = det.quantity_effective
        print(f"文件 {a.file}  样本 {n_samples}  周波 {det.cycles_total}  口径 {'一次侧(PT/CT)' if cfg.transform.enabled else '二次侧'}"
              f"  检测量 {'有功 P (W)' if qty == 'p' else '电流有效值 I (A)'}" + ("（数据源无电压）" if det.voltage_missing else ""))
        for e in det.summary().get("errors", []):
            print("  ⚠ " + e)
        if notes:
            print("—— 生效的参数覆盖 ——"); [print("  " + n) for n in notes]
        print("—— 各算法事件数 ——")
        print(f"  {'算法':14s} {'事件':>4s} {'投入↑':>5s} {'切除↓':>5s}  幅值范围({'W' if qty == 'p' else 'A'})")
        for algo in NILM_ALGO_DEFAULTS:
            evs = [e for e in events if e["algorithm"] == algo]
            on_ = bool(cfg.nilm.params(algo).get("enabled", True))
            if not on_:
                print(f"  {algo:14s}  (关闭)"); continue
            up = sum(1 for e in evs if e["direction"] == "up"); dn = len(evs) - up
            mag = [e.get("magnitude", e["magnitude_w"]) for e in evs]
            rng = f"{min(mag):.4g} ~ {max(mag):.4g}" if mag else "-"
            print(f"  {algo:14s} {len(evs):4d} {up:5d} {dn:5d}  {rng}   {NILM_ALGO_NAMES.get(algo, '')}")
        prof_on = bool(cfg.nilm.params("profile").get("enabled", False))
        print("—— 设备画像匹配诊断（v0.92.2）——")
        if not prof_on:
            print(f"  本次回放 profile 未启用（配置 {a.config or '默认 configs/default.json'} 里 nilm.algorithms.profile.enabled={prof_on}，"
                  f"nilm.profile_path={cfg.nilm.profile_path!r}）；请用 --config 指向勾选了画像匹配的那一侧配置，或加 --set profile.enabled=1 --set nilm.profile_path=<画像.json>")
        else:
            pf = det.summary().get("profile") or {}
            print(f"  画像文件 {pf.get('path')}  加载 {'成功' if pf.get('loaded') else '失败'}  {pf.get('error') or ''}  设备状态 {pf.get('device_state')}")
            s_ = pf.get("summary") or {}
            if s_:
                print(f"  画像口径 {s_.get('unit')}  启动样本 {(s_.get('startup') or {}).get('n', 0)}  停止样本 {(s_.get('shutdown') or {}).get('n', 0)}  前后窗 {s_.get('pre_cycles')}/{s_.get('post_cycles')}")
            hist = det.profile_hist
            if not hist:
                print("  全程没有产生任何候选：候选门槛＝max(画像最小 |Δ| 的一半, k_sigma×前窗噪声)。请核对本侧检测量与画像口径、"
                      "数据里是否真有 ≥ 该幅值的台阶（nilm_profile_diag.py --file 可看）")
            for g_on in sorted(hist):
                c = hist[g_on]
                top = sorted(c.get("contrib", {}).items(), key=lambda kv: -kv[1])[:3]
                print(f"  {c.get('t_start_local')}  {c['direction']:5s} D²/维={c['d2_per_dim']:<7g} 置信={c['confidence']:<7g} "
                      f"{c['status']:14s} {','.join(c.get('flags') or []) or '-':28s} 最大贡献 " + "  ".join(f"{k}={v}" for k, v in top)
                      + (f"   ΔP={c['vec'].get('d_p')} ΔIa={c['vec'].get('d_ia')}" if c.get("vec") else ""))
        print(f"事件已写入 {a.out}（{len(events)} 行）；下一步：python tools/nilm_check.py --events {a.out} --truth <真值表.csv>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
