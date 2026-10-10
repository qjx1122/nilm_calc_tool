"""elec_tool —— 电力系统电气量计算工具（算法核心包）

设计原则：
1. **算法核心与 UI 物理隔离**：本包不依赖任何 Web/GUI 库（仅 numpy），可被 Web 壳、Qt 壳、CLI 复用。
2. **全部口径可配置**：PT/CT 变比、采样率、额定频率、每个电气量的计算窗长/步长/截断策略。
3. **不臆断数据事实**：列名、编码、时间戳格式均自适应；无法确定时报错并给出明确提示。
"""

__version__ = "0.1.0"

from .config import (  # noqa: F401
    AppConfig,
    ColumnMap,
    HarmonicConfig,
    PowerConfig,
    SamplingConfig,
    SourceConfig,
    TransformConfig,
    WindowSpec,
    QUANTITY_KEYS,
)
from .blocks import SampleBlock, FrameBuffer  # noqa: F401

__all__ = [
    "AppConfig",
    "ColumnMap",
    "HarmonicConfig",
    "PowerConfig",
    "SamplingConfig",
    "SourceConfig",
    "TransformConfig",
    "WindowSpec",
    "QUANTITY_KEYS",
    "SampleBlock",
    "FrameBuffer",
    "__version__",
]
