"""Finite intent contracts for the assistant's closed business-tool catalog.

The model may suggest a registered tool, but this module is the server-side gate:
intent words, examples, parameter grounding, and the existing strict schema must all
agree before a proposal can be created. Unknown or ambiguous language is clarified.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.assistant_tools import TOOL_BY_NAME, TOOL_NAMES, validate_tool_arguments


# 意图契约配置从外部 CSV 文件加载（configs/intent_actions.csv）。
# 用户可通过修改 CSV 文件中的 actions 列扩展动词同义词，无需改动 Python 代码。
# 模块导入时自动加载；CSV 解析或校验失败会抛出明确错误，避免服务器以不完整配置启动。

_INTENT_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "configs", "intent_actions.csv")


def _split_csv_list(value: Optional[str]) -> Tuple[str, ...]:
    """把 CSV 单元格中分号分隔的列表还原为元组，忽略空项。"""
    if not value:
        return ()
    return tuple(item.strip() for item in str(value).split(";") if item.strip())


def _split_required_any(value: Optional[str]) -> Tuple[Tuple[str, ...], ...]:
    """把 CSV 单元格中 required_any 还原为元组的元组。

    格式：组内用逗号分隔字段，组间用分号分隔。例如 "d2_max,min_confidence;fs,f_nom"。
    空字符串表示无必需分组。
    """
    if not value:
        return ()
    groups = []
    for group in str(value).split(";"):
        group = group.strip()
        if group:
            groups.append(tuple(item.strip() for item in group.split(",") if item.strip()))
    return tuple(groups)


def load_intent_data_from_csv(csv_path: str = _INTENT_CSV_PATH) -> Dict[str, Dict[str, Any]]:
    """从 CSV 文件加载意图契约数据，返回与原 _INTENT_DATA 相同结构的字典。

    CSV 列：tool, intent, mode, actions, targets, positive, negative, policy, required_any
    - actions / targets / positive / negative：分号分隔的列表
    - required_any：组内逗号分隔，组间分号分隔；空表示无
    """
    data: Dict[str, Dict[str, Any]] = {}
    # utf-8-sig 可自动去除 UTF-8 BOM（Excel 中文版打开 CSV 需 BOM 才能正确识别中文）
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required_cols = {"tool", "intent", "mode", "actions", "targets", "positive", "negative", "policy"}
        missing = required_cols - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"意图配置 CSV 缺少必要列：{sorted(missing)}")
        for row in reader:
            tool = str(row["tool"]).strip()
            if not tool:
                continue
            data[tool] = {
                "intent": str(row["intent"]).strip(),
                "mode": str(row["mode"]).strip(),
                "actions": _split_csv_list(row.get("actions", "")),
                "targets": _split_csv_list(row.get("targets", "")),
                "positive": _split_csv_list(row.get("positive", "")),
                "negative": _split_csv_list(row.get("negative", "")),
                "policy": str(row.get("policy", "")).strip(),
                "required_any": _split_required_any(row.get("required_any", "")),
            }
    return data


# 在模块导入时从 CSV 加载意图数据；若 CSV 缺失或损坏，抛出错误阻止服务器以不完整配置启动。
_INTENT_DATA: Dict[str, Dict[str, Any]] = load_intent_data_from_csv()


_FIELD_GUIDANCE: Dict[str, str] = {
    "quantity": "从用户明确提到的固定电气量映射；没有明确对象时询问，不猜默认量。",
    "hours": "仅在用户明确给出小时数 / 时间范围时提供；否则省略服务端默认。",
    "max_points": "只采用用户明确给出的点数上限；否则省略默认值。",
    "active": "只有明确说活动 / 当前未结束或历史 / 已结束时设置布尔筛选。",
    "event_type": "仅映射用户明确提及的固定事件类型；未指定就省略。",
    "algorithm": "只能选用户明确提及的已注册算法；不从事件内容猜算法。",
    "channel": "按用户明确给出的单通道 / 相别映射固定枚举；多通道或不明确时澄清。",
    "limit": "只采用用户明确要求的条数；否则省略服务默认。",
    "curves": "只有用户明确要求加载曲线时才设置；未提及则省略。",
    "events": "只有用户明确要求加载电能质量事件时才设置；未提及则省略。",
    "nilm": "只有用户明确要求加载负荷辨识事件时才设置；未提及则省略。",
    "file_id": "必须来自本轮受控录波目录且由用户名称、ID或明确序号唯一指向；禁止构造路径或ID。",
    "bus_file_id": "必须来自本轮总线侧受控录波目录，并由用户明确指向。",
    "branch_file_id": "必须来自本轮分路侧受控录波目录，并由用户明确指向。",
    "profile_id": "必须来自本轮当前侧受控画像目录，且由用户明确指向；禁止猜ID。",
    "folder": "用户必须明确选择 data 或 output；未指定时询问，不自行选择目录。",
    "duration_s": "只有用户明确给出分析秒数时使用；否则省略默认值。",
    "max_cycles": "只有用户明确给出处理周波数时使用；否则省略默认值。",
    "fs_new": "目标采样率必须由用户明确给出并与数值一致；不得从文件元数据推断目标值。",
    "method": "仅映射用户指定的 linear / nearest / fft；未指定时省略默认。",
    "event": "必须明确对应启动台阶 start 或停止台阶 stop；不能猜测事件方向。",
    "bus_t_begin": "必须是用户明确提供的总线侧起始时间字符串。",
    "bus_t_end": "必须是用户明确提供的总线侧结束时间字符串。",
    "branch_t_begin": "必须是用户明确提供的分路侧起始时间字符串。",
    "branch_t_end": "必须是用户明确提供的分路侧结束时间字符串。",
    "phase": "只能使用用户明确指定的 A / B / C 相。",
    "known_side": "只在用户明确说明已知 CT 值属于总线侧或分路侧时设置。",
    "known_ct": "只有用户提供已知 CT 值时设置；不能据配置或常识补值。",
    "win_cycles": "只采用用户明确指定的窗口周波数；否则省略默认。",
    "device_id": "设备标识必须由用户明确给出并符合受控字符规则；不能自动生成。",
    "labels": "仅使用用户提供的设备标签；没有标签时省略。",
    "pre_cycles": "仅采用用户明确指定的前置周波数；否则省略默认。",
    "post_cycles": "仅采用用户明确指定的后置周波数；否则省略默认。",
    "phases": "只映射用户明确要求的相别组合；未指定时省略默认。",
    "scales": "每个档位比例都必须来自用户文本；禁止补齐或猜测比例。",
    "q_mode": "仅按用户明确指定的 scale / const 口径设置；未提及省略默认。",
    "dataset": "必须明确选择电气量结果、曲线或负荷辨识事件中的一种；“导出数据”不够明确。",
    "d2_max": "仅接受用户明确指定的马氏距离阈值数值。",
    "min_confidence": "仅接受用户明确指定的最小置信度数值。",
    "enabled": "布尔值必须与用户明确的启用 / 停用、打开 / 关闭意图一致。",
    "wiring": "只映射 3p3w / 3p4w 或明确的三相三线 / 三相四线表达。",
    "fs": "采样率必须在用户文本中有对应字段语义和明确数值。",
    "f_nom": "额定频率必须在用户文本中有对应字段语义和明确数值。",
    "f_min": "频率下限必须在用户文本中有对应字段语义和明确数值。",
    "f_max": "频率上限必须在用户文本中有对应字段语义和明确数值。",
    "pt_ratio": "PT变比必须由用户明确给出数值。",
    "ct_ratio": "CT变比必须由用户明确给出数值。",
    "voltage_input": "只能按用户明确的相电压 / 线电压口径映射。",
    "invert_current": "只有用户明确要求全局电流反向 / 恢复正常极性时设置。",
    "invert_phases": "只接受用户明确指定的反向相别；不猜测相序。",
    "reconstruct_3w": "只有用户明确要求启用 / 关闭三线重构时设置。",
    "order_min": "谐波起始次数必须由用户明确给出整数。",
    "order_max": "谐波结束次数必须由用户明确给出整数。",
    "thd_order_max": "THD最高次数必须由用户明确给出整数。",
    "include_interharmonic": "间谐波开关必须与用户明确的包含 / 不包含表达一致。",
    "apparent": "只映射用户明确选择的 arithmetic / vector 视在功率口径。",
    "reactive": "只映射用户明确选择的 harmonic_sum / quadrature 无功口径。",
    "fundamental_power": "只按用户明确要求启用 / 关闭基波功率输出。",
    "offset_s": "对齐偏移秒数必须由用户明确给出数值及其偏移语义。",
    "tolerance_s": "对齐容差秒数必须由用户明确给出数值及其容差语义。",
    "speed": "倍速必须由用户明确给出数值；“快一点”不等于指定了具体 speed。",
    "use_utc": "只有明确说UTC或本机 / 本地时间时设置对应布尔值。",
    "length_s": "窗长必须由用户明确给出秒数。",
    "step_s": "步长必须由用户明确给出秒数。",
    "parameter": "必须是用户明确提及且属于固定白名单的参数键；不能根据近似描述猜键。",
    "value": "参数新值必须由用户明确给出；并且要与所指参数字段对应。",
    "auto_params": "仅按用户明确要求自动 / 手动参数模式设置。",
    "min_delta_pct": "最小变化比例必须由用户明确给出百分比数值。",
    "min_gap_cycles": "最小间隔周波数必须由用户明确给出整数。",
    "rel_tol_pct": "相对容差百分比必须由用户明确给出数值。",
    "window_cycles": "窗口周波数必须由用户明确给出整数。",
}

_FIELD_TERMS: Dict[str, Tuple[str, ...]] = {
    "hours": ("小时", "时长", "hour"), "max_points": ("点数", "个点", "点"),
    "limit": ("条数", "条", "limit"), "duration_s": ("秒", "duration"),
    "max_cycles": ("周波", "周期", "cycles"), "fs_new": ("重采样到", "目标采样率", "新采样率"),
    "win_cycles": ("窗口周波", "win_cycles", "周波窗口"),
    "device_id": ("设备id", "设备编号", "device_id"),
    "known_ct": ("已知ct", "ct值", "变比已知"),
    "d2_max": ("d2_max", "马氏距离", "距离阈值"),
    "min_confidence": ("min_confidence", "最小置信度", "匹配置信度"),
    "fs": ("采样率", "采样频率", "fs"),
    "f_nom": ("额定频率", "f_nom"), "f_min": ("频率下限", "f_min"),
    "f_max": ("频率上限", "f_max"), "pt_ratio": ("pt变比", "pt_ratio"),
    "ct_ratio": ("ct变比", "ct_ratio"), "order_min": ("谐波起始次数", "order_min"),
    "order_max": ("谐波最高次数", "谐波结束次数", "order_max"),
    "thd_order_max": ("thd最高次数", "thd_order_max"),
    "offset_s": ("偏移", "offset_s", "时间偏移"), "tolerance_s": ("容差", "tolerance_s"),
    "speed": ("速度", "倍速", "speed"), "length_s": ("窗长", "窗口长度", "length_s"),
    "step_s": ("步长", "输出间隔", "step_s"),
    "min_delta_pct": ("最小变化比例", "min_delta_pct"),
    "min_gap_cycles": ("最小间隔周波", "min_gap_cycles"),
    "rel_tol_pct": ("相对容差", "rel_tol_pct"),
    "window_cycles": ("窗口周波", "window_cycles"),
}

_VALUE_ALIASES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "quantity": {
        "voltage": ("电压", "电压曲线", "电压量", "u量"),
        "current": ("电流", "电流曲线", "电流量", "i量"),
        "power": ("功率", "有功功率", "无功功率", "视在功率"),
        "power_factor": ("功率因数", "功率因数曲线", "pf"),
        "fundamental": ("基波", "基波量"), "harmonic": ("谐波", "谐波量"),
        "interharmonic": ("间谐波", "间谐波量"), "dc": ("直流", "直流偏置", "直流分量"),
        "spectrum": ("频谱", "频谱量"),
        "auto": ("自动", "自动检测量"), "p": ("有功口径", "按有功", "功率量"),
        "i": ("电流口径", "按电流", "电流变化量"),
    },
    "folder": {"data": ("data目录", "数据目录"), "output": ("output目录", "输出目录")},
    "event_type": {
        "fund_phasor": ("基波相量",), "harm_phasor": ("谐波相量",),
        "interharm": ("间谐波事件",), "freq": ("频率事件",),
        "rocof": ("rocof", "频率变化率"), "power_osc": ("功率振荡", "功率摆动"),
    },
    "algorithm": {
        "threshold": ("threshold", "阈值法"), "two_window": ("two_window", "双窗法", "双窗口"),
        "cusum": ("cusum", "累积和"), "glr": ("glr", "广义似然比"),
        "steady_state": ("steady_state", "稳态法"), "median_diff": ("median_diff", "中位差"),
        "profile": ("profile", "画像匹配"),
    },
    "channel": {
        "Ua": ("ua", "a相电压", "a相电压通道"), "Ub": ("ub", "b相电压", "b相电压通道"),
        "Uc": ("uc", "c相电压", "c相电压通道"), "Ia": ("ia", "a相电流", "a相电流通道"),
        "Ib": ("ib", "b相电流", "b相电流通道"), "Ic": ("ic", "c相电流", "c相电流通道"),
        "A": ("a相", "a相电流", "a相电压"), "B": ("b相", "b相电流", "b相电压"),
        "C": ("c相", "c相电流", "c相电压"), "total": ("总相", "总量", "total"),
    },
    "dataset": {
        "nilm_events": ("负荷辨识事件", "nilm事件"),
        "electrical_results": ("电气量结果", "计算结果"),
        "curves": ("趋势曲线", "保存曲线", "曲线数据"),
    },
    "wiring": {"3p3w": ("3p3w", "三相三线", "三线制"), "3p4w": ("3p4w", "三相四线", "四线制")},
    "method": {"linear": ("linear", "线性"), "nearest": ("nearest", "最近邻"), "fft": ("fft", "快速傅里叶")},
    "event": {"start": ("启动台阶", "投入台阶", "启动事件"), "stop": ("停止台阶", "切除台阶", "停机事件")},
    "phase": {"A": ("a相", "a相电流"), "B": ("b相", "b相电流"), "C": ("c相", "c相电流")},
    "known_side": {"bus": ("总线侧", "母线侧"), "branch": ("分路侧", "支路侧")},
    "apparent": {"arithmetic": ("算术", "算术法"), "vector": ("向量", "向量法")},
    "reactive": {"harmonic_sum": ("谐波总和", "谐波求和"), "quadrature": ("正交", "正交法")},
    "q_mode": {"scale": ("按比例缩放", "比例缩放", "scale"), "const": ("常数", "固定值", "const")},
    "voltage_input": {"phase": ("相电压", "相电压口径"), "line": ("线电压", "线电压口径")},
    "invert_phases": {
        "A": ("a相反向", "反向a相", "a相取反"), "B": ("b相反向", "反向b相", "b相取反"),
        "C": ("c相反向", "反向c相", "c相取反"), "AB": ("a和b相反向", "ab相反向"),
        "AC": ("a和c相反向", "ac相反向"), "BC": ("b和c相反向", "bc相反向"),
        "ABC": ("三相反向", "全部相反向", "abc相反向"),
    },
    "phases": {
        "auto": ("自动相别", "自动识别相别"), "A": ("a相",), "B": ("b相",), "C": ("c相",),
        "AB": ("ab相", "a和b相"), "AC": ("ac相", "a和c相"), "BC": ("bc相", "b和c相"),
    },
}

_BOOL_ALIASES: Dict[str, Dict[bool, Tuple[str, ...]]] = {
    "enabled": {True: ("启用", "开启", "打开", "激活", "true"), False: ("停用", "禁用", "关闭", "不启用", "false")},
    "active": {True: ("活动事件", "当前活动", "未结束事件"), False: ("历史事件", "已结束事件", "历史")},
    "curves": {True: ("曲线", "趋势曲线"), False: ("不加载曲线", "不要曲线")},
    "events": {True: ("电能质量事件", "事件列表"), False: ("不加载事件", "不要事件")},
    "nilm": {True: ("负荷辨识事件", "nilm事件"), False: ("不加载负荷事件", "不要负荷事件")},
    "include_interharmonic": {True: ("包含间谐波", "开启间谐波"), False: ("不包含间谐波", "关闭间谐波")},
    "fundamental_power": {True: ("基波功率输出", "开启基波功率"), False: ("关闭基波功率", "不输出基波功率")},
    "invert_current": {True: ("电流反向", "电流反相"), False: ("取消电流反向", "电流保持正常极性")},
    "reconstruct_3w": {True: ("启用三线重构", "开启三线重构"), False: ("关闭三线重构", "不进行三线重构")},
    "auto_params": {True: ("自动参数", "自动调整", "开启自动参数"),
                    False: ("手动参数", "关闭自动参数", "关闭nilm自动参数", "停用nilm自动参数")},
    "use_utc": {True: ("utc", "协调世界时", "世界时"), False: ("本机本地时间", "本地时间", "local time")},
}


@dataclass(frozen=True)
class ToolIntentContract:
    tool: str
    intent: str
    mode: str
    action_terms: Tuple[str, ...]
    target_terms: Tuple[str, ...]
    positive_examples: Tuple[str, ...]
    negative_examples: Tuple[str, ...]
    parameter_policy: str
    parameter_rules: Mapping[str, Mapping[str, Any]]
    required_any: Tuple[Tuple[str, ...], ...] = ()


def _schema_parameter_rules(tool: str, extra: Mapping[str, str]) -> Dict[str, Mapping[str, Any]]:
    schema = TOOL_BY_NAME[tool]["parameters"]
    required = set(schema.get("required", []))
    mode = _INTENT_DATA[tool]["mode"]
    rules: Dict[str, Mapping[str, Any]] = {}
    for field, prop in schema.get("properties", {}).items():
        rules[field] = {
            "required": field in required,
            "must_be_explicit": field in required or mode == "action",
            "constraint": dict(prop),
            "guidance": extra.get(field) or _FIELD_GUIDANCE.get(
                field, "只采用用户明确表达或受控资源上下文中的值；必需值缺失时先澄清，不得猜测。"
            ),
        }
    return rules


def _build_contract(tool: str, data: Mapping[str, Any]) -> ToolIntentContract:
    extra = data.get("parameter_guidance", {})
    return ToolIntentContract(
        tool=tool,
        intent=str(data["intent"]),
        mode=str(data["mode"]),
        action_terms=tuple(data["actions"]),
        target_terms=tuple(data["targets"]),
        positive_examples=tuple(data["positive"]),
        negative_examples=tuple(data["negative"]),
        parameter_policy=str(data["policy"]),
        parameter_rules=_schema_parameter_rules(tool, extra),
        required_any=tuple(tuple(group) for group in data.get("required_any", ())),
    )


TOOL_INTENT_CONTRACTS: Dict[str, ToolIntentContract] = {
    name: _build_contract(name, data) for name, data in _INTENT_DATA.items()
}


class _Clarification(Exception):
    """Internal non-error outcome: do not create a proposal; ask for clarification."""


def normalize_intent_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or "")).casefold()
    value = re.sub(r"\s+", "", value)
    # Keep decimal points between digits while stripping sentence punctuation.
    value = re.sub(r"(?<![0-9])\.(?![0-9])", "", value)
    return re.sub(r"[，,。!！?？；;：:\"'“”‘’（）()\[\]{}<>《》、]+", "", value)


_INFO_HOW_RE = re.compile(r"^(?:请问)?(?:如何|怎么|为什么|有什么办法|请解释|解释一下|说明一下|介绍一下)")
_ACTION_QUESTION_RE = re.compile(r"^(?:请问)?(?:是否|能否|能不能|可不可以|会不会)")
_NEGATION_PREFIX_RE = re.compile(r"(?:不要再|不要|别|禁止|不需要|无需|不执行|不允许|不要操作)(.{0,16})")
_NEGATED_ACTION_TERMS = ("执行", "操作", "调用", "做", "运行")
_PAST_REPORT_RE = re.compile(r"^(?:(?:我|系统)?(?:已经|已|刚刚|刚才|之前|上次).{0,12}(?:启动|播放|暂停|恢复|停止|修改|设置|加载|导出|清空|运行))")
_CONTRAST_RE = re.compile(r"(?:不是|并非).{1,24}?(?:而是|而要|应该是)")
_COMPOUND_ACTION_RE = re.compile(r"(?:然后|接着|随后|之后|并且|并同时|同时|而且|另外|并|再)")


def _effective_text(prompt: str) -> str:
    text = normalize_intent_text(prompt)
    # In an explicit contrast such as “不是调速，而是启动数据源”, classify only
    # the affirmative clause; never mistake the negated side for the requested action.
    match = _CONTRAST_RE.search(text)
    if match:
        text = text[match.end():]
    return text


def _is_non_action_request(prompt: str, contract: ToolIntentContract) -> bool:
    text = normalize_intent_text(prompt)
    if _PAST_REPORT_RE.search(text):
        return True
    if _INFO_HOW_RE.search(text):
        return True
    if contract.mode != "read" and _ACTION_QUESTION_RE.search(text):
        return True
    # Reject a negation only when it targets this contract's action. This lets a
    # positive request such as “start the source; do not query or switch files” pass,
    # while “do not start” cannot be turned into a start proposal.
    for match in _NEGATION_PREFIX_RE.finditer(text):
        following = match.group(1)
        if any(normalize_intent_text(term) in following for term in _NEGATED_ACTION_TERMS):
            return True
        if any(normalize_intent_text(term) in following
               for term in contract.action_terms if len(normalize_intent_text(term)) > 1):
            return True
    # “解释/分析/复述这句话” around a quoted command is a meta-question, not a request
    # to execute the command itself.
    if re.search(r"(?:解释|说明|分析|复述|翻译).{0,16}(?:这句话|这条指令|这段话)", text):
        return True
    return False


def tool_intent_score(prompt: str, tool: str) -> int:
    """Return a conservative lexical score; zero means the prompt is not a match."""
    contract = TOOL_INTENT_CONTRACTS.get(tool)
    item = TOOL_BY_NAME.get(tool)
    if contract is None or item is None:
        return 0
    text = _effective_text(prompt)
    if not text or _is_non_action_request(prompt, contract):
        return 0
    for example in contract.negative_examples:
        if normalize_intent_text(example) in normalize_intent_text(prompt):
            return 0
    # 互斥动词：同一输入中出现停止/终止/结束运行，启动类工具不得分；
    # 出现启动/开始/播放/运行，停止类工具不得分，避免“播放”类词汇把
    # 停止指令误判为启动（如“停止播放离线数据源”）。
    stop_verbs = ("停止", "终止", "结束运行")
    # “播放”不列入启动专属动词：它可出现在“停止播放”这类停止指令中，
    # 不应导致停止工具误判为 0。
    start_only_verbs = ("启动", "开始", "开始播放", "运行", "跑起来")
    has_stop = any(v in text for v in stop_verbs)
    has_start_only = any(v in text for v in start_only_verbs)
    if tool == "start_current_source" and has_stop:
        return 0
    if tool == "stop_current_source" and has_start_only:
        return 0
    # Exact catalog-title commands remain deterministic even when politely prefixed.
    title_text = text
    for prefix in ("请帮我", "麻烦帮我", "帮我", "请", "麻烦"):
        normalized_prefix = normalize_intent_text(prefix)
        if title_text.startswith(normalized_prefix):
            title_text = title_text[len(normalized_prefix):]
            break
    title = normalize_intent_text(str(item.get("title") or ""))
    if title and title == title_text:
        return 100
    for example in contract.positive_examples:
        normalized = normalize_intent_text(example)
        if normalized and normalized in text:
            return 90
    action_hits = [term for term in contract.action_terms if normalize_intent_text(term) in text]
    target_hits = [term for term in contract.target_terms if normalize_intent_text(term) in text]
    if not action_hits or not target_hits:
        return 0
    # Longer, more specific target phrases win over generic tokens; ties remain
    # ambiguous and are sent to clarification instead of selecting a nearby tool.
    return 40 + min(12, max(map(len, action_hits))) + min(24, max(map(len, target_hits)))


def find_tool_intent_candidates(prompt: str, top_k: Optional[int] = None) -> List[Tuple[str, int]]:
    """Return lexical-scored tool candidates, optionally limited to top-k.

    §6.2 候选意图召回：本阶段采用词法匹配，未来可扩展为向量召回。
    top-k 取 8，压缩模型判定的选择范围，降低 token 消耗并提高稳定性。
    """
    matches = [(name, score) for name in TOOL_NAMES if (score := tool_intent_score(prompt, name)) > 0]
    matches.sort(key=lambda pair: (-pair[1], pair[0]))
    if top_k is not None:
        matches = matches[: max(1, int(top_k))]
    return matches


def _number_mentioned(value: float | int, text: str, field: str = "") -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return False
    numeric = float(value)
    normalized = normalize_intent_text(text)
    forms = {str(value), f"{numeric:g}"}
    if numeric.is_integer():
        forms.add(str(int(numeric)))
    # Match numeric tokens, not arbitrary substrings (value 2 must not be grounded
    # by “二窗” or by the digit in 12800).
    for form in sorted(forms, key=len, reverse=True):
        escaped = re.escape(normalize_intent_text(form))
        if escaped and re.search(rf"(?<![0-9.]){escaped}(?![0-9.])", normalized):
            return True
    if field == "hours":
        if numeric == 24 and any(term in normalized for term in ("一天", "一日", "整天", "過去一天")):
            return True
        if numeric == 0.5 and any(term in normalized for term in ("半小时", "半個小时", "半个小时")):
            return True
    chinese = {0: "零〇", 1: "一", 2: "二两", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}
    if numeric.is_integer() and int(numeric) in chinese:
        numeral = chinese[int(numeric)]
        units = r"(?:倍|秒|分钟|小时|个小时|天|日|点|周波|周期|个点|点|次|档|级|相|%|百分比|个)"
        if re.search(rf"[{re.escape(numeral)}]{units}", normalized):
            return True
        if re.search(rf"(?:设为|改为|调整到|调到|调至|设成|设置为|增加到|降低到|阈值为|新值为)[{re.escape(numeral)}](?=$|{units})", normalized):
            return True
        if int(numeric) in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10} and f"百分之{numeral[0]}" in normalized:
            return True
    return False


_FIELD_NUMBER_UNITS: Dict[str, str] = {
    "hours": r"(?:小时|hour|天)", "max_points": r"(?:个点|点|points?)",
    "limit": r"(?:条|条数|个事件)", "duration_s": r"(?:秒|seconds?|secs?)",
    "max_cycles": r"(?:周波|周期|cycles?)", "win_cycles": r"(?:周波|周期|cycles?)",
    "window_cycles": r"(?:周波|周期|cycles?)", "min_gap_cycles": r"(?:周波|周期|cycles?)",
    "pre_cycles": r"(?:周波|周期|cycles?)", "post_cycles": r"(?:周波|周期|cycles?)",
    "fs": r"(?:hz|赫兹)", "fs_new": r"(?:hz|赫兹)",
    "f_nom": r"(?:hz|赫兹)", "f_min": r"(?:hz|赫兹)", "f_max": r"(?:hz|赫兹)",
    "speed": r"(?:倍|x)", "length_s": r"(?:秒|seconds?|secs?)", "step_s": r"(?:秒|seconds?|secs?)",
    "offset_s": r"(?:秒|seconds?|secs?)", "tolerance_s": r"(?:秒|seconds?|secs?)",
    "min_delta_pct": r"(?:%|百分比)", "rel_tol_pct": r"(?:%|百分比)",
}
_ASSIGNMENT_RE = re.compile(r"(?:设为|设置为|设成|改为|改成|改到|调到|调至|调整到|调整为|切换到|变为|增加到|降低到|设定为)")


def _number_occurrences(value: float | int, text: str) -> List[Tuple[int, int]]:
    normalized = normalize_intent_text(text)
    forms = {str(value), f"{float(value):g}"}
    if float(value).is_integer():
        forms.add(str(int(float(value))))
    spans: List[Tuple[int, int]] = []
    for form in forms:
        form = normalize_intent_text(form)
        if not form:
            continue
        for match in re.finditer(rf"(?<![0-9.]){re.escape(form)}(?![0-9.])", normalized):
            spans.append(match.span())
    return sorted(set(spans))


def _number_grounded_for_field(field: str, value: float | int, prompt: str,
                               args: Mapping[str, Any]) -> bool:
    if not _number_mentioned(value, prompt, field):
        return False
    text = normalize_intent_text(prompt)
    occurrences = _number_occurrences(value, prompt)
    all_numbers = list(re.finditer(r"(?<![0-9.])[0-9]+(?:\.[0-9]+)?(?![0-9.])", text))
    transitions = list(re.finditer(
        r"(?:从|由)([0-9]+(?:\.[0-9]+)?)(?:[^0-9]{0,12})(?:到|为|成)([0-9]+(?:\.[0-9]+)?)", text
    ))
    source_spans = {match.span(1) for match in transitions}
    if len(all_numbers) <= 1 and not (occurrences and any(span in source_spans for span in occurrences)):
        return True
    unit_pattern = _FIELD_NUMBER_UNITS.get(field)
    terms = list(_FIELD_TERMS.get(field, ()))
    if field == "value":
        parameter = str(args.get("parameter") or "")
        terms.extend(_EVENT_PARAMETER_ALIASES.get(parameter, ()))
        terms.extend(_NILM_PARAMETER_ALIASES.get(parameter, ()))
        if parameter:
            terms.append(parameter)
    for start, end in occurrences:
        if (start, end) in source_spans:
            continue
        suffix = text[end:end + 24]
        prefix = text[max(0, start - 24):start]
        if unit_pattern and re.match(unit_pattern, suffix):
            return True
        for term in terms:
            normalized_term = normalize_intent_text(term)
            if not normalized_term:
                continue
            term_at = prefix.rfind(normalized_term)
            if term_at >= 0:
                between = prefix[term_at + len(normalized_term):]
                # In “field from old to new”, the number immediately after 从/由 is
                # context, not the requested target value.
                if not re.search(r"(?:从|由)", between) and re.fullmatch(
                        r"(?:的|为|设为|设置为|设成|改为|改成|改到|调到|调至|调整到|调整为|切换到|变为|增加到|降低到|设定为)?",
                        between):
                    return True
        for assignment in _ASSIGNMENT_RE.finditer(text):
            if assignment.end() <= start and start - assignment.end() <= 16:
                before = text[max(0, assignment.start() - 40):assignment.start()]
                if not terms or any(normalize_intent_text(term) in before for term in terms if term):
                    return True
    # “from X to Y” binds Y as the requested value; the source value X is not a target.
    for match in re.finditer(r"(?:从|由)([0-9]+(?:\.[0-9]+)?)(?:[^0-9]{0,12})(?:到|为|成)([0-9]+(?:\.[0-9]+)?)", text):
        target = float(match.group(2))
        if target == float(value):
            before = text[max(0, match.start() - 40):match.start()]
            if not terms or any(normalize_intent_text(term) in before for term in terms if term):
                return True
    return False


def _field_context_present(field: str, text: str, args: Mapping[str, Any], tool: str = "") -> bool:
    normalized = normalize_intent_text(text)
    terms = list(_FIELD_TERMS.get(field, ()))
    if field == "value":
        parameter = str(args.get("parameter") or "")
        terms.extend(_VALUE_ALIASES.get("parameter", {}).get(parameter, ()))
        terms.extend(_EVENT_PARAMETER_ALIASES.get(parameter, ()))
        terms.extend(_NILM_PARAMETER_ALIASES.get(parameter, ()))
    if terms:
        return any(normalize_intent_text(term) in normalized for term in terms)
    if tool:
        return bool(_mentioned_enum_values(tool, field, text))
    return any(normalize_intent_text(term) in normalized
               for aliases in _VALUE_ALIASES.get(field, {}).values() for term in aliases) or any(
        normalize_intent_text(term) in normalized
        for values in _BOOL_ALIASES.get(field, {}).values() for term in values
    )


_EVENT_PARAMETER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "hysteresis": ("滞回", "回差"), "u_nom": ("额定电压",),
    "u1_high_pct": ("电压暂升", "暂升阈值"), "u1_low_pct": ("电压暂降", "暂降阈值"),
    "i1_high": ("电流过流", "过流阈值"), "hr_u_limit_pct": ("电压谐波限值",),
    "hr_i_limit_pct": ("电流谐波限值",), "thd_u_limit_pct": ("电压thd", "电压总谐波畸变"),
    "thd_i_limit_pct": ("电流thd", "电流总谐波畸变"), "ih_u_limit_pct": ("电压间谐波限值",),
    "ih_i_limit_pct": ("电流间谐波限值",), "f_low": ("频率下限",), "f_high": ("频率上限",),
    "rocof_limit": ("频率变化率限值", "rocof限值"), "osc_window_s": ("振荡窗口",),
    "osc_f_min": ("振荡最低频率",), "osc_f_max": ("振荡最高频率",),
    "osc_limit_pct": ("功率振荡限值",), "osc_min_w": ("最小功率振荡",),
    "osc_min_points": ("最少振荡点数",),
}

_NILM_PARAMETER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "d2_max": ("马氏距离阈值", "d2_max"), "drift_a": ("a相漂移", "drift_a"),
    "drift_w": ("功率漂移", "drift_w"), "k_sigma": ("噪声sigma倍数", "k_sigma"),
    "lambda_rel": ("相对lambda", "lambda_rel"), "margin": ("裕度", "margin"),
    "max_rise_cycles": ("最大上升周波", "max_rise_cycles"), "max_scale": ("最大比例", "max_scale"),
    "max_transient_cycles": ("最大暂态周波", "max_transient_cycles"), "median_cycles": ("中位数周波", "median_cycles"),
    "min_confidence": ("最小置信度", "min_confidence"), "min_delta_a": ("a相最小变化", "min_delta_a"),
    "min_delta_w": ("功率最小变化", "min_delta_w"), "min_scale": ("最小比例", "min_scale"),
    "min_stage": ("最小档位数", "min_stage"), "min_steady_cycles": ("最小稳态周波", "min_steady_cycles"),
    "noise_a": ("a相噪声", "noise_a"), "noise_w": ("功率噪声", "noise_w"),
    "phase_map": ("相别映射", "phase_map"), "post_cycles": ("后置周波", "post_cycles"),
    "pre_cycles": ("前置周波", "pre_cycles"), "settle_cycles": ("稳定周波", "settle_cycles"),
    "settle_tol_a": ("a相稳定容差", "settle_tol_a"), "settle_tol_w": ("功率稳定容差", "settle_tol_w"),
    "stage_dim_max": ("最大档位维度", "stage_dim_max"), "stage_free": ("自由档位", "stage_free"),
    "stage_max_scale": ("档位最大比例", "stage_max_scale"), "stage_min_scale": ("档位最小比例", "stage_min_scale"),
    "state_check": ("状态检查", "state_check"), "threshold": ("阈值", "threshold"),
    "threshold_a": ("a相阈值", "threshold_a"), "threshold_w": ("功率阈值", "threshold_w"),
    "tol_a": ("a相容差", "tol_a"), "tol_w": ("功率容差", "tol_w"),
    "window_cycles": ("窗口周波", "window_cycles"),
}


def _phrase_spans(phrase: str, text: str) -> List[Tuple[int, int]]:
    normalized = normalize_intent_text(phrase)
    if not normalized:
        return []
    if re.fullmatch(r"[a-z0-9_]+", normalized):
        pattern = re.compile(rf"(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])")
        return [match.span() for match in pattern.finditer(text)]
    return [match.span() for match in re.finditer(re.escape(normalized), text)]


def _mentioned_enum_values(tool: str, field: str, prompt: str) -> Dict[Any, List[Tuple[int, int]]]:
    schema = TOOL_BY_NAME[tool]["parameters"]
    prop = schema.get("properties", {}).get(field, {})
    choices = prop.get("enum")
    if not choices and prop.get("type") == "boolean":
        choices = [True, False]
    if not choices:
        return {}
    text = normalize_intent_text(prompt)
    found: Dict[Any, List[Tuple[int, int]]] = {}
    all_hits: List[Tuple[Any, int, int]] = []
    for value in choices:
        alternatives: Sequence[str]
        if isinstance(value, bool):
            alternatives = _BOOL_ALIASES.get(field, {}).get(value, ()) + (("true",) if value else ("false",))
        else:
            alternatives = (str(value),) + _VALUE_ALIASES.get(field, {}).get(str(value), ())
            if field == "parameter":
                alternatives += _EVENT_PARAMETER_ALIASES.get(str(value), ()) + _NILM_PARAMETER_ALIASES.get(str(value), ())
        for alternative in alternatives:
            for start, end in _phrase_spans(alternative, text):
                all_hits.append((value, start, end))
    # Prefer a longer, more specific phrase over an alias contained inside it:
    # “功率因数” identifies power_factor, not generic power; “A相阈值” is not plain threshold.
    for value, start, end in all_hits:
        contained = any(other_value != value and other_start <= start and other_end >= end
                        and other_end - other_start > end - start
                        for other_value, other_start, other_end in all_hits)
        if not contained:
            found.setdefault(value, []).append((start, end))
    return found


def _target_enum_values(tool: str, field: str, prompt: str,
                        mentioned: Optional[Mapping[Any, Sequence[Tuple[int, int]]]] = None) -> Optional[set[Any]]:
    mentioned = mentioned or _mentioned_enum_values(tool, field, prompt)
    if len(mentioned) <= 1:
        return set(mentioned)
    text = normalize_intent_text(prompt)
    markers = list(_ASSIGNMENT_RE.finditer(text))
    if markers:
        last_marker = markers[-1].end()
        target_values = {value for value, spans in mentioned.items()
                         if any(start >= last_marker for start, _end in spans)}
        if len(target_values) == 1:
            return target_values
    return None


def _field_value_ambiguity(tool: str, field: str, prompt: str) -> bool:
    mentioned = _mentioned_enum_values(tool, field, prompt)
    if len(mentioned) <= 1:
        return False
    return _target_enum_values(tool, field, prompt, mentioned) is None


def _resource_value_grounded(field: str, value: Any, prompt: str, context: Mapping[str, Any]) -> bool:
    id_field_to_collection = {
        "file_id": ("recordings", "file_id"), "bus_file_id": ("recordings", "file_id"),
        "branch_file_id": ("recordings", "file_id"), "profile_id": ("profiles", "id"),
    }
    collection_info = id_field_to_collection.get(field)
    if not collection_info:
        return False
    collection, id_key = collection_info
    rows = context.get(collection) if isinstance(context.get(collection), list) else []
    normalized = normalize_intent_text(prompt)
    wanted_id = str(value)
    bus_side = field == "bus_file_id"
    branch_side = field == "branch_file_id"
    side_terms = (("总线侧", "母线侧") if bus_side else ("分路侧", "支路侧")) if bus_side or branch_side else ()
    chinese_numbers = {1: "一", 2: "二两", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}
    matched_ids: set[str] = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        row_id = str(row.get(id_key) or "")
        if not row_id:
            continue
        spans: List[Tuple[int, int]] = []
        id_text = normalize_intent_text(row_id)
        if id_text:
            spans.extend(_phrase_spans(id_text, normalized))
        labels = (row.get("name"), row.get("label"), row.get("file_name"))
        for label in labels:
            safe_label = normalize_intent_text(str(label or ""))
            if safe_label and safe_label not in {"已脱敏录波文件", "已脱敏设备画像", "受控录波文件", "已脱敏画像"}:
                spans.extend(_phrase_spans(safe_label, normalized))
        ordinal_forms = [f"第{index}个", f"第{index}份", f"第{index}条", f"录波文件{index}", f"设备画像{index}"]
        if index in chinese_numbers:
            numeral = chinese_numbers[index]
            ordinal_forms.extend((f"第{numeral}个", f"第{numeral}份", f"第{numeral}条"))
        for ordinal in ordinal_forms:
            spans.extend(_phrase_spans(ordinal, normalized))
        if not spans:
            continue
        if side_terms:
            # A paired CT estimate must bind each selected recording to its named side;
            # mentioning two files without roles is not enough to assign them safely.
            has_side = False
            for start, end in spans:
                surrounding = normalized[max(0, start - 24):min(len(normalized), end + 24)]
                if any(normalize_intent_text(term) in surrounding for term in side_terms):
                    has_side = True
                    break
            if not has_side:
                continue
        matched_ids.add(row_id)
    # A single-file / profile slot must resolve to exactly one resource mentioned by
    # the user. Paired bus/branch slots are resolved independently with explicit side tags.
    if not bus_side and not branch_side and len(matched_ids) != 1:
        return False
    return wanted_id in matched_ids


def _boolean_target_context(tool: str, field: str, prompt: str, args: Mapping[str, Any]) -> bool:
    if field != "enabled":
        return True
    text = normalize_intent_text(prompt)
    if tool == "set_profile_detection_enabled":
        return any(term in text for term in ("画像匹配", "画像检测", "设备画像识别"))
    if tool == "set_event_detection_enabled":
        return any(term in text for term in ("电能质量事件检测", "事件检测总开关", "事件识别开关"))
    if tool == "set_nilm_algorithm_enabled":
        return bool(_mentioned_enum_values(tool, "algorithm", prompt))
    if tool == "set_nilm_core_parameters":
        if any(term in text for term in (
            "负荷辨识总开关", "负荷辨识开关", "负荷辨识功能", "负荷辨识检测功能",
        )):
            return True
        match = re.search(r"(?:启用|停用|关闭|打开)(?:负荷辨识|nilm)(?:总开关|开关|检测功能|检测|功能|算法)?", text)
        if not match:
            return False
        remainder = text[match.end():].lstrip("的")
        return not remainder.startswith(("自动参数", "自动调整", "手动参数", "基础参数"))
    if tool == "set_curve_save_enabled":
        quantity = str(args.get("quantity") or "")
        quantity_aliases = _VALUE_ALIASES.get("quantity", {}).get(quantity, ())
        target = any(term in text for term in ("曲线保存", "曲线落盘", "趋势曲线保存", "保存开关"))
        return target and (quantity in text or any(normalize_intent_text(term) in text for term in quantity_aliases))
    return True


def _value_grounded(tool: str, field: str, value: Any, prompt: str,
                    context: Mapping[str, Any], args: Mapping[str, Any]) -> bool:
    text = normalize_intent_text(prompt)
    if field in {"file_id", "bus_file_id", "branch_file_id", "profile_id"}:
        return _resource_value_grounded(field, value, prompt, context)
    if isinstance(value, bool):
        if not _boolean_target_context(tool, field, prompt, args):
            return False
        mentioned = _mentioned_enum_values(tool, field, prompt)
        if mentioned:
            targets = _target_enum_values(tool, field, prompt, mentioned)
            if targets is None or value not in targets:
                return False
            return True
        aliases = _BOOL_ALIASES.get(field, {}).get(value, ())
        return (any(normalize_intent_text(term) in text for term in aliases)
                or ("true" if value else "false") in text)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not _field_context_present(field, prompt, args, tool):
            return False
        if field == "value":
            parameter = str(args.get("parameter") or "")
            aliases = _EVENT_PARAMETER_ALIASES.get(parameter, ()) + _NILM_PARAMETER_ALIASES.get(parameter, ())
            if aliases and not any(normalize_intent_text(term) in text for term in aliases):
                return False
        return _number_grounded_for_field(field, value, prompt, args)
    if isinstance(value, list):
        if field == "scales":
            return bool(value) and all(_number_mentioned(item, prompt, field) for item in value) and any(
                term in text for term in ("档位", "倍", "比例", "scale"))
        return all(_value_grounded(tool, field, item, prompt, context, args) for item in value)
    if isinstance(value, str):
        normalized_value = normalize_intent_text(value)
        if field == "invert_phases" and not value:
            return any(term in text for term in (
                "取消相别反向", "恢复所有相位", "恢复正常相序", "不反向任何相", "清除相位取反"
            ))
        aliases = _VALUE_ALIASES.get(field, {}).get(value, ())
        if field == "parameter":
            aliases = aliases + _EVENT_PARAMETER_ALIASES.get(value, ()) + _NILM_PARAMETER_ALIASES.get(value, ())
        enum_values = _mentioned_enum_values(tool, field, prompt)
        if enum_values:
            target_values = _target_enum_values(tool, field, prompt, enum_values)
            allowed_values = target_values if target_values is not None else set(enum_values)
            if value not in allowed_values:
                return False
            if len(enum_values) > 1 and target_values is None:
                return False
        if normalized_value and normalized_value in text:
            if field not in {"bus_t_begin", "bus_t_end", "branch_t_begin", "branch_t_end"}:
                return True
        if aliases and any(normalize_intent_text(alias) in text for alias in aliases):
            return True
        if field in {"bus_t_begin", "bus_t_end", "branch_t_begin", "branch_t_end"}:
            side_terms = ("总线侧", "母线侧") if field.startswith("bus_") else ("分路侧", "支路侧")
            edge_terms = ("开始", "起始", "从") if field.endswith("begin") else ("结束", "终止", "到")
            return (normalized_value in text
                    and any(normalize_intent_text(term) in text for term in side_terms)
                    and any(normalize_intent_text(term) in text for term in edge_terms))
        return False
    return False


def _required_fields(tool: str) -> set[str]:
    schema = TOOL_BY_NAME[tool]["parameters"]
    required = set(schema.get("required", []))
    for group in TOOL_INTENT_CONTRACTS[tool].required_any:
        if not required.intersection(group):
            # A required-any group is represented as at least one supported input.
            required.add("|".join(group))
    return required


def _missing_parameter_prompt(tool: str, fields: Iterable[str]) -> str:
    contract = TOOL_INTENT_CONTRACTS[tool]
    schema_fields = contract.parameter_rules
    group_questions = {
        "set_electrical_parameters": "至少明确一个基础字段及新值（采样率、频率、PT/CT变比或电气变换选项）。",
        "set_harmonic_parameters": "至少明确要改的谐波字段及值（次数范围、THD最高次数或间谐波开关）。",
        "set_power_calculation_mode": "至少明确一个功率计算口径或基波功率开关及目标值。",
        "set_compare_alignment": "至少明确跨侧偏移秒数或时间对齐容差及数值。",
        "set_window_parameters": "至少明确一个固定电气量，以及窗长或步长的数值。",
        "set_nilm_core_parameters": "至少明确一个负荷辨识基础字段及其新值。",
    }
    questions: List[str] = []
    for field in fields:
        if "|" in field:
            questions.append(group_questions.get(tool, "请明确至少一个允许的参数字段及其值。"))
        elif field in schema_fields:
            questions.append(schema_fields[field]["guidance"])
        else:
            questions.append(f"请明确提供 {field}。")
    return "；".join(dict.fromkeys(questions))


def validate_model_tool_result(prompt: str, tool: str, raw_arguments: Any,
                               context: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Validate the model's proposed tool against the user intent and grounded slots.

    Returns ``{"ok": True, "arguments": ...}`` only when the proposal is a unique
    intent match and every retained argument is grounded. Otherwise returns a safe,
    user-facing clarification; it never creates a proposal itself.
    """
    context = context if isinstance(context, Mapping) else {}
    candidates = find_tool_intent_candidates(prompt)
    if not candidates:
        return {"ok": False, "clarification": (
            "我暂未创建操作预览，因为无法可靠确认请求对应的受控操作。请明确说明要查询、分析、修改或控制哪一项；"
            "涉及参数时请给出目标值。"
        )}
    if len(candidates) > 1 and _COMPOUND_ACTION_RE.search(_effective_text(prompt)):
        labels = [TOOL_INTENT_CONTRACTS[name].intent for name, _ in candidates[:3]]
        return {"ok": False, "clarification": (
            "我暂未创建操作预览。请求中包含多个动作或步骤（" + "、".join(labels) +
            "）；请拆分请求，每次确认一个操作。"
        )}
    # An exact registered example/title is a strong, explicit match and may outrank
    # a weaker lexical overlap (e.g. “resume paused playback” mentions “pause”).
    # Similar-strength candidates remain ambiguous and fail closed.
    if len(candidates) > 1 and candidates[0][1] - candidates[1][1] < 10:
        labels = [TOOL_INTENT_CONTRACTS[name].intent for name, _ in candidates[:3]]
        return {"ok": False, "clarification": (
            "我暂未创建操作预览。你的表达可能对应多个动作（" + "、".join(labels) +
            "）；请明确选择一个动作，复合操作请分步提出。"
        )}
    matched_tool, _score = candidates[0]
    if matched_tool != tool:
        return {"ok": False, "clarification": (
            f"我暂未创建操作预览。你的请求更符合「{TOOL_INTENT_CONTRACTS[matched_tool].intent}」，"
            f"而不是「{TOOL_INTENT_CONTRACTS.get(tool, TOOL_INTENT_CONTRACTS[matched_tool]).intent}」。"
            "请确认希望执行的单一动作。"
        )}
    try:
        raw = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    except (ValueError, TypeError):
        return {"ok": False, "clarification": "我暂未创建操作预览，因为模型返回的参数格式无法核验。请重新明确操作对象和参数。"}
    if not isinstance(raw, dict):
        return {"ok": False, "clarification": "我暂未创建操作预览，因为工具参数不是对象。请明确操作对象与所需参数。"}
    contract = TOOL_INTENT_CONTRACTS[tool]
    schema = TOOL_BY_NAME[tool]["parameters"]
    properties = schema.get("properties", {})
    if any(key not in properties for key in raw):
        return {"ok": False, "clarification": "我暂未创建操作预览，因为模型给出的参数超出该操作允许范围。请重新明确需要的固定参数。"}
    for field in raw:
        if _field_value_ambiguity(tool, field, prompt):
            return {"ok": False, "clarification": (
                f"我暂未创建操作预览。「{contract.intent}」中的「{field}」可能对应多个用户提到的值；"
                "请明确选择一个对象或拆分操作。"
            )}

    cleaned: Dict[str, Any] = {}
    missing_grounding: List[str] = []
    required = set(schema.get("required", []))
    required_any_fields = {field for group in contract.required_any for field in group}
    for field, value in raw.items():
        if _value_grounded(tool, field, value, prompt, context, raw):
            cleaned[field] = value
        elif (field in required or (contract.mode == "action" and field in required_any_fields)
              or _field_context_present(field, prompt, raw, tool)):
            # A value the user explicitly addressed but the model mis-grounded is not
            # safely discardable; ask instead of silently substituting a default.
            missing_grounding.append(field)
        # Ungrounded optional model guesses are deliberately discarded; the business
        # adapter may apply its own documented default, but the model cannot widen scope.
    if missing_grounding:
        ask = _missing_parameter_prompt(tool, missing_grounding)
        return {"ok": False, "clarification": (
            f"我暂未创建操作预览。「{contract.intent}」需要明确参数：{ask}"
        )}

    missing_required = sorted(required - set(cleaned))
    missing_groups = [group for group in contract.required_any if not set(group).intersection(cleaned)]
    if missing_required or missing_groups:
        ask = _missing_parameter_prompt(tool, [*missing_required, *["|".join(group) for group in missing_groups]])
        return {"ok": False, "clarification": (
            f"我暂未创建操作预览。「{contract.intent}」还缺少必要信息：{ask}"
        )}
    try:
        arguments = validate_tool_arguments(tool, cleaned)
    except ValueError as exc:
        return {"ok": False, "clarification": (
            f"我暂未创建操作预览，因为参数未通过该工具的固定校验（{str(exc)}）。请补充或更正参数后重试。"
        )}
    return {"ok": True, "arguments": arguments}


