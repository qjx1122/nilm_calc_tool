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
    "interharmonic",  # 间谐波（IEC 61000-4-7 分组：各次谐波之间的非整数次成分 / TIHD / 主导间谐波相量）
    "dc",             # 直流偏置（各相电压/电流直流分量、相对基波百分比、中性线直流）
    "spectrum",       # 频谱（0 ~ Nyquist）
)

WINDOW_POLICIES = ("integer_cycles", "full_window")
WINDOW_FUNCS = ("rect", "hann")
SOURCE_KINDS = ("csv_file", "csv_tail", "simulator", "tcp")
APPARENT_MODES = ("arithmetic", "vector")
REACTIVE_MODES = ("harmonic_sum", "quadrature")
VOLTAGE_INPUT_MODES = ("phase", "line")
# 有「趋势曲线」的电气量（spectrum 是瞬时频谱，不是时间趋势，不在此列）
CURVE_KEYS = ("voltage", "current", "power", "power_factor", "fundamental", "harmonic", "interharmonic", "dc")


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
        "interharmonic": WindowSpec(length_s=0.2),              # IEC 61000-4-7：10 周波 → 5 Hz 分辨率（每组 9 个间谐波 bin）
        "dc": WindowSpec(length_s=1.0, remove_dc=False),        # 直流量：整周期均值（remove_dc 对本量无意义，固定按原始值）
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
    enabled: bool = True           # False＝直接用二次值（调试/对比用）；界面出厂配置 configs/default.json 为 false（v0.99.8：默认不启用）
    invert_current: bool = False   # v0.92：电流极性反转（CT 接反 / P 为负时勾选；不依赖 enabled，三相同时取反）
    invert_phases: str = ""        # v0.93：分相电流极性反转，如 "A" / "AC"（与 invert_current 叠加；单相 CT 接反时用）
    wiring: str = "3p4w"           # v0.93：接线方式 3p4w＝三相四线（三 PT 三 CT）；3p3w＝三相三线两表法（B 相无 CT，Pb≡0 属正常，ΣP=Pa+Pc）
    reconstruct_3w: bool = False   # v0.94：3p3w 虚拟中性点重构——ib=−(ia+ic)（严格），相电压由 Uab/Ucb 重构（假设电压对称，近似）；重构后各分相量与 3p4w 同口径

    @property
    def power_ratio(self) -> float:
        return self.pt_ratio * self.ct_ratio

    def validate(self) -> None:
        if self.pt_ratio <= 0 or self.ct_ratio <= 0:
            raise ConfigError(f"PT/CT 变比必须 > 0（当前 PT={self.pt_ratio}, CT={self.ct_ratio}）")
        if self.voltage_input not in VOLTAGE_INPUT_MODES:
            raise ConfigError(f"transform.voltage_input 必须是 {VOLTAGE_INPUT_MODES}（当前 {self.voltage_input}）")
        if self.wiring not in ("3p4w", "3p3w"):
            raise ConfigError(f"transform.wiring 必须是 3p4w/3p3w（当前 {self.wiring}）")
        bad = [c for c in str(self.invert_phases).upper() if c not in "ABC ,/"]
        if bad:
            raise ConfigError(f"transform.invert_phases 只能含 A/B/C（当前 {self.invert_phases!r}）")

    def phase_signs(self) -> list:
        """各相电流符号 [sA, sB, sC]（全局反转 × 分相反转）。"""
        g = -1.0 if bool(self.invert_current) else 1.0
        inv = str(self.invert_phases or "").upper()
        return [g * (-1.0 if ch in inv else 1.0) for ch in "ABC"]

    @property
    def three_wire(self) -> bool:
        return str(self.wiring) == "3p3w"

    @property
    def reconstructing(self) -> bool:
        """v0.94：是否在做三线制重构（仅 wiring=3p3w 且 reconstruct_3w 时生效）。"""
        return self.three_wire and bool(self.reconstruct_3w)

    @property
    def b_phase_missing(self) -> bool:
        """本侧 B 相电流是否天然缺失（3p3w 且未重构）——画像匹配跳过 d_ib、体检不报 B 缺相。"""
        return self.three_wire and not bool(self.reconstruct_3w)

    @property
    def voltage_is_line(self) -> bool:
        """下游电压列是否仍为线电压（重构后已是相电压）。"""
        return self.voltage_input == "line" and not self.reconstructing

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
    # ---- 离线文件列映射（第 10 轮）----
    # mapping_enabled=False（默认）：表头可识别（配置名/别名）时按表头取列，否则按默认列序
    #   「时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流」（第 1~7 列）。
    # mapping_enabled=True：只按 mapping 取列。每个字段的值为：""＝不映射（该通道不播放，按 0 处理；
    #   时间戳不映射＝按配置 fs 合成时间轴）、纯数字＝第几列（从 1 起）、其它＝表头列名（精确或忽略大小写/空格）。
    mapping_enabled: bool = False
    mapping: Dict[str, str] = field(default_factory=lambda: {
        "timestamp": "1", "ua": "2", "ia": "3", "ub": "4", "ib": "5", "uc": "6", "ic": "7"})

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

    def _resolve_partial(self, header: List[str]) -> Dict[str, int]:
        """与 resolve 同规则，但不要求字段齐全：返回能识别的 {字段: 列索引}。"""
        norm = {self._norm(h): idx for idx, h in enumerate(header)}
        out: Dict[str, int] = {}
        configured = {"timestamp": self.timestamp, "ua": self.ua, "ia": self.ia,
                      "ub": self.ub, "ib": self.ib, "uc": self.uc, "ic": self.ic}
        for key, name in configured.items():
            if name in header:
                out[key] = header.index(name)
            elif self._norm(name) in norm:
                out[key] = norm[self._norm(name)]
        for key in configured:
            if key in out:
                continue
            for alias in self.ALIASES.get(key, []):
                if self._norm(alias) in norm:
                    out[key] = norm[self._norm(alias)]
                    break
        return out

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

    FIELDS = ("timestamp", "ua", "ia", "ub", "ib", "uc", "ic")
    FIELD_NAMES = {"timestamp": "时间", "ua": "A相电压", "ia": "A相电流", "ub": "B相电压",
                   "ib": "B相电流", "uc": "C相电压", "ic": "C相电流"}

    def validate(self) -> None:
        if not isinstance(self.mapping, dict):
            raise ConfigError("columns.mapping 必须是 {字段: 列号或列名} 字典")
        self.mapping = {k: ("" if v is None else str(v).strip()) for k, v in self.mapping.items() if k in self.FIELDS}
        for k in self.FIELDS:
            self.mapping.setdefault(k, "")
        if self.mapping_enabled:
            for k, v in self.mapping.items():
                if v.isdigit() and int(v) < 1:
                    raise ConfigError(f"columns.mapping.{k} 列号必须从 1 起（当前 {v}）")
            if not any(self.mapping[k] for k in self.FIELDS if k != "timestamp"):
                raise ConfigError("columns.mapping_enabled=true 但没有任何电压/电流通道被映射")
            used = [v for v in self.mapping.values() if v]
            dup = sorted({v for v in used if used.count(v) > 1})
            if dup:
                raise ConfigError(f"columns.mapping 有多个字段映射到同一列：{dup}")

    def layout(self, header: Optional[List[str]]) -> Dict[str, Optional[int]]:
        """字段 → 0 基列索引（None＝未映射）。这是离线/追加 CSV 取列的**唯一**规则。"""
        positional = {k: i for i, k in enumerate(self.FIELDS)}
        if not self.mapping_enabled:
            if header:
                try:
                    return dict(self.resolve(header))
                except ConfigError:
                    pass
                # v0.36：部分表头（如只有三相电流 ``时间戳,A相电流,B相电流,C相电流``）——**每一列**都能识别、含时间戳
                # 和至少一个通道、且字段不齐全 → 按识别结果取列，缺的字段 None（通道按 0 播放）。
                # 含任何不可识别列名的表头仍按默认列序（兼容老文件 / 老测试的既有行为）。
                part = self._resolve_partial(header)
                if part and "timestamp" in part and len(part) == len(header) and len(set(part.values())) == len(header) \
                        and any(k != "timestamp" for k in part):
                    return {k: part.get(k) for k in self.FIELDS}
            return positional
        norm = {self._norm(h): i for i, h in enumerate(header)} if header else {}
        out: Dict[str, Optional[int]] = {}
        for k in self.FIELDS:
            spec = str(self.mapping.get(k, "") or "").strip()
            if not spec:
                out[k] = None
            elif spec.isdigit():
                out[k] = int(spec) - 1
            elif header and spec in header:
                out[k] = header.index(spec)
            elif self._norm(spec) in norm:
                out[k] = norm[self._norm(spec)]
            else:
                raise ConfigError(f"columns.mapping.{k}='{spec}' 既不是列号也不在表头中"
                                  f"（表头={header}）；无表头文件请用列号（从 1 起）")
        return out

    def looks_like_header(self, row: List[str]) -> bool:
        """首行是否为表头。未启用映射：能按名字/别名识别即表头；启用映射：按名字映射的字段能在首行找到，
        或任一按列号映射的数据列在首行不是数值。"""
        cells = [str(c).strip() for c in row]
        if not self.mapping_enabled:
            try:
                self.resolve(cells)
                return True
            except ConfigError:
                pass
            # 识别不出名字但数据列（默认列序第 2~7 列）有非数值 → 仍是表头（否则会把表头当成一行坏数据）
            for c in range(1, min(7, len(cells))):
                if cells[c] == "":
                    continue
                try:
                    float(cells[c])
                except ValueError:
                    return True
            return False
        norm = {self._norm(h) for h in cells}
        for k in self.FIELDS:
            spec = str(self.mapping.get(k, "") or "").strip()
            if not spec:
                continue
            if spec.isdigit():
                c = int(spec) - 1
                if k != "timestamp" and c < len(cells) and cells[c] != "":
                    try:
                        float(cells[c])
                    except ValueError:
                        return True
            elif spec in cells or self._norm(spec) in norm:
                return True
        return False

    def unmapped(self, lay: Dict[str, Optional[int]]) -> List[str]:
        return [k for k in self.FIELDS if lay.get(k) is None]

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
    # 离线文件（csv_file / csv_tail）文本时标的时区解释（custom_time=False 时决定曲线时间）：
    #   file_time_utc=False → 文件里的日期时间 / "0/00/00 HH:MM:SS" 按本机本地时间解释，
    #                         曲线、落盘 CSV、事件时间与文件中的时间**一致**（默认）
    #   file_time_utc=True  → 文件时标视为 UTC，显示时换算成本地时间（北京时间会比文件多 8 h）
    #   纯数字 epoch 时标是绝对时刻，不受本开关影响。
    file_time_utc: bool = False
    # 离线文件播放起点（csv_file 专用）：从文件的指定位置开始播放，之前的数据直接跳过（不参与计算）。
    #   play_start_mode: begin   从头（默认，play_start_value 忽略）
    #                    row     从第 N 条数据行开始（1 起算，不含表头）：value="120001"
    #                    seconds 跳过文件开头 N 秒的数据（按配置 fs 换算成行数）：value="30"
    #                    percent 从文件的 N% 处开始（按字节位置，再对齐到行首）：value="50"
    #                    time    从文件时标 ≥ 指定时刻的第一条数据开始：value="2026-10-12 08:00:00"
    #                            或只填时刻 "08:00:00"（与文件时标的当天时刻比较，适合 0/00/00 写法）
    play_start_mode: str = "begin"
    # 离线文件播放倍速（csv_file 专用，v0.12.2）：1.0＝按数据真实时间速率播放（1 s 数据用 1 s 墙钟），2.0＝两倍速，
    # 0＝不限速（能算多快播多快，CLI/批处理/测试默认）。按「相邻两块的间隔」限速：暂停后恢复不会突发追赶。
    file_speed: float = 0.0
    # v0.85：分路侧专用——两侧都是离线文件联动启动时，分路侧倍速是否随总线侧（共用节拍钟、严格同步）。
    # True（默认）＝随总线侧，本侧 file_speed 忽略；False＝按本侧 file_speed 独立限速（各自节拍钟，不再互锁）。总线侧忽略此项。
    file_speed_follow: bool = True
    play_start_value: str = ""
    # 离线文件播放终点（csv_file，v0.15 公共时间段用）：epoch 秒文本；块起点 ≥ 该时刻即停止（空＝播到文件尾）
    play_end_time: str = ""
    # v0.17 指定时间段播放（csv_file；每侧独立，默认不启用）：启用后 起点＝文件时标 ≥ play_window_start 的第一条
    # （空＝从数据起点）、终点＝play_window_end（空＝播到数据终点）。两侧都是离线文件且启用「公共时间段」时以公共时间段为准。
    play_window: bool = False
    play_window_start: str = ""      # "2026-10-12 08:00:00" / epoch 秒 / 只填 "08:00:00"（与文件时标当天时刻比较）
    play_window_end: str = ""        # "2026-10-12 08:10:00" / epoch 秒 / 只填 "08:10:00"

    def validate(self) -> None:
        if self.play_window:
            for lab, v in (("play_window_start", self.play_window_start), ("play_window_end", self.play_window_end)):
                if str(v or "").strip():
                    try:
                        parse_play_start("time", v)
                    except ConfigError as exc:
                        raise ConfigError(f"source.{lab}: {exc}")
            if str(self.play_window_start or "").strip() and str(self.play_window_end or "").strip():
                a, b = parse_play_start("time", self.play_window_start), parse_play_start("time", self.play_window_end)
                if a[0] == b[0] and b[1] <= a[1]:
                    raise ConfigError(f"source.play_window_end 必须晚于 play_window_start（{self.play_window_start} → {self.play_window_end}）")
        if self.kind not in SOURCE_KINDS:
            raise ConfigError(f"source.kind 必须是 {SOURCE_KINDS}（当前 {self.kind}）")
        try:
            self.file_speed = float(self.file_speed)
            if self.file_speed < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ConfigError(f"source.file_speed 必须 ≥ 0（0＝不限速；当前 {self.file_speed!r}）")
        self.file_speed_follow = bool(self.file_speed_follow)
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
    # 界面曲线分线显示开关（v0.16）：键＝图表 id（如 "ov-u"），值＝被隐藏的曲线名列表（如 ["Ub","Uc"]）；
    # 只影响显示，不影响计算/保存。随配置持久化，重开页面仍保持。
    series_hidden: Dict[str, List[str]] = field(default_factory=dict)
    # 数据来源号（v0.17）：0＝总线侧、1＝分路侧。写入所有落盘/导出 CSV 的 source_id 列；服务端按侧别强制设置。
    source_id: int = 0
    # v0.20：软件启动时自动把上次运行落盘的曲线 / 事件 / 负荷辨识事件（CSV）与最后一次电气量结果
    # （output/last_result.json，两侧共用、按 source_id 分键）读回各子界面；关闭则仅在点「加载上次数据」时读取
    autoload_last: bool = True

    def validate(self) -> None:
        try:
            self.source_id = int(self.source_id)
        except (TypeError, ValueError):
            raise ConfigError("output.source_id 必须是整数（0＝总线侧，1＝分路侧）")
        if self.source_id not in (0, 1):
            raise ConfigError(f"output.source_id 必须是 0（总线侧）或 1（分路侧），当前 {self.source_id}")
        if not isinstance(self.series_hidden, dict):
            raise ConfigError("output.series_hidden 必须是 {图表id: [曲线名, ...]} 字典")
        clean: Dict[str, List[str]] = {}
        for k, v in self.series_hidden.items():
            if v is None:
                continue
            if not isinstance(v, (list, tuple)):
                raise ConfigError(f"output.series_hidden[{k!r}] 必须是曲线名列表")
            names = [str(x) for x in v if str(x).strip()]
            if names:
                clean[str(k)] = names
        self.series_hidden = clean
        if not str(self.realtime_dir).strip():
            raise ConfigError("output.realtime_dir 不能为空")
        if self.history_hours <= 0:
            raise ConfigError(f"output.history_hours 必须 > 0（当前 {self.history_hours}）")
        if self.history_max_points < 10:
            raise ConfigError(f"output.history_max_points 必须 ≥ 10（当前 {self.history_max_points}）")
        unknown = [k for k in self.curve_save if k not in CURVE_KEYS]
        if unknown:
            raise ConfigError(f"output.curve_save 含未知曲线 {unknown}；可用：{list(CURVE_KEYS)}")
        # 缺省键补齐为 True，界面与导出按完整八键工作
        self.curve_save = {k: bool(self.curve_save.get(k, True)) for k in CURVE_KEYS}


