#!/usr/bin/env python3
"""画像文件诊断：逐事件打印方向 / ΔP / ΔQ / ΔIa、ΔIb、ΔIc，并指出"方向与电流变化符号相反"的事件及最可能原因。

用法：
  python tools/nilm_profile_diag.py --profile output/nilm/profile_xxx.json
  python tools/nilm_profile_diag.py --file data/dev.csv [--config cfg.json] [--at 15:01:15 --at 14:39:49]
     文件模式（v0.92.1）：对 P 口径与 I 口径分别跑自动定位（稳态分段）并解释——在给定时刻（缺省＝任一口径找到的事件时刻）
     附近，稳态段怎么切、前后段间隔是否超过 max_transient、|Δ| 是否达到 min_delta，说明为什么某个口径找不到事件。
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _segments(x, tol, min_n):
    """复刻 nilm._steps_steady 的稳态分段：返回 [a, b) 列表。"""
    L = len(x); segs = []; a = 0; lo = hi = x[0] if L else 0.0
    for i in range(1, L + 1):
        if i < L:
            lo2, hi2 = min(lo, x[i]), max(hi, x[i])
            if hi2 - lo2 <= tol:
                lo, hi = lo2, hi2; continue
        if i - a >= min_n:
            segs.append((a, i))
        if i < L:
            a, lo, hi = i, x[i], x[i]
    return segs


def diag_file(a) -> int:
    from elec_tool.config import load_or_default
    from elec_tool.nilm import detect_steps
    from elec_tool.nilm_auto import auto_params
    from elec_tool.nilm_profile import load_cycles
    from elec_tool.timefmt import fmt_local
    cfg = load_or_default(a.config, strict=True)
    c, feat, t, p4, q4, i4, u_nonzero = load_cycles(cfg, a.file, max_cycles=int(a.max_cycles))
    cps = float(c.sampling.f_nom)
    series = {"p": p4[0], "i": i4[0]} if u_nonzero else {"i": i4[0]}
    found = {}; info = {}
    for q, x in series.items():
        ap = auto_params(x, cps)
        if ap is None:
            print(f"[{q}] 周波不足，无法自适应"); continue
        prm = ap["algorithms"]["steady_state"]; steps = detect_steps("steady_state", x, prm)
        segs = _segments(x, float(prm["tol_w"]), int(prm["min_steady_cycles"]))
        info[q] = (x, prm, segs); found[q] = steps
        st = ap.get("stats") or {}
        print(f"[{q} 口径] σ={st.get('sigma', float('nan')):.4g}  tol={prm['tol_w']:.4g}  min_steady={prm['min_steady_cycles']} 周波  "
              f"max_transient={prm['max_transient_cycles']} 周波  min_delta={prm['min_delta_w']:.4g}  稳态段 {len(segs)} 个  事件 {len(steps)} 个")
        for on, en, pre, post, sc in steps:
            print(f"    {fmt_local(float(t[on]))}  周波 {on}→{en}  {pre:.4g} → {post:.4g}  Δ={post - pre:+.4g}")
    # 待解释的时刻
    ks = set()
    for q, steps in found.items():
        for on, *_ in steps: ks.add(int(on))
    if a.at:
        from elec_tool.nilm_profile import parse_labels
        for lb in parse_labels("\n".join(f"{s_},开" for s_ in a.at), day_hint=float(t[0])):
            ks.add(int(np.searchsorted(t, lb["t"])))
    for k in sorted(ks):
        print(f"\n== {fmt_local(float(t[k]))}（周波 {k}）==")
        for q, (x, prm, segs) in info.items():
            hit = sorted((s_ for s_ in found[q] if abs(int(s_[0]) - k) <= 2 * int(prm["max_transient_cycles"])), key=lambda s_: abs(int(s_[0]) - k))
            if hit:
                print(f"  [{q}] ✅ 找到（Δ={hit[0][4]:+.4g}）"); continue
            before = [s_ for s_ in segs if s_[1] <= k + 2]; after = [s_ for s_ in segs if s_[0] >= k - 2]
            if not before or not after:
                print(f"  [{q}] ✗ 该时刻一侧没有任何稳态段（范围 ≤ tol={prm['tol_w']:.4g} 且 ≥{prm['min_steady_cycles']} 周波）——该口径噪声/波动相对 tol 太大"); continue
            b0, b1 = before[-1]; a0, a1 = after[0]
            gap = a0 - b1; d = float(np.mean(x[a0:a1]) - np.mean(x[b0:b1]))
            why = []
            if gap > int(prm["max_transient_cycles"]):
                why.append(f"前后稳态段间隔 {gap} 周波 > max_transient {prm['max_transient_cycles']}（过渡过程在该口径上太长 / 中间不稳）")
            if abs(d) < float(prm["min_delta_w"]):
                why.append(f"|Δ|={abs(d):.4g} < min_delta {prm['min_delta_w']:.4g}")
            if not why:
                why.append("前后段间隔与幅值都满足，但事件被归到了别的时刻（看上面事件列表）")
            seg_in = [s_ for s_ in segs if b1 < s_[0] < a0]
            print(f"  [{q}] ✗ 未找到：前段 [{b0},{b1}) 均值 {np.mean(x[b0:b1]):.4g} · 后段 [{a0},{a1}) 均值 {np.mean(x[a0:a1]):.4g} · Δ={d:+.4g}；"
                  + "；".join(why) + (f"；中间还有 {len(seg_in)} 个小稳态段" if seg_in else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=None, help="画像 JSON（画像模式）")
    ap.add_argument("--file", default=None, help="设备侧 CSV（文件模式：解释 P/I 口径自动定位差异）")
    ap.add_argument("--config", default=None); ap.add_argument("--max-cycles", default=400000)
    ap.add_argument("--at", action="append", default=[], help="要解释的时刻 HH:MM:SS（可多次）")
    a = ap.parse_args()
    if a.file:
        return diag_file(a)
    if not a.profile:
        ap.error("需要 --profile 或 --file")
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
