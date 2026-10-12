"""配置模型：全部可配置项集中于此，支持 JSON 持久化与运行时热更新。

口径说明（电力系统常用）：
- PT（电压互感器变比）：一次电压 / 二次电压，默认 100（如 10000V/100V）
- CT（电流互感器变比）：一次电流 / 二次电流，默认 15（如 75A/5A）
- 一次值 = 二次值 × 变比；功率一次值 = 二次功率 × PT × CT
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# 电气量子界面键（与 UI 导航条一一对应；顺序即导航条顺序）
QUANTITY_KEYS: Tuple[str, ...] = (
    "voltage",        # 三相电压（有效值 / 线电压 / 相电压 / 逐周期统计）
    "current",        # 三相电流（有效值 / 逐周期统计）
    "power",          # 有功 / 无功 / 视在
    "power_factor",   # 功率因数（总 / 分相 / 基波位移因数）
    "fundamental",    # 基波（幅值 / 相位 / 频率 / 序分量 / 不平衡度）
    "harmonic",       # 谐波 2~50 次（含有率 / THD）
    "spectrum",       # 频谱（0 ~ Nyquist）
)

WINDOW_POLICIES = ("integer_cycles", "full_window")
WINDOW_FUNCS = ("rect", "hann")
SOURCE_KINDS = ("csv_file", "csv_tail", "simulator", "tcp")
APPARENT_MODES = ("arithmetic", "vector")
REACTIVE_MODES = ("harmonic_sum", "quadrature")
VOLTAGE_INPUT_MODES = ("phase", "line")
# 有「趋势曲线」的电气量（spectrum 是瞬时频谱，不是时间趋势，不在此列）
CURVE_KEYS = ("voltage", "current", "power", "power_factor", "fundamental", "harmonic")


class ConfigError(ValueError):
    """配置非法（给出可直接执行的修复提示）。"""


def parse_time_text(text: str) -> float:
    """把用户填写的起始时间解析为 epoch 秒（**本地时间**解释）。

    接受：epoch 秒数字（如 1791800000 或 1791800000.5）、
          "2026-10-12 08:00:00[.fff]"、"2026/10/12 08:00:00"、"2026-10-12T08:00:00"、"2026-10-12"。
    非法文本抛 ConfigError（附可接受写法）。
    """
    from datetime import datetime
    s = str(text).strip()
    if not s:
        raise ConfigError("起始时间为空")
    try:
        v = float(s)
        if v < 0 or v > 1e11:
            raise ConfigError(f"起始时间 epoch 秒超出合理范围：{s}")
        return v
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
                "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            continue
    raise ConfigError(
        f"起始时间 '{s}' 无法解析；可写 epoch 秒（1791800000）或 '2026-10-12 08:00:00' / "
        f"'2026/10/12 08:00:00' / '2026-10-12T08:00:00' / '2026-10-12'")


@dataclass
class WindowSpec:
    """单个电气量的计算窗配置。

    length_s : 计算时间段（秒）——需求⑥「各电气量支持分别配置指定的时间段」
    step_s   : 输出步长（秒），None 表示等于 length_s（不重叠滚动）
    policy   : integer_cycles＝截断到整数个基波周期（FFT 类量必须用此策略，否则频谱泄漏）
               full_window＝严格按 length_s 取样（可能非整周期，仅建议用于时域量 RMS/功率）
    window_fn: rect / hann（仅 spectrum 生效；hann 会做幅值相干增益校正）
    remove_dc: 计算前是否去直流（去除后为「交流有效值」，否则为「真有效值含直流」）
    min_cycles: 整数周期截断时最少保留的周期数
    """

    length_s: float = 1.0
    step_s: Optional[float] = None
    policy: str = "integer_cycles"
    window_fn: str = "rect"
    remove_dc: bool = True
    min_cycles: int = 1

    def effective_step_s(self) -> float:
        return float(self.step_s) if self.step_s else float(self.length_s)

    def validate(self, name: str, fs: float) -> None:
        if self.length_s <= 0:
            raise ConfigError(f"[{name}] length_s 必须 > 0（当前 {self.length_s}）")
        if self.effective_step_s() <= 0:
            raise ConfigError(f"[{name}] step_s 必须 > 0（当前 {self.step_s}）")
        if self.policy not in WINDOW_POLICIES:
            raise ConfigError(f"[{name}] policy 必须是 {WINDOW_POLICIES}（当前 {self.policy}）")
        if self.window_fn not in WINDOW_FUNCS:
            raise ConfigError(f"[{name}] window_fn 必须是 {WINDOW_FUNCS}（当前 {self.window_fn}）")
        n = self.length_s * fs
        if n < 2:
            raise ConfigError(f"[{name}] length_s={self.length_s}s 在 fs={fs}Hz 下不足 2 个采样点")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WindowSpec":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def default_windows() -> Dict[str, WindowSpec]:
    """默认窗配置：时域量 1s，FFT 类量 1s（=50 个周波，频率分辨率 1Hz），频谱 1s。

    谐波/基波用 0.2s（=10 个周波，IEC 61000-4-7 推荐窗长）作为更快的默认值，
    便于观察谐波随时间变化；用户可在「窗口配置」子界面按量单独改（1s/5s 任意）。
    """
    return {
        "voltage": WindowSpec(length_s=1.0),
        "current": WindowSpec(length_s=1.0),
        "power": WindowSpec(length_s=1.0),
        "power_factor": WindowSpec(length_s=1.0),
        "fundamental": WindowSpec(length_s=0.2),
        "harmonic": WindowSpec(length_s=0.2),
        "spectrum": WindowSpec(length_s=1.0, window_fn="rect"),
    }


@dataclass
class SamplingConfig:
    """采样与频率口径。fs=6400Hz、f_nom=50Hz → 128 点/周波（2 的幂，FFT 友好）。"""

    fs: float = 6400.0
    f_nom: float = 50.0
    f_min: float = 45.0
    f_max: float = 65.0
    adaptive_freq: bool = False      # True＝每窗先估频再整周期截断（抗频率偏移泄漏）
    fs_from_timestamps: bool = True  # True＝用时间戳中位差校验/覆盖 fs（不一致时给告警）
    fs_tolerance: float = 0.01       # 时间戳推算 fs 与配置 fs 的相对容差

    @property
    def samples_per_cycle(self) -> float:
        return self.fs / self.f_nom

    @property
    def f_nyquist(self) -> float:
        return self.fs / 2.0

    def validate(self) -> None:
        if self.fs <= 0:
            raise ConfigError(f"sampling.fs 必须 > 0（当前 {self.fs}）")
        if not (0 < self.f_nom < self.f_nyquist):
            raise ConfigError(f"sampling.f_nom={self.f_nom} 必须落在 (0, Nyquist={self.f_nyquist})")
        if self.f_min >= self.f_max:
            raise ConfigError(f"sampling.f_min({self.f_min}) 必须 < f_max({self.f_max})")
        if self.f_nom < self.f_min or self.f_nom > self.f_max:
            raise ConfigError(f"sampling.f_nom={self.f_nom} 必须落在 [f_min, f_max]=[{self.f_min},{self.f_max}]")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SamplingConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class TransformConfig:
    """PT/CT 变比（需求：PT=100、CT=15，均可配置）。"""

    pt_ratio: float = 100.0
    ct_ratio: float = 15.0
    voltage_input: str = "phase"   # phase＝CSV 中为相电压；line＝CSV 中为线电压
    enabled: bool = True           # False＝直接用二次值（调试/对比用）

    @property
    def power_ratio(self) -> float:
        return self.pt_ratio * self.ct_ratio

    def validate(self) -> None:
        if self.pt_ratio <= 0 or self.ct_ratio <= 0:
            raise ConfigError(f"PT/CT 变比必须 > 0（当前 PT={self.pt_ratio}, CT={self.ct_ratio}）")
        if self.voltage_input not in VOLTAGE_INPUT_MODES:
            raise ConfigError(f"transform.voltage_input 必须是 {VOLTAGE_INPUT_MODES}（当前 {self.voltage_input}）")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransformConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class HarmonicConfig:
    """谐波口径：需求指定 2~50 次。"""

    order_min: int = 2
    order_max: int = 50
    thd_order_max: int = 50        # THD 计算到的最高次数
    include_interharmonic: bool = True   # 是否输出间谐波（非整数次）能量占比

    def validate(self, sampling: SamplingConfig) -> None:
        if self.order_min < 1 or self.order_max < self.order_min:
            raise ConfigError(f"harmonic 次数范围非法：order_min={self.order_min}, order_max={self.order_max}")
        f_max_h = self.order_max * sampling.f_nom
        if f_max_h >= sampling.f_nyquist:
            raise ConfigError(
                f"harmonic.order_max={self.order_max} 次对应 {f_max_h:.0f}Hz ≥ Nyquist {sampling.f_nyquist:.0f}Hz，会混叠；"
                f"fs={sampling.fs}Hz 下最高可分析 {int(sampling.f_nyquist // sampling.f_nom) - 1} 次"
            )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HarmonicConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PowerConfig:
    """功率口径（不同标准定义不同，必须显式配置并在结果中标注）。

    apparent  : arithmetic＝S=ΣU_k·I_k（三相算术视在，国网计量常用）
                vector＝S=√(P²+Q²)（几何视在）
    reactive  : harmonic_sum＝Q=Σ_h U_h·I_h·sinφ_h（逐次谐波无功之和，非正弦工况严格口径）
                quadrature＝Q=√(S²−P²)（由视在与有功反推）
    fundamental_power: 是否额外输出基波功率 P1/Q1/S1 与位移因数 DPF=cosφ1
    """

    apparent: str = "arithmetic"
    reactive: str = "harmonic_sum"
    fundamental_power: bool = True
    three_phase_mode: str = "four_wire"   # four_wire＝三相四线（Σ 分相功率）；three_wire 预留

    def validate(self) -> None:
        if self.apparent not in APPARENT_MODES:
            raise ConfigError(f"power.apparent 必须是 {APPARENT_MODES}（当前 {self.apparent}）")
        if self.reactive not in REACTIVE_MODES:
            raise ConfigError(f"power.reactive 必须是 {REACTIVE_MODES}（当前 {self.reactive}）")
        if self.three_phase_mode != "four_wire":
            raise ConfigError(
                f"power.three_phase_mode={self.three_phase_mode} 暂不支持："
                "本工具输入为三相电压+三相电流（三相四线口径）；三相三线需两瓦特表法，待需求确认后实现"
            )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PowerConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ColumnMap:
    """CSV 列名映射（默认＝用户给定格式），支持英文/中文别名自动识别。"""

    timestamp: str = "时间戳"
    ua: str = "A相电压"
    ia: str = "A相电流"
    ub: str = "B相电压"
    ib: str = "B相电流"
    uc: str = "C相电压"
    ic: str = "C相电流"
    encoding: str = "auto"          # auto / utf-8 / utf-8-sig / gbk / gb18030
    delimiter: str = ","
    has_header: bool = True
    timestamp_unit: str = "auto"    # auto / s / ms / us / ns / datetime

    ALIASES: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "timestamp": ["时间戳", "时间", "时标", "timestamp", "time", "ts", "datetime", "date_time"],
            "ua": ["a相电压", "ua", "u_a", "va", "v_a", "电压a", "phasea_voltage", "u_phase_a"],
            "ia": ["a相电流", "ia", "i_a", "电流a", "phasea_current", "i_phase_a"],
            "ub": ["b相电压", "ub", "u_b", "vb", "v_b", "电压b", "phaseb_voltage", "u_phase_b"],
            "ib": ["b相电流", "ib", "i_b", "电流b", "phaseb_current", "i_phase_b"],
            "uc": ["c相电压", "uc", "u_c", "vc", "v_c", "电压c", "phasec_voltage", "u_phase_c"],
            "ic": ["c相电流", "ic", "i_c", "电流c", "phasec_current", "i_phase_c"],
        }
    )

    def resolve(self, header: List[str]) -> Dict[str, int]:
        """把表头解析为 {字段: 列索引}。先精确匹配配置名，再走别名（大小写/空格不敏感）。"""
        norm = {self._norm(h): idx for idx, h in enumerate(header)}
        out: Dict[str, int] = {}
        configured = {
            "timestamp": self.timestamp, "ua": self.ua, "ia": self.ia,
            "ub": self.ub, "ib": self.ib, "uc": self.uc, "ic": self.ic,
        }
        for key, name in configured.items():
            if name in header:
                out[key] = header.index(name)
            elif self._norm(name) in norm:
                out[key] = norm[self._norm(name)]
        for key in configured:
            if key in out:
                continue
            for alias in self.ALIASES.get(key, []):
                a = self._norm(alias)
                if a in norm:
                    out[key] = norm[a]
                    break
        missing = [k for k in ("timestamp", "ua", "ia", "ub", "ib", "uc", "ic") if k not in out]
        if missing:
            raise ConfigError(
                f"CSV 表头无法识别字段 {missing}；表头={header}；"
                f"请在 configs 中显式指定 column_map 或修正表头（支持别名见 ColumnMap.ALIASES）"
            )
        return out

    @staticmethod
    def _norm(s: str) -> str:
        return "".join(str(s).split()).lower().replace("_", "").replace("-", "")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ColumnMap":
        keep = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        obj = cls(**keep)
        if "ALIASES" in d and isinstance(d["ALIASES"], dict):
            obj.ALIASES.update(d["ALIASES"])
        return obj


@dataclass
class SourceConfig:
    """数据源配置（需求④：实时采集 + 离线文件两种输入方式）。

    kind:
      csv_file  离线文件（一次读完，按窗滚动计算）
      csv_tail  实时：监视文件/目录追加内容（采集程序持续写 CSV 时用）
      simulator 实时：内置合成源（基波+2~50次谐波+噪声），用于联调与演示
      tcp       实时：TCP 客户端（frame=text_csv 按行解析；frame=binary 按 struct_fmt 解包）
    """

    kind: str = "simulator"
    path: str = ""                       # csv_file/csv_tail 的文件或目录
    poll_interval_s: float = 0.2         # 实时源轮询间隔
    block_samples: int = 640             # 每块样本数（6400Hz 下 = 0.1s）
    tail_from_end: bool = False          # csv_tail：True 只读新增内容
    watch_dir_newest: bool = True        # csv_tail：path 为目录时自动跟踪最新文件
    host: str = "127.0.0.1"
    port: int = 9000
    frame: str = "text_csv"              # text_csv | binary
    struct_fmt: str = "<7d"              # binary 帧格式（默认 7 个 double：t,ua,ia,ub,ib,uc,ic）🔶待用户协议确认
    struct_fields: str = "t,ua,ia,ub,ib,uc,ic"   # binary 帧字段顺序（与 struct_fmt 对应）🔶待用户协议确认
    struct_has_header: bool = False
    sim_f: float = 50.0                  # 模拟器基波频率
    sim_harmonics: Dict[int, float] = field(default_factory=lambda: {3: 0.08, 5: 0.06, 7: 0.03, 11: 0.015, 13: 0.01})
    sim_noise_ratio: float = 0.002
    sim_unbalance: float = 0.02
    sim_speed: float = 1.0               # 1.0＝按真实时间速率产出；>1 加速（联调用）
    # 离线文件播放的时间轴（csv_file 专用）：
    #   custom_time=False → 用文件里的时间戳播放（默认，保留文件真实缺口）
    #   custom_time=True  → 时间轴 = 起始时间 + 样本序号 / fs（等间隔，不再有缺口）；
    #       起始时间 custom_time_start 留空＝文件第 1 条数据的时间，否则填
    #       "2026-10-12 08:00:00"（本地时间文本）或 epoch 秒数字。
    #   典型用途：采集器时标只有当天时刻（0/00/00 00:12:40.0000）或 0.1ms 量化造成的抖动。
    custom_time: bool = False
    custom_time_start: str = ""
    # 离线文件播放起点（csv_file 专用）：从文件的指定位置开始播放，之前的数据直接跳过（不参与计算）。
    #   play_start_mode: begin   从头（默认，play_start_value 忽略）
    #                    row     从第 N 条数据行开始（1 起算，不含表头）：value="120001"
    #                    seconds 跳过文件开头 N 秒的数据（按配置 fs 换算成行数）：value="30"
    #                    percent 从文件的 N% 处开始（按字节位置，再对齐到行首）：value="50"
    #                    time    从文件时标 ≥ 指定时刻的第一条数据开始：value="2026-10-12 08:00:00"
    #                            或只填时刻 "08:00:00"（与文件时标的当天时刻比较，适合 0/00/00 写法）
    play_start_mode: str = "begin"
    play_start_value: str = ""

    def validate(self) -> None:
        if self.kind not in SOURCE_KINDS:
            raise ConfigError(f"source.kind 必须是 {SOURCE_KINDS}（当前 {self.kind}）")
        if self.play_start_mode not in PLAY_START_MODES:
            raise ConfigError(f"source.play_start_mode 必须是 {PLAY_START_MODES}（当前 {self.play_start_mode}）")
        if self.play_start_mode != "begin":
            parse_play_start(self.play_start_mode, self.play_start_value)   # 非法在保存配置时就报
        if self.custom_time and str(self.custom_time_start).strip():
            parse_time_text(str(self.custom_time_start))      # 非法文本在保存配置时就报错，而不是启动后
        if self.kind in ("csv_file", "csv_tail") and not self.path:
            raise ConfigError(f"source.kind={self.kind} 需要 source.path（文件或目录路径）")
        if self.kind == "tcp" and not (0 < self.port < 65536):
            raise ConfigError(f"source.port 非法：{self.port}")
        if self.block_samples <= 0:
            raise ConfigError(f"source.block_samples 必须 > 0（当前 {self.block_samples}）")
        if self.frame not in ("text_csv", "binary"):
            raise ConfigError(f"source.frame 必须是 ('text_csv','binary')（当前 {self.frame}）")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SourceConfig":
        keep = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        sim_h = keep.get("sim_harmonics")
        if isinstance(sim_h, dict):
            keep["sim_harmonics"] = {int(k): float(v) for k, v in sim_h.items()}
        return cls(**keep)


PLAY_START_MODES = ("begin", "row", "seconds", "percent", "time")


def parse_play_start(mode: str, value: Any) -> Any:
    """校验并解析播放起点取值：row→int(≥1)，seconds→float(≥0)，percent→float(0~100)，
    time→("abs", epoch 秒) 或 ("tod", 当天秒数)；begin→None。非法抛 ConfigError。"""
    text = str(value if value is not None else "").strip()
    if mode == "begin":
        return None
    if not text:
        raise ConfigError(f"source.play_start_mode={mode} 需要填写 source.play_start_value")
    if mode == "row":
        try:
            n = int(float(text))
        except ValueError:
            raise ConfigError(f"播放起点「第 N 行」必须是整数（当前 {text!r}）") from None
        if n < 1:
            raise ConfigError(f"播放起点「第 N 行」必须 ≥ 1（当前 {n}）")
        return n
    if mode == "seconds":
        try:
            v = float(text)
        except ValueError:
            raise ConfigError(f"播放起点「跳过 N 秒」必须是数字（当前 {text!r}）") from None
        if v < 0:
            raise ConfigError(f"播放起点「跳过 N 秒」不能为负（当前 {v}）")
        return v
    if mode == "percent":
        try:
            v = float(text.rstrip("%"))
        except ValueError:
            raise ConfigError(f"播放起点「百分比」必须是数字（当前 {text!r}）") from None
        if not (0 <= v <= 100):
            raise ConfigError(f"播放起点「百分比」须在 0~100（当前 {v}）")
        return v
    if mode == "time":
        import re as _re
        m = _re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?", text)
        if m:
            hh, mm, ss, frac = m.groups()
            if int(hh) > 23 or int(mm) > 59 or int(ss or 0) > 60:
                raise ConfigError(f"播放起点时刻非法：{text!r}")
            return ("tod", int(hh) * 3600 + int(mm) * 60 + int(ss or 0) + (float("0." + frac) if frac else 0.0))
        return ("abs", parse_time_text(text))
    raise ConfigError(f"未知播放起点模式 {mode!r}")


def default_curve_save() -> Dict[str, bool]:
    """六条趋势曲线的「保存曲线数据」开关默认值（全部保存）。"""
    return {k: True for k in CURVE_KEYS}


@dataclass
class OutputConfig:
    history_len: int = 600          # 兼容旧配置：已不再作为上限使用（见 history_hours / history_max_points）
    history_hours: float = 24.0     # 趋势曲线保留最近多少小时（按数据时间计；不足则全部保留）
    history_max_points: int = 500000  # 每条曲线内存上限（安全阀）：0.2s 步长的快量 24h≈43.2 万点，
                                      # 默认 50 万点可完整覆盖；紧凑数组存储每值 8 字节（≈32MB/曲线）。
                                      # 超出按时间最旧的丢弃；界面请求时再按 max_points 抽稀
    export_dir: str = "output"      # 导出目录
    spectrum_max_points: int = 1600  # 频谱推送给 UI 的最大点数（超出则等间隔抽稀）
    # 「保存曲线数据」时各曲线是否参与：键＝曲线（电气量）名，False＝保存时跳过该项
    curve_save: Dict[str, bool] = field(default_factory=default_curve_save)
    # 实时落盘：每算出一个曲线点就追加到 realtime_dir/<曲线>_<数据日期>.csv（受 curve_save 勾选过滤）
    realtime_save: bool = True
    realtime_dir: str = "output/realtime"

    def validate(self) -> None:
        if not str(self.realtime_dir).strip():
            raise ConfigError("output.realtime_dir 不能为空")
        if self.history_hours <= 0:
            raise ConfigError(f"output.history_hours 必须 > 0（当前 {self.history_hours}）")
        if self.history_max_points < 10:
            raise ConfigError(f"output.history_max_points 必须 ≥ 10（当前 {self.history_max_points}）")
        unknown = [k for k in self.curve_save if k not in CURVE_KEYS]
        if unknown:
            raise ConfigError(f"output.curve_save 含未知曲线 {unknown}；可用：{list(CURVE_KEYS)}")
        # 缺省键补齐为 True，界面与导出按完整六键工作
        self.curve_save = {k: bool(self.curve_save.get(k, True)) for k in CURVE_KEYS}


@dataclass
class AppConfig:
    """顶层配置。持久化为 JSON（configs/default.json）。"""

    name: str = "电力系统电气量计算工具"
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    transform: TransformConfig = field(default_factory=TransformConfig)
    harmonic: HarmonicConfig = field(default_factory=HarmonicConfig)
    power: PowerConfig = field(default_factory=PowerConfig)
    columns: ColumnMap = field(default_factory=ColumnMap)
    source: SourceConfig = field(default_factory=SourceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    windows: Dict[str, WindowSpec] = field(default_factory=default_windows)

    # ---------- 派生量 ----------
    @property
    def max_window_s(self) -> float:
        return max(w.length_s for w in self.windows.values())

    @property
    def min_step_s(self) -> float:
        return min(w.effective_step_s() for w in self.windows.values())

    def window(self, quantity: str) -> WindowSpec:
        if quantity not in self.windows:
            raise ConfigError(f"未知电气量 '{quantity}'；可用：{sorted(self.windows)}")
        return self.windows[quantity]

    # ---------- 校验 ----------
    def validate(self) -> "AppConfig":
        self.sampling.validate()
        self.transform.validate()
        self.harmonic.validate(self.sampling)
        self.power.validate()
        self.source.validate()
        self.output.validate()
        for name, spec in self.windows.items():
            spec.validate(name, self.sampling.fs)
        missing = [k for k in QUANTITY_KEYS if k not in self.windows]
        if missing:
            raise ConfigError(f"windows 缺少电气量配置：{missing}（需覆盖 {QUANTITY_KEYS}）")
        return self

    # ---------- 序列化 ----------
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["windows"] = {k: asdict(v) for k, v in self.windows.items()}
        d["source"]["sim_harmonics"] = {str(k): v for k, v in self.source.sim_harmonics.items()}
        d.pop("_ALIASES", None)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AppConfig":
        cfg = cls()
        if "name" in d:
            cfg.name = str(d["name"])
        for key, klass in (
            ("sampling", SamplingConfig), ("transform", TransformConfig), ("harmonic", HarmonicConfig),
            ("power", PowerConfig), ("columns", ColumnMap), ("source", SourceConfig),
        ):
            if isinstance(d.get(key), dict):
                setattr(cfg, key, klass.from_dict(d[key]))
        if isinstance(d.get("output"), dict):
            keep = {k: v for k, v in d["output"].items() if k in OutputConfig.__dataclass_fields__}
            cfg.output = OutputConfig(**keep)
        if isinstance(d.get("windows"), dict):
            wins: Dict[str, WindowSpec] = {}
            for k, v in d["windows"].items():
                if isinstance(v, dict):
                    wins[k] = WindowSpec.from_dict(v)
                elif isinstance(v, (int, float)):      # 简写：{"voltage": 5.0}
                    wins[k] = WindowSpec(length_s=float(v))
            if wins:
                cfg.windows = {**default_windows(), **wins}
        return cfg.validate()

    @classmethod
    def load(cls, path: str) -> "AppConfig":
        if not os.path.isfile(path):
            raise ConfigError(f"配置文件不存在：{path}（可用 --init-config 生成默认配置）")
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def save(self, path: str) -> str:
        self.validate()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json() + "\n")
        return path


def load_or_default(path: Optional[str]) -> AppConfig:
    """存在则加载，否则返回默认配置（CLI/服务启动用）。"""
    if path and os.path.isfile(path):
        return AppConfig.load(path)
    return AppConfig().validate()