@dataclass
class EventConfig:
    """事件判据（第 9 轮）。全部阈值可在「事件」子界面热更新；单位见各字段注释。

    通用：``enabled`` 总开关；``hysteresis`` 复归系数（越限后值回落到 limit×hysteresis 以下才算结束，防抖）；
    ``save`` 事件落盘到 ``events_dir/events_<数据日期>.csv``（开始/结束各一行）；``max_log`` 内存保留条数。
    """

    enabled: bool = True
    hysteresis: float = 0.95
    save: bool = True
    events_dir: str = "output/events"
    max_log: int = 2000
    # 基波相量超限：电压按相对额定相电压 u_nom（V）的百分比，电流按绝对值（A）。
    # limits_secondary=True（默认）：u_nom / i1_high 按**二次侧**填写（数据字典口径 57.74 V / 5 A），
    # 若 transform.enabled 则检测时自动乘 PT/CT 折算到一次侧，与计算结果同口径比较；False＝直接按计算结果的单位填。
    limits_secondary: bool = True
    u_nom: float = 57.74                    # 100/√3：二次侧额定相电压；接线电压口径请改 100
    u1_high_pct: float = 110.0
    u1_low_pct: float = 90.0
    i1_high: float = 6.0                    # 二次侧 5 A 额定 → 120%
    # 谐波相量超限：任一相任一次含有率 HR_h（% of 基波）或 THD 超过
    hr_u_limit_pct: float = 5.0
    hr_i_limit_pct: float = 10.0
    thd_u_limit_pct: float = 5.0
    thd_i_limit_pct: float = 10.0
    # 间谐波相量超限：任一相任一间谐波组有效值相对基波的百分比
    ih_u_limit_pct: float = 1.0
    ih_i_limit_pct: float = 2.0
    # 频率超限（Hz）与频率变化率超限（Hz/s，取相邻两次基波频率估计的差分）
    f_low: float = 49.5
    f_high: float = 50.5
    rocof_limit: float = 1.0
    # 功率振荡：对最近 osc_window_s 内的总有功 P 序列去趋势后谱分析，
    # 在 [osc_f_min, osc_f_max] Hz 内主导分量峰峰值 ≥ osc_limit_pct（% of |P 均值|）且 ≥ osc_min_w（W）判为振荡
    osc_window_s: float = 10.0
    osc_f_min: float = 0.1
    osc_f_max: float = 2.5
    osc_limit_pct: float = 5.0
    osc_min_w: float = 1.0
    osc_min_points: int = 8

    def validate(self) -> None:
        if not (0.5 <= self.hysteresis <= 1.0):
            raise ConfigError(f"events.hysteresis 必须在 0.5~1.0（当前 {self.hysteresis}）")
        if self.u_nom <= 0:
            raise ConfigError("events.u_nom 必须 > 0")
        if self.u1_low_pct >= self.u1_high_pct:
            raise ConfigError("events.u1_low_pct 必须小于 u1_high_pct")
        if self.f_low >= self.f_high:
            raise ConfigError("events.f_low 必须小于 f_high")
        for k in ("i1_high", "hr_u_limit_pct", "hr_i_limit_pct", "thd_u_limit_pct", "thd_i_limit_pct",
                  "ih_u_limit_pct", "ih_i_limit_pct", "rocof_limit", "osc_window_s", "osc_limit_pct", "osc_min_w"):
            if float(getattr(self, k)) <= 0:
                raise ConfigError(f"events.{k} 必须 > 0（当前 {getattr(self, k)}）")
        if not (0 < self.osc_f_min < self.osc_f_max):
            raise ConfigError("events.osc_f_min / osc_f_max 必须满足 0 < f_min < f_max")
        if self.osc_min_points < 4:
            raise ConfigError("events.osc_min_points 必须 ≥ 4")
        if self.max_log < 10:
            raise ConfigError("events.max_log 必须 ≥ 10")
        if not str(self.events_dir).strip():
            raise ConfigError("events.events_dir 不能为空")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EventConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------- 负荷辨识（第 12 轮）
