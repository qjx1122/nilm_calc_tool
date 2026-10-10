"""数据源抽象：离线文件 + 实时采集统一接口（需求④）。

所有源实现同一个协议：
    open() -> None
    read() -> Optional[SampleBlock]     # 取一块（二次侧值，未做 PT/CT 变换）
    close() -> None
    exhausted -> bool                   # 离线源读完为 True；实时源正常情况恒 False
    info() -> dict                      # 源状态（供 UI 展示与诊断）

新增采集通道（如 Modbus/IEC 61850/私有二进制协议）只需实现本接口，
上层引擎与算法**零改动**——这是「多算法模块物理隔离」的数据侧对应做法。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..blocks import SampleBlock


class DataSource:
    """数据源基类（协议定义）。"""

    kind: str = "abstract"

    def open(self) -> None:
        raise NotImplementedError

    def read(self) -> Optional[SampleBlock]:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    @property
    def exhausted(self) -> bool:
        return False

    def info(self) -> Dict[str, Any]:
        return {"kind": self.kind}

    # 上下文管理器支持
    def __enter__(self) -> "DataSource":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
