"""v0.91：离线 CSV 稀疏行索引（elec_tool.line_index）与周波窗定位提速。

- 索引三个接口与暴力计数逐位一致（随机行长、随机区间、含行跨检查点边界的情形）；
- 首次之后的定位只读 ≤ 1 个检查点间距的数据，不再整文件扫描；文件改写后自动失效；
- 走索引前后 iter_csv_blocks 的时标 / 行号定位结果（skipped_rows、首块时间）完全一致；
- 周波窗端点（nilm / elec cycles_file、wave_file）在大于 SEEK_FAST_MIN_BYTES 的文件上结果与旧法一致。
"""
from __future__ import annotations

import io
import os
import random

import numpy as np
import pytest

from elec_tool import line_index as li
from elec_tool.config import AppConfig
from elec_tool.sources import parsing as P


@pytest.fixture(autouse=True)
def _small_step(monkeypatch):
    monkeypatch.setattr(li, "STEP", 4096)
    monkeypatch.setattr(li, "_READ", 1000)
    li.invalidate()
    yield
    li.invalidate()


def _brute_offset(data: bytes, n: int, lo: int):
    c, i = 0, lo
    while c < n:
        j = data.find(b"\n", i)
        if j < 0:
            break
        c += 1; i = j + 1
    return (i if c == n else len(data)), c


