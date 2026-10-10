"""CSV / 时间戳解析测试（用户给定格式 + 各种真实世界脏情况）。"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, ColumnMap, SamplingConfig
from elec_tool.sources.parsing import (ParseError, detect_encoding, parse_rows, parse_timestamps,
                                       read_header, check_fs)
from tests.conftest import FS, HEADER_CN, HEADER_EN, write_csv


def test_user_format_header_detected(csv_factory, tmp_path):
    """用户给定格式：时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流"""
    art = csv_factory(str(tmp_path / "a.csv"), duration_s=0.5)
    header, enc = read_header(art["path"], "auto", ",")
    assert header == HEADER_CN
    assert enc.startswith("utf-8")


def test_parse_values_and_shape(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "b.csv"), duration_s=0.5)
    from elec_tool.sources import CsvFileSource
    src = CsvFileSource(base_cfg, path=art["path"], block_samples=100000)
    src.open()
    blk = src.read()
    assert blk is not None and blk.n == art["t"].size
    # 二次侧原值（未乘 PT/CT）应与注入值一致
    np.testing.assert_allclose(blk.u, art["u"], rtol=1e-5, atol=1e-4)
    np.testing.assert_allclose(blk.i, art["i"], rtol=1e-5, atol=1e-4)
    assert blk.scaled is False
    src.close()
    assert src.exhausted


def test_timestamp_modes(csv_factory, tmp_path, base_cfg):
    """epoch 秒 / epoch 毫秒 / ISO 字符串 三种时标都要能解析，且推算 fs≈6400。"""
    from elec_tool.sources import CsvFileSource
    for mode in ("epoch", "ms", "iso"):
        art = csv_factory(str(tmp_path / f"ts_{mode}.csv"), duration_s=0.3, ts_mode=mode)
        src = CsvFileSource(base_cfg, path=art["path"], block_samples=100000)
        src.open()
        blk = src.read()
        info = src.info()
        assert blk is not None and blk.n > 0
        assert abs(info["fs_est_from_timestamps"] - FS) / FS < 2e-3, (mode, info)
        # 时间单调递增
        assert np.all(np.diff(blk.t) > 0)
        src.close()


def test_english_header(csv_factory, tmp_path, base_cfg):
    from elec_tool.sources import CsvFileSource
    art = csv_factory(str(tmp_path / "en.csv"), duration_s=0.3, header=HEADER_EN)
    src = CsvFileSource(base_cfg, path=art["path"], block_samples=100000)
    src.open()
    blk = src.read()
    assert blk is not None and blk.n > 0
    np.testing.assert_allclose(blk.u[0], art["u"][0], rtol=1e-5, atol=1e-4)
    src.close()


def test_gbk_encoding(csv_factory, tmp_path, base_cfg):
    """中文表头 + GBK 编码（Windows 采集程序常见）必须能自动识别。"""
    from elec_tool.sources import CsvFileSource
    art = csv_factory(str(tmp_path / "gbk.csv"), duration_s=0.3, encoding="gbk")
    assert detect_encoding(art["path"]) in ("gbk", "gb18030")
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.columns.encoding = "auto"
    cfg.validate()
    src = CsvFileSource(cfg, path=art["path"], block_samples=100000)
    src.open()
    blk = src.read()
    assert blk is not None and blk.n > 0
    src.close()


def test_no_header_file(csv_factory, tmp_path, base_cfg):
    """无表头文件：按用户给定列序解析。"""
    from elec_tool.sources import CsvFileSource
    art = csv_factory(str(tmp_path / "nohdr.csv"), duration_s=0.3, header=[])
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.columns.has_header = False
    cfg.validate()
    src = CsvFileSource(cfg, path=art["path"], block_samples=100000)
    src.open()
    blk = src.read()
    assert blk is not None and blk.n > 0
    np.testing.assert_allclose(blk.u[0], art["u"][0], rtol=1e-5, atol=1e-4)
    src.close()


def test_nan_and_bad_cells_handled(csv_factory, tmp_path, base_cfg):
    """缺测/非数值单元：线性插值补齐并在 notes 中告警（不允许静默变 0）。"""
    from elec_tool.sources import CsvFileSource
    art = csv_factory(str(tmp_path / "nan.csv"), duration_s=0.3, inject_nan=[10, 11, 12])
    src = CsvFileSource(base_cfg, path=art["path"], block_samples=100000)
    src.open()
    blk = src.read()
    assert blk is not None
    assert np.all(np.isfinite(blk.u)), "NaN 必须被插值处理"
    notes = " ".join(src.info().get("notes") or [])
    assert ("缺测" in notes) or ("非数值" in notes) or ("插值" in notes)
    src.close()


def test_missing_file_raises_actionable(tmp_path, base_cfg):
    from elec_tool.sources import CsvFileSource
    src = CsvFileSource(base_cfg, path=str(tmp_path / "nope.csv"))
    with pytest.raises(ParseError) as ei:
        src.open()
    assert "不存在" in str(ei.value)


def test_empty_file_raises(tmp_path, base_cfg):
    from elec_tool.sources import CsvFileSource
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    src = CsvFileSource(base_cfg, path=str(p))
    with pytest.raises(ParseError):
        src.open()


def test_check_fs_warns_on_mismatch(base_cfg):
    _, notes = check_fs(6000.0, base_cfg.sampling)
    assert any("采样率" in n and "⚠" in n for n in notes)
    _, notes2 = check_fs(6400.01, base_cfg.sampling)
    assert any("校验通过" in n for n in notes2)


def test_parse_timestamps_relative_seconds():
    info = parse_timestamps([f"{k/6400:.9f}" for k in range(100)], "auto")
    assert info.mode == "relative_s"
    np.testing.assert_allclose(np.diff(info.t), 1 / 6400.0, rtol=1e-6)


def test_parse_timestamps_bad_value_raises():
    with pytest.raises(ParseError) as ei:
        parse_timestamps(["2026-10-10 04:00:00", "not-a-time"], "auto")
    assert "无法解析" in str(ei.value)


def test_block_invariants():
    t = np.arange(10, dtype=np.float64)
    u = np.ones((3, 10)); i = np.ones((3, 10)) * 2
    blk = SampleBlock(t=t, u=u, i=i)
    assert blk.n == 10 and blk.tail(4).n == 4
    assert blk.slice(2, 5).n == 3
    cat = SampleBlock.concat([blk.tail(3), blk.tail(2)])
    assert cat.n == 5
    with pytest.raises(ValueError):
        SampleBlock(t=t, u=np.ones((2, 10)), i=i)
    with pytest.raises(ValueError):
        SampleBlock(t=t[:5], u=u, i=i)
