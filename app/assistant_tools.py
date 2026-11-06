"""Closed allow-list for assistant business tools.

Model output is untrusted. This module declares only fixed application operations and
strictly normalizes their arguments; server-side adapters perform scope, path, range and
state checks again before invoking existing business logic.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional

from elec_tool.config import CURVE_KEYS, NILM_ALGO_DEFAULTS, NILM_CHANNELS, NILM_QUANTITIES, QUANTITY_KEYS

EVENT_TYPE_KEYS = ("fund_phasor", "harm_phasor", "interharm", "freq", "rocof", "power_osc")
EVENT_PARAMETER_KEYS = (
    "hysteresis", "u_nom", "u1_high_pct", "u1_low_pct", "i1_high",
    "hr_u_limit_pct", "hr_i_limit_pct", "thd_u_limit_pct", "thd_i_limit_pct",
    "ih_u_limit_pct", "ih_i_limit_pct", "f_low", "f_high", "rocof_limit",
    "osc_window_s", "osc_f_min", "osc_f_max", "osc_limit_pct", "osc_min_w", "osc_min_points",
)
NILM_PARAMETER_KEYS = tuple(sorted({
    key for params in NILM_ALGO_DEFAULTS.values() for key in params if key != "enabled"
}))
_FILE_ID_RE = re.compile(r"^[0-9a-f]{24}$")
_PROFILE_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_SAFE_DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _object(properties: Dict[str, Any], required: Iterable[str] = ()) -> Dict[str, Any]:
    schema: Dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    required_list = list(required)
    if required_list:
        schema["required"] = required_list
    return schema


def _tool(name: str, title: str, scope: str, description: str,
          properties: Optional[Dict[str, Any]] = None, required: Iterable[str] = (),
          high_risk: bool = False) -> Dict[str, Any]:
    return {"name": name, "title": title, "scope": scope, "description": description,
            "parameters": _object(properties or {}, required), "high_risk": high_risk}


TOOL_CATALOG: List[Dict[str, Any]] = [
    _tool("get_runtime_status", "查询当前侧运行状态", "state.read",
          "读取当前侧运行/暂停/结束状态、样本与历史摘要；不返回绝对路径、主机地址或配置文件内容。"),
    _tool("get_runtime_settings", "查询当前侧计算配置摘要", "config.read",
          "读取采样率、变比、接线、窗口、事件与负荷辨识的白名单摘要；不返回路径、主机/端口或任意完整配置。"),
    _tool("get_electrical_result", "查询当前侧最新电气量结果", "results.read",
          "只读取指定电气量的最新结果并截断大型数组；不读取原始录波文件。",
          {"quantity": {"type": "string", "enum": list(QUANTITY_KEYS)}}, ["quantity"]),
    _tool("get_history", "查询当前侧趋势历史", "history.read",
          "读取指定电气量最近一段趋势，时间最多 720 小时，最多返回 50 个抽稀点。",
          {"quantity": {"type": "string", "enum": list(QUANTITY_KEYS)},
           "hours": {"type": "number", "minimum": 0.001, "maximum": 720},
           "max_points": {"type": "integer", "minimum": 1, "maximum": 50}}, ["quantity"]),
    _tool("get_event_list", "查询电能质量事件", "events.read",
          "读取当前侧活动或历史电能质量事件，可按固定事件类型过滤，最多返回 50 条。",
          {"active": {"type": "boolean"},
           "event_type": {"type": "string", "enum": list(EVENT_TYPE_KEYS)},
           "limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    _tool("get_nilm_events", "查询负荷辨识事件", "nilm.events.read",
          "读取当前侧负荷辨识事件，可按固定算法、相别过滤，最多返回 50 条。",
          {"algorithm": {"type": "string", "enum": list(NILM_ALGO_DEFAULTS)},
           "channel": {"type": "string", "enum": list(NILM_CHANNELS)},
           "limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    _tool("compare_sides", "查询两侧电气量对比", "compare.read",
          "读取总线侧与分路侧指定曲线的时间对齐与差值摘要；最多 50 个点，不修改对齐参数。",
          {"quantity": {"type": "string", "enum": list(QUANTITY_KEYS)},
           "hours": {"type": "number", "minimum": 0.001, "maximum": 720},
           "max_points": {"type": "integer", "minimum": 1, "maximum": 50}}, ["quantity"]),
    _tool("load_last_history", "加载上次落盘的历史数据", "history.load",
          "把当前侧上次播放保存的曲线/事件/负荷事件载入内存供页面查看；不会启动数据源。",
          {"hours": {"type": "number", "minimum": 0.001, "maximum": 720},
           "curves": {"type": "boolean"}, "events": {"type": "boolean"}, "nilm": {"type": "boolean"}}),

    _tool("start_current_source", "启动当前侧数据源检测", "engine.start",
          "用户明确说‘播放数据源’、‘播放/启动离线数据源或CSV文件’、‘开始播放当前数据源’时，表示启动当前侧已配置的数据源，使用本工具；这些说法不表示修改播放速度。"
          "不接受模型传入的文件路径，不猜测或切换文件，不重启正在运行的数据源；未配置或当前来源不匹配时由服务端拒绝并提示。"
          "不得用查询可用录波或查询设备画像代替启动。总线侧可能按现有设置联动分路侧。",
          high_risk=True),

    _tool("pause_current_source", "暂停当前侧离线播放", "engine.pause",
          "暂停当前侧已运行的 csv_file 离线播放；实时源不支持暂停。总线侧按应用既有逻辑尝试同步分路侧。"),
    _tool("resume_current_source", "恢复当前侧离线播放", "engine.resume",
          "从暂停处继续当前侧 csv_file 离线播放；总线侧按应用既有逻辑尝试同步分路侧。"),
    _tool("stop_current_source", "停止当前侧数据源", "engine.stop",
          "停止当前侧数据源。总线侧依应用既有行为也会停止分路侧；执行前请确认影响范围。",
          high_risk=True),
    _tool("select_recording_source", "选择受控录波文件为数据源", "source.select",
          "将服务端上下文中已登记的录波 file_id 设为当前侧 csv_file 数据源。模型只能提交文件 ID，不能提交路径、目录或网络地址。",
          {"file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern}}, ["file_id"], high_risk=True),

    _tool("list_recordings", "查询可用录波文件", "recordings.read",
          "仅在用户明确要求列出可用录波文件时使用；只接受 folder（data/output）一个参数，不接受 side/path/source 等字段；列出固定 data / output 目录中服务端登记的 CSV/TXT 文件 ID、名称与大小；不返回绝对路径，不会把文件内容交给模型，也不能代替启动当前数据源。",
          {"folder": {"type": "string", "enum": ["data", "output"]}}, ["folder"]),
    _tool("inspect_recording", "检查录波文件信息", "recordings.inspect",
          "通过服务端签发的 file_id 检查采样率、点数、时长、通道和时间范围；不接受路径，结果不包含绝对路径。",
          {"file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern}}, ["file_id"]),
    _tool("analyze_recording_rms", "分析录波有效值摘要", "recordings.analyze",
          "通过受控 file_id 计算最多 120 秒的单通道逐周波 RMS，并只返回摘要统计，不向模型发送原始采样序列。",
          {"file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern},
           "channel": {"type": "string", "enum": ["Ua", "Ub", "Uc", "Ia", "Ib", "Ic"]},
           "duration_s": {"type": "number", "minimum": 0.01, "maximum": 120}}, ["file_id", "channel"]),
    _tool("tune_recording", "分析录波并生成负荷辨识调参建议", "recordings.tune",
          "通过受控 file_id 运行负荷辨识调参分析，不保存建议、不改运行配置；最多处理 30,000 周波。",
          {"file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern},
           "max_cycles": {"type": "integer", "minimum": 1000, "maximum": 30000}}, ["file_id"]),
    _tool("resample_recording", "重采样录波文件", "recordings.resample",
          "通过受控 file_id 将录波重采样到固定 data 目录；仅新建文件、不覆盖、不接受输出路径。会启动后台任务。",
          {"file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern},
           "fs_new": {"type": "number", "minimum": 100, "maximum": 1000000},
           "method": {"type": "string", "enum": ["linear", "nearest", "fft"]}},
          ["file_id", "fs_new"], high_risk=True),
    _tool("get_resample_status", "查询重采样任务状态", "recordings.resample.read",
          "读取当前后台重采样任务状态摘要，不返回文件系统绝对路径。"),
    _tool("cancel_resample", "取消重采样任务", "recordings.resample.cancel",
          "请求取消当前正在运行的重采样任务；已写出的部分数据由现有任务取消逻辑处理。"),

    _tool("estimate_ct_ratio", "估算两侧 CT 变比", "ct.estimate",
          "使用两侧受控录波 ID 和启停时间测量同一相电流台阶；只给出估算，不修改 CT 配置。不要猜测事件时间或 CT 已知值。",
          {"bus_file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern},
           "branch_file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern},
           "event": {"type": "string", "enum": ["start", "stop"]},
           "bus_t_begin": {"type": "string", "minLength": 1, "maxLength": 64},
           "bus_t_end": {"type": "string", "minLength": 1, "maxLength": 64},
           "branch_t_begin": {"type": "string", "minLength": 1, "maxLength": 64},
           "branch_t_end": {"type": "string", "minLength": 1, "maxLength": 64},
           "phase": {"type": "string", "enum": ["A", "B", "C"]},
           "known_side": {"type": "string", "enum": ["bus", "branch"]},
           "known_ct": {"type": "number", "minimum": 0.001, "maximum": 100000},
           "win_cycles": {"type": "integer", "minimum": 3, "maximum": 500}},
          ["bus_file_id", "branch_file_id", "event", "bus_t_begin", "bus_t_end", "branch_t_begin", "branch_t_end", "phase"]),
    _tool("extract_device_profile", "从录波提取设备画像", "profile.extract",
          "通过受控录波 file_id 提取设备画像并保存到应用配置的 NILM 输出目录；不接受文件路径或输出目录。会生成文件，需二次确认。",
          {"file_id": {"type": "string", "pattern": _FILE_ID_RE.pattern},
           "device_id": {"type": "string", "minLength": 1, "maxLength": 64},
           "labels": {"type": "string", "maxLength": 2000},
           "pre_cycles": {"type": "integer", "minimum": 3, "maximum": 5000},
           "post_cycles": {"type": "integer", "minimum": 3, "maximum": 10000},
           "max_cycles": {"type": "integer", "minimum": 1000, "maximum": 300000},
           "quantity": {"type": "string", "enum": list(NILM_QUANTITIES)},
           "phases": {"type": "string", "enum": ["auto", "A", "B", "C", "AB", "AC", "BC"]}},
          ["file_id", "device_id"], high_risk=True),
    _tool("derive_profile_stages", "派生多档位设备画像", "profile.derive",
          "从当前侧 output 目录已登记的画像 ID 派生最多 5 份假设档位画像；输出固定在原画像目录，不接受任何路径。",
          {"profile_id": {"type": "string", "pattern": _PROFILE_ID_RE.pattern},
           "scales": {"type": "array", "minItems": 1, "maxItems": 5,
                      "items": {"type": "number", "minimum": 0.05, "maximum": 20}},
           "q_mode": {"type": "string", "enum": ["scale", "const"]}},
          ["profile_id", "scales"], high_risk=True),

    _tool("export_csv", "导出当前侧 CSV", "data.export",
          "导出当前侧已有的电气量结果、负荷辨识事件或已保存曲线 CSV；不会读取原始录波内容并发送给模型。",
          {"dataset": {"type": "string", "enum": ["nilm_events", "electrical_results", "curves"]}}, ["dataset"]),
    _tool("set_profile_parameters", "修改设备画像匹配阈值", "profile.thresholds.write",
          "修改当前侧设备画像匹配阈值。只允许 d2_max 和 min_confidence；不要推断未提供的值。",
          {"d2_max": {"type": "number", "minimum": 0.01, "maximum": 100},
           "min_confidence": {"type": "number", "minimum": 0.01, "maximum": 1}}, high_risk=True),
    _tool("set_profile_detection_enabled", "启用或停用画像匹配算法", "profile.enabled.write",
          "只切换当前侧设备画像匹配算法开关，不修改画像文件或其他阈值。",
          {"enabled": {"type": "boolean"}}, ["enabled"], high_risk=True),
    _tool("list_profiles", "查询设备画像", "profiles.read",
          "仅在用户明确要求查询设备画像时使用；只列出应用 output 目录当前侧的设备画像 ID 与元数据，"
          "不读取原始波形或返回本地绝对路径，也不能代替启动当前数据源。"),
    _tool("load_latest_profile", "加载当前侧最新设备画像", "profile.load",
          "从应用 output 目录中选择当前侧最新设备画像，挂载并启用画像匹配；不能读取任意路径。",
          high_risk=True),
    _tool("load_profile_by_id", "加载指定设备画像", "profile.load",
          "只按服务端当前侧画像目录中列出的 profile_id 挂载并启用画像匹配；不能提交路径。",
          {"profile_id": {"type": "string", "pattern": _PROFILE_ID_RE.pattern}}, ["profile_id"], high_risk=True),
    _tool("set_wiring_mode", "切换当前侧接线模式", "config.wiring.write",
          "修改当前侧 transform.wiring，只接受 3p3w 或 3p4w；不自动更改 PT/CT、重构或相序参数。",
          {"wiring": {"type": "string", "enum": ["3p3w", "3p4w"]}}, ["wiring"], high_risk=True),
    _tool("set_electrical_parameters", "修改采样与电气变换参数", "config.electrical.write",
          "只修改 schema 中明确列出的采样频率、额定频率、PT/CT、接线电压口径和电流极性/重构参数；服务端重做 Nyquist 与互相关校验。",
          {"fs": {"type": "number", "minimum": 100, "maximum": 10000000},
           "f_nom": {"type": "number", "minimum": 1, "maximum": 500},
           "f_min": {"type": "number", "minimum": 1, "maximum": 500},
           "f_max": {"type": "number", "minimum": 1, "maximum": 500},
           "pt_ratio": {"type": "number", "minimum": 0.001, "maximum": 1000000},
           "ct_ratio": {"type": "number", "minimum": 0.001, "maximum": 1000000},
           "voltage_input": {"type": "string", "enum": ["phase", "line"]},
           "invert_current": {"type": "boolean"},
           "invert_phases": {"type": "string", "enum": ["", "A", "B", "C", "AB", "AC", "BC", "ABC"]},
           "reconstruct_3w": {"type": "boolean"}}, high_risk=True),
    _tool("set_harmonic_parameters", "修改谐波分析范围", "config.harmonic.write",
          "只修改谐波起止次数、THD 最高次数或间谐波输出开关；服务端按当前采样率与 Nyquist 限制校验。",
          {"order_min": {"type": "integer", "minimum": 1, "maximum": 1000},
           "order_max": {"type": "integer", "minimum": 1, "maximum": 1000},
           "thd_order_max": {"type": "integer", "minimum": 1, "maximum": 1000},
           "include_interharmonic": {"type": "boolean"}}, high_risk=True),
    _tool("set_power_calculation_mode", "修改功率计算口径", "config.power.write",
          "只修改视在功率、无功功率计算口径或基波功率输出开关；不更改采样、变比或接线配置。",
          {"apparent": {"type": "string", "enum": ["arithmetic", "vector"]},
           "reactive": {"type": "string", "enum": ["harmonic_sum", "quadrature"]},
           "fundamental_power": {"type": "boolean"}}, high_risk=True),
    _tool("set_compare_alignment", "修改跨侧对齐参数", "compare.config.write",
          "只修改总线侧 branch.time_offset_s / align_tol_s；不会改动两侧数据源或计算结果。",
          {"offset_s": {"type": "number", "minimum": -86400, "maximum": 86400},
           "tolerance_s": {"type": "number", "minimum": 0, "maximum": 3600}}, high_risk=True),
    _tool("set_playback_speed", "修改离线播放速度", "config.source.write",
          "仅当用户明确要求修改当前侧离线播放速度/倍速并给出目标数值时使用；‘播放’或‘启动’数据源不属于调速请求，本工具也不会启动数据源。"
          "只修改当前侧 csv_file 倍速；0 表示不限速，正值为实时倍数，不接受数据源路径或网络参数。",
          {"speed": {"type": "number", "minimum": 0, "maximum": 100}}, ["speed"], high_risk=True),
    _tool("set_file_time_utc", "设置录波时标解释方式", "config.source.write",
          "切换当前侧离线文件文本时标按 UTC 或本机本地时间解释；仅修改布尔设置，不读取或更换文件。",
          {"use_utc": {"type": "boolean"}}, ["use_utc"], high_risk=True),
    _tool("set_window_parameters", "修改电气量计算窗口", "config.windows.write",
          "只修改指定电气量的窗长和/或输出步长，服务端会按采样率与应用配置规则重新校验。",
          {"quantity": {"type": "string", "enum": list(QUANTITY_KEYS)},
           "length_s": {"type": "number", "minimum": 0.000001, "maximum": 3600},
           "step_s": {"type": "number", "minimum": 0.000001, "maximum": 3600}}, ["quantity"], high_risk=True),
    _tool("set_event_parameter", "修改电能质量事件阈值", "events.thresholds.write",
          "只修改固定白名单内的一项数值型事件阈值，不接受事件落盘目录、文件名或其他配置字段。",
          {"parameter": {"type": "string", "enum": list(EVENT_PARAMETER_KEYS)},
           "value": {"type": "number", "minimum": 0, "maximum": 100000000}},
          ["parameter", "value"], high_risk=True),
    _tool("set_event_detection_enabled", "启用或停用电能质量事件检测", "events.config.write",
          "只切换当前侧电能质量事件检测总开关，不修改阈值、落盘路径或事件数据。",
          {"enabled": {"type": "boolean"}}, ["enabled"], high_risk=True),
    _tool("set_nilm_parameter", "修改负荷辨识算法参数", "nilm.parameters.write",
          "只修改一个已注册算法的数值参数；参数键、取值范围与整数/枚举约束由服务端再次校验。",
          {"algorithm": {"type": "string", "enum": list(NILM_ALGO_DEFAULTS)},
           "parameter": {"type": "string", "enum": list(NILM_PARAMETER_KEYS)},
           "value": {"type": "number", "minimum": 0, "maximum": 100000}},
          ["algorithm", "parameter", "value"], high_risk=True),
    _tool("set_nilm_algorithm_enabled", "启用或停用负荷辨识算法", "nilm.parameters.write",
          "只切换一个已注册负荷辨识算法的 enabled 开关，不修改该算法其他参数。",
          {"algorithm": {"type": "string", "enum": list(NILM_ALGO_DEFAULTS)},
           "enabled": {"type": "boolean"}}, ["algorithm", "enabled"], high_risk=True),
    _tool("set_nilm_core_parameters", "修改负荷辨识基础参数", "nilm.parameters.write",
          "只修改已列出的负荷辨识总开关、检测量、对象或周波/比例参数；不接受路径、输出目录、画像列表或任意配置对象。",
          {"enabled": {"type": "boolean"}, "auto_params": {"type": "boolean"},
           "quantity": {"type": "string", "enum": list(NILM_QUANTITIES)},
           "channel": {"type": "string", "enum": list(NILM_CHANNELS)},
           "window_cycles": {"type": "integer", "minimum": 30, "maximum": 100000},
           "min_gap_cycles": {"type": "integer", "minimum": 0, "maximum": 100000},
           "rel_tol_pct": {"type": "number", "minimum": 0, "maximum": 50},
           "min_delta_pct": {"type": "number", "minimum": 0, "maximum": 100}}, high_risk=True),
    _tool("set_curve_save_enabled", "设置趋势曲线保存开关", "config.output.write",
          "切换一个固定趋势曲线的保存开关；不修改导出目录或任何文件路径。",
          {"quantity": {"type": "string", "enum": list(CURVE_KEYS)},
           "enabled": {"type": "boolean"}}, ["quantity", "enabled"], high_risk=True),

    _tool("clear_events", "清空当前侧电能质量事件列表", "events.clear",
          "清除当前侧引擎内存中的电能质量事件列表；不会删除磁盘 CSV。",
          high_risk=True),
    _tool("clear_nilm_events", "清空当前侧负荷辨识事件列表", "nilm.events.clear",
          "清除当前侧引擎内存中的负荷辨识事件列表；不会删除磁盘 CSV，也不等同于清除缓存。",
          high_risk=True),
    _tool("run_algorithm_selftest", "运行算法自检", "selftest.run",
          "使用当前侧采样率、额定频率与变比运行内置解析解自检；只返回检查摘要，不修改配置。"),
]

TOOL_BY_NAME = {item["name"]: item for item in TOOL_CATALOG}
TOOL_NAMES = tuple(TOOL_BY_NAME)


def openai_tool_schemas(enabled_names: Iterable[str]) -> List[Dict[str, Any]]:
    """Build OpenAI-compatible function declarations for only globally/operator-allowed tools."""
    names = set(enabled_names)
    return [
        {"type": "function", "function": {
            "name": item["name"], "description": item["description"],
            "parameters": item["parameters"],
        }}
        for item in TOOL_CATALOG if item["name"] in names
    ]


def _strict_string(raw: Dict[str, Any], key: str, *, choices: Optional[Iterable[str]] = None,
                   pattern: Optional[re.Pattern[str]] = None, max_length: int = 256,
                   required: bool = False) -> Optional[str]:
    if key not in raw:
        if required:
            raise ValueError(f"{key} 必须提供")
        return None
    value = raw[key]
    if not isinstance(value, str):
        raise ValueError(f"{key} 必须是文本")
    if not value or len(value) > max_length or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{key} 长度或字符无效")
    if choices is not None and value not in choices:
        raise ValueError(f"{key} 不在固定白名单内")
    if pattern is not None and not pattern.fullmatch(value):
        raise ValueError(f"{key} 格式无效")
    return value


def _strict_bool(raw: Dict[str, Any], key: str, *, required: bool = False) -> Optional[bool]:
    if key not in raw:
        if required:
            raise ValueError(f"{key} 必须提供")
        return None
    value = raw[key]
    if not isinstance(value, bool):
        raise ValueError(f"{key} 必须是 JSON 布尔值")
    return value


def _strict_number(raw: Dict[str, Any], key: str, low: float, high: float, *,
                   integer: bool = False, required: bool = False) -> Optional[float | int]:
    if key not in raw:
        if required:
            raise ValueError(f"{key} 必须提供")
        return None
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} 必须是 JSON 数字")
    number = float(value)
    if not math.isfinite(number) or number < low or number > high:
        raise ValueError(f"{key} 必须在 {low:g}–{high:g} 范围内")
    if integer:
        if int(number) != number:
            raise ValueError(f"{key} 必须是整数")
        return int(number)
    return number


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
    # get_runtime_status / get_runtime_settings / list_recordings 不接受 side 参数；
    # 侧别通过 plan 的 _side 字段传递，模型不应通过工具参数传递 side。
    # 为防御性起见，若模型误传 side，将其忽略而非报"未注册字段"。
    if name in {"get_runtime_status", "get_runtime_settings", "list_recordings"}:
        raw = {k: v for k, v in raw.items() if k != "side"}
    if any(key not in props for key in raw):
        unknown = [k for k in raw if k not in props]
        allowed = sorted(props.keys())
        raise ValueError(f"工具参数包含未注册字段：{', '.join(unknown)}；该工具仅接受：{', '.join(allowed)}")
    missing = [key for key in item["parameters"].get("required", []) if key not in raw]
    if missing:
        raise ValueError("工具参数缺少必需字段")

    if name == "set_profile_parameters":
        if not raw:
            raise ValueError("至少提供 d2_max 或 min_confidence")
        out = {}
        for key, bounds in (("d2_max", (0.01, 100.0)), ("min_confidence", (0.01, 1.0))):
            if key in raw:
                out[key] = _strict_number(raw, key, *bounds, required=True)
        return out
    if name == "set_wiring_mode":
        return {"wiring": _strict_string(raw, "wiring", choices=("3p3w", "3p4w"), required=True)}
    if name == "set_electrical_parameters":
        out: Dict[str, Any] = {}
        numeric = {"fs": (100, 10_000_000), "f_nom": (1, 500), "f_min": (1, 500), "f_max": (1, 500),
                   "pt_ratio": (0.001, 1_000_000), "ct_ratio": (0.001, 1_000_000)}
        for key, (low, high) in numeric.items():
            value = _strict_number(raw, key, low, high)
            if value is not None:
                out[key] = value
        voltage_input = _strict_string(raw, "voltage_input", choices=("phase", "line"))
        invert_phases = ("" if raw.get("invert_phases") == "" and "invert_phases" in raw
                         else _strict_string(raw, "invert_phases", choices=("A", "B", "C", "AB", "AC", "BC", "ABC")))
        if voltage_input is not None: out["voltage_input"] = voltage_input
        if invert_phases is not None: out["invert_phases"] = invert_phases
        for key in ("invert_current", "reconstruct_3w"):
            value = _strict_bool(raw, key)
            if value is not None: out[key] = value
        if not out:
            raise ValueError("至少提供一个采样或电气变换参数")
        return out
    if name == "set_harmonic_parameters":
        out = {}
        for key in ("order_min", "order_max", "thd_order_max"):
            value = _strict_number(raw, key, 1, 1000, integer=True)
            if value is not None: out[key] = value
        interharmonic = _strict_bool(raw, "include_interharmonic")
        if interharmonic is not None: out["include_interharmonic"] = interharmonic
        if not out: raise ValueError("至少提供一个谐波分析参数")
        return out
    if name == "set_power_calculation_mode":
        out = {}
        apparent = _strict_string(raw, "apparent", choices=("arithmetic", "vector"))
        reactive = _strict_string(raw, "reactive", choices=("harmonic_sum", "quadrature"))
        fundamental = _strict_bool(raw, "fundamental_power")
        if apparent is not None: out["apparent"] = apparent
        if reactive is not None: out["reactive"] = reactive
        if fundamental is not None: out["fundamental_power"] = fundamental
        if not out: raise ValueError("至少提供一个功率计算口径")
        return out
    if name == "set_compare_alignment":
        out = {}
        offset = _strict_number(raw, "offset_s", -86400, 86400)
        tolerance = _strict_number(raw, "tolerance_s", 0, 3600)
        if offset is not None: out["offset_s"] = offset
        if tolerance is not None: out["tolerance_s"] = tolerance
        if not out: raise ValueError("至少提供 offset_s 或 tolerance_s")
        return out
    if name == "set_playback_speed":
        return {"speed": _strict_number(raw, "speed", 0, 100, required=True)}
    if name == "set_file_time_utc":
        return {"use_utc": _strict_bool(raw, "use_utc", required=True)}
    if name == "export_csv":
        return {"dataset": _strict_string(raw, "dataset", choices=("nilm_events", "electrical_results", "curves"), required=True)}
    if name == "list_recordings":
        return {"folder": _strict_string(raw, "folder", choices=("data", "output"), required=True)}
    if name in {"select_recording_source", "inspect_recording", "tune_recording", "resample_recording",
                "analyze_recording_rms", "extract_device_profile"}:
        out = {"file_id": _strict_string(raw, "file_id", pattern=_FILE_ID_RE, required=True)}
        if name == "resample_recording":
            out["fs_new"] = _strict_number(raw, "fs_new", 100, 1_000_000, required=True)
            method = _strict_string(raw, "method", choices=("linear", "nearest", "fft"))
            if method is not None:
                out["method"] = method
        elif name == "analyze_recording_rms":
            channel = _strict_string(raw, "channel", choices=("Ua", "Ub", "Uc", "Ia", "Ib", "Ic"), required=True)
            duration = _strict_number(raw, "duration_s", 0.01, 120)
            if channel is not None:
                out["channel"] = channel
            if duration is not None:
                out["duration_s"] = duration
        elif name == "tune_recording":
            cycles = _strict_number(raw, "max_cycles", 1000, 30_000, integer=True)
            if cycles is not None:
                out["max_cycles"] = cycles
        elif name == "extract_device_profile":
            device = _strict_string(raw, "device_id", max_length=64, required=True)
            if not _SAFE_DEVICE_ID_RE.fullmatch(device or ""):
                raise ValueError("device_id 只能包含英文字母、数字、点、下划线和连字符")
            out["device_id"] = device
            if "labels" in raw:
                labels = raw["labels"]
                if not isinstance(labels, str) or len(labels) > 2000 or any(
                        (ord(ch) < 32 and ch not in "\r\n\t") or ord(ch) == 127 for ch in labels):
                    raise ValueError("labels 必须是不超过 2000 字符的标签文本")
                out["labels"] = labels
            for key, low, high in (("pre_cycles", 3, 5000), ("post_cycles", 3, 10000),
                                   ("max_cycles", 1000, 300000)):
                value = _strict_number(raw, key, low, high, integer=True)
                if value is not None:
                    out[key] = value
            quantity = _strict_string(raw, "quantity", choices=NILM_QUANTITIES)
            phases = _strict_string(raw, "phases", choices=("auto", "A", "B", "C", "AB", "AC", "BC"))
            if quantity is not None:
                out["quantity"] = quantity
            if phases is not None:
                out["phases"] = phases
        return out
    if name == "load_profile_by_id":
        return {"profile_id": _strict_string(raw, "profile_id", pattern=_PROFILE_ID_RE, required=True)}
    if name == "derive_profile_stages":
        profile_id = _strict_string(raw, "profile_id", pattern=_PROFILE_ID_RE, required=True)
        values = raw.get("scales")
        if not isinstance(values, list) or not 1 <= len(values) <= 5:
            raise ValueError("scales 必须是 1–5 个数值的数组")
        scales: List[float] = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("scales 中每一项都必须是 JSON 数字")
            number = float(value)
            if not math.isfinite(number) or not 0.05 <= number <= 20:
                raise ValueError("scales 中每一项必须在 0.05–20 范围内")
            scales.append(number)
        if len(set(scales)) != len(scales):
            raise ValueError("scales 不能包含重复档位")
        q_mode = _strict_string(raw, "q_mode", choices=("scale", "const"))
        out = {"profile_id": profile_id, "scales": scales}
        if q_mode is not None:
            out["q_mode"] = q_mode
        return out
    if name == "estimate_ct_ratio":
        out: Dict[str, Any] = {
            "bus_file_id": _strict_string(raw, "bus_file_id", pattern=_FILE_ID_RE, required=True),
            "branch_file_id": _strict_string(raw, "branch_file_id", pattern=_FILE_ID_RE, required=True),
            "event": _strict_string(raw, "event", choices=("start", "stop"), required=True),
            "phase": _strict_string(raw, "phase", choices=("A", "B", "C"), required=True),
        }
        for key in ("bus_t_begin", "bus_t_end", "branch_t_begin", "branch_t_end"):
            out[key] = _strict_string(raw, key, max_length=64, required=True)
        known_side = _strict_string(raw, "known_side", choices=("bus", "branch"))
        known_ct = _strict_number(raw, "known_ct", 0.001, 100_000)
        if (known_side is None) != (known_ct is None):
            raise ValueError("known_side 与 known_ct 必须同时提供，或都不提供")
        if known_side is not None:
            out["known_side"] = known_side
            out["known_ct"] = known_ct
        cycles = _strict_number(raw, "win_cycles", 3, 500, integer=True)
        if cycles is not None:
            out["win_cycles"] = cycles
        return out
    if name in {"get_electrical_result", "get_history", "compare_sides"}:
        out = {"quantity": _strict_string(raw, "quantity", choices=QUANTITY_KEYS, required=True)}
        if name != "get_electrical_result":
            hours = _strict_number(raw, "hours", 0.001, 720)
            points = _strict_number(raw, "max_points", 1, 50, integer=True)
            if hours is not None:
                out["hours"] = hours
            if points is not None:
                out["max_points"] = points
        return out
    if name == "get_event_list":
        out: Dict[str, Any] = {}
        active = _strict_bool(raw, "active")
        event_type = _strict_string(raw, "event_type", choices=EVENT_TYPE_KEYS)
        limit = _strict_number(raw, "limit", 1, 50, integer=True)
        if active is not None:
            out["active"] = active
        if event_type is not None:
            out["event_type"] = event_type
        if limit is not None:
            out["limit"] = limit
        return out
    if name == "get_nilm_events":
        out = {}
        algo = _strict_string(raw, "algorithm", choices=NILM_ALGO_DEFAULTS)
        channel = _strict_string(raw, "channel", choices=NILM_CHANNELS)
        limit = _strict_number(raw, "limit", 1, 50, integer=True)
        if algo is not None:
            out["algorithm"] = algo
        if channel is not None:
            out["channel"] = channel
        if limit is not None:
            out["limit"] = limit
        return out
    if name == "load_last_history":
        out = {}
        hours = _strict_number(raw, "hours", 0.001, 720)
        if hours is not None:
            out["hours"] = hours
        for key in ("curves", "events", "nilm"):
            value = _strict_bool(raw, key)
            if value is not None:
                out[key] = value
        return out
    if name == "set_profile_detection_enabled":
        return {"enabled": _strict_bool(raw, "enabled", required=True)}
    if name == "set_window_parameters":
        out = {"quantity": _strict_string(raw, "quantity", choices=QUANTITY_KEYS, required=True)}
        for key in ("length_s", "step_s"):
            value = _strict_number(raw, key, 0.000001, 3600)
            if value is not None:
                out[key] = value
        if not any(key in out for key in ("length_s", "step_s")):
            raise ValueError("至少提供 length_s 或 step_s")
        return out
    if name == "set_event_parameter":
        parameter = _strict_string(raw, "parameter", choices=EVENT_PARAMETER_KEYS, required=True)
        if parameter == "osc_min_points":
            value = _strict_number(raw, "value", 4, 100_000, integer=True, required=True)
        else:
            value = _strict_number(raw, "value", 0, 100_000_000, required=True)
        return {"parameter": parameter, "value": value}
    if name == "set_event_detection_enabled":
        return {"enabled": _strict_bool(raw, "enabled", required=True)}
    if name == "set_nilm_parameter":
        algorithm = _strict_string(raw, "algorithm", choices=NILM_ALGO_DEFAULTS, required=True)
        parameter = _strict_string(raw, "parameter", choices=NILM_PARAMETER_KEYS, required=True)
        if parameter not in NILM_ALGO_DEFAULTS[algorithm] or parameter == "enabled":
            raise ValueError("parameter 不属于所选算法的数值参数白名单")
        return {"algorithm": algorithm, "parameter": parameter,
                "value": _strict_number(raw, "value", 0, 100_000, required=True)}
    if name == "set_nilm_algorithm_enabled":
        return {"algorithm": _strict_string(raw, "algorithm", choices=NILM_ALGO_DEFAULTS, required=True),
                "enabled": _strict_bool(raw, "enabled", required=True)}
    if name == "set_nilm_core_parameters":
        out: Dict[str, Any] = {}
        enabled = _strict_bool(raw, "enabled")
        auto_params = _strict_bool(raw, "auto_params")
        quantity = _strict_string(raw, "quantity", choices=NILM_QUANTITIES)
        channel = _strict_string(raw, "channel", choices=NILM_CHANNELS)
        if enabled is not None: out["enabled"] = enabled
        if auto_params is not None: out["auto_params"] = auto_params
        if quantity is not None: out["quantity"] = quantity
        if channel is not None: out["channel"] = channel
        for key, low, high in (("window_cycles", 30, 100_000), ("min_gap_cycles", 0, 100_000)):
            value = _strict_number(raw, key, low, high, integer=True)
            if value is not None: out[key] = value
        for key, low, high in (("rel_tol_pct", 0, 50), ("min_delta_pct", 0, 100)):
            value = _strict_number(raw, key, low, high)
            if value is not None: out[key] = value
        if not out:
            raise ValueError("至少提供一个负荷辨识基础参数")
        return out
    if name == "set_curve_save_enabled":
        return {"quantity": _strict_string(raw, "quantity", choices=CURVE_KEYS, required=True),
                "enabled": _strict_bool(raw, "enabled", required=True)}
    return {}
