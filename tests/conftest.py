"""pytest 共用夹具。"""

from __future__ import annotations

import csv
import math
import os
import sys
import time
from datetime import datetime as _dt
from typing import Dict, List, Optional, Sequence

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elec_tool.config import (AppConfig, ColumnMap, HarmonicConfig, PowerConfig, QUANTITY_KEYS,  # noqa: E402
                              SamplingConfig, SourceConfig, TransformConfig, WindowSpec)
from elec_tool.selftest import HarmSpec, build_signal, expected_values  # noqa: E402

FS = 6400.0
F_NOM = 50.0
PT = 100.0
CT = 15.0

HEADER_CN = ["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"]
HEADER_EN = ["timestamp", "Ua", "Ia", "Ub", "Ib", "Uc", "Ic"]


@pytest.fixture(autouse=True)
def _isolate_realtime_dir(tmp_path, monkeypatch):
    """实时落盘（output.realtime_save 默认开）在测试里一律写到临时目录，不污染仓库 output/。"""
    monkeypatch.setenv("ELEC_TOOL_REALTIME_DIR", str(tmp_path / "realtime"))
    monkeypatch.setenv("ELEC_TOOL_EVENTS_DIR", str(tmp_path / "events"))      # 第 9 轮：事件 CSV 同样隔离
    monkeypatch.setenv("ELEC_TOOL_NILM_DIR", str(tmp_path / "nilm"))          # 第 12 轮：负荷事件 CSV 隔离
    yield


@pytest.fixture
def base_cfg() -> AppConfig:
    """用户给定工况：fs=6400、PT=100、CT=15、50Hz、谐波 2~50。"""
    return AppConfig(
        sampling=SamplingConfig(fs=FS, f_nom=F_NOM),
        transform=TransformConfig(pt_ratio=PT, ct_ratio=CT),
        harmonic=HarmonicConfig(order_min=2, order_max=50),
        power=PowerConfig(),
        windows={k: WindowSpec(length_s=1.0) for k in
                 QUANTITY_KEYS},
    ).validate()


@pytest.fixture
def default_specs() -> List[HarmSpec]:
    """平衡三相 + 3/5/7/11/13 次谐波，基波 φ=30°（感性）。"""
    u1 = 100.0 / math.sqrt(3)     # 二次侧相电压 57.735V
    i1 = 5.0                      # 二次侧相电流 5A
    return [
        HarmSpec(1, u1, i1, phi_deg=30.0),
        HarmSpec(3, 0.08 * u1, 0.10 * i1, phi_deg=45.0),
        HarmSpec(5, 0.06 * u1, 0.08 * i1, phi_deg=60.0),
        HarmSpec(7, 0.03 * u1, 0.05 * i1, phi_deg=20.0),
        HarmSpec(11, 0.015 * u1, 0.02 * i1, phi_deg=10.0),
        HarmSpec(13, 0.010 * u1, 0.015 * i1, phi_deg=80.0),
    ]


def write_csv(path: str, t: np.ndarray, u: np.ndarray, i: np.ndarray,
              header: Optional[Sequence[str]] = None, encoding: str = "utf-8",
              ts_mode: str = "epoch", fmt: str = "%.6f",
              inject_nan: Optional[List[int]] = None) -> str:
    """按用户给定列格式写 CSV（可选英文表头 / GBK 编码 / ISO 时间戳 / 注入缺测）。"""
    header = list(header if header is not None else HEADER_CN)
    spec = fmt.lstrip("%") or ".6f"          # printf 风格 → f-string 格式说明符
    num = lambda v: format(float(v), spec)   # noqa: E731
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding=encoding, newline="") as fh:
        w = csv.writer(fh)
        if header:
            w.writerow(header)
        for k in range(t.size):
            if ts_mode == "epoch":
                ts = f"{t[k]:.9f}"
            elif ts_mode == "ms":
                ts = f"{t[k]*1000:.3f}"
            elif ts_mode == "iso":
                ts = _dt.fromtimestamp(t[k]).strftime("%Y-%m-%d %H:%M:%S.%f")   # µs 精度
            elif ts_mode == "none":
                ts = f"{k / FS:.9f}"
            elif ts_mode == "clock":
                # 用户 2026-10-12 给出的采集器写法：日期段全 0、只有当天时刻、小数 4 位（0.1ms，截断）
                tod = float(t[k]) % 86400.0
                hh, mm = int(tod // 3600), int(tod % 3600 // 60)
                ss = tod % 60
                ts = f"0/00/00 {hh:02d}:{mm:02d}:{int(ss):02d}.{int((ss - int(ss)) * 10000):04d}"
            else:
                raise ValueError(ts_mode)
            row = [ts, num(u[0, k]), num(i[0, k]), num(u[1, k]),
                   num(i[1, k]), num(u[2, k]), num(i[2, k])]
            if inject_nan and k in inject_nan:
                row[1] = ""            # A 相电压缺测
                row[4] = "NaN"
            w.writerow(row)
    return path


@pytest.fixture
def csv_factory(default_specs):
    """生成解析信号并写成 CSV 的工厂夹具。"""
    def _make(path: str, duration_s: float = 1.2, f: float = F_NOM, header=None,
              encoding: str = "utf-8", ts_mode: str = "epoch", noise: float = 0.0,
              inject_nan: Optional[List[int]] = None, specs=None,
              u_dc: float = 0.0, neg_seq: float = 0.0) -> Dict[str, object]:
        sp = specs if specs is not None else default_specs
        t, u, i = build_signal(sp, FS, duration_s, f, noise_ratio=noise,
                               u_dc=u_dc, neg_seq_ratio=neg_seq)
        write_csv(path, t, u, i, header=header, encoding=encoding, ts_mode=ts_mode,
                  inject_nan=inject_nan)
        return {"path": path, "t": t, "u": u, "i": i, "specs": sp, "f": f,
                "expected": expected_values(sp, TransformConfig(pt_ratio=PT, ct_ratio=CT), FS, f)}
    return _make
