"""Closed allow-list for assistant business tools.

Model output is untrusted. This module only describes the tools that may be proposed and
normalizes their arguments; execution is deliberately implemented by server API adapters.
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, Iterable, List


TOOL_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "set_profile_parameters",
        "title": "修改设备画像匹配阈值",
        "scope": "profile.thresholds.write",
        "description": "修改当前侧设备画像匹配阈值。只允许 d2_max（D²/维上限）和 min_confidence；变更会热更新并按系统现有配置保存规则写入运行配置文件。不要推断未提供的值。",
        "parameters": {
            "type": "object", "properties": {
                "d2_max": {"type": "number", "minimum": 0.01, "maximum": 100},
                "min_confidence": {"type": "number", "minimum": 0.01, "maximum": 1},
            }, "additionalProperties": False,
        },
        "high_risk": True,
    },
    {
        "name": "set_wiring_mode",
        "title": "切换当前侧接线模式",
        "scope": "config.wiring.write",
        "description": "修改当前侧 transform.wiring，只接受 3p3w 或 3p4w；不自动更改 PT/CT、重构或相序参数。",
        "parameters": {"type": "object", "properties": {
            "wiring": {"type": "string", "enum": ["3p3w", "3p4w"]},
        }, "required": ["wiring"], "additionalProperties": False},
        "high_risk": True,
    },
    {
        "name": "load_latest_profile",
        "title": "加载当前侧最新设备画像",
        "scope": "profile.load",
        "description": "从应用 output 目录中选择当前侧文件名标记的最新设备画像，挂载到当前侧并启用画像匹配。不能读取任意路径。",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "high_risk": True,
    },
    {
        "name": "start_current_source",
        "title": "启动当前侧数据源检测",
        "scope": "engine.start",
        "description": "启动当前侧已配置的数据源；不接受模型传入的文件路径，不重启正在运行的数据源，不联动启动另一侧。",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "high_risk": False,
    },
    {
        "name": "export_csv",
        "title": "导出当前侧 CSV",
        "scope": "data.export",
        "description": "导出当前侧已有的电气量结果、负荷辨识事件或已保存曲线 CSV；不会读取原始录波内容并发送给模型。",
        "parameters": {"type": "object", "properties": {
            "dataset": {"type": "string", "enum": ["nilm_events", "electrical_results", "curves"]},
        }, "required": ["dataset"], "additionalProperties": False},
        "high_risk": False,
    },
    {
        "name": "list_recordings",
        "title": "查询可用录波文件",
        "scope": "recordings.read",
        "description": "只列出仓库 data 或 output 下的文件名与大小，不打开、不上传文件内容。",
        "parameters": {"type": "object", "properties": {
            "folder": {"type": "string", "enum": ["data", "output"]},
        }, "required": ["folder"], "additionalProperties": False},
        "high_risk": False,
    },
    {
        "name": "list_profiles",
        "title": "查询设备画像",
        "scope": "profiles.read",
        "description": "只列出应用 output 目录内的设备画像元数据，不读取原始波形。",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "high_risk": False,
    },
    {
        "name": "clear_nilm_events",
        "title": "清空当前侧负荷辨识事件列表",
        "scope": "nilm.events.clear",
        "description": "清除当前侧引擎内存中的负荷辨识事件列表；不会删除磁盘 CSV，也不等同于清除缓存。该动作不可由模型直接执行。",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "high_risk": True,
    },
]

TOOL_BY_NAME = {item["name"]: item for item in TOOL_CATALOG}
TOOL_NAMES = tuple(TOOL_BY_NAME)


def openai_tool_schemas(enabled_names: Iterable[str]) -> List[Dict[str, Any]]:
    """Build OpenAI-compatible function declarations for only globally and personally allowed tools."""
    names = set(enabled_names)
    return [
        {"type": "function", "function": {
            "name": item["name"], "description": item["description"],
            "parameters": item["parameters"],
        }}
        for item in TOOL_CATALOG if item["name"] in names
    ]


def validate_tool_arguments(name: str, raw: Any) -> Dict[str, Any]:
    """Strictly normalize a model-generated tool argument object; reject extras and coercions."""
    item = TOOL_BY_NAME.get(str(name or ""))
    if item is None:
        raise ValueError("模型请求了未注册的工具")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raise ValueError("工具参数不是有效 JSON") from None
    if not isinstance(raw, dict):
        raise ValueError("工具参数必须是 JSON 对象")
    props = item["parameters"].get("properties", {})
    if any(key not in props for key in raw):
        raise ValueError("工具参数包含未注册字段")
    missing = [key for key in item["parameters"].get("required", []) if key not in raw]
    if missing:
        raise ValueError("工具参数缺少必需字段")

    if name == "set_profile_parameters":
        if not raw:
            raise ValueError("至少提供 d2_max 或 min_confidence")
        out: Dict[str, Any] = {}
        for key, low, high in (("d2_max", 0.01, 100.0), ("min_confidence", 0.01, 1.0)):
            if key not in raw:
                continue
            value = raw[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key} 必须是 JSON 数字")
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                raise ValueError(f"{key} 必须是有限数字") from None
            if not math.isfinite(number) or number < low or number > high:
                raise ValueError(f"{key} 必须在 {low:g}–{high:g} 范围内")
            out[key] = number
        return out
    if name == "set_wiring_mode":
        wiring = raw.get("wiring")
        if not isinstance(wiring, str) or wiring not in {"3p3w", "3p4w"}:
            raise ValueError("wiring 只能是 3p3w 或 3p4w")
        return {"wiring": wiring}
    if name == "export_csv":
        dataset = raw.get("dataset")
        if not isinstance(dataset, str) or dataset not in {"nilm_events", "electrical_results", "curves"}:
            raise ValueError("dataset 不在 CSV 导出白名单内")
        return {"dataset": dataset}
    if name == "list_recordings":
        folder = raw.get("folder")
        if not isinstance(folder, str) or folder not in {"data", "output"}:
            raise ValueError("folder 只能是 data 或 output")
        return {"folder": folder}
    return {}
