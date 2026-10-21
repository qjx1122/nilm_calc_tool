"""负荷辨识调参结果 → 配置（v0.50）。

`tools/nilm_tune.py` 量噪声后给出 6 种算法的建议参数；本模块负责把这份建议**叠加到一份现有配置上**并
把更新后的完整配置写到输出目录，供 nilm_tune.py ``--apply``、nilm_replay.py ``--params`` 与
Web 接口 ``POST /api/nilm/tune/apply`` 共用。

原则：
* 只改 ``nilm.quantity / rel_tol_pct / min_delta_pct / algorithms.<算法>.<已知参数>``，其余配置一律保留；
* 建议里没给的参数（如 ``enabled``、界面手改过的其它键）保持原值；
* **默认不回写配置文件**，只在输出目录（``cfg.nilm.nilm_dir``，默认 ``output/nilm``）生成
  ``nilm_tuned_config_<时间戳>.json``；要落到正式配置须显式要求（CLI ``--save-config`` / API ``persist``）。
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import NILM_ALGO_DEFAULTS, NILM_CHANNELS, AppConfig, ConfigError, parse_play_start


class TuneError(ValueError):
    """输入不满足调参条件（无整周波 / 无电压却按 P / I 口径填 total …）；``code`` 与 CLI 退出码一致（2）。"""

    code = 2


_SUFFIX = {"W": "_w", "A": "_a"}



def _ceil_sig(x: float, sig: int = 2) -> float:
    """向上取 2 位有效数字（参数填整数好记）。"""
    if x <= 0 or not math.isfinite(x):
        return 0.0
    e = math.floor(math.log10(x)) - (sig - 1)
    return math.ceil(x / 10 ** e) * 10 ** e


def measure(p: np.ndarray, unit: str = "W") -> dict:
    """逐周波序列（有功 W 或电流有效值 A）的噪声统计。键名不带单位，``unit`` 字段标明。"""
    p = np.asarray(p, dtype=np.float64)
    d = np.diff(p)
    mad_d = float(np.median(np.abs(d - np.median(d)))) * 1.4826          # 差分的稳健 σ_d
    sigma = mad_d / math.sqrt(2.0)                                       # 单周波噪声 σ（差分方差 = 2σ²）
    level = float(np.median(np.abs(p)))
    # 5 周波 / 10 周波滚动极差的 95 分位（稳态容差直接看这个）
    # 稳健口径：取 min(95 分位, 2×中位数)，段内偶有事件时不被少数含事件的窗拉高
    def rng(n: int) -> float:
        if len(p) < n:
            return float("nan")
        w = np.lib.stride_tricks.sliding_window_view(p, n)
        r = w.max(axis=1) - w.min(axis=1)
        return float(min(np.percentile(r, 95), 2.0 * np.median(r)))
    # 相邻两个 10 周波均值之差的稳健 σ（双滑窗 / GLR 的噪声尺度；高斯噪声下 ≈ σ×sqrt(2/10)）
    if len(p) >= 30:
        m10 = np.convolve(p, np.ones(10) / 10, mode="valid")
        dm = m10[10:] - m10[:-10]
        sig_m10 = float(np.median(np.abs(dm - np.median(dm)))) * 1.4826
    else:
        sig_m10 = float("nan")
    return {
        "cycles": int(len(p)), "unit": unit, "level": level,
        "sigma_cycle": sigma, "sigma_cycle_pct": (100.0 * sigma / level if level else float("nan")),
        "max_abs_diff": float(np.max(np.abs(d))) if d.size else 0.0,
        "has_events_hint": bool(d.size and np.max(np.abs(d)) > 10 * sigma),
        "range5_p95": rng(5), "range10_p95": rng(10),
        "sigma_mean10": sig_m10,
        "min": float(p.min()), "max": float(p.max()),
    }


def suggest(m: dict, min_load: float | None) -> dict:
    """由噪声统计给出参数建议（规则见 NILM_TUNING_GUIDE.md §2）。单位随 ``m["unit"]``：W → ``*_w``，A → ``*_a``。"""
    unit = m.get("unit", "W")
    sx = _SUFFIX[unit]
    s, lvl = m["sigma_cycle"], m["level"]
    tol = _ceil_sig(max(m["range5_p95"] * 1.2, 4 * s))                # 稳态容差：5 周波极差 95 分位 ×1.2
    noise_floor = _ceil_sig(max(6 * s, 1e-9))                        # 噪声能触发的最小「阶跃」
    if min_load is None:
        min_d = _ceil_sig(max(noise_floor, 0.02 * lvl))              # 没给最小负荷：取 6σ 与 2% 基荷的大者
        note = f"未指定 --min-load-{sx[1]}，min_delta{sx} 取 max(6σ, 2%×基荷)；请按现场最小关心负荷改"
    else:
        min_d = _ceil_sig(max(0.5 * float(min_load), noise_floor))   # 门槛放在最小负荷的一半，但不低于噪声底
        note = (f"min_delta{sx} = max(最小关心负荷/2, 6σ)" if 0.5 * min_load >= noise_floor
                else f"⚠ 最小关心负荷 {min_load:g} {unit} 的一半低于噪声底 {noise_floor:g} {unit}：该负荷无法可靠检出，门槛按噪声底给")
    k = _ceil_sig(max(0.25 * min_d, 0.5 * s))                        # CUSUM 漂移：取最小幅值的 1/4（兼顾缓慢爬坡）
    h = _ceil_sig(max(2.0 * (min_d - k), 5 * s))                     # 门限：恰为 min_delta 的阶跃约 2 周波触发；且 ≥5σ
    # 相对门槛只在「基荷远大于门槛」时有意义；基荷小（分路侧设备关着时 P≈0）会算出 >100% 甚至几千 %，
    # 配置校验 rel_tol_pct ≤ 50 / min_delta_pct ≤ 100 会拒绝 → 一律夹到合法范围，门槛以绝对值为准
    mdp = (100.0 * min_d / lvl) if lvl else 0.0
    if mdp > 50.0:
        mdp = 0.0
        note += f"；基荷相对门槛过小（基荷 < 2×min_delta{sx}），nilm.min_delta_pct 置 0，只用各算法绝对值 {unit}"
    tol10 = _ceil_sig(max(m["range10_p95"] * 1.2, 5 * s))
    noise = _ceil_sig(max(s, 1e-9))
    return {
        "note": note, "unit": unit, "quantity": "p" if unit == "W" else "i",
        "rel_tol_pct": round(min(5.0, max(0.05, 100.0 * tol / lvl)), 2) if lvl else 1.0,
        "min_delta_pct": round(mdp, 2),
        "algorithms": {
            "threshold":    {f"min_delta{sx}": min_d, "settle_cycles": 5, f"settle_tol{sx}": tol, "max_rise_cycles": 40},
            "median_diff":  {"median_cycles": 5, f"min_delta{sx}": min_d, "settle_cycles": 5, f"settle_tol{sx}": tol, "max_rise_cycles": 40},
            "two_window":   {"pre_cycles": 10, "post_cycles": 10, f"min_delta{sx}": min_d, "k_sigma": 3.0},
            "cusum":        {f"drift{sx}": k, f"threshold{sx}": h, f"min_delta{sx}": min_d, "settle_cycles": 5},
            "glr":          {"window_cycles": 15, "threshold": 25.0, f"min_delta{sx}": min_d, f"noise{sx}": noise, "settle_cycles": 5},
            "steady_state": {f"tol{sx}": tol10, "min_steady_cycles": 10, f"min_delta{sx}": min_d, "max_transient_cycles": 100},
        },
    }


def run_tune(base: AppConfig, file: str, *, channel: Optional[str] = None, quantity: Optional[str] = None,
             min_load_w: Optional[float] = None, min_load_a: Optional[float] = None, max_cycles: int = 30000,
             t_start: str = "", t_end: str = "", duration_s: Optional[float] = None) -> Dict[str, Any]:
    """量一段背景数据的逐周波噪声并给出参数建议（``tools/nilm_tune.py`` 与 ``POST /api/process/nilm_tune`` 共用）。

    - ``base``：提供 PT/CT、fs、f_nom、列映射与缺省 ``nilm.quantity`` 的配置（不被修改）；
    - ``t_start`` / ``t_end``：分析时间段，文本格式同播放时间段（``2026-10-13 08:00:02.5`` / ``08:00:02.5`` / epoch 秒），
      都为空＝整个文件；``duration_s``：从起点（或文件开头）起的时长（秒），与 ``t_end`` 同时给时取先到者；
    - 返回与 CLI ``--json`` 相同结构的 dict，另含 ``t_range``；输入不满足抛 ``TuneError``。
    """
    from .nilm import CycleFeatures
    from .scaling import scale_block
    from .sources import create_source
    cfg = AppConfig.from_dict(base.to_dict())
    cfg.source.kind = "csv_file"; cfg.source.path = file
    cfg.source.file_speed = 0.0; cfg.source.play_window = False; cfg.source.play_end_time = ""
    cfg.source.play_start_mode = "begin"; cfg.source.play_start_value = ""
    ts_txt, te_txt = str(t_start or "").strip(), str(t_end or "").strip()
    if ts_txt:
        parse_play_start("time", ts_txt)                       # 非法时间文本在这里就报 ConfigError
        cfg.source.play_start_mode = "time"; cfg.source.play_start_value = ts_txt
    if te_txt:
        parse_play_start("time", te_txt)
        cfg.source.play_end_time = te_txt
    if duration_s is not None:
        duration_s = float(duration_s)
        if not (duration_s > 0):
            raise TuneError(f"时长必须 > 0 秒（当前 {duration_s}）")
    if ts_txt and te_txt:
        a, b = parse_play_start("time", ts_txt), parse_play_start("time", te_txt)
        if a[0] == b[0] and b[1] <= a[1]:
            raise TuneError(f"结束时间必须晚于开始时间（{ts_txt} → {te_txt}）")
    cfg.validate()
    feat = CycleFeatures(cfg.sampling.fs, cfg.sampling.f_nom)
    ps, is_, ts = [], [], []
    u_nonzero = False
    t_first: Optional[float] = None
    n_cyc = 0
    max_cycles = max(1, int(max_cycles))
    from .sources.parsing import ParseError
    try:
        with create_source(cfg) as src:
            while True:
                blk = src.read()
                if blk is None:
                    if src.exhausted:
                        break
                    continue
                if not u_nonzero and np.any(np.abs(blk.u) > 0):
                    u_nonzero = True
                f = feat.push(scale_block(blk, cfg.transform))
                if f["t"].size:
                    if t_first is None:
                        t_first = float(f["t"][0])
                    if duration_s is not None:
                        keep = f["t"] <= t_first + duration_s
                        if not keep.all():
                            ps.append(f["p"][:, keep]); is_.append(f["i"][:, keep]); ts.append(f["t"][keep])
                            n_cyc += int(keep.sum())
                            break
                    ps.append(f["p"]); is_.append(f["i"]); ts.append(f["t"])
                    n_cyc += int(f["t"].size)
                if n_cyc >= max_cycles:
                    break
    except ParseError as exc:
        raise TuneError(str(exc)) from exc
    if not ps or not sum(x.shape[1] for x in ps):
        raise TuneError("没有读到整周波数据" + ("（指定时间段内无数据，请对照文件时间范围）" if (ts_txt or te_txt) else ""))
    q_req = quantity or str(getattr(cfg.nilm, "quantity", "auto") or "auto")
    qty = q_req if q_req != "auto" else ("i" if not u_nonzero else "p")
    if qty == "p" and not u_nonzero:
        raise TuneError("数据源没有电压（电压列未映射或全为 0）：有功恒为 0，无法按 P 调参；请用 quantity=i（或 auto）")
    unit = "W" if qty == "p" else "A"
    ch = channel or ("total" if qty == "p" else "A")
    if ch not in NILM_CHANNELS:
        raise TuneError(f"检测对象必须是 {list(NILM_CHANNELS)}（当前 {ch!r}）")
    if qty == "i" and ch == "total":
        raise TuneError("仅电流（I 口径）检测不存在跨相合并（三相电流有效值不能像有功那样相加），只能单相：对象请填 A / B / C")
    ci = NILM_CHANNELS.index(ch)
    p = np.concatenate(ps if qty == "p" else is_, axis=1)[ci][:max_cycles]
    t = np.concatenate(ts)[:max_cycles]
    m = measure(p, unit)
    min_load = min_load_w if qty == "p" else min_load_a
    sg = suggest(m, min_load)
    notes: List[str] = []
    if qty == "i" and min_load_w is not None and min_load_a is None:
        notes.append("I 口径请用 min_load_a（A）；min_load_w 已忽略")
    return {"file": file, "channel": ch, "fs": cfg.sampling.fs, "f_nom": cfg.sampling.f_nom,
            "quantity": qty, "quantity_requested": q_req, "unit": unit, "voltage_present": u_nonzero,
            "scaled": bool(cfg.transform.enabled), "t_span_s": float(t[-1] - t[0]) if len(t) > 1 else 0.0,
            "t_range": {"start": ts_txt, "end": te_txt, "duration_s": duration_s,
                        "t_first": float(t[0]), "t_last": float(t[-1]), "whole_file": not (ts_txt or te_txt or duration_s)},
            "notes": notes, "measure": m, "suggest": sg}


def tune_result_path(cfg: AppConfig, name: str = "", out_dir: Optional[str] = None) -> str:
    """调参结果 JSON 的保存路径：``<nilm_dir>/<name>``，name 空＝``tune_<YYYYmmdd_HHMMSS>.json``；
    name 里的 ``{时间}`` / ``{time}`` 占位符替换为时间戳；只取文件名部分（不允许目录穿越）。"""
    d = out_dir or cfg.nilm.nilm_dir or cfg.output.export_dir or "output"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    n = os.path.basename(str(name or "").strip()) or f"tune_{stamp}.json"
    n = n.replace("{时间}", stamp).replace("{time}", stamp)
    if not n.lower().endswith(".json"):
        n += ".json"
    return os.path.join(d, n)


def _fmt(v: Any) -> str:
    return f"{v:g}" if isinstance(v, float) else f"{v}"


def apply_nilm_params(cfg: AppConfig, params: Dict[str, Any]) -> List[str]:
    """把 nilm_tune --json 的输出（整份 / 其 ``suggest`` 片段 / 直接的 nilm 片段）叠加到 ``cfg.nilm``。

    返回逐项说明行（供 CLI 打印 / API 返回）。不校验、不落盘——调用方决定。
    """
    sg = params.get("suggest", params) if isinstance(params, dict) else {}
    if isinstance(sg, dict) and "nilm" in sg and isinstance(sg["nilm"], dict):   # 允许直接给 {"nilm": {...}}
        sg = sg["nilm"]
    notes: List[str] = []
    q = sg.get("quantity") or (params.get("quantity") if isinstance(params, dict) else None)
    if q in ("auto", "p", "i"):
        cfg.nilm.quantity = q; notes.append(f"nilm.quantity = {q}")
    if "rel_tol_pct" in sg:
        cfg.nilm.rel_tol_pct = float(sg["rel_tol_pct"]); notes.append(f"nilm.rel_tol_pct = {cfg.nilm.rel_tol_pct}")
    if "min_delta_pct" in sg:
        cfg.nilm.min_delta_pct = float(sg["min_delta_pct"]); notes.append(f"nilm.min_delta_pct = {cfg.nilm.min_delta_pct}")
    for algo, prm in (sg.get("algorithms") or {}).items():
        if algo not in NILM_ALGO_DEFAULTS or not isinstance(prm, dict):
            continue
        upd = {k: v for k, v in prm.items() if k in NILM_ALGO_DEFAULTS[algo]}
        if not upd:
            continue
        cur = dict(cfg.nilm.algorithms.get(algo) or {})
        cur.update(upd)
        cfg.nilm.algorithms[algo] = cur
        notes.append(f"{algo}: " + "  ".join(f"{k}={_fmt(v)}" for k, v in upd.items()))   # 只列实际套用的键
    return notes


def tuned_config_path(cfg: AppConfig, out_dir: Optional[str] = None, tag: str = "") -> str:
    """默认输出路径：``<nilm_dir>/nilm_tuned_config[_<tag>]_<YYYYmmdd_HHMMSS>.json``。"""
    d = out_dir or cfg.nilm.nilm_dir or cfg.output.export_dir or "output"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    name = "nilm_tuned_config" + (f"_{tag}" if tag else "") + f"_{stamp}.json"
    return os.path.join(d, name)


def export_tuned_config(base: AppConfig, params: Dict[str, Any], *, out_path: Optional[str] = None,
                        out_dir: Optional[str] = None, tag: str = "",
                        meta: Optional[Dict[str, Any]] = None) -> Tuple[AppConfig, str, List[str]]:
    """在 ``base`` 的副本上叠加建议参数，校验后写到输出目录，返回 (新配置, 文件路径, 说明行)。

    ``base`` 本身不被修改；写出的 JSON 是**完整配置**（可直接作为 ``--config`` / ELEC_TOOL_CONFIG_PATH 使用），
    附带 ``_tuning`` 元信息（来源文件、对象、时间、改动项）便于追溯；``AppConfig.from_dict`` 会忽略未知键。
    """
    cfg = AppConfig.from_dict(base.to_dict())
    notes = apply_nilm_params(cfg, params)
    cfg.validate()
    path = out_path or tuned_config_path(cfg, out_dir, tag)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    data = cfg.to_dict()
    info: Dict[str, Any] = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "changes": notes}
    if isinstance(params, dict):
        for k in ("file", "channel", "quantity", "unit", "t_span_s"):
            if k in params:
                info[k] = params[k]
    if meta:
        info.update(meta)
    data["_tuning"] = info
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return cfg, path, notes
