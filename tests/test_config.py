"""配置层测试：默认值、校验、序列化、列名映射。"""

from __future__ import annotations

import json
import math
import os

import pytest

from elec_tool.config import (AppConfig, ColumnMap, ConfigError, HarmonicConfig, PowerConfig,
                              QUANTITY_KEYS, SamplingConfig, SourceConfig, TransformConfig,
                              WindowSpec, default_windows, load_or_default)
from tests.conftest import HEADER_CN, HEADER_EN


def test_defaults_match_user_spec():
    """默认配置必须与用户给定工况一致（fs=6400 / PT=100 / CT=15 / 2~50 次）。"""
    cfg = AppConfig().validate()
    assert cfg.sampling.fs == 6400.0
    assert cfg.sampling.f_nom == 50.0
    assert cfg.transform.pt_ratio == 100.0
    assert cfg.transform.ct_ratio == 15.0
    assert cfg.harmonic.order_min == 2 and cfg.harmonic.order_max == 50
    assert set(QUANTITY_KEYS) <= set(cfg.windows)
    # 128 点/周波，50 次谐波 2500Hz < Nyquist 3200Hz（不混叠）
    assert cfg.sampling.samples_per_cycle == 128.0
    assert cfg.harmonic.order_max * cfg.sampling.f_nom < cfg.sampling.f_nyquist


def test_power_ratio():
    assert TransformConfig(pt_ratio=100.0, ct_ratio=15.0).power_ratio == 1500.0


@pytest.mark.parametrize("mutate,msg", [
    (lambda c: setattr(c.sampling, "fs", 0), "fs"),
    (lambda c: setattr(c.sampling, "f_nom", 4000), "f_nom"),
    (lambda c: setattr(c.sampling, "f_min", 60), "f_min"),
    (lambda c: setattr(c.transform, "pt_ratio", 0), "PT/CT"),
    (lambda c: setattr(c.transform, "voltage_input", "xxx"), "voltage_input"),
    (lambda c: setattr(c.harmonic, "order_max", 200), "混叠"),
    (lambda c: setattr(c.power, "apparent", "xxx"), "apparent"),
    (lambda c: setattr(c.power, "reactive", "xxx"), "reactive"),
    (lambda c: setattr(c.power, "three_phase_mode", "three_wire"), "暂不支持"),
    (lambda c: setattr(c.source, "kind", "modbus"), "source.kind"),
    (lambda c: setattr(c.source, "kind", "csv_file"), "source.path"),
])
def test_validation_errors_are_actionable(mutate, msg):
    """非法配置必须报错，且报错信息里带可执行的修复线索。"""
    cfg = AppConfig()
    mutate(cfg)
    with pytest.raises(ConfigError) as ei:
        cfg.validate()
    assert msg in str(ei.value)


def test_harmonic_nyquist_limit_message():
    """fs=6400 时最高可分析 63 次；配到 100 次必须给出明确上限提示。"""
    cfg = AppConfig()
    cfg.harmonic.order_max = 100
    with pytest.raises(ConfigError) as ei:
        cfg.validate()
    assert "最高可分析" in str(ei.value)


def test_window_validation():
    cfg = AppConfig()
    cfg.windows["voltage"].length_s = -1
    with pytest.raises(ConfigError):
        cfg.validate()
    cfg = AppConfig()
    cfg.windows["voltage"].policy = "blackman"
    with pytest.raises(ConfigError):
        cfg.validate()


def test_json_roundtrip(tmp_path):
    cfg = AppConfig().validate()
    cfg.windows["voltage"].length_s = 5.0
    cfg.transform.pt_ratio = 200.0
    p = str(tmp_path / "cfg.json")
    cfg.save(p)
    back = AppConfig.load(p)
    assert back.windows["voltage"].length_s == 5.0
    assert back.transform.pt_ratio == 200.0
    assert back.to_dict() == cfg.to_dict()
    # JSON 必须可被标准库解析（无 NaN/Infinity 非法字面量）
    json.loads(open(p, encoding="utf-8").read())


def test_from_dict_window_shorthand():
    cfg = AppConfig.from_dict({"windows": {"voltage": 5.0, "harmonic": {"length_s": 0.4, "policy": "integer_cycles"}}})
    assert cfg.windows["voltage"].length_s == 5.0
    assert cfg.windows["harmonic"].length_s == 0.4
    # 未指定的量保留默认（不能被简写清空）
    assert cfg.windows["spectrum"].length_s == default_windows()["spectrum"].length_s


def test_column_map_chinese_and_english():
    cm = ColumnMap()
    assert cm.resolve(HEADER_CN) == {"timestamp": 0, "ua": 1, "ia": 2, "ub": 3, "ib": 4, "uc": 5, "ic": 6}
    idx = cm.resolve(HEADER_EN)
    assert idx["ua"] == 1 and idx["ic"] == 6


def test_column_map_aliases_and_order_free():
    cm = ColumnMap()
    header = ["time", "I_A", "U_A", "I_B", "U_B", "I_C", "U_C"]     # 乱序 + 别名
    idx = cm.resolve(header)
    assert header[idx["ua"]] == "U_A" and header[idx["ia"]] == "I_A"
    assert header[idx["timestamp"]] == "time"


def test_column_map_missing_column_raises():
    cm = ColumnMap()
    with pytest.raises(ConfigError) as ei:
        cm.resolve(["时间戳", "A相电压", "A相电流"])
    assert "无法识别字段" in str(ei.value)


def test_load_or_default(tmp_path):
    cfg = load_or_default(str(tmp_path / "nope.json"))
    assert cfg.sampling.fs == 6400.0
    p = str(tmp_path / "c.json")
    AppConfig().validate().save(p)
    assert load_or_default(p).sampling.fs == 6400.0
    with pytest.raises(ConfigError):
        AppConfig.load(str(tmp_path / "nope.json"))


def test_max_and_min_window_derivation():
    cfg = AppConfig().validate()
    cfg.windows["voltage"].length_s = 5.0
    cfg.windows["harmonic"].step_s = 0.1
    assert cfg.max_window_s == 5.0
    assert cfg.min_step_s == 0.1
    assert cfg.windows["harmonic"].effective_step_s() == 0.1


def test_branch_hide_ui_config_roundtrip():
    """v0.33：branch.hide_ui（隐藏分路侧界面）默认 False、可写入、validate 归一为 bool、to_dict 往返保留。"""
    from elec_tool.config import AppConfig
    c = AppConfig.from_dict({})
    assert c.branch.hide_ui is False
    c2 = AppConfig.from_dict({"branch": {"enabled": True, "hide_ui": 1}}).validate()
    assert c2.branch.hide_ui is True and c2.branch.enabled is True
    assert AppConfig.from_dict(c2.to_dict()).branch.hide_ui is True
