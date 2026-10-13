#!/usr/bin/env python3
"""cli.py —— 电气量计算工具命令行入口（离线批算 / 实时监视 / 自检 / 样例数据生成）。

用法示例：
    python cli.py init-config  --out configs/default.json
    python cli.py gen-sample   --out data/sample_6400hz.csv --duration 10
    python cli.py selftest                            # 解析解自检（不需要任何真实数据）
    python cli.py compute --file data/xxx.csv --format table
    python cli.py compute --file data/xxx.csv --format csv --out output/result.csv
    python cli.py live --source simulator --duration 30
    python cli.py live --source csv_tail --path data/live.csv
    python cli.py live --source tcp --host 127.0.0.1 --port 9000
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import math
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from elec_tool import __version__
from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, ConfigError, QUANTITY_KEYS, WindowSpec, load_or_default
from elec_tool.engine import LiveEngine
from elec_tool.metrics import MetricsResult
from elec_tool.scaling import scale_block
from elec_tool.selftest import run_selftest, summarize
from elec_tool.sources import create_source

DEFAULT_CONFIG = os.path.join("configs", "default.json")

# 每个子界面在 CLI 表格中展示的关键指标（完整结果用 --format json/csv）
KEY_METRICS: Dict[str, List[tuple]] = {
    "voltage": [("rms.A", "Ua", "V"), ("rms.B", "Ub", "V"), ("rms.C", "Uc", "V"),
                ("line_rms.Uab", "Uab", "V"), ("line_rms.Ubc", "Ubc", "V"), ("line_rms.Uca", "Uca", "V"),
                ("unbalance_pct", "不平衡度", "%")],
    "current": [("rms.A", "Ia", "A"), ("rms.B", "Ib", "A"), ("rms.C", "Ic", "A"),
                ("neutral_rms", "零线电流 In", "A"), ("unbalance_pct", "不平衡度", "%")],
    "power": [("p_total", "有功 P", "W"), ("q_total", "无功 Q", "var"), ("s_total", "视在 S", "VA"),
              ("quadrant.name", "象限", "")],
    "power_factor": [("pf_total", "功率因数 PF", ""), ("dpf", "位移因数 DPF", ""),
                     ("phi1_deg", "φ1", "deg")],
    "fundamental": [("freq_hz", "频率", "Hz"), ("u1_rms.A", "U1(A)", "V"), ("i1_rms.A", "I1(A)", "A"),
                    ("phase_sequence", "相序", ""), ("unbalance_u_pct", "电压不平衡", "%")],
    "harmonic": [("thd_u_pct.A", "THD_U(A)", "%"), ("thd_i_pct.A", "THD_I(A)", "%"),
                 ("u.A.orders_rms.3", "U3", "V"), ("u.A.orders_rms.5", "U5", "V"),
                 ("u.A.orders_rms.7", "U7", "V")],
    "spectrum": [("peak.freq_hz", "主峰频率", "Hz"), ("peak.amp_rms", "主峰幅值", "V/A"),
                 ("freq_resolution_hz", "分辨率", "Hz")],
}


def _dig(obj: Any, path: str) -> Any:
    cur = obj
    for p in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur


def _fmt(v: Any, unit: str) -> str:
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return "NaN"
        av = abs(float(v))
        if av >= 1e6:
            return f"{float(v)/1e6:.4f} M{unit}"
        if av >= 1e4:
            return f"{float(v)/1e3:.3f} k{unit}"
        if av >= 100:
            return f"{float(v):.3f} {unit}".strip()
        return f"{float(v):.5f} {unit}".strip()
    return str(v)


def print_result_table(res: MetricsResult, keys: Optional[Sequence[str]] = None,
                       show_window: bool = True) -> None:
    """按子界面分组打印关键指标（对齐需求②③的分界面组织方式）。"""
    keys = list(keys or QUANTITY_KEYS)
    t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res.t_ref)) if np.isfinite(res.t_ref) else "—"
    print("=" * 78)
    print(f"数据时刻 {t_str}   fs={res.fs:.0f}Hz   f={res.f_used:.4f}Hz({res.f_source})   "
          f"PT={res.meta.get('pt_ratio')} CT={res.meta.get('ct_ratio')}")
    print("=" * 78)
    for key in keys:
        q = res.quantities.get(key)
        if q is None:
            continue
        w = q.window or {}
        head = f"[{key}]"
        if show_window:
            cyc = w.get("n_cycles")
            head += f" 窗长={w.get('length_s_requested')}s 实际={round(w.get('length_s_actual') or 0, 4)}s " \
                    f"点数={w.get('n_samples')} 周期数={cyc} 策略={w.get('policy')}"
        print(head)
        if not q.ok:
            print(f"    ✗ 未计算：{q.error}")
            continue
        for path, label, unit in KEY_METRICS.get(key, []):
            print(f"    {label:<14} {_fmt(_dig(q.values, path), unit)}")
        for n in (q.values.get("notes") or []):
            print(f"    ⚠ {n}")
        for n in (w.get("notes") or []):
            print(f"    · {n}")
    print()


def _print_diagnostics(engine, st: dict) -> None:
    """收尾诊断：数据缺口 + 引擎告警 + **数据源告警**。

    源告警只在 source.info() 里（如 TCP 帧格式不匹配→时间戳解析失败改用合成时间轴、
    csv_tail 文件轮转、缺测插值），不打印就会出现「看着正常、其实时间轴是假的」。
    """
    if st.get("n_gaps"):
        print(f"  ⚠ 检测到 {st['n_gaps']} 处数据时间跳变（疑似丢点），示例：{st['gaps'][:3]}")
    try:
        rt = engine.writer.info()
        if rt.get("enabled"):
            total = sum(rt.get("rows_written", {}).values())
            print(f"  · 实时落盘：{rt.get('dir')}（本次写入 {total} 行，"
                  f"{len(rt.get('files') or [])} 个文件" + ("" if not rt.get("errors") else f"，错误：{rt['errors'][-1]}") + "）")
    except Exception:
        pass
    for n in (st.get("notes") or [])[-6:]:
        print(f"  · {n}")
    try:
        info = engine.source.info()
    except Exception:
        return
    seen = set()
    for n in (info.get("notes") or [])[-8:]:
        key = re.sub(r"[0-9A-Za-z.+eE\-]+", "", str(n))[:40]
        if key in seen:
            continue
        seen.add(key)
        text = str(n)
        print(f"  · 源：{text if len(text) <= 170 else text[:170] + '…'}")


def _fmt_clock(t_ref: float) -> str:
    """把数据时刻格式化成 HH:MM:SS；坏值（inf/nan/超范围）不得让 CLI 崩掉。"""
    if not np.isfinite(t_ref):
        return "--"
    try:
        return time.strftime("%H:%M:%S", time.localtime(float(t_ref)))
    except (OverflowError, OSError, ValueError):
        return f"t={t_ref:.6g}"      # 时间轴异常时原样显示，便于定位（如帧格式不匹配）


def write_csv_rows(res: MetricsResult, path: str) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    rows = res.scalar_table()
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["t_ref", "quantity", "metric", "value", "unit", "window_s"])
        if fh.tell() == 0:
            w.writeheader()
        for r in rows:
            w.writerow({"t_ref": res.t_ref, "quantity": r["quantity"], "metric": r["metric"],
                        "value": r["value"], "unit": r["unit"], "window_s": r["window_s"]})
    return len(rows)


# ------------------------------------------------------------------ 子命令

def cmd_init_config(args: argparse.Namespace) -> int:
    cfg = AppConfig().validate()
    if args.fs:
        cfg.sampling.fs = float(args.fs)
    if args.pt:
        cfg.transform.pt_ratio = float(args.pt)
    if args.ct:
        cfg.transform.ct_ratio = float(args.ct)
    cfg.validate()
    if os.path.exists(args.out) and not args.force:
        print(f"✗ 文件已存在：{args.out}（用 --force 覆盖）", file=sys.stderr)
        return 2
    cfg.save(args.out)
    print(f"✓ 默认配置已写入 {args.out}")
    print(f"  fs={cfg.sampling.fs}Hz  f_nom={cfg.sampling.f_nom}Hz  PT={cfg.transform.pt_ratio}  "
          f"CT={cfg.transform.ct_ratio}  谐波={cfg.harmonic.order_min}~{cfg.harmonic.order_max}次")
    print("  各量窗长：" + ", ".join(f"{k}={w.length_s}s" for k, w in cfg.windows.items()))
    return 0


def cmd_gen_sample(args: argparse.Namespace) -> int:
    """生成与用户给定格式完全一致的样例 CSV：时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流"""
    cfg = load_or_default(args.config)
    if args.fs:
        cfg.sampling.fs = float(args.fs)
    from elec_tool.selftest import HarmSpec, build_signal
    specs = [HarmSpec(1, 100.0 / math.sqrt(3), 5.0, phi_deg=30.0)]
    for item in sorted((args.harmonics or "3:0.08,5:0.06,7:0.03,11:0.015,13:0.01").split(",")):
        if ":" not in item:
            continue
        k, v = item.split(":", 1)
        specs.append(HarmSpec(int(k), float(v) * 100.0 / math.sqrt(3), float(v) * 1.4 * 5.0, phi_deg=40.0))
    t, u, i = build_signal(specs, cfg.sampling.fs, args.duration, args.freq,
                          noise_ratio=args.noise, t0=args.t0 or time.time())
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)

    def ts_str(v: float) -> str:
        # epoch 秒用 %.9f：6400Hz 的间隔 156.25µs 若只写 6 位小数会被量化，
        # 导致「时间戳推算采样率」出现 0.2% 假偏差（gen-sample 实测踩坑）
        if args.ts_format == "epoch":
            return f"{v:.9f}"
        if args.ts_format == "ms":
            return f"{v*1000:.3f}"
        from datetime import datetime
        return datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S.%f")

    with open(args.out, "w", encoding=args.encoding, newline="") as fh:
        w = csv.writer(fh)
        w.writerow([cfg.columns.timestamp, cfg.columns.ua, cfg.columns.ia, cfg.columns.ub,
                    cfg.columns.ib, cfg.columns.uc, cfg.columns.ic])
        for k in range(t.size):
            w.writerow([ts_str(t[k]), f"{u[0,k]:.6f}", f"{i[0,k]:.6f}", f"{u[1,k]:.6f}",
                        f"{i[1,k]:.6f}", f"{u[2,k]:.6f}", f"{i[2,k]:.6f}"])
    size = os.path.getsize(args.out)
    print(f"✓ 样例数据已生成：{args.out}")
    print(f"  fs={cfg.sampling.fs}Hz  时长={args.duration}s  行数={t.size}  文件大小={size/1024/1024:.2f}MB")
    print(f"  时间戳格式={args.ts_format}  编码={args.encoding}")
    print(f"  基波={args.freq}Hz  二次侧 U1={100/math.sqrt(3):.3f}V(相)  I1=5.000A  φ=30°  噪声比={args.noise}")
    print(f"  一次侧期望：U1={100/math.sqrt(3)*cfg.transform.pt_ratio:.1f}V  "
          f"I1={5.0*cfg.transform.ct_ratio:.1f}A  （PT={cfg.transform.pt_ratio}, CT={cfg.transform.ct_ratio}）")
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    t0 = time.time()
    checks = run_selftest(fs=args.fs or 6400.0, f=args.freq or 50.0, pt=args.pt or 100.0,
                          ct=args.ct or 15.0, duration_s=args.window or 1.0, verbose=args.verbose)
    s = summarize(checks)
    if args.json:
        print(json.dumps({"summary": {k: v for k, v in s.items() if k != "failures"},
                          "checks": [c.to_dict() for c in checks]}, ensure_ascii=False, indent=2))
    else:
        if args.verbose:
            for c in checks:
                flag = "PASS" if c.ok else "FAIL"
                print(f"[{flag}] {c.id:<10} {c.name:<34} 期望={c.expected:14.6g} 实际={c.actual:14.6g} "
                      f"相对误差={c.rel_err*100:9.5f}% (容差 {c.tol_rel*100:.3f}%) {c.unit}")
        print("-" * 78)
        print(f"自检项 {s['total']} 个：通过 {s['passed']}，失败 {s['failed']}，"
              f"通过率 {s['pass_rate_pct']:.1f}%，最差相对误差 {s['worst_rel_err']:.3e}，"
              f"耗时 {time.time()-t0:.2f}s")
        print(f"工况：fs={args.fs or 6400.0}Hz  f={args.freq or 50.0}Hz  PT={args.pt or 100.0}  "
              f"CT={args.ct or 15.0}  窗长={args.window or 1.0}s")
        for f_ in s["failures"]:
            print(f"  ✗ {f_['id']} {f_['name']}: 期望 {f_['expected']:.6g} 实际 {f_['actual']:.6g} "
                  f"(相对误差 {f_['rel_err']*100:.4f}% > 容差 {f_['tol_rel']*100:.3f}%)")
    return 0 if s["all_ok"] else 1


def _apply_overrides(cfg: AppConfig, args: argparse.Namespace) -> AppConfig:
    if getattr(args, "pt", None):
        cfg.transform.pt_ratio = float(args.pt)
    if getattr(args, "ct", None):
        cfg.transform.ct_ratio = float(args.ct)
    if getattr(args, "fs", None):
        cfg.sampling.fs = float(args.fs)
    if getattr(args, "freq", None):
        cfg.sampling.f_nom = float(args.freq)
    if getattr(args, "adaptive", None):
        cfg.sampling.adaptive_freq = True
    if getattr(args, "hmax", None):
        cfg.harmonic.order_max = int(args.hmax)
    if getattr(args, "apparent", None):
        cfg.power.apparent = args.apparent
    if getattr(args, "reactive", None):
        cfg.power.reactive = args.reactive
    if getattr(args, "no_scale", None):
        cfg.transform.enabled = False
    if getattr(args, "custom_time", None):
        cfg.source.custom_time = True
    if getattr(args, "custom_time_start", None):
        cfg.source.custom_time = True
        cfg.source.custom_time_start = str(args.custom_time_start)
    if getattr(args, "play_from", None):
        text = str(args.play_from)
        if ":" not in text:
            raise ConfigError(f"--play-from 需写成 模式:值（row/sec/pct/time），当前 {text!r}")
        mode, val = text.split(":", 1)
        mode = {"row": "row", "sec": "seconds", "seconds": "seconds", "pct": "percent", "percent": "percent",
                "time": "time"}.get(mode.strip().lower())
        if mode is None:
            raise ConfigError(f"--play-from 模式只能是 row/sec/pct/time，当前 {text!r}")
        cfg.source.play_start_mode = mode
        cfg.source.play_start_value = val.strip()
    if getattr(args, "realtime_save", None):
        cfg.output.realtime_save = (args.realtime_save == "on")
    if getattr(args, "realtime_dir", None):
        cfg.output.realtime_dir = str(args.realtime_dir)
    for item in (getattr(args, "set_window", None) or []):
        if not item or "=" not in item:
            continue
        key, val = item.split("=", 1)
        key = key.strip()
        if key not in QUANTITY_KEYS:
            raise ConfigError(f"--set-window 未知电气量 '{key}'（可用 {list(QUANTITY_KEYS)}）")
        try:
            cfg.windows[key] = dataclasses.replace(cfg.windows[key], length_s=float(val))
        except ValueError:
            raise ConfigError(f"--set-window {item} 解析失败，格式应为 电气量=秒（如 voltage=5）")
    return cfg.validate()


def cmd_compute(args: argparse.Namespace) -> int:
    """离线文件批算：读完整文件，按各量窗长滚动计算并输出。"""
    cfg = _apply_overrides(load_or_default(args.config), args)
    if args.file:
        cfg.source.kind = "csv_file"
        cfg.source.path = args.file
    if cfg.source.kind != "csv_file":
        cfg.source.kind = "csv_file"
    if not cfg.source.path:
        print("✗ 需要 --file 指定离线 CSV 路径（或在配置中设 source.path）", file=sys.stderr)
        return 2
    cfg.source.block_samples = int(args.block or max(int(cfg.sampling.fs * cfg.min_step_s), 64))
    cfg.validate()
    engine = LiveEngine(cfg)
    engine.start()
    print(f"● 离线批算：{cfg.source.path}")
    print(f"  fs={cfg.sampling.fs}Hz  PT={cfg.transform.pt_ratio}  CT={cfg.transform.ct_ratio}  "
          f"块={cfg.source.block_samples}点({cfg.source.block_samples/cfg.sampling.fs:.3f}s)")
    print("  各量窗长：" + ", ".join(f"{k}={w.length_s}s/step{w.effective_step_s()}s"
                                     for k, w in cfg.windows.items()))
    n_out = 0
    csv_path = args.out if (args.format == "csv" and args.out) else None
    if args.format == "csv" and not csv_path:
        csv_path = os.path.join(cfg.output.export_dir, f"result_{int(time.time())}.csv")
    last_print = 0.0
    for res in engine.run(max_ticks=args.max_ticks):
        n_out += 1
        if args.format == "json":
            print(json.dumps(res.to_dict(), ensure_ascii=False))
        elif args.format == "csv":
            write_csv_rows(res, csv_path)
        else:
            if n_out == 1 or args.every <= 1 or (n_out % max(1, args.every) == 0):
                print_result_table(res, keys=args.quantities.split(",") if args.quantities else None)
        last_print = time.time()
        if args.limit and n_out >= args.limit:
            break
    # 注：engine.run() 在源读完时会自行 flush_all() 收尾，此处不再重复计算
    st = engine.state.to_dict()
    print("-" * 78)
    print(f"✓ 完成：输出 {n_out} 次；读入样本 {st['samples_in']}（{st['data_duration_s']:.2f}s 数据），"
          f"块 {st['blocks_in']}，缓冲 {st['buffer_fill']}/{st['buffer_capacity']}")
    print(f"  各量输出次数：{st['emits']}")
    _print_diagnostics(engine, st)
    if csv_path:
        print(f"  CSV 结果：{csv_path}")
    return 0


def cmd_live(args: argparse.Namespace) -> int:
    """实时监视：simulator / csv_tail / tcp。"""
    cfg = _apply_overrides(load_or_default(args.config), args)
    cfg.source.kind = args.source
    if args.path:
        cfg.source.path = args.path
    if args.host:
        cfg.source.host = args.host
    if args.port:
        cfg.source.port = int(args.port)
    if args.block:
        cfg.source.block_samples = int(args.block)
    if args.pace is not None:
        cfg.source.sim_speed = float(args.pace)
    if getattr(args, "from_end", False):
        cfg.source.tail_from_end = True
    if getattr(args, "watch_newest", False):
        cfg.source.watch_dir_newest = True
    if getattr(args, "frame", None):
        cfg.source.frame = args.frame
    if getattr(args, "struct_fmt", None):
        cfg.source.struct_fmt = args.struct_fmt
    if getattr(args, "struct_fields", None):
        cfg.source.struct_fields = args.struct_fields
    cfg.validate()
    engine = LiveEngine(cfg)
    engine.start()
    print(f"● 实时监视：source={cfg.source.kind}  fs={cfg.sampling.fs}Hz  "
          f"PT={cfg.transform.pt_ratio} CT={cfg.transform.ct_ratio}")
    print(f"  各量窗长：" + ", ".join(f"{k}={w.length_s}s" for k, w in cfg.windows.items()))
    print(f"  按 Ctrl+C 停止；时长限制 {args.duration or '无'}s")
    n = 0
    try:
        for res in engine.run(duration_s=args.duration, max_ticks=args.max_ticks):
            n += 1
            if args.format == "json":
                print(json.dumps(res.to_dict(), ensure_ascii=False), flush=True)
            elif args.format == "csv" and args.out:
                write_csv_rows(res, args.out)
            else:
                keys = args.quantities.split(",") if args.quantities else ["voltage", "current", "power"]
                line = []
                for k in keys:
                    q = res.quantities.get(k)
                    if not q or not q.ok:
                        continue
                    if k == "voltage":
                        line.append(f"U={_dig(q.values,'rms.A'):.1f}/{_dig(q.values,'rms.B'):.1f}/"
                                    f"{_dig(q.values,'rms.C'):.1f}V")
                    elif k == "current":
                        line.append(f"I={_dig(q.values,'rms.A'):.2f}/{_dig(q.values,'rms.B'):.2f}/"
                                    f"{_dig(q.values,'rms.C'):.2f}A")
                    elif k == "power":
                        line.append(f"P={_dig(q.values,'p_total')/1e3:.2f}kW "
                                    f"Q={_dig(q.values,'q_total')/1e3:.2f}kvar")
                    elif k == "power_factor":
                        line.append(f"PF={_dig(q.values,'pf_total'):.4f}")
                    elif k == "fundamental":
                        line.append(f"f={res.f_used:.3f}Hz")
                    elif k == "harmonic":
                        line.append(f"THDu={_dig(q.values,'thd_u_worst_pct'):.2f}%")
                ts = _fmt_clock(res.t_ref)
                print(f"[{ts}] " + "  ".join(line) + f"   ({','.join(res.quantities)})", flush=True)
    except KeyboardInterrupt:
        print("\n● 收到中断，停止…")
    finally:
        engine.stop()
    st = engine.state.to_dict()
    print(f"✓ 结束：输出 {n} 次，样本 {st['samples_in']}，数据时长 {st['data_duration_s']:.2f}s，"
          f"实时速率 {st['rate_samples_per_s']:.0f} 样本/s")
    _print_diagnostics(engine, st)
    return 0


def cmd_resample(args: argparse.Namespace) -> int:
    """离线波形 CSV 重采样 → data/<原名>_re_<fs>.csv（与 Web「数据处理」子界面同一实现）。"""
    from elec_tool.resample import ResampleError, ResampleJob, resample_csv
    cfg = load_or_default(args.config)
    last = {"p": -1}

    def on_progress(j: ResampleJob) -> None:
        pct = int(j.progress * 100)
        if pct // 5 != last["p"] // 5 and sys.stderr.isatty():
            last["p"] = pct
            print(f"\r  {j.stage:<9} {pct:3d}%", end="", file=sys.stderr, flush=True)

    job = ResampleJob(on_progress=on_progress)
    try:
        r = resample_csv(args.file, args.fs, args.out_dir, cfg=cfg, fs_src=args.fs_src, method=args.method,
                         overwrite=args.overwrite, decimals=args.decimals, job=job, root=os.getcwd())
    except ResampleError as exc:
        print(f"\n✗ 重采样失败：{exc}", file=sys.stderr)
        return 2
    if sys.stderr.isatty():
        print("", file=sys.stderr)
    if args.format == "json":
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print(f"✓ 已写出 {r['out_path']}（{r['out_size_mb']} MB）")
    print(f"  行数 {r['rows_in']} → {r['rows_out']}；原采样率 {r['fs_src']:g} Hz（{r['fs_src_source']}）→ 目标 {r['fs_new']:g} Hz；"
          f"方法 {r['method']}；耗时 {r['elapsed_s']}s")
    print(f"  时间戳 {r['ts_first_in']!r} → 输出首/末 {r['ts_first_out']!r} / {r['ts_last_out']!r}（模式 {r['ts_mode']}）")
    for n in r["notes"]:
        print("  · " + n)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """启动 Web 界面（导航条 + 各电气量子界面 + 实时推送）。"""
    try:
        import uvicorn
    except ImportError:
        print("✗ 未安装 Web 依赖：pip install fastapi 'uvicorn[standard]'", file=sys.stderr)
        return 2
    cfg = _apply_overrides(load_or_default(args.config), args)
    os.environ["ELEC_TOOL_CONFIG"] = json.dumps(cfg.to_dict(), ensure_ascii=False)
    os.environ["ELEC_TOOL_HOST"] = args.host
    os.environ["ELEC_TOOL_PORT"] = str(args.port)
    print(f"● 启动 Web 界面：http://{args.host}:{args.port}  （配置：fs={cfg.sampling.fs}Hz "
          f"PT={cfg.transform.pt_ratio} CT={cfg.transform.ct_ratio} source={cfg.source.kind}）")
    uvicorn.run("app.server:app", host=args.host, port=args.port, reload=False, log_level=args.log_level)
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    """探查数据源：打印文件表头/编码/前几行/推算采样率（不计算，用于排查数据问题）。"""
    cfg = load_or_default(args.config)
    path = args.file or cfg.source.path
    if not path or not os.path.exists(path):
        print(f"✗ 路径不存在：{path!r}", file=sys.stderr)
        return 2
    from elec_tool.sources.parsing import detect_encoding, read_header
    if os.path.isdir(path):
        files = sorted(f for f in os.listdir(path) if f.lower().endswith(".csv"))
        print(f"● 目录 {path} 下 CSV 文件 {len(files)} 个：{files[:10]}{'…' if len(files) > 10 else ''}")
        if not files:
            return 1
        path = os.path.join(path, files[-1])
    enc = detect_encoding(path)
    header, enc2 = read_header(path, cfg.columns.encoding, cfg.columns.delimiter)
    print(f"● 文件：{path}")
    print(f"  大小：{os.path.getsize(path)/1024/1024:.2f} MB   编码：{enc}（表头读取用 {enc2}）")
    print(f"  表头：{header}")
    try:
        idx = cfg.columns.resolve(header)
        print(f"  列映射：{idx}")
    except Exception as exc:
        print(f"  ✗ 列映射失败：{exc}")
        return 1
    with open(path, "r", encoding=enc2, newline="") as fh:
        rows = [next(fh).rstrip("\n") for _ in range(1, 4)]
    print("  前 3 行：")
    for r in rows:
        print(f"    {r}")
    # 推算采样率与总行数（大文件只读前 20 万行估算）
    from elec_tool.sources.parsing import parse_timestamps
    ts: List[str] = []
    with open(path, "r", encoding=enc2, newline="") as fh:
        rdr = csv.reader(fh, delimiter=cfg.columns.delimiter)
        next(rdr, None)
        for k, row in enumerate(rdr):
            if k >= 200000:
                break
            if row and len(row) > idx["timestamp"]:
                ts.append(row[idx["timestamp"]])
    info = parse_timestamps(ts[:2000], cfg.columns.timestamp_unit)
    print(f"  时间戳模式：{info.mode}   推算采样率：{info.fs_est:.4f} Hz（配置 {cfg.sampling.fs} Hz）")
    print(f"  已扫描行数（上限 20 万）：{len(ts)}")
    for n in info.notes:
        print(f"  · {n}")
    return 0


# ------------------------------------------------------------------ 入口

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cli.py", description=f"电力系统电气量计算工具 v{__version__}")
    p.add_argument("--version", action="version", version=f"elec_tool {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--config", default=DEFAULT_CONFIG, help=f"配置文件路径（默认 {DEFAULT_CONFIG}，不存在则用内置默认）")
        sp.add_argument("--pt", type=float, help="电压变比 PT（覆盖配置）")
        sp.add_argument("--ct", type=float, help="电流变比 CT（覆盖配置）")
        sp.add_argument("--fs", type=float, help="采样频率 Hz（覆盖配置）")
        sp.add_argument("--freq", type=float, help="额定频率 Hz（覆盖配置）")
        sp.add_argument("--hmax", type=int, help="最高谐波次数（覆盖配置）")
        sp.add_argument("--adaptive", action="store_true", help="启用频率自适应（估频后整周期截断）")
        sp.add_argument("--no-scale", action="store_true", help="不做 PT/CT 变换（直接用二次值）")
        sp.add_argument("--set-window", action="append", metavar="量=秒",
                        help="设置某电气量窗长，可重复（如 --set-window voltage=5 --set-window harmonic=0.2）")
        sp.add_argument("--apparent", choices=["arithmetic", "vector"], help="视在功率口径")
        sp.add_argument("--reactive", choices=["harmonic_sum", "quadrature"], help="无功口径")
        sp.add_argument("--realtime-save", dest="realtime_save", choices=["on", "off"],
                        help="曲线点实时落盘到 output/realtime/<曲线>_<日期>.csv（默认按配置 output.realtime_save，出厂 on）")
        sp.add_argument("--realtime-dir", dest="realtime_dir", help="实时落盘目录（默认 output/realtime）")

    sp = sub.add_parser("init-config", help="生成默认配置文件")
    sp.add_argument("--out", default=DEFAULT_CONFIG)
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--fs", type=float)
    sp.add_argument("--pt", type=float)
    sp.add_argument("--ct", type=float)
    sp.set_defaults(func=cmd_init_config)

    sp = sub.add_parser("gen-sample", help="生成样例 CSV（与用户给定列格式一致）")
    sp.add_argument("--out", default=os.path.join("data", "sample_6400hz.csv"))
    sp.add_argument("--duration", type=float, default=5.0)
    sp.add_argument("--freq", type=float, default=50.0)
    sp.add_argument("--noise", type=float, default=0.001)
    sp.add_argument("--harmonics", default="3:0.08,5:0.06,7:0.03,11:0.015,13:0.01",
                    help="次:相对幅值，逗号分隔")
    sp.add_argument("--t0", type=float, help="起始 epoch 秒（默认当前时间）")
    sp.add_argument("--ts-format", choices=["epoch", "iso", "ms"], default="epoch",
                    dest="ts_format", help="时间戳写法（用于验证解析器对各种格式的兼容性）")
    sp.add_argument("--encoding", default="utf-8")
    sp.add_argument("--config", default=DEFAULT_CONFIG)
    sp.add_argument("--fs", type=float)
    sp.set_defaults(func=cmd_gen_sample)

    sp = sub.add_parser("selftest", help="解析解自检（无需真实数据）")
    sp.add_argument("--fs", type=float)
    sp.add_argument("--freq", type=float)
    sp.add_argument("--pt", type=float)
    sp.add_argument("--ct", type=float)
    sp.add_argument("--window", type=float, help="自检窗长（秒），默认 1")
    sp.add_argument("-v", "--verbose", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_selftest)

    sp = sub.add_parser("sources", help="探查数据源（表头/编码/采样率）")
    sp.add_argument("--file")
    sp.add_argument("--config", default=DEFAULT_CONFIG)
    sp.set_defaults(func=cmd_sources)

    sp = sub.add_parser("compute", help="离线文件批算")
    common(sp)
    sp.add_argument("--file", help="离线 CSV 路径")
    sp.add_argument("--format", choices=["table", "json", "csv"], default="table")
    sp.add_argument("--out", help="format=csv 时的输出路径（默认 output/result_<ts>.csv）")
    sp.add_argument("--quantities", help="只输出指定量，逗号分隔（如 voltage,power）")
    sp.add_argument("--block", type=int, help="每块样本数（默认按最小步长自动）")
    sp.add_argument("--every", type=int, default=1, help="table 模式下每 N 次输出打印一次")
    sp.add_argument("--limit", type=int, help="最多输出次数")
    sp.add_argument("--max-ticks", type=int, dest="max_ticks", help="最多轮询次数")
    sp.add_argument("--custom-time", action="store_true", dest="custom_time",
                    help="自定义播放时间：时间轴＝起始时间＋样本序号/fs（起始默认＝文件第 1 条数据时间）")
    sp.add_argument("--custom-time-start", dest="custom_time_start",
                    help="自定义播放的起始时间（'2026-10-12 08:00:00' 或 epoch 秒），给出即启用 --custom-time")
    sp.add_argument("--play-from", dest="play_from", metavar="模式:值",
                    help="从文件指定位置开始播放：row:120001（第 N 行）/ sec:30（跳过 N 秒）/ "
                         "pct:50（文件 N%% 处）/ time:'2026-10-12 08:00:00' 或 time:08:00:00（时标 ≥ 该时刻）")
    sp.set_defaults(func=cmd_compute)

    sp = sub.add_parser("live", help="实时监视（simulator / csv_tail / tcp）")
    common(sp)
    sp.add_argument("--source", choices=["simulator", "csv_tail", "tcp"], default="simulator")
    sp.add_argument("--path", help="csv_tail 的文件或目录")
    sp.add_argument("--host")
    sp.add_argument("--port", type=int)
    sp.add_argument("--block", type=int)
    sp.add_argument("--pace", type=float, help="simulator 速率倍数（>1 加速，0.001 近似全速）")
    sp.add_argument("--from-end", action="store_true", dest="from_end",
                    help="csv_tail：从文件末尾开始，只算新写入的数据（不补算历史）")
    sp.add_argument("--watch-newest", action="store_true", dest="watch_newest",
                    help="csv_tail：--path 给目录时自动跟目录内最新的 CSV（采集器按天/按段换文件时用）")
    sp.add_argument("--frame", choices=["text_csv", "binary"],
                    help="tcp：帧格式（text_csv＝每行一条 CSV；binary＝struct 定长帧）")
    sp.add_argument("--struct-fmt", dest="struct_fmt",
                    help='tcp binary：struct 格式串（默认 "<7d"＝7 个 double 小端）')
    sp.add_argument("--struct-fields", dest="struct_fields",
                    help='tcp binary：字段顺序，逗号分隔（默认 "t,ua,ia,ub,ib,uc,ic"）')
    sp.add_argument("--duration", type=float, help="运行时长（秒）")
    sp.add_argument("--format", choices=["table", "json", "csv"], default="table")
    sp.add_argument("--out")
    sp.add_argument("--quantities", default="voltage,current,power")
    sp.add_argument("--max-ticks", type=int, dest="max_ticks")
    sp.set_defaults(func=cmd_live)

    sp = sub.add_parser("resample", help="离线波形 CSV 重采样 → data/<原名>_re_<fs>.csv")
    sp.add_argument("--config", default=DEFAULT_CONFIG, help="配置文件路径（取列映射/编码/分隔符）")
    sp.add_argument("file", help="源 CSV 路径")
    sp.add_argument("--fs", type=float, required=True, help="目标采样率 Hz（如 6400）")
    sp.add_argument("--fs-src", type=float, dest="fs_src", help="原采样率 Hz（默认由时间戳推算）")
    sp.add_argument("--method", choices=["linear", "nearest", "fft"], default="linear",
                    help="linear 线性插值（流式，默认）/ nearest 最近邻 / fft 频域（抗混叠，整文件载入）")
    sp.add_argument("--out-dir", dest="out_dir", default="data", help="输出目录（默认 data）")
    sp.add_argument("--overwrite", action="store_true", help="输出已存在时覆盖")
    sp.add_argument("--decimals", type=int, default=6, help="数值列小数位（默认 6）")
    sp.add_argument("--format", choices=["table", "json"], default="table")
    sp.set_defaults(func=cmd_resample)

    sp = sub.add_parser("serve", help="启动 Web 界面")
    common(sp)
    sp.add_argument("--host", default="0.0.0.0")
    sp.add_argument("--port", type=int, default=8000)
    sp.add_argument("--log-level", default="warning")
    sp.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except ConfigError as exc:
        print(f"✗ 配置错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n● 已中断", file=sys.stderr)
        return 130
    except FileNotFoundError as exc:
        print(f"✗ 文件不存在：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"✗ 执行失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        if os.environ.get("ELEC_TOOL_DEBUG"):
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
