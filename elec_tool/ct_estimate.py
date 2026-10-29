"""v0.96：估计 CT 变比（数据处理子界面「估计 CT」/ ``tools/ct_estimate.py`` 同一实现）。

原理：同一台设备的一次启动 / 停止，在总线侧与分路侧造成的**一次侧**电流台阶相同：
    ΔI_bus_sec × CT_bus = ΔI_branch_sec × CT_branch
分别在两侧文件的指定时刻附近量出所选单相电流（二次侧有效值）的台阶 ΔI，已知一侧 CT 即可估计另一侧：
    CT_未知 = CT_已知 × |ΔI_已知侧| / |ΔI_未知侧|

* 每侧可分别指定：文件、启停时刻、单相（A/B/C）、接线方式（3p4w / 3p3w，可选 3P3W 虚拟中性点重构）、CT 极性
  （全局 / 分相反转）与离线文件列映射；PT/CT 变换在此**强制关闭**（直接量二次侧安培）。
* 台阶：时刻 ± 容差范围内，逐周波有效值双窗中位数差 |median(后窗) − median(前窗)| 最大处；
  前 / 后窗长度（秒）可配，后窗应 ≥ 设备启动过程时长。
* 粗估：只用单相电流有效值的幅值，不考虑其它负荷同时变化、两侧相别对应错误、启动冲击等因素；
  结果附带两侧台阶方向一致性与信噪比提示。3p3w 侧选 B 相时必须勾选重构（否则 B 相恒 0）。
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional

import numpy as np

from .config import AppConfig, parse_play_start
from .wave_preview import WaveError, apply_col_map, file_info, make_base, rms_curve

SIDES = ("bus", "branch")
SIDE_NAMES = {"bus": "总线侧", "branch": "分路侧"}
PHASES = ("A", "B", "C")


class CtEstimateError(ValueError):
    pass


def _abs_time(info: Dict[str, Any], txt: str, what: str) -> float:
    """时刻文本 → epoch 秒（写法同数据源页：完整日期时间 / epoch 秒 / HH:MM:SS[.fff]，只写时刻＝文件数据起始当天）。"""
    s = str(txt or "").strip()
    if not s:
        raise CtEstimateError(f"{what}：未填写启停时刻")
    try:
        kind, v = parse_play_start("time", s)
    except Exception as exc:  # noqa: BLE001
        raise CtEstimateError(f"{what}：启停时刻无法解析（{s!r}）：{exc}") from None
    if kind == "tod":
        from .timefmt import local_tod_s
        t0 = float(info["t_start"])
        return t0 - local_tod_s(t0) + float(v)
    return float(v)


def side_base(default_cfg: AppConfig, spec: Dict[str, Any]) -> AppConfig:
    """一侧的基准配置：出厂配置 + 接线 / 极性 / 列映射；PT/CT 关闭（量二次侧）。"""
    base = make_base(default_cfg, pt_ct_enabled="0", f_nom=spec.get("f_nom"), file_time_utc=spec.get("file_time_utc"),
                     wiring=spec.get("wiring"), reconstruct_3w=spec.get("reconstruct_3w"),
                     invert_current=spec.get("invert_current"), invert_phases=spec.get("invert_phases"))
    apply_col_map(base, spec.get("col_map_enabled"), spec.get("col_map"), err=CtEstimateError)
    return base


def measure_step(default_cfg: AppConfig, spec: Dict[str, Any], *, pre_s: float = 2.0, post_s: float = 2.0,
                 tol_s: float = 1.0, side: str = "") -> Dict[str, Any]:
    """量一侧指定时刻附近所选单相电流（二次侧有效值）的台阶。

    spec：{path, t_event, phase: A/B/C, wiring?, reconstruct_3w?, invert_current?, invert_phases?, col_map_enabled?, col_map?, f_nom?, file_time_utc?}
    返回 {path, phase, t_event, t_step, pre_a, post_a, delta_a, direction, noise_a, snr, cycles, notes}
    """
    name = SIDE_NAMES.get(side, side or "该侧")
    path = str(spec.get("path") or "").strip()
    if not path or not os.path.isfile(path):
        raise CtEstimateError(f"{name}：文件不存在：{path or '（未填写）'}")
    phase = str(spec.get("phase") or "A").strip().upper()
    if phase not in PHASES:
        raise CtEstimateError(f"{name}：相别必须是 A / B / C（当前 {phase!r}）")
    for k, v in (("pre_s", pre_s), ("post_s", post_s), ("tol_s", tol_s)):
        if not (float(v) > 0):
            raise CtEstimateError(f"{k} 必须 > 0 秒（当前 {v}）")
    try:
        base = side_base(default_cfg, spec)
    except WaveError as exc:
        raise CtEstimateError(f"{name}：{exc}") from None
    if base.transform.three_wire and phase == "B" and not base.transform.reconstruct_3w:
        raise CtEstimateError(f"{name}：三相三线两表法没有 B 相电流（恒为 0）；请改选 A / C 相，或勾选「3P3W 虚拟中性点重构」")
    try:
        info = file_info(base, path)
    except WaveError as exc:
        raise CtEstimateError(f"{name}：{exc}") from None
    t_ev = _abs_time(info, spec.get("t_event"), name)
    t0, t1 = float(info["t_start"]), float(info["t_end"]) if info.get("t_end") is not None else float("inf")
    if not (t0 - 1e-6 <= t_ev <= t1 + 1e-6):
        from .wave_preview import fmt_t
        raise CtEstimateError(f"{name}：启停时刻 {fmt_t(t_ev)} 不在文件数据时间范围内（{fmt_t(t0)} ~ {fmt_t(t1) if math.isfinite(t1) else '?'}）")
    ch = "I" + phase.lower()
    ws = max(t0, t_ev - pre_s - tol_s); dur = (t_ev + post_s + tol_s) - ws
    try:
        r = rms_curve(base, path, t_start=repr(ws), duration_s=dur, channels=[ch], agg_cycles=1, max_points=10_000_000)
    except WaveError as exc:
        raise CtEstimateError(f"{name}：{exc}") from None
    t = np.asarray(r["t"], dtype=np.float64); x = np.asarray(r["channels"][ch], dtype=np.float64)
    f_nom = float(r["f_nom"])
    pre_n = max(3, int(round(pre_s * f_nom))); post_n = max(3, int(round(post_s * f_nom)))
    n = x.size
    if n < pre_n + post_n + 2:
        raise CtEstimateError(f"{name}：时刻附近只读到 {n} 个周波，不够前窗 {pre_n} + 后窗 {post_n}（文件太短或时刻靠近文件边缘）")
    cand = np.where(np.abs(t - t_ev) <= tol_s + 1e-9)[0]
    cand = cand[(cand >= pre_n) & (cand <= n - post_n)]
    if cand.size == 0:
        cand = np.arange(pre_n, n - post_n + 1)
    ds = np.empty(cand.size); pres = np.empty(cand.size); posts = np.empty(cand.size)
    for k, j in enumerate(cand):
        pres[k] = float(np.median(x[j - pre_n:j])); posts[k] = float(np.median(x[j:j + post_n])); ds[k] = posts[k] - pres[k]
    dmax = float(np.max(np.abs(ds)))
    # 中位数双窗对干净台阶是一段平台：在 ≥98% 最大值的候选里取单周波跳变最大处作为动作时刻
    top = np.where(np.abs(ds) >= 0.98 * dmax)[0] if dmax > 0 else np.array([0])
    jumps = np.array([abs(x[cand[k]] - x[cand[k] - 1]) for k in top])
    k_best = int(top[int(np.argmax(jumps))])
    best_j, best_d, pre_v, post_v = int(cand[k_best]), float(ds[k_best]), float(pres[k_best]), float(posts[k_best])
    seg = x[best_j - pre_n:best_j]
    noise = float(1.4826 * np.median(np.abs(seg - np.median(seg)))) if seg.size else 0.0
    snr = (abs(best_d) / noise) if noise > 0 else float("inf")
    notes: List[str] = []
    if abs(best_d) <= 0:
        notes.append("未量到台阶（ΔI=0）：请核对时刻、相别与列映射")
    elif math.isfinite(snr) and snr < 5:
        notes.append(f"台阶信噪比低（|ΔI|/噪声≈{snr:.1f}）：可能不是该设备动作，或其它负荷同时变化")
    if abs(t[best_j] - t_ev) > tol_s * 0.9 + 1e-9:
        notes.append("台阶位置贴近容差边界：实际动作时刻可能在容差范围之外，建议核对时刻或放大容差")
    return {"side": side, "path": path, "phase": phase, "channel": ch, "t_event": t_ev, "t_step": float(t[best_j]),
            "pre_a": pre_v, "post_a": post_v, "delta_a": best_d, "direction": ("up" if best_d > 0 else ("down" if best_d < 0 else "flat")),
            "noise_a": noise, "snr": (snr if math.isfinite(snr) else None), "cycles": int(n), "f_nom": f_nom,
            "pre_cycles": pre_n, "post_cycles": post_n, "fs": float(r["fs"]),
            "wiring": str(base.transform.wiring), "reconstruct_3w": bool(base.transform.reconstruct_3w),
            "invert_current": bool(base.transform.invert_current), "invert_phases": str(base.transform.invert_phases or ""),
            "notes": notes}


def estimate_ct(default_cfg: AppConfig, bus: Dict[str, Any], branch: Dict[str, Any], *, known_side: str = "branch",
                known_ct: float = 15.0, pre_s: float = 2.0, post_s: float = 2.0, tol_s: float = 1.0) -> Dict[str, Any]:
    """两侧各量一次台阶，按已知一侧 CT 估计另一侧 CT。返回 {ok, bus, branch, ratio, known_side, known_ct, estimated_side, estimated_ct, notes}。"""
    known_side = str(known_side or "branch").strip().lower()
    if known_side not in SIDES:
        raise CtEstimateError(f"known_side 必须是 bus / branch（当前 {known_side!r}）")
    try:
        known_ct = float(known_ct)
    except (TypeError, ValueError):
        raise CtEstimateError(f"已知 CT 变比必须是数字（当前 {known_ct!r}）") from None
    if not (known_ct > 0):
        raise CtEstimateError(f"已知 CT 变比必须 > 0（当前 {known_ct:g}）")
    mb = measure_step(default_cfg, bus, pre_s=pre_s, post_s=post_s, tol_s=tol_s, side="bus")
    mr = measure_step(default_cfg, branch, pre_s=pre_s, post_s=post_s, tol_s=tol_s, side="branch")
    notes: List[str] = [f"总线侧：{n}" for n in mb["notes"]] + [f"分路侧：{n}" for n in mr["notes"]]
    db, dr = abs(mb["delta_a"]), abs(mr["delta_a"])
    other = "bus" if known_side == "branch" else "branch"
    if mb["direction"] != "flat" and mr["direction"] != "flat" and mb["direction"] != mr["direction"]:
        notes.append("两侧台阶方向相反（一侧上升一侧下降）：两侧填写的时刻可能不是同一次动作，或相别 / 时钟不对应；估计值仅供参考")
    est: Optional[float] = None; ratio: Optional[float] = None
    if db > 0 and dr > 0:
        ratio = dr / db                                    # ΔI_branch_sec / ΔI_bus_sec
        est = known_ct * (dr / db) if known_side == "branch" else known_ct * (db / dr)
    else:
        notes.append("有一侧未量到台阶，无法估计 CT")
    if est is not None:
        # 常见 CT 一次额定值（/5A 或 /1A）给个「最接近的标称」提示
        for sec in (5.0, 1.0):
            prim = est * sec
            std = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 80, 100, 120, 150, 200, 250, 300, 400, 500, 600, 750, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000]
            near = min(std, key=lambda s: abs(s - prim))
            if abs(near - prim) / prim <= 0.12:
                notes.append(f"最接近的标称 CT：{near}/{sec:g} A（变比 {near / sec:g}，与估计值差 {abs(near / sec - est) / est * 100:.1f}%）")
                break
    return {"ok": True, "bus": mb, "branch": mr, "ratio_branch_over_bus": ratio, "known_side": known_side, "known_ct": known_ct,
            "estimated_side": other, "estimated_ct": est, "pre_s": float(pre_s), "post_s": float(post_s), "tol_s": float(tol_s),
            "formula": "CT_未知 = CT_已知 × |ΔI_已知侧(二次)| / |ΔI_未知侧(二次)|", "notes": notes}
