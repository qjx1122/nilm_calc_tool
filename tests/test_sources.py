"""数据源测试：离线分块 / 文件追加实时 / 模拟器 / TCP 实时流（需求④）。"""

from __future__ import annotations

import math
import os
import socket
import struct
import threading
import time

import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig, SamplingConfig, SourceConfig, TransformConfig
from elec_tool.scaling import scale_block
from elec_tool.sources import (CsvFileSource, CsvTailSource, SimulatorSource, TcpStreamSource,
                               create_source)
from elec_tool.selftest import build_signal, HarmSpec
from tests.conftest import CT, FS, HEADER_CN, PT, write_csv


# ---------------------------------------------------------------- 离线分块

def test_csv_file_chunking(csv_factory, tmp_path, base_cfg):
    art = csv_factory(str(tmp_path / "c.csv"), duration_s=1.0)
    src = CsvFileSource(base_cfg, path=art["path"], block_samples=1280)
    src.open()
    blocks = []
    while True:
        b = src.read()
        if b is None:
            break
        blocks.append(b)
    total = sum(b.n for b in blocks)
    assert total == art["t"].size
    assert len(blocks) == 5                        # 32000 / 1280 = 25? → 1s=6400 点 / 1280 = 5 块
    assert all(b.n == 1280 for b in blocks)
    assert src.exhausted
    info = src.info()
    assert info["blocks_read"] == 5 and info["samples_read"] == total
    assert info["encoding"].startswith("utf-8")
    src.close()


def test_csv_file_scaling_applies(csv_factory, tmp_path, base_cfg):
    """PT/CT 变换必须在源头之外单独一步完成，且线性正确。"""
    art = csv_factory(str(tmp_path / "d.csv"), duration_s=0.4)
    src = CsvFileSource(base_cfg, path=art["path"], block_samples=100000)
    src.open()
    blk = src.read()
    assert blk.scaled is False
    s = scale_block(blk, base_cfg.transform)
    assert s.scaled is True
    np.testing.assert_allclose(s.u, blk.u * PT, rtol=0, atol=0)
    np.testing.assert_allclose(s.i, blk.i * CT, rtol=0, atol=0)
    # 幂等：再次变换不得二次放大
    s2 = scale_block(s, base_cfg.transform)
    np.testing.assert_allclose(s2.u, s.u)
    src.close()


# ---------------------------------------------------------------- 文件追加（实时）

def test_csv_tail_reads_appends_and_rotates(tmp_path, base_cfg):
    path = str(tmp_path / "live.csv")
    t, u, i = build_signal([HarmSpec(1, 100 / math.sqrt(3), 5.0, 30.0)], FS, 2.0, 50.0)
    # 先写表头 + 前 0.5s
    write_csv(path, t[:3200], u[:, :3200], i[:, :3200])
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.source = SourceConfig(kind="csv_tail", path=path, block_samples=640)
    cfg.validate()
    src = CsvTailSource(cfg)
    src.open()
    got = []
    for _ in range(10):
        b = src.read()
        if b is not None:
            got.append(b)
    assert sum(b.n for b in got) == 3200
    # 追加 0.5s → 应只读到新增部分
    with open(path, "a", encoding="utf-8", newline="") as fh:
        for k in range(3200, 6400):
            fh.write(f"{t[k]:.9f},{u[0,k]:.6f},{i[0,k]:.6f},{u[1,k]:.6f},{i[1,k]:.6f},"
                     f"{u[2,k]:.6f},{i[2,k]:.6f}\n")
    got2 = []
    for _ in range(10):
        b = src.read()
        if b is not None:
            got2.append(b)
    assert sum(b.n for b in got2) == 3200
    # 数值正确性：追加段第一块应与原信号对应
    merged = SampleBlock.concat(got2)
    np.testing.assert_allclose(merged.u[0][:100], u[0, 3200:3300], rtol=1e-5, atol=1e-4)
    assert src.info()["blocks_read"] >= 10
    # 文件被截断（轮转）→ 应自动重开而不是崩
    write_csv(path, t[:640], u[:, :640], i[:, :640])
    for _ in range(5):
        src.read()
    assert any("截断" in n or "轮转" in n for n in src.info()["notes"])
    src.close()


