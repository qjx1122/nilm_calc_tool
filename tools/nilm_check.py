#!/usr/bin/env python
"""负荷辨识对账：把检出的事件 CSV 与「设备真实开/关时刻表」逐条比对，给出每种算法的 命中 / 漏报 / 误报 与上线结论。

用法（仓库根目录、已激活 .venv）：
    python tools/nilm_check.py --events output/replay_events.csv --truth data/truth.csv
    python tools/nilm_check.py --events output/nilm/nilm_events_20261015.csv --truth data/truth.csv --tol-s 1.0 --source-id 0

真值表 truth.csv（Excel 另存为 CSV UTF-8 即可），3 列、第 1 行表头：
    时间,动作,备注
    2026-10-15 09:12:30,开,空压机
    2026-10-15 09:20:05,关,空压机
    09:35:10,开,            ← 只写时刻也行（按事件文件里的日期补齐）
动作可写：开/关、on/off、up/down、投入/切除、1/0；**其它/忽略** = 已知是别的设备在动（匹配上的事件不算误报）。

总线上还有其它设备启停时（v0.22.1）——按**幅值带**归属：
    --mag-w 500 --mag-tol-pct 30            ΔP 不在 500×(1±30%) 内的事件记为「其它设备」，不算误报
    --dq-var 240                            可选：ΔQ 也要同号且在 ±(tol+20)% 内
    --signature-from output/dev_events.csv  直接用设备侧回放结果（命中事件）的 ΔP/ΔQ 均值作指纹（配合 --truth 同一张真值表时取真值附近的事件）
判定规则（每种算法单独算）：
    命中：真值时刻 ±tol 秒内有同方向（且带内）事件；漏报：没有；误报：带内事件不对应任何真值；其它设备：带外事件或匹配到「其它」真值。
    结论：命中率 100% 且误报 0 → ✅ 可上线；命中率 100% 但有误报 → ⚠ 门槛偏低；有漏报 → ✗ 门槛偏高或该设备幅值低于噪声。
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from elec_tool.config import NILM_ALGO_DEFAULTS, NILM_ALGO_NAMES, parse_time_text   # noqa: E402

_UP = {"开", "on", "up", "投入", "启动", "start", "1", "开机", "合"}
_DN = {"关", "off", "down", "切除", "停止", "stop", "0", "关机", "分"}
_OTHER = {"其它", "其他", "忽略", "other", "ignore", "skip"}


def _norm_dir(s: str) -> str:
    s = str(s).strip().lower()
    if s in _UP:
        return "up"
    if s in _DN:
        return "down"
    if s in _OTHER:
        return "other"
    raise SystemExit(f"真值表「动作」不认识：{s!r}（可写 开/关、on/off、up/down、投入/切除、1/0、其它）")


def read_events(path: str, source_id: Optional[int]) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        if source_id is not None and str(r.get("source_id", "0")).strip() not in ("", str(source_id)):
            continue
        try:
            out.append({"algorithm": r["algorithm"], "t": float(r["t_start"]), "dir": r["direction"],
                        "mag": float(r.get("magnitude_w") or 0), "dp": float(r.get("delta_p_w") or 0),
                        "dq": float(r.get("delta_q_var") or 0), "local": r.get("t_start_local", "")})
        except (KeyError, ValueError):
            continue
    return out


def read_truth(path: str, day_hint: Optional[float]) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.reader(fh) if r and any(c.strip() for c in r)]
    if rows and not _looks_like_time(rows[0][0]):
        rows = rows[1:]                                   # 表头
    out = []
    is_tod = lambda s: ":" in s and "-" not in s and "/" not in s and " " not in s     # noqa: E731
    if day_hint is None:                      # 事件文件为空时：用真值表里第一条带日期的行补日期
        for r in rows:
            if r and not is_tod(r[0].strip()):
                try:
                    day_hint = parse_time_text(r[0].strip()); break
                except Exception:
                    pass
    for r in rows:
        if len(r) < 2:
            raise SystemExit(f"真值表每行至少要「时间,动作」两列：{r}")
        txt = r[0].strip()
        if is_tod(txt):                                                                 # 只有时刻
            if day_hint is None:
                raise SystemExit("真值表只写了时刻、事件文件又为空，无法补日期；请至少有一行写完整日期时间")
            hh, mm, *rest = txt.split(":")
            ss = float(rest[0]) if rest else 0.0
            base = datetime.fromtimestamp(day_hint).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            t = base + int(hh) * 3600 + int(mm) * 60 + ss
        else:
            t = parse_time_text(txt)
        out.append({"t": t, "dir": _norm_dir(r[1]), "note": (r[2].strip() if len(r) > 2 else ""), "text": txt})
    return out


def _looks_like_time(s: str) -> bool:
    s = s.strip()
    return bool(s) and (s[0].isdigit())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--events", required=True, help="事件 CSV（nilm_replay.py 的 --out 或 output/nilm/nilm_events_*.csv）")
    ap.add_argument("--truth", required=True, help="真值表 CSV：时间,动作[,备注]")
    ap.add_argument("--tol-s", type=float, default=1.0, help="时刻允许误差（秒，默认 1.0）")
    ap.add_argument("--source-id", type=int, default=None, help="只看某一侧（0 总线 / 1 分路；默认全部）")
    ap.add_argument("--out", default=None, help="把逐条对账结果另存为 CSV（给 Excel 看）")
    ap.add_argument("--mag-w", type=float, default=None, help="待检设备的 |ΔP| 指纹（W，计算口径）；给出后带外事件记为「其它设备」")
    ap.add_argument("--mag-tol-pct", type=float, default=30.0, help="幅值带宽度 ±%%（默认 30）")
    ap.add_argument("--dq-var", type=float, default=None, help="待检设备的 ΔQ 指纹（var，带符号的开机值；关机取反）；给出后 ΔQ 也参与归属")
    ap.add_argument("--signature-from", default=None, help="从设备侧回放的事件 CSV 取指纹（真值附近的命中事件 ΔP/ΔQ 均值），代替手填 --mag-w/--dq-var")
    ap.add_argument("--signature-truth", default=None, help="设备侧文件自己的真值表（时刻与 --signature-from 对应；默认用 --truth）")
    a = ap.parse_args()

    evs = read_events(a.events, a.source_id)
    truth = read_truth(a.truth, evs[0]["t"] if evs else None)
    if not truth:
        raise SystemExit("真值表为空")
    targets = [t for t in truth if t["dir"] != "other"]
    others = [t for t in truth if t["dir"] == "other"]
    if not targets:
        raise SystemExit("真值表里没有待检设备的 开/关 行")
    mag_w, dq_var = a.mag_w, a.dq_var
    if a.signature_from:
        sev = read_events(a.signature_from, None)
        st = targets
        if a.signature_truth:
            st = [t for t in read_truth(a.signature_truth, sev[0]["t"] if sev else None) if t["dir"] != "other"]
        m_, q_ = [], []
        for tr in st:
            near = [e for e in sev if e["dir"] == tr["dir"] and abs(e["t"] - tr["t"]) <= a.tol_s]
            if near:
                m_ += [e["mag"] for e in near]; q_ += [e["dq"] if tr["dir"] == "up" else -e["dq"] for e in near]
        if not m_:
            raise SystemExit(f"--signature-from {a.signature_from} 里在真值时刻附近没有事件，无法取指纹（请先用设备侧文件回放并确认 ✅）")
        mag_w = sum(m_) / len(m_); dq_var = sum(q_) / len(q_)
        print(f"设备指纹（来自 {a.signature_from}，{len(m_)} 次）：|ΔP| = {mag_w:.4g} W，ΔQ(开机) = {dq_var:.4g} var")

    def in_band(e: Dict[str, Any]) -> bool:
        """事件是否落在待检设备的幅值带内（未给指纹 → 全部视为带内）。"""
        if mag_w is None:
            return True
        tol = a.mag_tol_pct / 100.0
        if not (mag_w * (1 - tol) <= e["mag"] <= mag_w * (1 + tol)):
            return False
        if dq_var is not None and abs(dq_var) > 1e-9:
            want = dq_var if e["dir"] == "up" else -dq_var
            if want * e["dq"] < 0 or abs(e["dq"] - want) > abs(want) * (tol + 0.2):
                return False
        return True

    algos = [x for x in NILM_ALGO_DEFAULTS if any(e["algorithm"] == x for e in evs)] or list(NILM_ALGO_DEFAULTS)

    band = f"  幅值带 {mag_w * (1 - a.mag_tol_pct / 100):.4g}~{mag_w * (1 + a.mag_tol_pct / 100):.4g} W" if mag_w is not None else ""
    print(f"事件文件 {a.events}（{len(evs)} 条）  真值 {len(targets)} 条待检 + {len(others)} 条其它  容差 ±{a.tol_s:g} s{band}")
    print(f"  {'算法':14s} {'真值':>4s} {'命中':>4s} {'漏报':>4s} {'误报':>4s} {'其它设备':>6s}  {'命中率':>6s}  结论")
    detail: List[List[Any]] = []
    verdicts: Dict[str, str] = {}
    mags: Dict[str, List[float]] = {}
    n_other_total = 0
    for algo in algos:
        ae = [e for e in evs if e["algorithm"] == algo]
        used = set()
        hit = 0
        for tr in targets:
            best = None
            for i, e in enumerate(ae):
                if i in used or e["dir"] != tr["dir"] or not in_band(e):
                    continue
                d = abs(e["t"] - tr["t"])
                if d <= a.tol_s and (best is None or d < best[0]):
                    best = (d, i)
            if best is not None:
                used.add(best[1]); hit += 1; e = ae[best[1]]
                mags.setdefault(algo, []).append(e["mag"])
                detail.append([algo, tr["text"], "开" if tr["dir"] == "up" else "关", tr["note"], "命中", e["local"], f"{e['dp']:.1f}", f"{e['dq']:.1f}", f"{best[0]:.3f}"])
            else:
                detail.append([algo, tr["text"], "开" if tr["dir"] == "up" else "关", tr["note"], "漏报", "", "", "", ""])
        # 已知的其它设备动作：时刻对上的事件归为「其它设备」
        for tr in others:
            for i, e in enumerate(ae):
                if i not in used and abs(e["t"] - tr["t"]) <= a.tol_s:
                    used.add(i)
                    detail.append([algo, tr["text"], "其它", tr["note"], "其它设备(真值)", e["local"], f"{e['dp']:.1f}", f"{e['dq']:.1f}", f"{abs(e['t'] - tr['t']):.3f}"])
        rest = [e for i, e in enumerate(ae) if i not in used]
        fa = [e for e in rest if in_band(e)]
        oth = [e for e in rest if not in_band(e)]
        for e in fa:
            detail.append([algo, "", "", "", "误报", e["local"], f"{e['dp']:.1f}", f"{e['dq']:.1f}", ""])
        for e in oth:
            detail.append([algo, "", "", "", "其它设备(带外)", e["local"], f"{e['dp']:.1f}", f"{e['dq']:.1f}", ""])
        n_oth = len(oth) + sum(1 for d in detail if d[0] == algo and d[4] == "其它设备(真值)")
        n_other_total = max(n_other_total, n_oth)
        miss = len(targets) - hit
        rate = 100.0 * hit / len(targets)
        if miss == 0 and not fa:
            v = "✅ 可上线"
        elif miss == 0:
            v = f"⚠ 有 {len(fa)} 条带内误报：调高 min_delta_w / 容差，或核对误报时刻是否为功率相近的其它设备（相近则总线侧无法区分）"
        elif hit == 0:
            v = "✗ 全漏：门槛/量级可能填错，或该设备幅值低于噪声底（看 nilm_tune 的 ⚠）"
        else:
            v = f"✗ 漏 {miss} 条：调低 min_delta_w（不低于 6σ），或加长 window/pre/post；若漏的那次 ±0.2 s 内有其它设备动作则属叠加、换一段数据"
        verdicts[algo] = v
        print(f"  {algo:14s} {len(targets):4d} {hit:4d} {miss:4d} {len(fa):4d} {n_oth:6d}  {rate:5.0f}%  {v}   ({NILM_ALGO_NAMES.get(algo, '')})")
    ok = [x for x, v in verdicts.items() if v.startswith("✅")]
    print("—— 设备特征（命中事件的 |ΔP| 均值，W，计算口径）——")
    for algo, m in mags.items():
        print(f"  {algo:14s} {sum(m) / len(m):.4g}  （{len(m)} 次）")
    print("—— 总结论 ——")
    if n_other_total and mag_w is None:
        print(f"  ℹ 有事件匹配到「其它」真值行；若总线上还有未登记的其它设备，请加 --mag-w/--signature-from 按幅值带归属，否则它们会被算成误报。")
    elif n_other_total:
        print(f"  ℹ 带外 / 已知其它设备事件最多 {n_other_total} 条（不计误报）；这些是总线上别的负荷，不需要为它们调参。")
    if len(ok) >= 2:
        print(f"  ✅ {len(ok)} 种算法全部命中且 0 误报（{', '.join(ok)}）：该设备可以上线；建议生产只保留这几种，其余关闭。")
    elif ok:
        print(f"  ⚠ 只有 1 种算法（{ok[0]}）达标：可试运行，但请再采一段数据复核后再上线。")
    else:
        print("  ✗ 没有算法达标：按上表的结论改参数后重新回放；若 6 种都「全漏」，先检查 PT/CT 口径与 --min-load-w 单位。")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh); w.writerow(["算法", "真值时间", "真值动作", "备注", "结果", "事件时间", "ΔP_W", "ΔQ_var", "时刻误差_s"]); w.writerows(detail)
        print(f"逐条对账已写入 {a.out}")
    return 0 if len(ok) >= 2 else 1


if __name__ == "__main__":
    sys.exit(main())