# ---------------------------------------------------------------------------
# 置信度标准化与三档分流（设计文档 §6.5）
# ---------------------------------------------------------------------------

# 置信度阈值（0-1 标准化后）
CONFIDENCE_HIGH = 0.80   # 高置信：直接路由
CONFIDENCE_MED_LOW = 0.55  # 低置信下界
CONFIDENCE_GAP_MIN = 0.15  # top1 与 top2 最小分差


def normalize_confidence(score: int) -> float:
    """将 0-100 的词法得分标准化为 0-1 的置信度。

    当前阶段仅基于词法得分；后续引入模型判定后，可按多源融合公式
    c_final = 0.5 × c_model + 0.3 × c_gap_norm + 0.2 × c_sim 合成。
    """
    if score <= 0:
        return 0.0
    if score >= 100:
        return 1.0
    return round(score / 100.0, 4)


def classify_confidence(confidence: float, gap: float = 0.0) -> str:
    """三档分流判定。

    返回 "high" / "medium" / "low" 三档之一：
      - high:  >= 0.80 且 top1-top2 分差 >= 0.15 -> 直接路由
      - medium: 0.55-0.80 或分差不足           -> 走通用检索，标注未精确匹配
      - low:    < 0.55                            -> 进入“其他”域通用问答
    """
    if confidence >= CONFIDENCE_HIGH and gap >= CONFIDENCE_GAP_MIN:
        return "high"
    if confidence < CONFIDENCE_MED_LOW:
        return "low"
    return "medium"


