#!/usr/bin/env python3
"""画像文件诊断：逐事件打印方向 / ΔP / ΔQ / ΔIa、ΔIb、ΔIc，并指出"方向与电流变化符号相反"的事件及最可能原因。

用法：python tools/nilm_profile_diag.py --profile output/nilm/profile_xxx.json
"""
import argparse, json, sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True)
    a = ap.parse_args()
    doc = json.load(open(a.profile, encoding="utf-8"))
    print(f"设备 {doc.get('device_id')}  口径 {doc.get('quantity')}({doc.get('unit')})  标签方式 {doc.get('label_mode')}  "
          f"前后窗 {doc.get('pre_cycles')}/{doc.get('post_cycles')}  PT/CT {'启用' if (doc.get('pt_ct') or {}).get('enabled') else '未启用'}")
    bad = 0; p_neg = 0; n = 0
    for name, key in (("启动 START", "startup"), ("停止 STOP", "shutdown")):
        g = doc.get(key)
        if not g:
            print(f"\n[{name}] 无样本"); continue
        print(f"\n[{name}] n={g['n']}   μ: " + "  ".join(f"{k}={v:.4g}" for k, v in zip(doc["features"], g["mu"])))
        want = 1 if key == "startup" else -1
        for e in g.get("events", []):
            v = e["vec"]; n += 1
            di = v["d_ia"] + v["d_ib"] + v["d_ic"]
            flags = []
            if di * want < 0: flags.append("ΔI 符号与方向相反"); bad += 1
            if v["d_p"] * want < 0: flags.append("ΔP 符号与方向相反")
            if v["d_p"] * di < 0: flags.append("ΔP 与 ΔI 异号（P 极性可疑）"); p_neg += 1
            print(f"  {e.get('t_start_local')}  周波 {e.get('onset')}→{e.get('end')}  ΔP={v['d_p']:.4g} ΔQ={v['d_q']:.4g}  "
                  f"ΔIa={v['d_ia']:.4g} ΔIb={v['d_ib']:.4g} ΔIc={v['d_ic']:.4g}  峰值比={v['peak_ratio']:.3g}  {e.get('source','')}"
                  + (f"   ⚠ {'；'.join(flags)}" if flags else ""))
    for s in doc.get("notes") or []:
        print("note:", s)
    print()
    if bad == 0:
        print("✅ 所有事件的电流变化符号都与方向一致。"); return 0
    print(f"⚠ {bad}/{n} 个事件的电流变化符号与方向相反。可能原因（按概率）：")
    if doc.get("quantity") == "p" and p_neg:
        print("  1. 方向是按 ΔP 的符号判的，而 ΔP 与 ΔI 异号 ⇒ 有功 P 为负：CT 极性接反 / 电压电流相别没配对（列映射错）/ 电流列与电压列互换。"
              "\n     处理：核对列映射与 PT/CT；或用 --quantity i 按电流口径重提画像（方向按 ΔI 判）。")
    if doc.get("label_mode") == "labels":
        print("  2. 标签时刻偏差超过 --label-tol（默认 2 s）：±容差内找到的是别的变化（甚至相邻的反向事件），但方向仍按标签归类（notes 里会有“请复核”）。"
              "\n     处理：核对标签时刻（时区 / 日期 / 秒级精度），或加大 --label-tol。")
    else:
        print("  2. 自动定位模式下方向＝post−pre 的符号：若设备侧录波包含其它负荷的变化，或启动有先降后升的过程，会把片段方向判反。处理：给启停标签。")
    print("  3. 前后窗（--pre/--post）太长、跨过了相邻事件：事件后窗落进了下一次停机里。处理：减小 --post，或保证两次启停间隔 > post 周波。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