NILM_CHANNELS = ("total", "A", "B", "C")
NILM_QUANTITIES = ("auto", "p", "i")          # v0.36：检测量 有功 / 电流有效值 / 自动

# 各事件检测算法的默认参数（单位：W＝有功功率；cycles＝周波数）。键名即界面/配置里的参数名。
NILM_ALGO_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # 每个算法的绝对阈值分两套：``*_w``（W，P 口径＝有功检测时用）与 ``*_a``（A，I 口径＝电流有效值检测时用，v0.37）。
    # 检测器按当前检测量只取其中一套（见 nilm.NilmDetector._evaluate），另一套不参与。A 套默认值按二次侧
    # 单相 ≈6 A（1000 W / 3 相 / 57.74 V / pf 0.9）给出，与 W 套默认值在同一相对量级；一次侧请靠 rel_tol_pct / min_delta_pct。
    # 阈值差分：相邻周波差分超过门槛即判为事件起点，之后连续 settle_cycles 个周波波动 < tol 即为终点
    "threshold":    {"enabled": True, "min_delta_w": 50.0, "settle_cycles": 5, "settle_tol_w": 20.0, "max_rise_cycles": 40,
                     "min_delta_a": 0.3, "settle_tol_a": 0.1},
    # 双滑窗均值差：|mean(后窗) − mean(前窗)| 的局部极大值 ≥ min_delta 且 ≥ k_sigma×前窗标准差
    "two_window":   {"enabled": True, "pre_cycles": 10, "post_cycles": 10, "min_delta_w": 50.0, "k_sigma": 3.0,
                     "min_delta_a": 0.3},
    # CUSUM 累积和（双侧）：相对参考均值的累积偏差超过 threshold 触发；drift 为允许漂移（k）
    "cusum":        {"enabled": True, "drift_w": 10.0, "threshold_w": 200.0, "min_delta_w": 50.0, "settle_cycles": 5,
                     "drift_a": 0.05, "threshold_a": 1.0, "min_delta_a": 0.3},
    # GLR 广义似然比（高斯均值突变）：窗内各候选点的对数似然比 ≥ threshold 且幅值 ≥ min_delta；noise 为噪声 σ 下限
    "glr":          {"enabled": True, "window_cycles": 15, "threshold": 25.0, "min_delta_w": 50.0, "noise_w": 10.0, "settle_cycles": 5,
                     "min_delta_a": 0.3, "noise_a": 0.05},
    # 稳态分段（Hart 1992）：连续 ≥ min_steady_cycles 个周波极差 ≤ tol 为一个稳态；相邻稳态均值差 ≥ min_delta 即事件
    "steady_state": {"enabled": True, "tol_w": 30.0, "min_steady_cycles": 10, "min_delta_w": 50.0, "max_transient_cycles": 100,
                     "tol_a": 0.15, "min_delta_a": 0.3},
    # 中值滤波差分：先 median_cycles 点中值滤波去尖峰，再按阈值差分法检测（对暂态尖峰/缺口不敏感）
    "median_diff":  {"enabled": True, "median_cycles": 5, "min_delta_w": 50.0, "settle_cycles": 5, "settle_tol_w": 20.0, "max_rise_cycles": 40,
                     "min_delta_a": 0.3, "settle_tol_a": 0.1},
    # v0.90：设备画像匹配（《设备画像提取与总线侧负荷辨识事件检测算法方案》基础版）：画像文件路径在 nilm.profile_path；
    #   候选＝稳健双滑窗（前后窗长取画像 pre/post，门槛 k_sigma×噪声 且 ≥ 画像幅值一半）→ 特征向量与启动/停止画像的对角马氏距离 D²
    #   → 置信度 exp(−D²/2d)。d2_max＝每维平均 D² 上限；min_confidence＝最低置信度；margin＝最优/次优 D² 比下限（区分度）；
    #   lambda_rel＝协方差收缩系数；state_check＝1 启用设备状态机（OFF→START / ON→STOP 合理，否则置信度减半并标记）。默认不启用。
    "profile":      {"enabled": False, "d2_max": 9.0, "min_confidence": 0.3, "k_sigma": 4.0, "margin": 1.5, "lambda_rel": 0.1, "state_check": 1,
                     "phase_map": 1, "max_scale": 8},   # v0.99.15：多尺度候选最大倍数（1＝单尺度）；v0.99.6：总线/设备侧相序映射 1 ABC·2 ACB·3 BAC·4 BCA·5 CAB·6 CBA·0 自动
}
# 逐周波标量序列上的 6 种突变检测算法（画像匹配是多特征算法，不在其中）
NILM_SCALAR_ALGOS = ("threshold", "two_window", "cusum", "glr", "steady_state", "median_diff")
# W 参数 → I 口径下对应的 A 参数（算法函数始终读 *_w 键；I 口径时检测器用 *_a 的值覆盖 *_w 再调用）
NILM_W_TO_A = {"min_delta_w": "min_delta_a", "settle_tol_w": "settle_tol_a", "tol_w": "tol_a",
               "drift_w": "drift_a", "noise_w": "noise_a", "threshold_w": "threshold_a"}
