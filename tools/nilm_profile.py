#!/usr/bin/env python
"""设备画像提取（v0.90）：从设备侧（分路侧）含启停过程的周波录波构建设备画像 JSON，供总线侧「设备画像匹配」算法加载。

用法（仓库根目录、已激活 .venv）：
    python tools/nilm_profile.py --file data/pump_dev.csv --device pumpA --labels data/pump_truth.csv
    python tools/nilm_profile.py --file data/pump_dev.csv --device pumpA                 # 无标签：稳态分段 + 自适应参数自动定位启停
    python tools/nilm_profile.py --file data/pump_dev.csv --device pumpA --config configs/branch.json --pre 10 --post 50 --out output/nilm/profile_pumpA.json
    python tools/nilm_profile.py --file ... --quantity i                                  # 只有电流的数据源：I 口径画像（总线侧也须 I 口径）

--labels 为真值表 CSV / 文本：每行「时间,动作[,备注]」，时间写法同 nilm_check 真值表（完整日期时间 / epoch 秒 / HH:MM:SS），
动作可写 开/关、启动/停止、on/off、start/stop。--label-tol 为标签时刻与真实变化点的容差（s，默认 2）。
画像写到 --out（默认 <nilm_dir>/profile_<device>_<时间戳>.json）；把该路径填到总线侧 nilm.profile_path 并勾选「设备画像匹配」即可。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from elec_tool.config import ConfigError, load_or_default   # noqa: E402
from elec_tool.nilm_profile import (ProfileError, STAGE_GRID_RATIO, build_profile, derive_stage_profile,   # noqa: E402
                                    load_profile, profile_feature_names, save_profile, stage_grid_ratio, stage_window)


def build_cli_command(file: str, *, device: str, config=None, labels=None, label_tol=None, pre=None, post=None, quantity=None,
                      t_start="", t_end="", custom_time=False, custom_time_start="", custom_time_end="", out=None, merge_gap=None,
                      derive_stages=None, derive_grid=None, derive_center=None, derive_ratio=None, stage_q_mode=None,
                      stage_ih_exp=None, stage_dur_exp=None, stage_out_dir=None) -> str:
    q = lambda s: f'"{s}"' if any(ch in str(s) for ch in " \t\"'") else str(s)   # noqa: E731
    parts = ["python", "tools/nilm_profile.py", "--file", q(file), "--device", q(device)]
    if config:
        parts += ["--config", q(config)]
    if labels:
        parts += ["--labels", q(labels)]
    if label_tol is not None:
        parts += ["--label-tol", f"{float(label_tol):g}"]
    if pre is not None:
        parts += ["--pre", str(int(pre))]
    if post is not None:
        parts += ["--post", str(int(post))]
    if merge_gap is not None:
        parts += ["--merge-gap", f"{float(merge_gap):g}"]
    if quantity:
        parts += ["--quantity", str(quantity)]
    if t_start:
        parts += ["--t-start", q(t_start)]
    if t_end:
        parts += ["--t-end", q(t_end)]
    if custom_time:
        parts += ["--custom-time"]
        if custom_time_start:
            parts += ["--custom-time-start", q(custom_time_start)]
        if custom_time_end:
            parts += ["--custom-time-end", q(custom_time_end)]
    if out:
        parts += ["--out", q(out)]
    # v0.99.28：档位派生（多档位设备只录到部分档位时的补救）
    if derive_stages:
        parts += ["--derive-stages", q(str(derive_stages))]
    if derive_grid is not None:
        parts += ["--derive-grid", str(int(derive_grid))]
    if derive_center is not None:
        parts += ["--derive-center", f"{float(derive_center):g}"]
    if derive_ratio is not None:
        parts += ["--derive-ratio", f"{float(derive_ratio):g}"]
    if stage_q_mode:
        parts += ["--stage-q-mode", str(stage_q_mode)]
    if stage_ih_exp is not None:
        parts += ["--stage-ih-exp", f"{float(stage_ih_exp):g}"]
    if stage_dur_exp is not None:
        parts += ["--stage-dur-exp", f"{float(stage_dur_exp):g}"]
    if stage_out_dir:
        parts += ["--stage-out-dir", q(stage_out_dir)]
    return " ".join(parts)


def _apply_wiring_args(cfg, a):
    """v0.95：命令行接线 / 极性覆盖配置 transform 同名项。"""
    if a.wiring:
        cfg.transform.wiring = a.wiring
    if a.reconstruct_3w:
        cfg.transform.reconstruct_3w = True
    if a.invert_current:
        cfg.transform.invert_current = True
    if a.invert_phases is not None:
        cfg.transform.invert_phases = "".join(ch for ch in a.invert_phases.upper() if ch in "ABC")
    cfg.transform.validate()


def _print_stage_table(doc, derived, base_path):
    """打印档位派生结果：可接受区间、候选门槛、派生清单、可直接粘贴的 profile_path。"""
    win = stage_window(doc)
    print(f"\n档位派生（v0.99.28）：基准画像录到的是 **1 档**，可接受区间 {win['k_lo']}~{win['k_hi']}×，"
          f"候选门槛 {win['min_d']:g} {win['unit']}（低于 {win['k_gate']}× 的档位连候选都不会生成）")
    for d in derived:
        w = d["window"]
        k = float((d["doc"].get("stage") or {}).get("scale") or 1.0)
        tag = "（＝基准画像，未复制）" if abs(k - 1.0) < 1e-9 else ""
        print(f"  · {str(d['doc'].get('device_id')):<22s} k={k:<8.4g} 可接受 {w['k_lo']}~{w['k_hi']}×  "
              f"min_d={w['min_d']:g} {w['unit']:<3s} → {d['path']}{tag}")
    seq = [os.path.abspath(base_path)] + [d["path"] for d in derived]
    paths = ";".join(dict.fromkeys(seq))
    print(f"\n  把下面这串填到总线侧 nilm.profile_path（界面「设备画像」多选 / 配置项）：\n    {paths}")
    print("  注意：派生档位无实录，是假设画像；上线后用候选 CSV 的 c_* 与 status 复核，只有 ΔP/ΔI/ΔQ/ΔIh 按倍数外推，peak/dur 未外推。")


def _stage_scales(a, doc=None) -> list:
    """命令行里的档位倍数列表：``--derive-stages "0.4,0.7"`` 或按 ``--derive-grid`` 自动生成网格。

    网格间距缺省取**该画像实测**的接受窗口之比 ``k_hi/k_lo``（``stage_grid_ratio``）——不同样本量 / 噪声水平下
    窗口宽度不同，用固定常数会留缝或重复。
    """
    if a.derive_stages:
        out = []
        for tok in str(a.derive_stages).replace(";", ",").replace("x", "").replace("X", "").replace("×", "").split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                out.append(float(tok))
            except ValueError:
                raise ProfileError(f"--derive-stages 里的倍数不是数字：{tok!r}（例：0.4,0.7,1.5）")
        if not out:
            raise ProfileError("--derive-stages 为空")
        return out
    if a.derive_grid:
        n = int(a.derive_grid)
        if n < 1 or n > 40:
            raise ProfileError(f"--derive-grid 份数应在 1~40（当前 {n}）")
        r = float(a.derive_ratio) if a.derive_ratio else (stage_grid_ratio(doc) if doc else STAGE_GRID_RATIO)
        half = (n - 1) / 2.0
        return [round(float(a.derive_center) * (r ** (j - half)), 6) for j in range(n)]
    return []


def _derive_stages(doc, a, out_profile):
    """按 CLI 参数派生档位画像并写盘；返回 ``[{path, doc, window}]``（未开启派生时返回 ``[]``）。"""
    scales = _stage_scales(a, doc)
    if not scales:
        return []
    d = a.stage_out_dir or os.path.dirname(os.path.abspath(out_profile)) or "."
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    stem = os.path.splitext(os.path.basename(out_profile))[0]
    out = []
    for k in scales:
        if abs(float(k) - 1.0) < 1e-9:                    # k=1 就是基准画像本身，不再复制一份
            out.append({"path": os.path.abspath(out_profile), "doc": doc, "window": stage_window(doc)})
            continue
        sub = derive_stage_profile(doc, k, q_mode=a.stage_q_mode, ih_exp=a.stage_ih_exp, dur_exp=a.stage_dur_exp)
        sub["command"] = doc.get("command", "")          # 与基准画像同一条命令（含 --derive-* 参数，见 build_cli_command）
        p = os.path.join(d, f"{stem}_stage{float(k):.4g}.json")
        save_profile(sub, p)
        out.append({"path": p, "doc": sub, "window": stage_window(sub)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=None, help="设备侧波形 CSV（用 --derive-from 从既有画像派生时可省略）")
    ap.add_argument("--device", default="device", help="设备 ID（写进画像）")
    ap.add_argument("--config", default=None, help="基准配置（PT/CT、fs、列映射）；缺省 configs/runtime.json，没有则 configs/default.json")
    ap.add_argument("--labels", default=None, help="启停标签：CSV 文件路径，或直接写文本（分号 / 换行分隔的「时间,动作」）")
    ap.add_argument("--label-tol", type=float, default=2.0, help="标签时刻容差（s）")
    ap.add_argument("--pre", type=int, default=10, help="事件前窗周波数")
    ap.add_argument("--post", type=int, default=50, help="事件后窗周波数（应 ≥ 设备启动过程时长）")
    ap.add_argument("--merge-gap", type=float, default=10.0, help="自动定位模式：同方向连续、间隔 ≤ 该秒数的事件合并为一次（0＝不合并）")
    ap.add_argument("--quantity", default=None, choices=[None, "auto", "p", "i"], help="画像口径（缺省取配置 nilm.quantity）")
    ap.add_argument("--t-start", default=""); ap.add_argument("--t-end", default="")
    ap.add_argument("--custom-time", action="store_true"); ap.add_argument("--custom-time-start", default=""); ap.add_argument("--custom-time-end", default="")
    ap.add_argument("--out", default=None, help="输出画像 JSON 路径（默认 <nilm_dir>/profile_<device>_<时间戳>.json）")
    ap.add_argument("--wiring", default=None, choices=("3p4w", "3p3w"), help="v0.95：接线方式（覆盖配置 transform.wiring）")
    ap.add_argument("--reconstruct-3w", action="store_true", help="v0.95：3P3W 虚拟中性点重构（覆盖配置 transform.reconstruct_3w）")
    ap.add_argument("--invert-current", action="store_true", help="v0.95：三相电流极性反转（覆盖配置 transform.invert_current）")
    ap.add_argument("--invert-phases", default=None, help="v0.95：分相电流极性反转，如 A / AC（覆盖配置 transform.invert_phases）")
    ap.add_argument("--json", action="store_true", help="把画像文档打印到 stdout")
    # v0.99.28：多档位 / 变频设备只录到部分档位时，按倍数派生"假设画像"覆盖未录档位
    ap.add_argument("--derive-stages", default=None,
                    help="档位派生：按这些倍数（相对**本次画录取到的档位**，逗号分隔，如 0.4,0.7）各派生一份画像")
    ap.add_argument("--derive-grid", type=int, default=None,
                    help=f"档位派生：按网格自动生成 N 份（间距默认 {STAGE_GRID_RATIO:g}=接受窗口 1.30/0.70，无缝不重叠）")
    ap.add_argument("--derive-center", type=float, default=1.0, help="网格中心倍数（默认 1＝以本次录到的档位为中心）")
    ap.add_argument("--derive-ratio", type=float, default=None,
                    help=f"网格间距倍数（缺省按该画像**实测**接受窗口 k_hi/k_lo 自动算，本机实测约 {STAGE_GRID_RATIO:g}）")
    ap.add_argument("--stage-q-mode", default="scale", choices=("scale", "const"),
                    help="派生时 ΔQ 随档位缩放（scale，默认）还是保持恒定（const，励磁无功≈不变时用）")
    ap.add_argument("--stage-ih-exp", type=float, default=1.0, help="派生时 ΔIh ∝ k^ih_exp（默认 1；轻载 THD 升高可取 0.7~0.9）")
    ap.add_argument("--stage-dur-exp", type=float, default=0.0, help="派生时 dur ∝ k^dur_exp（默认 0＝不变，σ 已有 50%% 下限）")
    ap.add_argument("--stage-out-dir", default=None, help="派生画像输出目录（默认与 --out / --derive-from 同目录）")
    ap.add_argument("--derive-from", default=None,
                    help="不重新提取，直接从这份既有画像 JSON 派生档位画像（与 --derive-stages / --derive-grid 同用）")
    a = ap.parse_args()
    if a.derive_from:                                   # v0.99.28：从既有画像派生档位画像（不重跑提取）
        if not (a.derive_stages or a.derive_grid):
            print("错误：--derive-from 需要同时给 --derive-stages 或 --derive-grid", file=sys.stderr)
            return 2
        try:
            src_doc = load_profile(a.derive_from)
            derived = _derive_stages(src_doc, a, a.derive_from)
        except (ProfileError, OSError, ValueError) as exc:
            print(f"错误（档位派生）：{exc}", file=sys.stderr)
            return 2
        if a.json:
            print(json.dumps({"derived_from": os.path.abspath(a.derive_from),
                              "stage_profiles": [{"path": d["path"], "device_id": d["doc"]["device_id"],
                                                  "scale": d["doc"]["stage"]["scale"], "window": d["window"]} for d in derived]},
                             ensure_ascii=False, indent=1))
            return 0
        print(f"基准画像：{os.path.abspath(a.derive_from)}（设备 {src_doc.get('device_id')}，未重新提取）")
        _print_stage_table(src_doc, derived, a.derive_from)
        return 0
    if not a.file:
        print("错误：--file 必填（设备侧波形 CSV）；若只想按既有画像派生档位，用 --derive-from <画像.json>", file=sys.stderr)
        return 2
    # v0.99.26：--config 缺省时按帮助里写的那样去找 configs/runtime.json → configs/default.json。
    #   此前直接 load_or_default(None) 会退回**代码级**默认值（PT=100 / CT=15），与界面实际运行用的
    #   configs/default.json（PT=CT=1）不是一套变比 ⇒ 画像的 ΔI/ΔP 差 15/1500 倍，总线侧永远匹配不上。
    cfg_path = a.config
    if not cfg_path:
        for _cand in (os.path.join(ROOT, "configs", "runtime.json"), os.path.join(ROOT, "configs", "default.json")):
            if os.path.isfile(_cand):
                cfg_path = _cand
                break
    try:
        cfg = load_or_default(cfg_path, strict=bool(a.config))
        _apply_wiring_args(cfg, a)
        labels_txt = None
        if a.labels:
            if os.path.isfile(a.labels):
                with open(a.labels, encoding="utf-8-sig") as fh:
                    labels_txt = fh.read()
            else:
                labels_txt = a.labels.replace(";", "\n")
        doc = build_profile(cfg, a.file, device_id=a.device, labels=labels_txt, label_tol_s=a.label_tol, pre_cycles=a.pre,
                            post_cycles=a.post, quantity=a.quantity, merge_gap_s=a.merge_gap, t_start=a.t_start, t_end=a.t_end, custom_time=a.custom_time,
                            custom_time_start=a.custom_time_start, custom_time_end=a.custom_time_end)
    except (ProfileError, ConfigError, OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    out = a.out or os.path.join(cfg.nilm.nilm_dir, f"profile_{a.device}_{time.strftime('%Y%m%d_%H%M%S')}.json")
    if not os.path.isabs(out):
        out = os.path.join(ROOT, out) if not os.path.exists(os.path.dirname(out) or ".") else out
    doc["command"] = build_cli_command(a.file, device=a.device, config=(a.config or cfg_path), labels=a.labels, label_tol=a.label_tol, pre=a.pre, post=a.post,
                                       quantity=a.quantity, t_start=a.t_start, t_end=a.t_end, custom_time=a.custom_time,
                                       custom_time_start=a.custom_time_start, custom_time_end=a.custom_time_end, out=a.out,
                                       derive_stages=a.derive_stages, derive_grid=a.derive_grid, derive_center=(a.derive_center if (a.derive_stages or a.derive_grid) else None),
                                       derive_ratio=(a.derive_ratio if a.derive_grid else None), stage_q_mode=(a.stage_q_mode if (a.derive_stages or a.derive_grid) else None),
                                       stage_ih_exp=(a.stage_ih_exp if (a.derive_stages or a.derive_grid) else None),
                                       stage_dur_exp=(a.stage_dur_exp if (a.derive_stages or a.derive_grid) else None), stage_out_dir=a.stage_out_dir)
    save_profile(doc, out)
    try:
        derived = _derive_stages(doc, a, out)
    except (ProfileError, OSError, ValueError) as exc:
        print(f"错误（档位派生）：{exc}", file=sys.stderr)
        return 2
    if a.json:
        payload = {k: v for k, v in doc.items() if not k.startswith("_")}
        if derived:
            payload["stage_profiles"] = [{"path": d["path"], "device_id": d["doc"]["device_id"], "scale": d["doc"]["stage"]["scale"]} for d in derived]
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0
    print(f"设备画像已写出：{out}")
    print(f"  设备 {doc['device_id']}  口径 {doc['unit']}  周波 {doc['cycles']}  标签方式 {doc['label_mode']}  前后窗 {doc['pre_cycles']}/{doc['post_cycles']}")
    for key, name in (("startup", "启动"), ("shutdown", "停止")):
        g = doc.get(key)
        if not g:
            print(f"  {name}画像：无样本"); continue
        print(f"  {name}画像：{g['n']} 次事件  持续 {g['dur_cycles']['min']:.0f}~{g['dur_cycles']['max']:.0f} 周波")
        for j, k in enumerate(profile_feature_names(doc)):          # v0.99.26：按画像实际维度打印（含 d_ih 谐波电流）
            print(f"      {k:<11} μ={g['mu'][j]:>12.4g}  σ={g['sigma'][j]:>10.4g}")
        for e in g["events"]:
            print(f"      · {e['t_start_local']}  ΔP={e['vec']['d_p']:.4g}  ΔIa/b/c={e['vec']['d_ia']:.4g}/{e['vec']['d_ib']:.4g}/{e['vec']['d_ic']:.4g}  峰值比={e['vec']['peak_ratio']:.2f}  {e['source']}")
    for n in doc.get("notes", []):
        print("  ⚠ " + n)
    if derived:
        _print_stage_table(doc, derived, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