def confidence_diversion(
    confidence: float, gap: float = 0.0
) -> Dict[str, Any]:
    """返回置信度分流决策，供路由层决定是否直接创建提案。

    字段：
      - tier: "high" / "medium" / "low"
      - route_directly: 是否可跳过模型判定直接创建提案（仅 high 且确定性路由已命中时为 True）
      - message: 面向用户的简要说明（medium/low 时供参考）
    """
    tier = classify_confidence(confidence, gap)
    if tier == "high":
        return {
            "tier": "high",
            "route_directly": True,
            "message": "置信度高，可直接路由。",
        }
    if tier == "medium":
        return {
            "tier": "medium",
            "route_directly": False,
            "message": "置信度中等，建议通过模型判定或澄清后再操作。",
        }
    return {
        "tier": "low",
        "route_directly": False,
        "message": "置信度低，未能可靠匹配受控操作，请更明确地说明意图。",
    }


def fuse_confidence(
    lexical_score: int,
    model_confidence: Optional[float] = None,
    gap: float = 0.0,
    similarity: Optional[float] = None,
) -> float:
    """多源置信度融合（设计文档 §6.5）。

    融合公式：c_final = 0.5 × c_model + 0.3 × c_gap_norm + 0.2 × c_sim

    参数：
      - lexical_score: 0-100 的词法得分（当前阶段的 c_model 兜底）
      - model_confidence: 模型自评分，0-1；未提供时用词法得分标准化值代替
      - gap: top1 与 top2 候选原始分差，0-100；用于计算 c_gap_norm
      - similarity: 召回相似度，0-1；未提供时用词法得分标准化值代替

    返回 0-1 的融合置信度。
    """
    c_lex = normalize_confidence(lexical_score)
    c_model = model_confidence if model_confidence is not None else c_lex
    c_model = max(0.0, min(1.0, float(c_model)))
    # c_gap_norm：gap 越大越可信，gap >= 0.5（即原始分差 >= 50）视为完全可信
    c_gap = max(0.0, min(1.0, abs(float(gap)) / 50.0))
    c_sim = similarity if similarity is not None else c_lex
    c_sim = max(0.0, min(1.0, float(c_sim)))
    return round(0.5 * c_model + 0.3 * c_gap + 0.2 * c_sim, 4)