NILM_ALGO_NAMES = {"threshold": "阈值差分", "two_window": "双滑窗均值差", "cusum": "CUSUM 累积和",
                   "glr": "GLR 广义似然比", "steady_state": "稳态分段(Hart)", "median_diff": "中值滤波差分",
                   "profile": "设备画像匹配"}


@dataclass
class NilmConfig:
    """负荷辨识 · 事件检测（第 12 轮）。对**逐周波**有功/无功/电流序列做突变检测。

    ``channels``：检测对象，total＝三相总有功，A/B/C＝分相有功；``window_cycles``：参与检测与界面显示的周波窗长；
    ``min_gap_cycles``：同一算法同一对象两次事件之间的最小间隔（去重）；``algorithms``：各算法参数（见 NILM_ALGO_DEFAULTS）。
    事件落盘 ``nilm_dir/nilm_events_<数据日期>.csv``。阈值单位为 W，按**计算口径**（启用 PT/CT 时为一次侧）填写。
    """

    enabled: bool = True
    save: bool = True
    nilm_dir: str = "output/nilm"
    max_log: int = 5000
    channels: List[str] = field(default_factory=lambda: ["total"])
    window_cycles: int = 300
    min_gap_cycles: int = 10
    # 相对门槛（按窗内 |P| 中位数的百分比，与各算法的绝对 W 值取较大者）：
    #   rel_tol_pct 作用于「容差/噪声/漂移」类参数（settle_tol_w / tol_w / drift_w / noise_w / threshold_w），
    #   min_delta_pct 作用于各算法的 min_delta_w。这样同一套默认值在二次侧（W 级）和一次侧（MW 级）都能用。
    rel_tol_pct: float = 1.0
    min_delta_pct: float = 0.0
    # v0.36：检测量。p＝逐周波有功（需电压+电流）；i＝逐周波电流有效值（只需电流，数据源无电压时用）；
    #   auto＝数据源电压全为 0/未映射时自动用 i，否则用 p。i 口径下各算法用 ``*_a``（A）这套绝对阈值，
    #   W 套不参与；rel_tol_pct / min_delta_pct 同样按窗内 |I| 中位数折算后与 A 套取较大者（v0.37）。
    quantity: str = "auto"
    # v0.87：自适应算法参数（v0.88 起总线侧、分路侧均可启用）。true＝运行时按当前周波窗数据自动推导各算法全部数值参数
    #   （噪声 σ / 稳定周波 / 最短稳态 / 暂态时长 / 最小幅值 / 各门限，见 nilm_auto.py），下方各算法数值与 rel_tol_pct /
    #   min_delta_pct 不再参与（算法 enabled 仍由配置决定）；两侧各自独立配置、各自按本侧数据推导（v0.88）。
    auto_params: bool = False
    # v0.99.17：性能。eval_every_cycles＝每进多少个新周波评估一次全部算法（1＝每块都评估，旧行为；默认 10≈0.2 s，事件时刻不变、
    #   只影响上报延迟）；auto_stats_every_cycles＝自适应公共统计量（σ/Allan/τ…）每多少周波重算一次（默认 50≈1 s）。
    eval_every_cycles: int = 10
    auto_stats_every_cycles: int = 50
    # v0.90：设备画像文件路径（tools/nilm_profile.py 或数据处理页「设备画像提取」生成的 JSON；相对路径相对仓库根）。
    #   空＝未加载画像，algorithms.profile.enabled 即使为 true 也不检测并在 summary.notes 说明。
    profile_path: str = ""
    algorithms: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {k: dict(v) for k, v in NILM_ALGO_DEFAULTS.items()})

    def params(self, algo: str) -> Dict[str, Any]:
        base = dict(NILM_ALGO_DEFAULTS[algo])
        base.update({k: v for k, v in (self.algorithms.get(algo) or {}).items() if k in base})
        return base

    def validate(self) -> None:
        self.auto_params = bool(self.auto_params) if not isinstance(self.auto_params, str) else self.auto_params.strip().lower() in ("1", "true", "on", "yes")
        self.quantity = str(self.quantity or "auto").strip().lower()
        self.profile_path = str(self.profile_path or "").strip()
        if self.quantity not in NILM_QUANTITIES:
            raise ConfigError(f"nilm.quantity 必须是 {NILM_QUANTITIES} 之一（当前 {self.quantity!r}）")
        if not self.channels or any(c not in NILM_CHANNELS for c in self.channels):
            raise ConfigError(f"nilm.channels 必须是 {NILM_CHANNELS} 的非空子集（当前 {self.channels}）")
        self.eval_every_cycles = max(1, int(float(getattr(self, "eval_every_cycles", 10) or 1)))
        self.auto_stats_every_cycles = max(1, int(float(getattr(self, "auto_stats_every_cycles", 50) or 1)))
        if int(self.window_cycles) < 30:
            raise ConfigError(f"nilm.window_cycles 必须 ≥ 30（当前 {self.window_cycles}）")
        if int(self.min_gap_cycles) < 0:
            raise ConfigError("nilm.min_gap_cycles 必须 ≥ 0")
        if int(self.max_log) < 10:
            raise ConfigError("nilm.max_log 必须 ≥ 10")
        if not (0 <= float(self.rel_tol_pct) <= 50):
            raise ConfigError(f"nilm.rel_tol_pct 必须在 0~50（当前 {self.rel_tol_pct}；它是占窗内 |P| 中位数的百分比，不是 W）")
        if not (0 <= float(self.min_delta_pct) <= 100):
            raise ConfigError(f"nilm.min_delta_pct 必须在 0~100（当前 {self.min_delta_pct}；它是占窗内 |P| 中位数的百分比，不是 W；只用各算法绝对值请填 0）")
        if not str(self.nilm_dir).strip():
            raise ConfigError("nilm.nilm_dir 不能为空")
        unknown = [a for a in self.algorithms if a not in NILM_ALGO_DEFAULTS]
        if unknown:
            raise ConfigError(f"nilm.algorithms 含未知算法 {unknown}；可用：{list(NILM_ALGO_DEFAULTS)}")
        for a in NILM_ALGO_DEFAULTS:
            prm = self.params(a)
            for k, v in prm.items():
                if k == "enabled":
                    continue
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    raise ConfigError(f"nilm.algorithms.{a}.{k} 必须是数值（当前 {v!r}）")
                if fv <= 0 and not (a == "profile" and k in ("state_check", "phase_map")):      # v0.90：state_check 允许 0（关闭状态机）；v0.99.6：phase_map 0＝自动
                    raise ConfigError(f"nilm.algorithms.{a}.{k} 必须 > 0（当前 {v}）")
                if a == "profile" and k == "phase_map" and (int(fv) != fv or not (0 <= fv <= 6)):
                    raise ConfigError(f"nilm.algorithms.profile.phase_map 必须是 0（自动）或 1..6（1 ABC·2 ACB·3 BAC·4 BCA·5 CAB·6 CBA），当前 {v}")
                if k.endswith("cycles") and int(fv) != fv:
                    raise ConfigError(f"nilm.algorithms.{a}.{k} 必须是整数周波数（当前 {v}）")
            if a in ("threshold", "median_diff") and int(prm["max_rise_cycles"]) < int(prm["settle_cycles"]):
                raise ConfigError(f"nilm.algorithms.{a}.max_rise_cycles 必须 ≥ settle_cycles")
        need = max(int(self.params("glr")["window_cycles"]) * 2 + 2,
                   int(self.params("two_window")["pre_cycles"]) + int(self.params("two_window")["post_cycles"]) + 2,
                   int(self.params("steady_state")["min_steady_cycles"]) * 2 + 2)
        if int(self.window_cycles) < need:
            raise ConfigError(f"nilm.window_cycles={self.window_cycles} 小于算法所需的最小窗长 {need}（GLR 2×window / 双滑窗 pre+post / 稳态 2×min_steady）")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NilmConfig":
        obj = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k != "algorithms"})
        algos = d.get("algorithms")
        if isinstance(algos, dict):
            merged = {k: dict(v) for k, v in NILM_ALGO_DEFAULTS.items()}
            for a, prm in algos.items():
                if a in merged and isinstance(prm, dict):
                    merged[a].update({k: v for k, v in prm.items() if k in merged[a]})
            obj.algorithms = merged
        return obj