def test_csv_tail_dir_watch_newest(tmp_path, base_cfg):
    d = tmp_path / "d"
    d.mkdir()
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, 30.0)], FS, 0.3, 50.0)
    write_csv(str(d / "old.csv"), t[:640], u[:, :640], i[:, :640])
    time.sleep(0.01)
    write_csv(str(d / "new.csv"), t, u, i)
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.source = SourceConfig(kind="csv_tail", path=str(d), block_samples=640, watch_dir_newest=True)
    cfg.validate()
    src = CsvTailSource(cfg)
    src.open()
    assert src._active_path.endswith("new.csv")
    src.close()


def test_csv_tail_partial_line_not_consumed(tmp_path, base_cfg):
    """半行数据（采集程序正在写）不得被当成完整记录。"""
    path = str(tmp_path / "partial.csv")
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, 30.0)], FS, 0.2, 50.0)
    write_csv(path, t[:640], u[:, :640], i[:, :640])
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{t[640]:.9f},{u[0,640]:.6f}")       # 半行，无换行
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.source = SourceConfig(kind="csv_tail", path=path, block_samples=100)
    cfg.validate()
    src = CsvTailSource(cfg)
    src.open()
    total = 0
    for _ in range(10):
        b = src.read()
        if b is not None:
            total += b.n
            assert np.all(np.isfinite(b.u)), "半行数据被误当成完整记录"
    assert total == 600, f"640 行按 100 点成块应出 6 块，实得 {total}"
    assert src.info()["pending_rows"] == 40          # 余量留待凑块，半行未被消费
    src.close()


# ---------------------------------------------------------------- 模拟器

def test_simulator_shapes_and_values(base_cfg):
    src = SimulatorSource(base_cfg, u1_sec=100 / math.sqrt(3), i1_sec=5.0, f=50.0,
                          noise_ratio=0.0, unbalance=0.0, harmonics_u={}, harmonics_i={},
                          block_samples=6400, realtime_pace=False)
    src.open()
    b = src.read()
    assert b is not None and b.n == 6400 and b.u.shape == (3, 6400)
    assert b.scaled is False
    # epoch 秒量级（~1.8e9）下 double 的绝对精度约 2.4e-7s，相对采样间隔 156.25µs 为 ~0.15%
    # → 时间戳间隔只能按此量级校验；算法本身按「样本序号 / fs」定周期，不受该抖动影响
    np.testing.assert_allclose(np.diff(b.t), 1 / FS, rtol=3e-3)
    # 纯基波无噪声 → 二次侧 RMS 应等于设定值
    from elec_tool.analysis.rms import rms
    assert rms(b.u[0]) == pytest.approx(100 / math.sqrt(3), rel=1e-6)
    assert rms(b.i[0]) == pytest.approx(5.0, rel=1e-6)
    s = scale_block(b, base_cfg.transform)
    assert rms(s.u[0]) == pytest.approx(100 / math.sqrt(3) * PT, rel=1e-6)
    assert rms(s.i[0]) == pytest.approx(5.0 * CT, rel=1e-6)
    info = src.info()
    assert info["u1_primary_rms"] == pytest.approx(100 / math.sqrt(3) * PT, rel=1e-9)


def test_simulator_reproducible_with_seed(base_cfg):
    kw = dict(u1_sec=57.735, i1_sec=5.0, noise_ratio=0.01, seed=42, block_samples=1280,
              realtime_pace=False)
    a = SimulatorSource(base_cfg, **kw); a.open(); ba = a.read()
    b = SimulatorSource(base_cfg, **kw); b.open(); bb = b.read()
    np.testing.assert_allclose(ba.u, bb.u)
    np.testing.assert_allclose(ba.i, bb.i)


def test_simulator_continuous_timeline(base_cfg):
    src = SimulatorSource(base_cfg, block_samples=640, realtime_pace=False)
    src.open()
    b1 = src.read(); b2 = src.read()
    assert b2.t_start == pytest.approx(b1.t_end + 1 / FS, rel=1e-9)


# ---------------------------------------------------------------- TCP 实时流

