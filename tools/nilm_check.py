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
动作可写：开/关、on/off、up/down、投入/切除、1/0。

判定规则（每种算法单独算）：
    命中：真值时刻 ±tol 秒内有同方向事件；漏报：没有；误报：事件不对应任何真值。
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


def _norm_dir(s: str) -> str:
    s = str(s).strip().lower()
    if s in _UP:
        return "up"
    if s in _DN:
        return "down"
    raise SystemExit(f"真值表「动作」不认识：{s!r}（可写 开/关、on/off、up/down、投入/切除、1/0）")


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
    a = ap.parse_args()

    evs = read_events(a.events, a.source_id)
    truth = read_truth(a.truth, evs[0]["t"] if evs else None)
    if not truth:
        raise SystemExit("真值表为空")
    algos = [x for x in NILM_ALGO_DEFAULTS if any(e["algorithm"] == x for e in evs)] or list(NILM_ALGO_DEFAULTS)

    print(f"事件文件 {a.events}（{len(evs)} 条）  真值 {len(truth)} 条  容差 ±{a.tol_s:g} s")
    print(f"  {'算法':14s} {'真值':>4s} {'命中':>4s} {'漏报':>4s} {'误报':>4s}  {'命中率':>6s}  结论")
    detail: List[List[Any]] = []
    verdicts: Dict[str, str] = {}
    mags: Dict[str, List[float]] = {}
    for algo in algos:
        ae = [e for e in evs if e["algorithm"] == algo]
        used = set()
        hit = 0
        for tr in truth:
            best = None
            for i, e in enumerate(ae):
                if i in used or e["dir"] != tr["dir"]:
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
        fa = [e for i, e in enumerate(ae) if i not in used]
        for e in fa:
            detail.append([algo, "", "", "", "误报", e["local"], f"{e['dp']:.1f}", f"{e['dq']:.1f}", ""])
        miss = len(truth) - hit
        rate = 100.0 * hit / len(truth)
        if miss == 0 and not fa:
            v = "✅ 可上线"
        elif miss == 0:
            v = f"⚠ 有 {len(fa)} 条误报：调高 min_delta_w / 容差，或核对误报时刻是否为其它设备"
        elif hit == 0:
            v = "✗ 全漏：门槛/量级可能填错，或该设备幅值低于噪声底（看 nilm_tune 的 ⚠）"
        else:
            v = f"✗ 漏 {miss} 条：调低 min_delta_w（不低于 6σ），或加长 window/pre/post"
        verdicts[algo] = v
        print(f"  {algo:14s} {len(truth):4d} {hit:4d} {miss:4d} {len(fa):4d}  {rate:5.0f}%  {v}   ({NILM_ALGO_NAMES.get(algo, '')})")
    ok = [x for x, v in verdicts.items() if v.startswith("✅")]
    print("—— 设备特征（命中事件的 |ΔP| 均值，W，计算口径）——")
    for algo, m in mags.items():
        print(f"  {algo:14s} {sum(m) / len(m):.4g}  （{len(m)} 次）")
    print("—— 总结论 ——")
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
