"""v0.15.4 大文件快速定位：字节二分（time）/ 字节计行（row、seconds）与顺序扫结果逐行一致。"""
import datetime
import os

import pytest

from elec_tool.config import AppConfig
from elec_tool.sources import create_source
import elec_tool.sources.parsing as P


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    from elec_tool.selftest import build_signal, HarmSpec
    from tests.conftest import write_csv
    fs = 6400.0; T0 = 1_760_000_000.0
    t, u, i = build_signal([HarmSpec(1, 57.735, 5.0, phi_deg=0.0)], fs, 40.0, t0=T0)     # ≈ 20 MB，> 4 MB 走快速路径
    p = str(tmp_path_factory.mktemp("big") / "big.csv")
    write_csv(p, t, u, i)
    assert os.path.getsize(p) > P.SEEK_FAST_MIN_BYTES
    return {"path": p, "t": t, "fs": fs}


def _first(path, mode, val, fast):
    old = P.SEEK_FAST_MIN_BYTES
    P.SEEK_FAST_MIN_BYTES = old if fast else (1 << 60)
    try:
        cfg = AppConfig(); cfg.source.kind = "csv_file"; cfg.source.path = path; cfg.source.block_samples = 640
        cfg.source.play_start_mode = mode; cfg.source.play_start_value = val
        s = create_source(cfg); s.open()
        try:
            b = s.read()
        except Exception as exc:
            return ("error", type(exc).__name__)
        return (b.t_start if b else None, s.info()["play_seek"]["skipped_rows"], s.info()["play_seek"]["method"])
    finally:
        P.SEEK_FAST_MIN_BYTES = old


def test_fast_seek_matches_sequential(big):
    p, t = big["path"], big["t"]
    tgt = t[0] + 23.4567
    txt = datetime.datetime.fromtimestamp(tgt).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    f = _first(p, "time", txt, True); s = _first(p, "time", txt, False)
    assert f[2] == "time(bisect)" and s[2] == "time" and f[:2] == s[:2], (f, s)
    assert f[0] >= tgt - 1e-3 and f[0] - tgt < 1 / big["fs"] + 1e-3
    tod = datetime.datetime.fromtimestamp(t[0] + 30.0).strftime("%H:%M:%S")
    f = _first(p, "time", tod, True); s = _first(p, "time", tod, False)
    assert f[2] == "time(bisect)" and f[:2] == s[:2], (f, s)
    for mode, val in (("row", "100001"), ("seconds", "12.5")):
        f = _first(p, mode, val, True); s = _first(p, mode, val, False)
        assert f[2] == "row(bytes)" and f[:2] == s[:2], (mode, f, s)
    assert _first(p, "row", "2", True)[:2] == (pytest.approx(t[1]), 1)      # 最小跳行也走对


def test_fast_seek_eof_and_before_start(big):
    p, t = big["path"], big["t"]
    assert _first(p, "time", "2099-01-01 00:00:00", True) == ("error", "ParseError")        # 起点越界：与旧路径同样报错
    early = datetime.datetime.fromtimestamp(t[0] - 100).strftime("%Y-%m-%d %H:%M:%S")
    r = _first(p, "time", early, True)
    assert r[0] == pytest.approx(t[0]) and r[1] == 0                                          # 目标早于文件 → 从头播
    r = _first(p, "row", "999999999", True)
    assert r == ("error", "ParseError")
