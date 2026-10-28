"""v0.92：电流极性反转开关 + 画像自动定位切碎事件合并。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import test_r90_nilm_profile as T
from elec_tool.config import AppConfig, TransformConfig
from elec_tool.blocks import SampleBlock
from elec_tool.scaling import scale_block
from elec_tool.nilm_profile import build_profile


def test_invert_current_applies_even_without_ptct():
    blk = SampleBlock(t=np.zeros(4), u=np.ones((3, 4)), i=np.ones((3, 4)) * 2.0)
    tr = TransformConfig(enabled=False, invert_current=True)
    out = scale_block(blk, tr)
    assert np.allclose(out.i, -2.0) and np.allclose(out.u, 1.0)
    tr2 = TransformConfig(enabled=True, pt_ratio=100, ct_ratio=15, invert_current=True)
    assert np.allclose(scale_block(blk, tr2).i, -30.0)
    assert np.allclose(scale_block(blk, TransformConfig(enabled=False)).i, 2.0)


def test_invert_current_fixes_negative_p_profile(tmp_path):
    t, u, i = T._wave(T._dev, 20.0)
    f = str(tmp_path / "dev_neg.csv"); T._write_csv(f, t, u, -i)   # CT 接反
    c = AppConfig(); c.transform.enabled = False
    doc = build_profile(c, f, device_id="d")
    assert any("ΔP 与 ΔI 异号" in n for n in doc["notes"])
    c.transform.invert_current = True
    doc2 = build_profile(c, f, device_id="d")
    assert not any("ΔP 与 ΔI 异号" in n for n in doc2["notes"])
    ip = doc2["features"].index("d_p"); ia = doc2["features"].index("d_ia")
    assert doc2["startup"]["mu"][ip] > 0 and doc2["startup"]["mu"][ia] > 0
    assert doc2["shutdown"]["mu"][ip] < 0 and doc2["shutdown"]["mu"][ia] < 0


def test_merge_gap_collapses_fragmented_events(tmp_path):
    """一次启动后负荷分 3 级缓升（每级 +5 %，间隔 2 s）：稳态分段会切成多段；默认 merge_gap 10 s 合并为 1 次启动。"""
    def dev(ts):
        on = (ts >= 3) & (ts < 15)
        lvl = 500.0 * (1.0 + 0.05 * np.clip(np.floor((ts - 3) / 2.0), 0, 3))
        return np.where(on, lvl, 0.0)
    t, u, i = T._wave(dev, 20.0)
    f = str(tmp_path / "ramp.csv"); T._write_csv(f, t, u, i)
    c = AppConfig(); c.transform.enabled = False
    d0 = build_profile(c, f, device_id="d", merge_gap_s=0)
    d1 = build_profile(c, f, device_id="d")
    n0 = (d0["startup"] or {"n": 0})["n"]; n1 = (d1["startup"] or {"n": 0})["n"]
    assert n0 >= n1 >= 1
    if n0 > 1:
        assert n1 == 1 and any("已合并" in n for n in d1["notes"])


def _motor_wave(dur=20.0):
    """电机型负荷：P 过渡 0.5 s 衰减，启动无功电流 5 倍 / 3 s 衰减——I 口径过渡远长于稳态分段的 max_transient。"""
    FS, F = T.FS, T.F
    n = int(FS * dur); t = np.arange(n) / FS; w = 2 * np.pi * F * t
    on = (t >= 3) & (t < 15); tau = np.clip(t - 3, 0, None)
    P = 20 + np.where(on, 500.0 + 250 * np.exp(-tau / 0.5), 0); Imag = np.where(on, 2000 * np.exp(-tau / 3.0), 0)
    U, ang = 57.74, np.arccos(0.9); u = np.zeros((3, n)); i = np.zeros((3, n)); rng = np.random.default_rng(1)
    for k, ph in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        u[k] = U * np.sqrt(2) * np.sin(w + ph)
        i[k] = (P / 3) / (U * 0.9) * np.sqrt(2) * np.sin(w + ph - ang) + (Imag / 3) / U * np.sqrt(2) * np.sin(w + ph - np.pi / 2) + rng.normal(0, 0.01, n)
    return T.T0 + t, u, i


def test_two_window_supplements_long_transient_start_for_p_and_i(tmp_path):
    """v0.92.1：稳态分段因过渡过长漏掉启动时，由双滑窗补充；P / I 两种口径都应各得 1 次启动 + 1 次停止，且停止是真正的大台阶。"""
    t, u, i = _motor_wave(); f = str(tmp_path / "motor.csv"); T._write_csv(f, t, u, i)
    c = AppConfig(); c.transform.enabled = False
    for q in ("p", "i"):
        d = build_profile(c, f, device_id="m", quantity=q)
        assert d["startup"] and d["startup"]["n"] == 1, q
        assert d["shutdown"] and d["shutdown"]["n"] == 1, q
        ia = d["features"].index("d_ia")
        assert d["startup"]["mu"][ia] > 3 and d["shutdown"]["mu"][ia] < -3, (q, d["shutdown"]["mu"][ia])
        assert any("双滑窗补充" in n for n in d["notes"]), q


def test_engine_first_gap_not_suppressed_and_ptct_mismatch_warns(tmp_path):
    """v0.92.2：(1) 事件落在文件头 min_gap_cycles 周波内也应报出；(2) 画像 PT/CT 与本侧不一致时给出明确错误并不运行匹配。"""
    import json
    from elec_tool.nilm import NilmDetector
    from elec_tool.nilm_profile import FEATURES
    from elec_tool.scaling import scale_block
    from elec_tool.sources import create_source
    t, u, i = T._wave(T._dev, 8.0); f = str(tmp_path / "d.csv"); T._write_csv(f, t, u, i)
    c = AppConfig(); c.transform.enabled = False
    prof = build_profile(c, f, device_id="d")
    pp = str(tmp_path / "p.json"); json.dump(prof, open(pp, "w"))
    c.source.kind = "csv_file"; c.source.path = f; c.source.file_speed = 0.0
    c.nilm.enabled = True; c.nilm.save = False; c.nilm.min_gap_cycles = 500; c.nilm.window_cycles = 300
    for a in c.nilm.algorithms: c.nilm.algorithms[a]["enabled"] = False
    c.nilm.algorithms["profile"] = {"enabled": True}; c.nilm.profile_path = pp

    def run(cfg):
        det = NilmDetector(cfg, root=str(tmp_path)); evs = []
        with create_source(cfg) as src:
            while True:
                b = src.read()
                if b is None:
                    if src.exhausted: break
                    continue
                evs += det.ingest(scale_block(b, cfg.transform))
        return det, evs
    det, evs = run(c)
    assert any(e["algorithm"] == "profile" and e["t_start"] < T.T0 + 3 for e in evs), "文件头 2 s 处的启动（<500 周波）应被报出"
    prof["pt_ct"] = {"enabled": True, "pt_ratio": 100, "ct_ratio": 15}; json.dump(prof, open(pp, "w"))
    det2, evs2 = run(c)
    assert not [e for e in evs2 if e["algorithm"] == "profile"]
    assert any("PT/CT" in e for e in det2.summary()["errors"])
