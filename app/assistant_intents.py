"""Finite intent contracts for the assistant's closed business-tool catalog.

The model may suggest a registered tool, but this module is the server-side gate:
intent words, examples, parameter grounding, and the existing strict schema must all
agree before a proposal can be created. Unknown or ambiguous language is clarified.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.assistant_tools import TOOL_BY_NAME, TOOL_NAMES, validate_tool_arguments


# Kept finite and explicit. Examples are both reviewable policy and regression data;
# they are not treated as instructions if they appear in untrusted tool/resource data.
_INTENT_DATA: Dict[str, Dict[str, Any]] = {
    "get_runtime_status": {
        "intent": "查询当前侧运行状态",
        "mode": "read",
        "actions": ("查询", "查看", "看看", "现在", "当前", "在跑", "什么状态", "是否运行"),
        "targets": ("运行状态", "运行情况", "数据源状态", "数据源在跑", "暂停状态", "结束状态", "样本数"),
        "positive": ("查一下当前侧运行状态", "现在数据源在跑吗"),
        "negative": ("启动当前侧数据源", "查询当前侧计算配置"),
        "policy": "只查询当前侧状态摘要，不接受参数；状态问题不等于要求启动、暂停或停止。",
    },
    "get_runtime_settings": {
        "intent": "查询当前侧计算配置摘要",
        "mode": "read",
        "actions": ("查询", "查看", "看看", "当前", "现在"),
        "targets": ("计算配置", "配置摘要", "采样率和变比", "接线模式和窗口", "当前参数", "计算设置"),
        "positive": ("查看当前侧计算配置摘要", "现在的采样率和变比是多少"),
        "negative": ("查询当前侧运行状态", "把采样率改为12800"),
        "policy": "只读取白名单配置摘要；用户未要求修改时不能调用任何配置写工具。",
    },
    "get_electrical_result": {
        "intent": "查询指定电气量最新结果",
        "mode": "read",
        "actions": ("查询", "查看", "看看", "显示", "取一下", "最新", "当前值"),
        "targets": ("最新结果", "电气量结果", "当前结果", "最新电压", "最新电流", "最新功率", "最新谐波", "最新频谱"),
        "positive": ("查询最新电压结果", "查看当前侧最新功率因数结果"),
        "negative": ("查询电压趋势历史", "修改电压计算窗口"),
        "policy": "quantity 必须由用户明确指定并映射到固定枚举；不能猜测默认电气量。",
    },
    "get_history": {
        "intent": "查询指定电气量趋势历史",
        "mode": "read",
        "actions": ("查询", "查看", "看看", "最近", "过去"),
        "targets": ("趋势历史", "历史曲线", "变化趋势", "趋势", "历史数据", "电压历史", "电流历史", "功率历史"),
        "positive": ("查询最近24小时电压趋势", "看看功率因数历史曲线"),
        "negative": ("查询最新电压结果", "加载上次落盘的历史数据"),
        "policy": "quantity 必须明确；hours / max_points 只有在用户明确给出时才采用，否则省略使用服务端默认。",
    },
    "get_event_list": {
        "intent": "查询电能质量事件",
        "mode": "read",
        "actions": ("查询", "查看", "看看", "列出", "有哪些", "多少", "当前", "最近"),
        "targets": ("电能质量事件", "事件列表", "电压暂升事件", "谐波事件", "频率事件", "rocof事件", "功率振荡事件"),
        "positive": ("列出当前电能质量事件", "最近有哪些频率事件"),
        "negative": ("修改电能质量事件阈值", "清空电能质量事件列表"),
        "policy": "只读事件；active / event_type / limit 只能按用户明确筛选条件设置，未提及的可选项省略。",
    },
    "get_nilm_events": {
        "intent": "查询负荷辨识事件",
        "mode": "read",
        "actions": ("查询", "查看", "看看", "列出", "有哪些", "多少", "当前", "最近"),
        "targets": ("负荷辨识事件", "nilm事件", "负荷事件", "算法事件", "画像匹配事件"),
        "positive": ("查询负荷辨识事件", "列出最近的画像匹配事件"),
        "negative": ("修改负荷辨识参数", "清空负荷辨识事件"),
        "policy": "算法 / 相别 / limit 仅采用用户明确指定值；未指定筛选项时省略。",
    },
    "compare_sides": {
        "intent": "查询总线侧与分路侧电气量对比",
        "mode": "read",
        "actions": ("比较", "对比", "查询", "查看", "看看"),
        "targets": ("两侧", "总线侧和分路侧", "总线与分路", "跨侧", "侧间差值", "时间对齐"),
        "positive": ("对比总线侧和分路侧电压", "查询两侧功率的时间对齐差值"),
        "negative": ("修改跨侧对齐参数", "只查询总线侧电压最新结果"),
        "policy": "quantity 必须明确；hours / max_points 只有用户明确给出时才使用，不能把对比请求改成配置写入。",
    },
    "load_last_history": {
        "intent": "加载上次落盘历史到当前页面",
        "mode": "action",
        "actions": ("加载", "载入", "恢复到页面", "显示上次保存"),
        "targets": ("上次落盘历史", "上次播放历史", "保存的曲线", "上次保存的数据"),
        "positive": ("加载上次落盘的历史数据", "把上次播放保存的曲线载入页面"),
        "negative": ("查询最近24小时历史趋势", "启动当前数据源"),
        "policy": "无必需参数；hours / curves / events / nilm 仅按用户明确要求筛选，不得默认省略某类数据。",
    },
    "start_current_source": {
        "intent": "启动当前侧已配置数据源",
        "mode": "action",
        "actions": ("启动", "开始", "开始播放", "播放", "运行", "跑起来"),
        "targets": ("当前数据源", "离线数据源", "数据源", "csv文件", "当前离线文件"),
        "positive": ("启动当前侧已配置的数据源", "播放离线数据源CSV文件"),
        "negative": ("如何播放离线数据源", "修改离线播放速度"),
        "policy": "无参数；只使用当前侧已有配置。CSV / 文件字样不授权选择文件或推断路径；问句、否定句不启动。",
    },
    "pause_current_source": {
        "intent": "暂停当前侧离线播放",
        "mode": "action",
        "actions": ("暂停", "暂时停止", "停一下"),
        "targets": ("离线播放", "当前播放", "数据源播放", "csv播放", "数据源"),
        "positive": ("暂停当前侧离线播放", "把正在播放的CSV停一下"),
        "negative": ("停止当前侧数据源", "恢复离线播放"),
        "policy": "无参数；只适用于当前侧可暂停的离线播放，不能把暂停改成停止或启动。",
    },
    "resume_current_source": {
        "intent": "恢复当前侧已暂停的离线播放",
        "mode": "action",
        "actions": ("恢复", "继续", "接着", "继续播放"),
        "targets": ("暂停播放", "离线播放", "csv播放", "当前数据源", "数据源"),
        "positive": ("恢复当前侧离线播放", "继续刚才暂停的CSV播放"),
        "negative": ("重新启动数据源", "把播放速度调到2倍"),
        "policy": "无参数；仅恢复已暂停来源，不重启、不改变倍速。",
    },
    "stop_current_source": {
        "intent": "停止当前侧数据源",
        "mode": "action",
        "actions": ("停止", "终止", "结束运行"),
        "targets": ("当前数据源", "数据源运行", "当前侧来源", "采集任务", "数据源"),
        "positive": ("停止当前侧数据源", "终止当前数据源检测"),
        "negative": ("暂停当前侧离线播放", "查询数据源运行状态"),
        "policy": "无参数；须是明确停止请求。提示总线侧既有联动影响，不能与暂停或清除事件混淆。",
    },
    "select_recording_source": {
        "intent": "选择一个受控录波文件作为当前数据源",
        "mode": "action",
        "actions": ("选择", "设为", "切换到", "改用", "使用", "作为"),
        "targets": ("录波文件", "csv文件", "文件作为数据源", "离线文件数据源"),
        "positive": ("把指定录波文件设为当前数据源", "改用记录名称为X的CSV文件"),
        "negative": ("列出可用录波文件", "启动当前已配置的数据源"),
        "policy": "file_id 必须指向本轮受控目录中由用户名称 / ID / 明确序号选中的唯一文件；不接受路径或任意文件名。",
    },
    "list_recordings": {
        "intent": "列出受控录波文件目录",
        "mode": "read",
        "actions": ("查询", "查看", "列出", "有哪些", "显示"),
        "targets": ("可用录波文件", "录波文件列表", "csv文件目录", "data目录文件", "output目录文件"),
        "positive": ("列出data目录里的可用录波文件", "查看output目录的CSV文件列表"),
        "negative": ("把某个文件设为数据源", "启动当前数据源"),
        "policy": "folder 为必需枚举；用户未明确 data / output 时澄清，不自行挑一个目录。",
    },
    "inspect_recording": {
        "intent": "检查受控录波文件结构信息",
        "mode": "analysis",
        "actions": ("检查", "查看", "读取摘要", "分析文件信息", "查看信息"),
        "targets": ("录波文件信息", "采样率", "通道数", "点数", "时长", "时间范围"),
        "positive": ("检查指定CSV的采样率和通道", "查看受控录波文件的点数与时长"),
        "negative": ("分析录波有效值RMS", "列出可用录波文件"),
        "policy": "file_id 必须对应用户明确指出的本轮受控文件；不读取未登记路径。",
    },
    "analyze_recording_rms": {
        "intent": "计算受控录波单通道逐周波RMS摘要",
        "mode": "analysis",
        "actions": ("分析", "计算", "统计", "求", "检查"),
        "targets": ("录波rms", "有效值", "逐周波有效值", "周波rms"),
        "positive": ("计算指定录波Ia通道的逐周波RMS", "分析这份文件的A相电压有效值"),
        "negative": ("检查录波文件信息", "估算CT变比"),
        "policy": "file_id 和单个 channel 必须明确且来自受控清单 / 固定通道；duration_s 只有明确给出时采用。",
    },
    "tune_recording": {
        "intent": "分析受控录波并生成负荷辨识调参建议",
        "mode": "analysis",
        "actions": ("调参分析", "分析", "生成建议", "评估参数", "调优"),
        "targets": ("录波", "负荷辨识", "nilm", "检测参数"),
        "positive": ("分析这份录波并给负荷辨识调参建议", "评估CSV上的NILM参数"),
        "negative": ("修改正在使用的负荷辨识参数", "提取设备画像"),
        "policy": "file_id 必须由用户选定的受控录波解析；max_cycles 只按用户指定值采用，否则省略服务端默认。",
    },
    "resample_recording": {
        "intent": "对受控录波创建重采样文件",
        "mode": "action",
        "actions": ("重采样", "重新采样", "转换采样率"),
        "targets": ("录波", "csv文件", "波形文件"),
        "positive": ("把指定录波重采样到12800Hz", "将这份CSV的采样率转换为10000"),
        "negative": ("查询重采样任务状态", "取消重采样任务"),
        "policy": "file_id 与 fs_new 必须由用户明确指向受控文件并给出目标采样率；method 未明确时省略。",
    },
    "get_resample_status": {
        "intent": "查询当前后台重采样任务状态",
        "mode": "read",
        "actions": ("查询", "查看", "现在", "当前", "进度"),
        "targets": ("重采样任务状态", "重采样进度", "重采样任务", "后台重采样"),
        "positive": ("查看当前重采样任务状态", "重采样现在到什么进度了"),
        "negative": ("启动录波重采样", "取消重采样任务"),
        "policy": "无参数；仅查询当前任务，不猜测具体任务 ID。",
    },
    "cancel_resample": {
        "intent": "请求取消当前重采样任务",
        "mode": "action",
        "actions": ("取消", "中止", "停止"),
        "targets": ("重采样任务", "后台重采样", "正在重采样"),
        "positive": ("取消当前重采样任务", "中止正在进行的录波重采样"),
        "negative": ("查询重采样任务状态", "停止当前数据源"),
        "policy": "无参数；只取消当前后台重采样任务，不删除其他文件或清理整个缓存。",
    },
    "estimate_ct_ratio": {
        "intent": "依据两侧受控录波和事件时间估算CT变比",
        "mode": "analysis",
        "actions": ("估算", "计算", "评估"),
        "targets": ("ct变比", "电流变比", "总线侧和分路侧电流台阶"),
        "positive": ("根据两侧录波的A相启动台阶估算CT变比", "用总线与分路事件时间计算CT倍率"),
        "negative": ("修改CT变比配置", "查询两侧电流曲线"),
        "policy": "两侧 file_id、事件类型、四个时间边界、phase 均需由用户明确提供并映射到受控资源；不得猜时间、相别或已知CT值。",
    },
    "extract_device_profile": {
        "intent": "从受控录波提取设备画像",
        "mode": "action",
        "actions": ("提取", "生成", "建立", "创建"),
        "targets": ("设备画像", "负荷画像", "用电设备画像", "设备特征画像"),
        "positive": ("从指定录波提取设备画像", "为设备ID pump_1生成NILM画像"),
        "negative": ("查询设备画像列表", "加载最新设备画像"),
        "policy": "file_id 与 device_id 必须有明确来源；其他采样窗 / 标签 / 量 / 相别只接受用户明示值，输出目录固定由服务端管理。",
    },
    "derive_profile_stages": {
        "intent": "从指定画像派生多档位假设画像",
        "mode": "action",
        "actions": ("派生", "生成", "扩展", "制作档位"),
        "targets": ("设备画像", "多档位", "档位画像", "假设档位"),
        "positive": ("为指定设备画像派生2倍和3倍档位", "从画像ID生成多档位假设画像"),
        "negative": ("加载设备画像", "查询画像列表"),
        "policy": "profile_id 必须对应用户明确选择的受控画像；scales 中每个倍率都须在用户文本出现；q_mode 未提及时省略。",
    },
    "export_csv": {
        "intent": "导出指定类别的当前侧CSV结果",
        "mode": "action",
        "actions": ("导出", "下载", "保存成csv"),
        "targets": ("csv", "电气量结果", "曲线", "负荷辨识事件", "nilm事件"),
        "positive": ("导出当前侧电气量结果CSV", "下载已保存趋势曲线CSV"),
        "negative": ("查询CSV文件目录", "重采样录波CSV"),
        "policy": "dataset 必须由用户指定为固定类别之一；不能把原始录波、路径或输出文件名作为导出参数。",
    },
    "set_profile_parameters": {
        "intent": "修改当前侧设备画像匹配阈值",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "改为", "设成"),
        "targets": ("画像匹配阈值", "d2_max", "最小置信度", "匹配置信度"),
        "positive": ("把画像匹配的d2_max设为4", "将设备画像最小置信度调整到0.8"),
        "negative": ("查询画像匹配阈值", "启用画像匹配算法"),
        "policy": "至少明确给出 d2_max 或 min_confidence 之一及数值；模型不得补齐另一个阈值。",
        "required_any": (("d2_max", "min_confidence"),),
    },
    "set_profile_detection_enabled": {
        "intent": "启用或停用设备画像匹配算法",
        "mode": "action",
        "actions": ("启用", "停用", "打开", "关闭", "切换"),
        "targets": ("画像匹配算法", "设备画像识别", "画像检测"),
        "positive": ("启用设备画像匹配", "关闭画像检测算法"),
        "negative": ("查询设备画像", "修改画像匹配阈值"),
        "policy": "enabled 必须与用户明确的启用 / 停用语义一致；只切换开关，不修改阈值或画像文件。",
    },
    "list_profiles": {
        "intent": "查询当前侧受控设备画像列表",
        "mode": "read",
        "actions": ("查询", "查看", "列出", "有哪些", "显示"),
        "targets": ("设备画像列表", "画像目录", "可用画像", "画像有哪些"),
        "positive": ("列出当前侧设备画像", "查询有哪些可用画像"),
        "negative": ("加载最新设备画像", "从录波提取设备画像"),
        "policy": "无参数；只查询当前侧受控画像清单，不读取任意文件。",
    },
    "load_latest_profile": {
        "intent": "加载当前侧最新设备画像",
        "mode": "action",
        "actions": ("加载", "载入", "启用", "挂载"),
        "targets": ("最新设备画像", "最新画像", "当前侧最新画像"),
        "positive": ("加载当前侧最新设备画像", "启用最新画像匹配"),
        "negative": ("列出设备画像", "从录波提取画像"),
        "policy": "无参数；仅按服务端当前侧最新画像解析并在确认时复验，不由模型提交路径。",
    },
    "load_profile_by_id": {
        "intent": "加载用户指定的受控设备画像",
        "mode": "action",
        "actions": ("加载", "载入", "启用", "使用"),
        "targets": ("指定画像", "画像id", "设备画像文件"),
        "positive": ("加载指定profile_id的设备画像", "启用画像ID abcdef0123456789"),
        "negative": ("加载最新设备画像", "查询画像列表"),
        "policy": "profile_id 必须匹配用户明确指定且属于本轮当前侧清单的画像；不从名称猜 ID。",
    },
    "set_wiring_mode": {
        "intent": "切换当前侧接线模式",
        "mode": "action",
        "actions": ("切换", "设置", "修改", "改成", "改为"),
        "targets": ("接线模式", "接线方式", "3p3w", "3p4w", "三相三线", "三相四线"),
        "positive": ("把接线模式切换到3p4w", "设置成三相三线制"),
        "negative": ("查询当前接线模式", "修改PT和CT变比"),
        "policy": "wiring 必须由用户明示为 3p3w 或 3p4w；不能连带修改 PT / CT 或重构参数。",
    },
    "set_electrical_parameters": {
        "intent": "修改采样与电气变换参数",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "改为", "设成"),
        "targets": ("采样率", "额定频率", "pt变比", "ct变比", "电压输入口径", "电流反向", "三线重构"),
        "positive": ("把采样率设为12800Hz", "将PT变比改为1000"),
        "negative": ("查询采样率和变比", "切换接线模式"),
        "policy": "至少一个字段和值必须由用户明确给出；只修改提到的字段，其余可选字段不得猜测或一并重设。",
        "required_any": (("fs", "f_nom", "f_min", "f_max", "pt_ratio", "ct_ratio", "voltage_input", "invert_current", "invert_phases", "reconstruct_3w"),),
    },
    "set_harmonic_parameters": {
        "intent": "修改谐波分析范围或间谐波开关",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "改为", "打开", "关闭"),
        "targets": ("谐波范围", "谐波次数", "thd最高次数", "间谐波输出"),
        "positive": ("把谐波最高次数改为50", "开启间谐波输出"),
        "negative": ("查询谐波分析结果", "修改电气量计算窗口"),
        "policy": "至少明确提供一个谐波字段；次数须有明确整数值，间谐波开关须有明确开 / 关语义。",
        "required_any": (("order_min", "order_max", "thd_order_max", "include_interharmonic"),),
    },
    "set_power_calculation_mode": {
        "intent": "修改功率计算口径",
        "mode": "action",
        "actions": ("修改", "设置", "切换", "调整", "改为", "关闭", "开启"),
        "targets": ("视在功率口径", "无功功率口径", "基波功率输出", "功率计算模式"),
        "positive": ("将视在功率改为向量法", "关闭基波功率输出"),
        "negative": ("查询有功功率结果", "调整功率曲线窗口"),
        "policy": "至少一个口径 / 开关值由用户明确指定；枚举值按白名单匹配，不修改采样、变比或接线。",
        "required_any": (("apparent", "reactive", "fundamental_power"),),
    },
    "set_compare_alignment": {
        "intent": "修改总线侧跨侧时间对齐参数",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "改为"),
        "targets": ("跨侧时间偏移", "对齐偏移", "对齐容差", "时间对齐参数"),
        "positive": ("把跨侧对齐偏移设为2秒", "将时间对齐容差调整到0.5秒"),
        "negative": ("查询两侧数据对齐结果", "改动分路侧数据源"),
        "policy": "至少一个 offset_s / tolerance_s 及其数值须由用户明示；只允许总线侧写入，其他侧或数据源配置不在此工具范围。",
        "required_any": (("offset_s", "tolerance_s"),),
    },
    "set_playback_speed": {
        "intent": "修改当前侧CSV离线播放速度",
        "mode": "action",
        "actions": ("调整", "修改", "设置", "调到", "调至", "改成", "改为"),
        "targets": ("播放速度", "离线倍速", "播放倍速", "速度"),
        "positive": ("将离线播放速度设置为2倍", "把当前CSV倍速调整到0.5"),
        "negative": ("播放离线数据源", "启动当前数据源", "恢复暂停播放"),
        "policy": "speed 必须是用户明确指定的数值；单说播放 / 启动 / 快慢不提供足够值，也不启动数据源。",
    },
    "set_file_time_utc": {
        "intent": "设置CSV文本时标按UTC或本机时间解释",
        "mode": "action",
        "actions": ("设置", "切换", "修改", "改为", "按"),
        "targets": ("时标解释", "时间戳按utc", "按本地时间解析", "utc模式", "时间按本机"),
        "positive": ("把当前CSV时标设为UTC", "时间戳按本机本地时间解释"),
        "negative": ("设置系统时区", "更换离线数据源文件"),
        "policy": "use_utc 必须由用户明确选择 UTC 或本机本地时间；不得把系统时区变更当作此设置。",
    },
    "set_window_parameters": {
        "intent": "修改指定电气量的计算窗长或步长",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "改成", "改为"),
        "targets": ("计算窗口", "窗长", "步长", "输出间隔"),
        "positive": ("把电压计算窗长设为1秒", "将谐波步长改成0.2秒"),
        "negative": ("查询趋势历史", "修改谐波次数范围"),
        "policy": "quantity 必须明确，且 length_s / step_s 至少指定一项；数值必须出现在请求中，不能猜默认电气量。",
        "required_any": (("length_s", "step_s"),),
    },
    "set_event_parameter": {
        "intent": "修改一项电能质量事件数值阈值",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "改为", "提高", "降低"),
        "targets": ("电能质量事件阈值", "电压暂升阈值", "谐波阈值", "rocof阈值", "事件限值"),
        "positive": ("把电压暂升阈值设为110", "降低电能质量事件的THD电压限值到5"),
        "negative": ("查询电能质量事件", "启用事件检测"),
        "policy": "parameter 必须指向固定白名单中的一项，value 必须由用户明确提供；不能根据常识猜默认阈值。",
    },
    "set_event_detection_enabled": {
        "intent": "启用或停用电能质量事件检测总开关",
        "mode": "action",
        "actions": ("启用", "停用", "打开", "关闭", "切换"),
        "targets": ("电能质量事件检测", "事件检测总开关", "事件识别开关"),
        "positive": ("启用电能质量事件检测", "关闭事件检测总开关"),
        "negative": ("修改事件阈值", "查询电能质量事件"),
        "policy": "enabled 必须按用户明确的开 / 关意图设置；不修改阈值、目录或事件数据。",
    },
    "set_nilm_parameter": {
        "intent": "修改一个已注册负荷辨识算法数值参数",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "改为", "设为"),
        "targets": ("负荷辨识算法参数", "nilm参数", "检测参数", "周波参数"),
        "positive": ("把threshold算法的threshold参数改为0.8", "调整CUSUM的窗口周波参数到10"),
        "negative": ("启用负荷辨识算法", "生成录波调参建议"),
        "policy": "algorithm、parameter 和 value 均需从用户请求明确得到；未提及的算法 / 键 / 数值不得推断。",
    },
    "set_nilm_algorithm_enabled": {
        "intent": "启用或停用一个负荷辨识算法",
        "mode": "action",
        "actions": ("启用", "停用", "打开", "关闭", "切换"),
        "targets": ("负荷辨识算法", "nilm算法", "threshold算法", "双窗法", "双窗口", "two_window算法",
                    "cusum算法", "累积和算法", "glr算法", "广义似然比算法", "steady_state算法", "稳态法",
                    "median_diff算法", "中位差算法", "profile算法"),
        "positive": ("启用CUSUM负荷辨识算法", "停用threshold算法"),
        "negative": ("修改负荷辨识参数", "查询负荷辨识事件"),
        "policy": "algorithm 和 enabled 都必须由用户明示；只切换对应算法开关。",
    },
    "set_nilm_core_parameters": {
        "intent": "修改负荷辨识基础检测参数",
        "mode": "action",
        "actions": ("修改", "设置", "调整", "开启", "关闭", "启用", "停用", "打开", "禁用", "改为"),
        "targets": ("负荷辨识基础参数", "负荷辨识", "nilm基础设置", "自动参数", "检测量", "检测对象", "周波间隔", "变化比例"),
        "positive": ("把负荷辨识检测对象改成A相", "将NILM最小变化比例设为5%"),
        "negative": ("修改某个算法专属参数", "查询负荷辨识事件"),
        "policy": "至少明确一个基础字段及值；未提及字段不改，不接收画像、输出目录或任意配置对象。",
        "required_any": (("enabled", "auto_params", "quantity", "channel", "window_cycles", "min_gap_cycles", "rel_tol_pct", "min_delta_pct"),),
    },
    "set_curve_save_enabled": {
        "intent": "切换指定趋势曲线的保存开关",
        "mode": "action",
        "actions": ("启用", "停用", "打开", "关闭", "设置", "切换"),
        "targets": ("趋势曲线保存", "曲线落盘", "曲线保存开关", "电压曲线保存"),
        "positive": ("开启电压趋势曲线保存", "关闭功率因数曲线落盘"),
        "negative": ("导出已保存曲线CSV", "查询最新电压结果"),
        "policy": "quantity 与 enabled 均需明确；不能修改输出目录或文件名。",
    },
    "clear_events": {
        "intent": "清空当前侧内存中的电能质量事件列表",
        "mode": "action",
        "actions": ("清空", "清除", "移除"),
        "targets": ("电能质量事件列表", "内存事件", "当前事件"),
        "positive": ("清空当前侧电能质量事件", "清除内存中的事件列表"),
        "negative": ("查询电能质量事件", "删除磁盘事件CSV"),
        "policy": "无参数；需明确清空事件列表。该工具不删除磁盘CSV，也不清除整体缓存。",
    },
    "clear_nilm_events": {
        "intent": "清空当前侧内存中的负荷辨识事件列表",
        "mode": "action",
        "actions": ("清空", "清除", "移除"),
        "targets": ("负荷辨识事件列表", "nilm事件", "负荷事件"),
        "positive": ("清空当前侧负荷辨识事件", "清除内存中的NILM事件列表"),
        "negative": ("查询负荷辨识事件", "清理缓存"),
        "policy": "无参数；只清当前侧内存事件，不删除磁盘CSV，也不等于清除缓存。",
    },
    "run_algorithm_selftest": {
        "intent": "运行内置算法自检",
        "mode": "action",
        "actions": ("运行", "执行", "做一下", "启动"),
        "targets": ("算法自检", "解析解自检", "自检测试"),
        "positive": ("运行算法自检", "执行内置解析解自检测试"),
        "negative": ("查询算法参数", "启动当前数据源"),
        "policy": "无参数；只运行内置自检并返回摘要，不修改配置。",
    },
}


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


def find_tool_intent_candidates(prompt: str) -> List[Tuple[str, int]]:
    matches = [(name, score) for name in TOOL_NAMES if (score := tool_intent_score(prompt, name)) > 0]
    return sorted(matches, key=lambda pair: (-pair[1], pair[0]))


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