@dataclass
class BranchConfig:
    """分路侧设备数据源的挂接（第 14 轮）。只在**总线侧**配置里有意义。

    分路侧本身是一份完整、独立的 AppConfig（数据源 / 采样 / 变比 / 窗口 / 事件 / 负荷辨识 全部独立），
    存放在 ``config_path``；``enabled=True`` 时总线侧「启动播放」会同时启动分路侧。
    """

    enabled: bool = False
    config_path: str = "configs/branch.json"
    label: str = "分路侧设备"
    # 第 15 轮：跨侧对齐参数（只影响 /api/compare 的时间轴对齐，不改任何一侧的计算）
    time_offset_s: float = 0.0     # 分路侧时标 + offset ≈ 总线侧时标（两份文件起点不同步时用）
    align_tol_s: float = 0.0       # 配对容差（秒）；0＝自动＝max(两侧输出步长)×0.6
    # v0.15：只播放两侧文件的公共时间段（联动启动时两侧都从公共起点播到公共终点）
    common_window: bool = False
    # v0.33：隐藏分路侧界面——True 时「实时监测」「事件与分析」各子界面右侧的分路侧列整体隐藏（分路侧仍照常计算 / 落盘，
    # 只是不在这些页面显示）；False 时按 enabled 显示。总览 / 跨侧对比 / 数据源与控制 不受影响。
    hide_ui: bool = False
    common_start: str = ""         # 公共时间段内的自定义播放起始时间（本地时间文本 / epoch 秒）；空＝公共起点
    common_end: str = ""           # v0.17：公共时间段内的自定义播放结束时间；空＝公共终点

    def validate(self) -> None:
        if not str(self.config_path).strip():
            raise ConfigError("branch.config_path 不能为空")
        self.hide_ui = bool(self.hide_ui)
        try:
            self.time_offset_s = float(self.time_offset_s)
            self.align_tol_s = float(self.align_tol_s)
        except (TypeError, ValueError):
            raise ConfigError("branch.time_offset_s / align_tol_s 必须是数字")
        if self.align_tol_s < 0:
            raise ConfigError("branch.align_tol_s 不能为负")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BranchConfig":
        keep = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**keep)


