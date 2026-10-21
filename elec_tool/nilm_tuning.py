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
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from .config import NILM_ALGO_DEFAULTS, AppConfig


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