def test_index_matches_brute_force(tmp_path):
    rng = random.Random(7)
    p = tmp_path / "r.csv"
    p.write_bytes(b"".join(b"x" * rng.randint(0, 60) + b"\n" for _ in range(50000)) + b"tail-no-newline")
    data = p.read_bytes()
    for _ in range(300):
        lo = rng.randint(0, len(data)); hi = rng.randint(lo, len(data))
        assert li.count_newlines(str(p), lo, hi) == data[lo:hi].count(b"\n")
    assert li.total_newlines(str(p)) == data.count(b"\n")
    for _ in range(300):
        lo = rng.choice([0, rng.randint(0, len(data) // 2)]); n = rng.randint(0, 52000)
        assert li.byte_offset_of_row(str(p), n, lo) == _brute_offset(data, n, lo), (lo, n)
    # 行恰好结束在检查点边界 / 跨边界：构造定长行使边界落在行中与行尾
    q = tmp_path / "fixed.csv"
    q.write_bytes(b"0123456789\n" * 20000)                       # 11 字节一行，4096 不是 11 的倍数 → 边界在行中
    d2 = q.read_bytes()
    for n in (0, 1, 372, 373, 744, 745, 1117, 5000, 19999, 20000, 20001):
        assert li.byte_offset_of_row(str(q), n, 0) == _brute_offset(d2, n, 0), n
    r = tmp_path / "aligned.csv"
    r.write_bytes(b"x" * 4095 + b"\n" + (b"y" * 7 + b"\n") * 3000)       # 第一行恰好在边界结束
    d3 = r.read_bytes()
    for n in (0, 1, 2, 100):
        assert li.byte_offset_of_row(str(r), n, 0) == _brute_offset(d3, n, 0), n
    assert li.count_newlines(str(r), 0, 4096) == 1 and li.count_newlines(str(r), 4096, 4096 + 16) == 2


def test_index_reads_little_after_warm_and_invalidates_on_change(tmp_path, monkeypatch):
    p = tmp_path / "b.csv"
    p.write_bytes((b"a,b,c\n") * 200000)                          # 1.2 MB，≈300 个检查点
    li.warm(str(p), background=False)
    read = {"n": 0}
    real_open = open

    class _Counting(io.FileIO):
        def read(self, n=-1):
            b = super().read(n); read["n"] += len(b); return b

    monkeypatch.setattr(li, "open", lambda path, mode="rb": _Counting(path, "rb"), raising=False)
    size = os.path.getsize(p)
    for hi in (size // 3, size // 2, size - 10):
        read["n"] = 0
        li.count_newlines(str(p), 6, hi)
        assert read["n"] <= 2 * li.STEP, (hi, read["n"])        # 两端各 ≤ 1 个 STEP
        read["n"] = 0
        li.byte_offset_of_row(str(p), hi // 6, 0)
        assert read["n"] <= 2 * li.STEP
    read["n"] = 0
    assert li.total_newlines(str(p)) == 200000 and read["n"] == 0  # 总数已缓存，不读文件
    monkeypatch.delattr(li, "open")
    # 文件追加 → 索引按 (size, mtime) 失效并重建
    with open(p, "ab") as fh:
        fh.write(b"a,b,c\n" * 5)
    assert li.total_newlines(str(p)) == 200005


def _write_wave_csv(path, seconds=3, fs=6400, t0_text="08:00:00", with_date=False):
    rows = [b"\xe6\x97\xb6\xe9\x97\xb4\xe6\x88\xb3,A\xe7\x9b\xb8\xe7\x94\xb5\xe5\x8e\x8b,A\xe7\x9b\xb8\xe7\x94\xb5\xe6\xb5\x81,B\xe7\x9b\xb8\xe7\x94\xb5\xe5\x8e\x8b,B\xe7\x9b\xb8\xe7\x94\xb5\xe6\xb5\x81,C\xe7\x9b\xb8\xe7\x94\xb5\xe5\x8e\x8b,C\xe7\x9b\xb8\xe7\x94\xb5\xe6\xb5\x81\n"]
    h, m, s0 = (int(x) for x in t0_text.split(":"))
    for s in range(seconds):
        sec = s0 + s
        clock = f"{h:02d}:{m + sec // 60:02d}:{sec % 60:02d}"
        pre = ("2026/10/13 " if with_date else "0/00/00 ") + clock
        t = np.arange(fs) / fs; w = 2 * np.pi * 50 * t
        u = 57.74 * np.sqrt(2) * np.sin(w); i = 3 * np.sqrt(2) * np.sin(w - 0.45)
        frac = (np.arange(fs) * 10000 // fs).astype(int)
        for k in range(fs):
            rows.append(f"{pre}.{frac[k]:04d},{u[k]:.4f},{i[k]:.4f},{u[k]:.4f},{i[k]:.4f},{u[k]:.4f},{i[k]:.4f}\n".encode())
    with open(path, "wb") as fh:
        fh.writelines(rows)


def _seek_info(cfg_path, start_mode, start_value, fast_min):
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = cfg_path
    cfg.source.play_start_mode = start_mode; cfg.source.play_start_value = start_value; cfg.source.file_speed = 0
    cfg.validate()
    from elec_tool.sources import create_source
    old = P.SEEK_FAST_MIN_BYTES; P.SEEK_FAST_MIN_BYTES = fast_min
    try:
        with create_source(cfg) as src:
            blk = None
            while blk is None:
                blk = src.read()
                if blk is None and src.exhausted:
                    break
            return dict(src._seek_info), (float(blk.t[0]) if blk is not None else None)
    finally:
        P.SEEK_FAST_MIN_BYTES = old


def test_seek_results_identical_with_and_without_index(tmp_path):
    p = tmp_path / "w.csv"; _write_wave_csv(p, seconds=4)
    # 顺序扫（旧路径：阈值设成比文件大） vs 字节二分 + 索引（阈值 0）
    for mode, val in (("time", "08:00:02.5"), ("row", "13000"), ("seconds", "1.25")):
        slow, t_slow = _seek_info(str(p), mode, val, 1 << 40)
        li.invalidate()
        fast, t_fast = _seek_info(str(p), mode, val, 0)
        fast2, t_fast2 = _seek_info(str(p), mode, val, 0)         # 第二次走已建好的索引
        assert slow["skipped_rows"] == fast["skipped_rows"] == fast2["skipped_rows"], (mode, slow, fast)
        assert t_slow == t_fast == t_fast2
        if mode == "time":
            assert fast["method"] == "time(bisect)" and slow["method"] == "time"
        if mode in ("row", "seconds"):
            assert fast["method"] == "row(bytes)"


def test_window_endpoints_fast_path_same_result(tmp_path, monkeypatch):
    """周波窗三条路径（nilm cycles_file / wave_file / elec cycles）在「走索引」与「旧顺序扫」下结果一致。"""
    from elec_tool.nilm import load_cycles_from_file
    from elec_tool.wave_preview import file_info, load_waveform, cycle_values
    p = tmp_path / "w.csv"; _write_wave_csv(p, seconds=4)
    cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = str(p); cfg.validate()
    info = file_info(cfg, str(p)); t0 = float(info["t_start"])
    tc = t0 + 2.0
    out = {}
    for tag, thr in (("slow", 1 << 40), ("fast", 0)):
        monkeypatch.setattr(P, "SEEK_FAST_MIN_BYTES", thr); li.invalidate()
        c = load_cycles_from_file(cfg, tc, 50)
        w = load_waveform(cfg, str(p), t_start=repr(tc - 0.5), n_cycles=50)
        e = cycle_values(w, 50.0)
        out[tag] = (list(c["t"]), c["channels"]["total"]["p"][:5], w["t"][:3], w["channels"]["Ua"][:3], e["t"][:3])
    assert out["slow"] == out["fast"]
    assert abs(out["fast"][0][25] - tc) < 0.03 and len(out["fast"][0]) == 50
    # 自定义时间（行号定位）同样一致
    c2 = AppConfig.from_dict(cfg.to_dict()); c2.source.custom_time = True; c2.source.custom_time_start = repr(t0)
    res = {}
    for tag, thr in (("slow", 1 << 40), ("fast", 0)):
        monkeypatch.setattr(P, "SEEK_FAST_MIN_BYTES", thr); li.invalidate()
        w = load_waveform(c2, str(p), t_start=repr(tc - 0.5), n_cycles=50)
        res[tag] = (w["t"][:3], w["channels"]["Ia"][:3], w["n"])
    assert res["slow"] == res["fast"]


def test_warm_background_builds_full_index(tmp_path):
    p = tmp_path / "b.csv"; p.write_bytes(b"1,2\n" * 100000)
    li.warm(str(p))
    import time
    for _ in range(200):
        ix = li._get(str(p))
        if ix.total is not None:
            break
        time.sleep(0.01)
    assert li._get(str(p)).total == 100000
    li.warm("/no/such/file.csv")                                   # 不存在：静默