@dataclass
class ProcessingConfig:
    """v0.34：数据处理子界面（离线 CSV 重采样）的参数。

    ``error_window_s``：重采样前后相对误差的统计时间窗（秒）。重采样完成后按该窗长把原始文件与输出文件
    对齐切窗，逐窗逐通道计算 RMS 相对误差与波形相对误差（NRMSE），写入 ``<输出名>_err.csv``。
    ``error_report=False`` 时不计算、不生成误差文件。
    """

    error_report: bool = True
    error_window_s: float = 1.0

    def validate(self) -> None:
        self.error_report = bool(self.error_report)
        try:
            self.error_window_s = float(self.error_window_s)
        except (TypeError, ValueError):
            raise ConfigError("processing.error_window_s 必须是数字（秒）")
        if not (self.error_window_s > 0) or self.error_window_s > 3600:
            raise ConfigError("processing.error_window_s 必须在 (0, 3600] 秒之间")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProcessingConfig":
        keep = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**keep)


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
    events: EventConfig = field(default_factory=EventConfig)
    nilm: NilmConfig = field(default_factory=NilmConfig)
    branch: BranchConfig = field(default_factory=BranchConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
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
        self.columns.validate()
        self.output.validate()
        self.events.validate()
        self.nilm.validate()
        self.branch.validate()
        self.processing.validate()
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
            ("events", EventConfig), ("nilm", NilmConfig), ("branch", BranchConfig),
            ("processing", ProcessingConfig),
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


def load_or_default(path: Optional[str], strict: bool = False) -> AppConfig:
    """存在则加载，否则返回默认配置（CLI/服务启动用）。

    v0.92.3：``strict=True``（命令行工具显式传入 --config 时）——文件不存在直接报 ConfigError，而不是悄悄退回出厂配置
    （曾导致用户传错路径 config/ vs configs/ 后，回放用的是默认配置：PT/CT 启用、6 种算法全开、profile 关闭，却看不出来）。
    """
    if path and os.path.isfile(path):
        return AppConfig.load(path)
    if path and strict:
        hint = ""
        alt = [c for c in (path.replace("config/", "configs/", 1), path.replace("config\\", "configs\\", 1)) if c != path and os.path.isfile(c)]
        if alt:
            hint = f"；是否想用 {alt[0]}？"
        raise ConfigError(f"配置文件不存在：{path}（当前目录 {os.getcwd()}）{hint}")
    return AppConfig().validate()
