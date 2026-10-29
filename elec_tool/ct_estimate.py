"""v0.96：估计 CT 变比（数据处理子界面「估计 CT」/ ``tools/ct_estimate.py`` 同一实现）。

原理：同一台设备的一次启动 / 停止，在总线侧与分路侧造成的**一次侧**电流台阶相同：
    ΔI_bus_sec × CT_bus = ΔI_branch_sec × CT_branch
分别在两侧文件的指定时刻附近量出所选单相电流（二次侧有效值）的台阶 ΔI，已知一侧 CT 即可估计另一侧：
    CT_未知 = CT_已知 × |ΔI_已知侧| / |ΔI_未知侧|

* 每侧可分别指定：文件、启停时刻、单相（A/B/C）、接线方式（3p4w / 3p3w，可选 3P3W 虚拟中性点重构）、CT 极性
  （全局 / 分相反转）与离线文件列映射；PT/CT 变换在此**强制关闭**（直接量二次侧安培）。
* 每侧给「事件类型（启动 / 停机）+ 事件时间段（开始 / 结束时刻）」：事件前稳态＝开始时刻前 N 个周波有效值中位数，
  事件后稳态＝结束时刻后 N 个周波中位数（N＝计算周波数，默认 50），ΔI＝后 − 前；时间段应完整包住启动冲击 / 爬升或停机滑行过程。
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


EVENTS = {"start": "启动", "stop": "停机"}


def measure_step(default_cfg: AppConfig, spec: Dict[str, Any], *, win_cycles: int = 50, side: str = "",
                 pre_s: Optional[float] = None, post_s: Optional[float] = None, tol_s: Optional[float] = None) -> Dict[str, Any]:
    """量一侧「事件时间段」前后所选单相电流（二次侧有效值）的台阶。

    spec：{path, event: start|stop, t_begin, t_end, phase: A/B/C, win_cycles?, wiring?, reconstruct_3w?, invert_current?, invert_phases?,
           col_map_enabled?, col_map?, f_nom?, file_time_utc?}
    * 事件前稳态＝[t_begin − win, t_begin) 内 win_cycles 个周波有效值的中位数；事件后稳态＝(t_end, t_end + win] 内的中位数；
      ΔI = 后 − 前；t_step＝时间段内单周波跳变最大处（只作参考）。
    * event 给出预期方向（启动 ↑ / 停机 ↓），与量到的方向不符时提示。
    返回 {path, phase, event, t_begin, t_end, t_step, pre_a, post_a, delta_a, direction, expected, noise_a, snr, win_cycles, notes, ...}
    """
    name = SIDE_NAMES.get(side, side or "该侧")
    path = str(spec.get("path") or "").strip()
    if not path or not os.path.isfile(path):
        raise CtEstimateError(f"{name}：文件不存在：{path or '（未填写）'}")
    phase = str(spec.get("phase") or "A").strip().upper()
    if phase not in PHASES:
        raise CtEstimateError(f"{name}：相别必须是 A / B / C（当前 {phase!r}）")
    event = str(spec.get("event") or "").strip().lower()
    if event not in EVENTS:
        raise CtEstimateError(f"{name}：事件类型必须是 start（启动）/ stop（停机）（当前 {event!r}）")
    try:
        win = int(float(spec.get("win_cycles") or win_cycles))
    except (TypeError, ValueError):
        raise CtEstimateError(f"{name}：计算周波数必须是整数（当前 {spec.get('win_cycles')!r}）") from None
    if win < 3:
        raise CtEstimateError(f"{name}：计算周波数必须 ≥ 3（当前 {win}）")
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
    tb = _abs_time(info, spec.get("t_begin"), f"{name}（{EVENTS[event]}开始时刻）")
    te = _abs_time(info, spec.get("t_end"), f"{name}（{EVENTS[event]}结束时刻）")
    if te < tb:
        raise CtEstimateError(f"{name}：{EVENTS[event]}结束时刻早于开始时刻")
    t0, t1 = float(info["t_start"]), float(info["t_end"]) if info.get("t_end") is not None else float("inf")
    from .wave_preview import fmt_t
    for x, what in ((tb, "开始"), (te, "结束")):
        if not (t0 - 1e-6 <= x <= t1 + 1e-6):
            raise CtEstimateError(f"{name}：{EVENTS[event]}{what}时刻 {fmt_t(x)} 不在文件数据时间范围内（{fmt_t(t0)} ~ {fmt_t(t1) if math.isfinite(t1) else '?'}）")
    f_nom = float(base.sampling.f_nom); win_s = win / f_nom
    ch = "I" + phase.lower()
    ws = max(t0, tb - win_s - 2.0 / f_nom); dur = (te + win_s + 2.0 / f_nom) - ws
    try:
        r = rms_curve(base, path, t_start=repr(ws), duration_s=dur, channels=[ch], agg_cycles=1, max_points=10_000_000)
    except WaveError as exc:
        raise CtEstimateError(f"{name}：{exc}") from None
    t = np.asarray(r["t"], dtype=np.float64); x = np.asarray(r["channels"][ch], dtype=np.float64)
    f_nom = float(r["f_nom"]); period = 1.0 / f_nom
    pre_m = (t + period <= tb + 1e-6) & (t >= tb - win_s - 1e-6)        # 整周波完全落在开始时刻之前的最近 win 个
    post_m = (t >= te - 1e-6) & (t < te + win_s - 1e-6)                   # 从结束时刻起的 win 个整周波
    n_pre, n_post = int(pre_m.sum()), int(post_m.sum())
    if n_pre < 3 or n_post < 3:
        raise CtEstimateError(f"{name}：事件前 / 后只读到 {n_pre} / {n_post} 个周波（需要各 ≥3）：时间段太靠近文件边缘，或请减小计算周波数")
    pre_seg, post_seg = x[pre_m], x[post_m]
    pre_v, post_v = float(np.median(pre_seg)), float(np.median(post_seg))
    delta = post_v - pre_v
    inside = np.where((t >= tb - period) & (t <= te + period))[0]
    if inside.size >= 2:
        jumps = np.abs(np.diff(x[inside])); k = int(np.argmax(jumps)); t_step = float(t[inside[k + 1]])
    else:
        t_step = tb
    noise = float(1.4826 * max(np.median(np.abs(pre_seg - pre_v)), np.median(np.abs(post_seg - post_v))))
    snr = (abs(delta) / noise) if noise > 0 else float("inf")
    direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
    expected = "up" if event == "start" else "down"
    notes: List[str] = []
    if n_pre < win or n_post < win:
        notes.append(f"事件前 / 后实际只有 {n_pre} / {n_post} 个周波（设定 {win}）")
    if direction == "flat":
        notes.append("未量到台阶（ΔI=0）：请核对时间段、相别与列映射")
    elif direction != expected:
        notes.append(f"量到的台阶方向（{'上升' if direction == 'up' else '下降'}）与事件类型「{EVENTS[event]}」不符：时间段或事件类型可能填错")
    if math.isfinite(snr) and snr < 5 and direction != "flat":
        notes.append(f"台阶信噪比低（|ΔI|/噪声≈{snr:.1f}）：可能不是该设备动作，或其它负荷同时变化")
    return {"side": side, "path": path, "phase": phase, "channel": ch, "event": event, "event_name": EVENTS[event],
            "t_begin": tb, "t_end": te, "t_step": t_step, "pre_a": pre_v, "post_a": post_v, "delta_a": delta, "direction": direction,
            "expected": expected, "noise_a": noise, "snr": (snr if math.isfinite(snr) else None), "win_cycles": win,
            "n_pre": n_pre, "n_post": n_post, "f_nom": f_nom, "fs": float(r["fs"]),
            "wiring": str(base.transform.wiring), "reconstruct_3w": bool(base.transform.reconstruct_3w),
            "invert_current": bool(base.transform.invert_current), "invert_phases": str(base.transform.invert_phases or ""),
            "notes": notes}


def _ct_of(spec: Dict[str, Any], name: str) -> Optional[float]:
    v = spec.get("ct")
    if v in (None, ""):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise CtEstimateError(f"{name}：CT 变比必须是数字（当前 {v!r}）") from None
    if not (f > 0):
        raise CtEstimateError(f"{name}：CT 变比必须 > 0（当前 {f:g}）")
    return f


def _truthy(v: Any) -> bool:
    return str(v).strip().lower() in ("1", "true", "on", "yes") if not isinstance(v, bool) else v


def _nominal_hint(est: float) -> Optional[str]:
    std = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 80, 100, 120, 150, 200, 250, 300, 400, 500, 600, 750, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000]
    for sec in (5.0, 1.0):
        prim = est * sec
        near = min(std, key=lambda s: abs(s - prim))
        if abs(near - prim) / prim <= 0.12:
            return f"最接近的标称 CT：{near}/{sec:g} A（变比 {near / sec:g}，与估计值差 {abs(near / sec - est) / est * 100:.1f}%）"
    return None


def estimate_ct(default_cfg: AppConfig, bus: Dict[str, Any], branch: Dict[str, Any], *, known_side: Optional[str] = None,
                known_ct: Optional[float] = None, win_cycles: int = 50) -> Dict[str, Any]:
    """两侧各量一次台阶，按「CT 已知」的一侧估计另一侧。

    每侧 spec 另含 ``known``（本侧 CT 已知，可勾可不勾）与 ``ct``（本侧 CT 变比）。兼容旧参数 known_side/known_ct（等价于把该侧 known=1、ct=known_ct）。
    * 只勾一侧：估计另一侧；* 两侧都勾：互为参照各估一次，并给出与填写值的偏差（用于核对）；* 都不勾：只给台阶比值。
    返回 {ok, bus, branch, ratio_branch_over_bus, estimates: {bus: {...}|None, branch: {...}|None}, estimated_side, estimated_ct, notes}
    """
    bus = dict(bus or {}); branch = dict(branch or {})
    if known_side:
        ks = str(known_side).strip().lower()
        if ks not in SIDES:
            raise CtEstimateError(f"known_side 必须是 bus / branch（当前 {known_side!r}）")
        (bus if ks == "bus" else branch).update({"known": True, "ct": known_ct if known_ct is not None else 15.0})
    mb = measure_step(default_cfg, bus, win_cycles=win_cycles, side="bus")
    mr = measure_step(default_cfg, branch, win_cycles=win_cycles, side="branch")
    notes: List[str] = [f"总线侧：{n}" for n in mb["notes"]] + [f"分路侧：{n}" for n in mr["notes"]]
    db, dr = abs(mb["delta_a"]), abs(mr["delta_a"])
    if mb["direction"] != "flat" and mr["direction"] != "flat" and mb["direction"] != mr["direction"]:
        notes.append("两侧台阶方向相反（一侧上升一侧下降）：两侧的时间段可能不是同一次动作，或相别 / 时钟不对应；估计值仅供参考")
    if mb["event"] != mr["event"]:
        notes.append(f"两侧事件类型不同（总线侧{mb['event_name']}、分路侧{mr['event_name']}）：应为同一次动作")
    ratio: Optional[float] = (dr / db) if (db > 0 and dr > 0) else None
    if ratio is None:
        notes.append("有一侧未量到台阶，无法估计 CT")
    known = {"bus": _truthy(bus.get("known")), "branch": _truthy(branch.get("known"))}
    cts = {"bus": _ct_of(bus, "总线侧"), "branch": _ct_of(branch, "分路侧")}
    for sd in SIDES:
        if known[sd] and cts[sd] is None:
            raise CtEstimateError(f"{SIDE_NAMES[sd]}：勾选了「本侧 CT 已知」但未填写 CT 变比")
    estimates: Dict[str, Optional[Dict[str, Any]]] = {"bus": None, "branch": None}
    if ratio is not None:
        if known["branch"]:
            est = cts["branch"] * ratio
            estimates["bus"] = {"from": "branch", "known_ct": cts["branch"], "ct": est, "configured": cts["bus"],
                                "deviation_pct": (abs(est - cts["bus"]) / cts["bus"] * 100.0) if cts["bus"] else None, "nominal": _nominal_hint(est)}
        if known["bus"]:
            est = cts["bus"] / ratio
            estimates["branch"] = {"from": "bus", "known_ct": cts["bus"], "ct": est, "configured": cts["branch"],
                                   "deviation_pct": (abs(est - cts["branch"]) / cts["branch"] * 100.0) if cts["branch"] else None, "nominal": _nominal_hint(est)}
    if not known["bus"] and not known["branch"]:
        notes.append("两侧都未勾选「本侧 CT 已知」：只给出台阶比值 ΔI分路/ΔI总线，勾选一侧后可估计另一侧")
    elif known["bus"] and known["branch"]:
        notes.append("两侧都勾选了「本侧 CT 已知」：互为参照各估一次，并与填写值比较（偏差大 ⇒ 某侧 CT、相别或时间段有误）")
    for sd in SIDES:
        e = estimates[sd]
        if e and e.get("nominal"):
            notes.append(f"{SIDE_NAMES[sd]}：{e['nominal']}")
    # 兼容字段：单侧已知时给 estimated_side / estimated_ct
    one = [sd for sd in SIDES if estimates[sd] is not None]
    est_side = one[0] if len(one) == 1 else None
    return {"ok": True, "bus": mb, "branch": mr, "ratio_branch_over_bus": ratio, "known": known, "ct_input": cts, "estimates": estimates,
            "estimated_side": est_side, "estimated_ct": (estimates[est_side]["ct"] if est_side else None),
            "known_side": (("bus" if known["bus"] else "branch") if est_side else None), "known_ct": (estimates[est_side]["known_ct"] if est_side else None),
            "win_cycles": int(win_cycles), "formula": "CT_未知 = CT_已知 × |ΔI_已知侧(二次)| / |ΔI_未知侧(二次)|", "notes": notes}