def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def test_tcp_text_csv_stream(base_cfg):
    """TCP 文本流：带表头的 CSV 行（与离线格式一致）。"""
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, 30.0)], FS, 0.2, 50.0)
    port = _free_port()
    ready = threading.Event()

    def server():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", port)); srv.listen(1); ready.set()
        conn, _ = srv.accept()
        conn.sendall((",".join(HEADER_CN) + "\n").encode("utf-8"))
        payload = "".join(f"{t[k]:.9f},{u[0,k]:.6f},{i[0,k]:.6f},{u[1,k]:.6f},"
                          f"{i[1,k]:.6f},{u[2,k]:.6f},{i[2,k]:.6f}\n" for k in range(t.size))
        conn.sendall(payload.encode("utf-8"))
        time.sleep(0.6)
        conn.close(); srv.close()

    th = threading.Thread(target=server, daemon=True); th.start()
    ready.wait(3)
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.source = SourceConfig(kind="tcp", host="127.0.0.1", port=port, frame="text_csv",
                              block_samples=640)
    cfg.validate()
    src = TcpStreamSource(cfg, timeout_s=1.0)
    src.open()
    got = []
    t_end = time.time() + 5
    while time.time() < t_end and sum(b.n for b in got) < t.size:
        b = src.read()
        if b is not None:
            got.append(b)
    src.close()
    total = sum(b.n for b in got)
    assert total == t.size, f"应收到 {t.size} 点，实收 {total}；notes={src.info()['notes']}"
    merged = SampleBlock.concat(got)
    np.testing.assert_allclose(merged.u[0][:50], u[0, :50], rtol=1e-5, atol=1e-4)
    assert np.all(np.diff(merged.t) > 0)
    assert src.info()["colmap"] is not None


def test_tcp_binary_frames(base_cfg):
    """TCP 二进制帧：<7d（t,ua,ia,ub,ib,uc,ic）。"""
    n = 1280
    t0 = time.time()
    t = t0 + np.arange(n) / FS
    u = np.vstack([math.sqrt(2) * 57.735 * np.cos(2 * math.pi * 50 * (t - t0) + b)
                   for b in (0, -2 * math.pi / 3, 2 * math.pi / 3)])
    i = np.vstack([math.sqrt(2) * 5.0 * np.cos(2 * math.pi * 50 * (t - t0) + b - math.radians(30))
                   for b in (0, -2 * math.pi / 3, 2 * math.pi / 3)])
    port = _free_port()
    ready = threading.Event()

    def server():
        srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", port)); srv.listen(1); ready.set()
        conn, _ = srv.accept()
        buf = b"".join(struct.pack("<7d", t[k], u[0, k], i[0, k], u[1, k], i[1, k], u[2, k], i[2, k])
                       for k in range(n))
        conn.sendall(buf)
        time.sleep(0.6); conn.close(); srv.close()

    th = threading.Thread(target=server, daemon=True); th.start(); ready.wait(3)
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.source = SourceConfig(kind="tcp", host="127.0.0.1", port=port, frame="binary",
                              struct_fmt="<7d", struct_fields="t,ua,ia,ub,ib,uc,ic", block_samples=640)
    cfg.validate()
    src = TcpStreamSource(cfg, timeout_s=1.0)
    src.open()
    got = []
    t_end = time.time() + 5
    while time.time() < t_end and sum(b.n for b in got) < n:
        b = src.read()
        if b is not None:
            got.append(b)
    src.close()
    assert sum(b.n for b in got) == n
    merged = SampleBlock.concat(got)
    np.testing.assert_allclose(merged.u[0], u[0], rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(merged.t, t, rtol=1e-9, atol=1e-9)


def test_tcp_connect_failure_is_actionable(base_cfg):
    port = _free_port()                     # 没人监听
    cfg = AppConfig(sampling=base_cfg.sampling, transform=base_cfg.transform)
    cfg.source = SourceConfig(kind="tcp", host="127.0.0.1", port=port)
    cfg.validate()
    src = TcpStreamSource(cfg, timeout_s=0.5)
    from elec_tool.sources.parsing import ParseError
    with pytest.raises(ParseError) as ei:
        src.open()
    assert "TCP 连接失败" in str(ei.value) and "排查" in str(ei.value)


# ---------------------------------------------------------------- 工厂

def test_create_source_factory(base_cfg, tmp_path, csv_factory):
    art = csv_factory(str(tmp_path / "f.csv"), duration_s=0.2)
    for kind, path in (("csv_file", art["path"]), ("csv_tail", art["path"]),
                       ("simulator", None), ("tcp", None)):
        src = create_source(base_cfg, kind=kind, path=path)
        assert src.kind == kind
    with pytest.raises(Exception):
        create_source(base_cfg, kind="modbus")
