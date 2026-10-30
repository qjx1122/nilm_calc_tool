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
from elec_tool.nilm_profile import ProfileError, build_profile, profile_feature_names, save_profile   # noqa: E402


def build_cli_command(file: str, *, device: str, config=None, labels=None, label_tol=None, pre=None, post=None, quantity=None,
                      t_start="", t_end="", custom_time=False, custom_time_start="", custom_time_end="", out=None, merge_gap=None) -> str:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="设备侧波形 CSV")
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
    a = ap.parse_args()
    try:
        cfg = load_or_default(a.config, strict=True)
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
    doc["command"] = build_cli_command(a.file, device=a.device, config=a.config, labels=a.labels, label_tol=a.label_tol, pre=a.pre, post=a.post,
                                       quantity=a.quantity, t_start=a.t_start, t_end=a.t_end, custom_time=a.custom_time,
                                       custom_time_start=a.custom_time_start, custom_time_end=a.custom_time_end, out=a.out)
    save_profile(doc, out)
    if a.json:
        print(json.dumps({k: v for k, v in doc.items() if not k.startswith("_")}, ensure_ascii=False, indent=1))
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