# ---------------------------------------------------------------------------
# IntentRecognitionResult Schema（设计文档 §8.4.1，阶段 B 预留）
# ---------------------------------------------------------------------------

INTENT_RECOGNITION_RESULT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "IntentRecognitionResult",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "intent_code", "intent_name", "confidence", "reason", "slots",
        "missing_slots", "need_clarify", "clarify_question",
        "sub_intents", "rewritten_query", "entities",
    ],
    "properties": {
        "intent_code": {"type": "string"},
        "intent_name": {"type": "string", "maxLength": 20},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string", "maxLength": 120},
        "slots": {"type": "object", "additionalProperties": False},
        "missing_slots": {"type": "array", "uniqueItems": True, "maxItems": 5},
        "need_clarify": {"type": "boolean"},
        "clarify_question": {"type": ["string", "null"], "maxLength": 30},
        "sub_intents": {"type": "array", "maxItems": 5},
        "rewritten_query": {"type": "string", "minLength": 1, "maxLength": 200},
        "entities": {"type": "array", "maxItems": 10},
    },
}


def build_intent_recognition_result(
    intent_code: str,
    intent_name: str,
    confidence: float,
    reason: str,
    slots: Optional[Dict[str, Any]] = None,
    missing_slots: Optional[Sequence[str]] = None,
    need_clarify: bool = False,
    clarify_question: Optional[str] = None,
    sub_intents: Optional[Sequence[str]] = None,
    rewritten_query: Optional[str] = None,
    entities: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """构建符合 IntentRecognitionResult Schema 的结构化意图识别输出。"""
    return {
        "intent_code": intent_code,
        "intent_name": intent_name[:20],
        "confidence": max(0.0, min(1.0, float(confidence))),
        "reason": reason[:120],
        "slots": slots or {},
        "missing_slots": list(missing_slots or [])[:5],
        "need_clarify": bool(need_clarify),
        "clarify_question": (clarify_question or None)[:30] if clarify_question else None,
        "sub_intents": list(sub_intents or [])[:5],
        "rewritten_query": (rewritten_query or "")[:200],
        "entities": list(entities or [])[:10],
    }


def validate_intent_recognition_result(result: Any) -> Dict[str, Any]:
    """对 IntentRecognitionResult 做结构化校验（无 jsonschema 依赖的轻量版本）。"""
    if not isinstance(result, dict):
        return {"ok": False, "error": "结果必须是 JSON 对象"}
    for key in INTENT_RECOGNITION_RESULT_SCHEMA["required"]:
        if key not in result:
            return {"ok": False, "error": f"缺少必填字段: {key}"}
    if not isinstance(result["confidence"], (int, float)) or not (0 <= result["confidence"] <= 1):
        return {"ok": False, "error": "confidence 必须是 0 到 1 之间的数字"}
    if not isinstance(result["need_clarify"], bool):
        return {"ok": False, "error": "need_clarify 必须是布尔值"}
    if result["clarify_question"] is not None and not isinstance(result["clarify_question"], str):
        return {"ok": False, "error": "clarify_question 必须是字符串或 null"}
    if not isinstance(result["slots"], dict):
        return {"ok": False, "error": "slots 必须是对象"}
    if not isinstance(result["missing_slots"], list):
        return {"ok": False, "error": "missing_slots 必须是数组"}
    if not isinstance(result["sub_intents"], list):
        return {"ok": False, "error": "sub_intents 必须是数组"}
    if not isinstance(result["entities"], list):
        return {"ok": False, "error": "entities 必须是数组"}
    return {"ok": True, "result": result}


# ---------------------------------------------------------------------------
# 意图识别缓存（设计文档 §6.10）
# ---------------------------------------------------------------------------

class _IntentCache:
    """简单的意图识别内存缓存，TTL 默认 1 小时。

    键由“意图字典版本 + 归一化问句”的 SHA-256 哈希构成，命中时直接返回
    缓存的结构化识别结果，避免重复模型调用。
    """

    def __init__(self, ttl_s: float = 3600.0, dict_version: str = "v2.0"):
        self.ttl_s = float(ttl_s)
        self.dict_version = str(dict_version)
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def _key(self, prompt: str) -> str:
        h = hashlib.sha256()
        h.update(self.dict_version.encode("utf-8"))
        h.update(b"\0")
        h.update(normalize_intent_text(prompt).encode("utf-8"))
        return h.hexdigest()

    def get(self, prompt: str) -> Optional[Dict[str, Any]]:
        key = self._key(prompt)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            expiry, value = entry
            if time.time() > expiry:
                del self._cache[key]
                return None
            return dict(value)

    def set(self, prompt: str, value: Dict[str, Any]) -> None:
        key = self._key(prompt)
        with self._lock:
            self._cache[key] = (time.time() + self.ttl_s, dict(value))

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


intent_cache = _IntentCache()


# ---------------------------------------------------------------------------
# 阶段 B：结构化意图识别入口（设计文档 §8.4.1）
# ---------------------------------------------------------------------------

def recognize_intent(
    prompt: str,
    context: Optional[Mapping[str, Any]] = None,
    top_k: int = 8,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """结构化意图识别入口（阶段 B）。

    流程：
      1. 查缓存（归一化问句 + 字典版本哈希）
      2. 候选意图召回（top-k，默认 8）
      3. 复合意图检测（_COMPOUND_ACTION_RE）
      4. 置信度计算与多源融合（fuse_confidence）
      5. 三档分流（classify_confidence / confidence_diversion）
      6. 构建并返回符合 IntentRecognitionResult Schema 的结构化结果

    返回字段：
      - ok: 是否可直接路由（tier == high 且非复合）
      - tier: "high" / "medium" / "low"
      - result: IntentRecognitionResult 结构
      - candidates: [(tool_name, lexical_score), ...] 召回候选
      - cache_hit: 是否命中缓存
    """
    context = context if isinstance(context, Mapping) else {}
    cache_key_prompt = normalize_intent_text(prompt)

    if use_cache:
        cached = intent_cache.get(prompt)
        if cached is not None:
            cached = dict(cached)
            cached["cache_hit"] = True
            return cached

    candidates = find_tool_intent_candidates(prompt, top_k=top_k)
    effective = _effective_text(prompt)
    is_compound = bool(_COMPOUND_ACTION_RE.search(effective)) and len(candidates) > 1

    # 无候选
    if not candidates:
        result = build_intent_recognition_result(
            intent_code="",
            intent_name="",
            confidence=0.0,
            reason="无候选意图匹配",
            need_clarify=True,
            clarify_question="我暂未创建操作预览，因为无法可靠确认请求对应的受控操作。请明确说明要查询、分析、修改或控制哪一项。",
        )
        outcome = {
            "ok": False,
            "tier": "low",
            "result": result,
            "candidates": [],
            "cache_hit": False,
        }
        if use_cache:
            intent_cache.set(prompt, outcome)
        return outcome

    top_tool, top_score = candidates[0]
    confidence = normalize_confidence(top_score)
    gap = 0.0
    if len(candidates) >= 2:
        gap = abs(top_score - candidates[1][1]) / 100.0

    # 多源融合：当前阶段以词法得分作为 c_model/c_sim 的兜底值
    fused = fuse_confidence(top_score, model_confidence=None, gap=gap * 100.0, similarity=None)
    # 单候选无歧义：词法得分达到中档阈值（>=40，即动词+目标均有匹配）时，
    # 直接判定为 high tier，避免 gap=0 拉低融合置信度导致误入 low tier。
    if len(candidates) == 1 and top_score >= 40:
        tier = "high"
    else:
        tier = classify_confidence(fused, gap)

    # 复合意图：检测到多个动作且有多个候选，拒绝直接路由，要求拆分
    if is_compound:
        sub_intents = [name for name, _ in candidates[:5]]
        result = build_intent_recognition_result(
            intent_code="",
            intent_name="复合意图",
            confidence=fused,
            reason="检测到多个并列动作，请拆分为单一动作",
            need_clarify=True,
            clarify_question="请求中包含多个动作（如“启动并调速”），请拆分为单一动作再提交。",
            sub_intents=sub_intents,
        )
        outcome = {
            "ok": False,
            "tier": "low",
            "result": result,
            "candidates": candidates,
            "cache_hit": False,
        }
        if use_cache:
            intent_cache.set(prompt, outcome)
        return outcome

    # 低置信：进入“其他”域通用问答
    if tier == "low":
        contract = TOOL_INTENT_CONTRACTS.get(top_tool)
        intent_name = contract.intent if contract else ""
        result = build_intent_recognition_result(
            intent_code=top_tool,
            intent_name=intent_name,
            confidence=fused,
            reason="置信度过低，无法可靠匹配受控操作",
            need_clarify=True,
            clarify_question="我暂未创建操作预览，置信度不足，请更明确地说明意图。",
        )
        outcome = {
            "ok": False,
            "tier": "low",
            "result": result,
            "candidates": candidates,
            "cache_hit": False,
        }
        if use_cache:
            intent_cache.set(prompt, outcome)
        return outcome

    # 高/中置信：返回结构化结果
    contract = TOOL_INTENT_CONTRACTS[top_tool]
    need_clarify = tier == "medium"
    result = build_intent_recognition_result(
        intent_code=top_tool,
        intent_name=contract.intent,
        confidence=fused,
        reason=f"词法匹配得分 {top_score}，置信度 {fused}",
        need_clarify=need_clarify,
        clarify_question=(
            "表达可能对应多个动作，请明确选择一个。"
            if need_clarify
            else None
        ),
    )
    outcome = {
        "ok": tier == "high",
        "tier": tier,
        "result": result,
        "candidates": candidates,
        "cache_hit": False,
    }
    if use_cache:
        intent_cache.set(prompt, outcome)
    return outcome


def tool_intent_hint(tool: str) -> str:
    """Compact, trusted guidance appended only to this allowed tool's model schema."""
    contract = TOOL_INTENT_CONTRACTS[tool]
    positives = "；".join(contract.positive_examples[:2])
    negatives = "；".join(contract.negative_examples[:2])
    parameters = contract.parameter_policy
    return f"意图边界：{contract.intent}。正例：{positives}。不适用：{negatives}。参数规则：{parameters}"


def validate_intent_catalog() -> None:
    """Raise if the finite intent contract stops covering the registered tool catalog."""
    catalog = set(TOOL_NAMES)
    contracts = set(TOOL_INTENT_CONTRACTS)
    missing = sorted(catalog - contracts)
    extra = sorted(contracts - catalog)
    if missing or extra:
        raise AssertionError(f"意图目录与工具目录不一致；missing={missing}, extra={extra}")
    for tool, contract in TOOL_INTENT_CONTRACTS.items():
        if contract.tool != tool or not contract.intent or contract.mode not in {"read", "action", "analysis"}:
            raise AssertionError(f"{tool} 的意图元数据不完整")
        if len(contract.positive_examples) < 2 or len(contract.negative_examples) < 2:
            raise AssertionError(f"{tool} 必须至少有两个正例和两个反例")
        if not contract.action_terms or not contract.target_terms or not contract.parameter_policy:
            raise AssertionError(f"{tool} 缺少动作词、目标词或参数规则")
        schema_fields = set(TOOL_BY_NAME[tool]["parameters"].get("properties", {}))
        if set(contract.parameter_rules) != schema_fields:
            raise AssertionError(f"{tool} 参数规则与 schema 字段不一致")
        for group in contract.required_any:
            if not set(group) <= schema_fields:
                raise AssertionError(f"{tool} 的 required_any 含未知参数")


validate_intent_catalog()
