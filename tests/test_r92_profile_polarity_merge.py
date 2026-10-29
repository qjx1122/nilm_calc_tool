"""v0.92：电流极性反转开关 + 画像自动定位切碎事件合并。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pytest
from elec_tool.config import ConfigError
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
    """v0.92.2：(1) 事件落在文件头 min_gap_cycles 周波内也应报出；(2) 画像 PT/CT 启用标志与本侧不一致时给出明确提示（v0.99.22 起仍照常匹配）。"""
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
    # v0.99.22：PT/CT 启用标志不一致只警告、匹配照常运行（口径是否真差一个变比由数据决定）：这里画像与数据同源，仍应报出
    assert [e for e in evs2 if e["algorithm"] == "profile"]
    assert any("PT/CT" in e and "请确认两侧数据都是一次侧量" in e for e in det2.summary()["errors"])


def test_engine_warns_when_phase_missing_or_signs_disagree(tmp_path):
    """v0.92.6：B 相电流为 0、A 相极性与 C 相相反时，ΣP 抵消 → 无候选，但必须给出数据体检提示。"""
    import csv, json
    from elec_tool.nilm import NilmDetector
    from elec_tool.scaling import scale_block
    from elec_tool.sources import create_source
    FS, F = T.FS, T.F; n = int(FS * 8.0); t = np.arange(n) / FS; w = 2 * np.pi * F * t
    I = np.where(t < 4, 36.0, 0.3); u = np.zeros((3, n)); i = np.zeros((3, n))
    for k, ph in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
        u[k] = 230 * np.sqrt(2) * np.sin(w + ph); i[k] = I * np.sqrt(2) * np.sin(w + ph)
    i[0] *= -1; i[1] *= 0
    f = str(tmp_path / "bus.csv"); T._write_csv(f, T.T0 + t, u, i)
    c = AppConfig(); c.transform.enabled = False
    d = str(tmp_path / "dev.csv"); td, ud, idd = T._wave(T._dev, 8.0); T._write_csv(d, td, ud, idd)
    prof = build_profile(c, d, device_id="d"); pp = str(tmp_path / "p.json"); json.dump(prof, open(pp, "w"))
    c.source.kind = "csv_file"; c.source.path = f; c.source.file_speed = 0.0; c.nilm.enabled = True; c.nilm.save = False
    for a in c.nilm.algorithms: c.nilm.algorithms[a]["enabled"] = False
    c.nilm.algorithms["profile"] = {"enabled": True}; c.nilm.profile_path = pp
    det = NilmDetector(c, root=str(tmp_path))
    with create_source(c) as src:
        while True:
            b = src.read()
            if b is None:
                if src.exhausted: break
                continue
            det.ingest(scale_block(b, c.transform))
    errs = det.summary()["errors"]
    assert sum("数据体检" in e for e in errs) == 1
    assert any("B 相电流≈0" in e and "符号不一致" in e for e in errs)


def test_v093_phase_signs_and_scale_current():
    """v0.93：分相极性反转只翻指定相；与全局反转叠加。"""
    from elec_tool.scaling import scale_current
    tr = TransformConfig(enabled=False, invert_phases="A")
    assert tr.phase_signs() == [-1.0, 1.0, 1.0]
    i = np.ones((3, 4)); out = scale_current(i, tr)
    assert out[0, 0] == -1.0 and out[1, 0] == 1.0 and out[2, 0] == 1.0
    tr2 = TransformConfig(enabled=True, ct_ratio=15, invert_current=True, invert_phases="C")
    assert tr2.phase_signs() == [-1.0, -1.0, 1.0]
    assert np.allclose(scale_current(i, tr2)[:, 0], [-15, -15, 15])
    with pytest.raises(ConfigError):
        TransformConfig(wiring="xx").validate()
    with pytest.raises(ConfigError):
        TransformConfig(invert_phases="D").validate()


def test_v093_three_wire_bus_detects_after_wiring_and_polarity_fix(tmp_path):
    """v0.93：三相三线两表法（A/C 列为 Uab/Ucb、B 无 CT）+ A 相 CT 接反：
    原样 → 无候选 + 体检提示；wiring=3p3w + invert_phases=A → 提示消失、停机命中。"""
    import json
    from elec_tool.nilm import NilmDetector
    from elec_tool.scaling import scale_block
    from elec_tool.sources import create_source
    # 设备侧用 T._dev（600 W 台阶、pf 0.9）；总线侧同一设备装在三相三线两表法回路：A/C 电压列=Uab/Ucb、B 无 CT、A 相 CT 接反
    t_, u, i = T._wave(T._dev, 20.0, pf=0.9)
    t = t_ - T.T0
    u3 = np.vstack([u[0] - u[1], np.zeros(t.size), u[2] - u[1]]); i3 = np.vstack([-i[0], np.zeros(t.size), i[2]])
    f = str(tmp_path / "bus.csv"); T._write_csv(f, T.T0 + t, u3, i3)
    c = AppConfig(); c.transform.enabled = False
    d = str(tmp_path / "dev.csv"); T._write_csv(d, t_, u, i)
    prof = build_profile(c, d, device_id="d", labels=T._labels(), pre_cycles=10, post_cycles=50)
    pp = str(tmp_path / "p.json"); json.dump(prof, open(pp, "w"))

    def run(wiring, inv):
        c2 = AppConfig(); c2.transform.enabled = False; c2.transform.wiring = wiring; c2.transform.invert_phases = inv
        c2.source.kind = "csv_file"; c2.source.path = f; c2.source.file_speed = 0.0; c2.nilm.enabled = True; c2.nilm.save = False
        for a in c2.nilm.algorithms: c2.nilm.algorithms[a]["enabled"] = False
        c2.nilm.algorithms["profile"] = {"enabled": True}; c2.nilm.profile_path = pp
        det = NilmDetector(c2, root=str(tmp_path)); evs = []
        with create_source(c2) as src:
            while True:
                b = src.read()
                if b is None:
                    if src.exhausted: break
                    continue
                evs += det.ingest(scale_block(b, c2.transform))
        return evs, det.summary()["errors"]

    evs, errs = run("3p4w", "")
    assert not evs and any("数据体检" in e and "B 相电流≈0" in e and "CT 极性可能接反" in e for e in errs)
    evs, errs = run("3p3w", "")
    assert any("符号不一致" in e and "B 相电流≈0" not in e for e in errs)
    evs, errs = run("3p3w", "A")
    assert not any("数据体检" in e for e in errs)
    stops = [e for e in evs if e.get("algorithm") == "profile" and e.get("profile_direction") == "STOP"]
    assert len(stops) >= 2 and any(abs((float(st["t_start"]) % 86400) - ((T.T0 + 5.0) % 86400)) < 0.3 for st in stops)


def test_v094_reconstruct_three_wire_matches_four_wire():
    """v0.94：3p3w 虚拟中性点重构——不对称电流（ia+ib+ic=0）下分相 P 与 I 均与四线制一致（电压对称）。"""
    from elec_tool.scaling import scale_block
    FS = 10000.0; n = 4000; t = np.arange(n) / FS; w = 2 * np.pi * 50 * t; U = 230.0; phi = np.deg2rad(28)
    ph = (0, -2 * np.pi / 3, 2 * np.pi / 3)
    u = np.vstack([U * np.sqrt(2) * np.sin(w + p) for p in ph])
    ia = -36 * np.sqrt(2) * np.sin(w + ph[0] + phi); ic = -40 * np.sqrt(2) * np.sin(w + ph[2] + phi); ib = -(ia + ic)
    i = np.vstack([ia, ib, ic])
    pqi = lambda uu, ii: ([float(np.mean(uu[k] * ii[k])) for k in range(3)], [float(np.sqrt(np.mean(ii[k] ** 2))) for k in range(3)])
    P4, I4 = pqi(u, i)
    u3 = np.vstack([u[0] - u[1], np.zeros(n), u[2] - u[1]]); i3 = np.vstack([-ia, np.zeros(n), ic])   # 两表法 + A 相 CT 反
    tr = TransformConfig(enabled=False, wiring="3p3w", invert_phases="A", reconstruct_3w=True)
    assert tr.reconstructing and not tr.b_phase_missing and not tr.voltage_is_line
    b = scale_block(SampleBlock(t=t, u=u3, i=i3, scaled=False), tr)
    P3, I3 = pqi(b.u, b.i)
    assert np.allclose(P4, P3, rtol=1e-6) and np.allclose(I4, I3, rtol=1e-6)
    # 未开重构：B 相缺失语义保持
    tr0 = TransformConfig(enabled=False, wiring="3p3w")
    assert tr0.b_phase_missing and not tr0.reconstructing
    assert scale_block(SampleBlock(t=t, u=u3, i=i3, scaled=False), tr0) .i[1].max() == 0.0


def test_v094_reconstruct_enables_b_channel_and_full_profile(tmp_path):
    """v0.94：重构后 B 相通道可检测、画像匹配不再跳过 d_ib 且仍命中停机。"""
    import json
    from elec_tool.nilm import NilmDetector
    from elec_tool.scaling import scale_block
    from elec_tool.sources import create_source
    t_, u, i = T._wave(T._dev, 20.0, pf=0.9)
    u3 = np.vstack([u[0] - u[1], np.zeros(t_.size), u[2] - u[1]]); i3 = np.vstack([-i[0], np.zeros(t_.size), i[2]])
    f = str(tmp_path / "bus.csv"); T._write_csv(f, t_, u3, i3)
    c = AppConfig(); c.transform.enabled = False
    d = str(tmp_path / "dev.csv"); T._write_csv(d, t_, u, i)
    prof = build_profile(c, d, device_id="d", labels=T._labels(), pre_cycles=10, post_cycles=50)
    pp = str(tmp_path / "p.json"); json.dump(prof, open(pp, "w"))

    def run(algos, channels):
        c2 = AppConfig(); c2.transform.enabled = False; c2.transform.wiring = "3p3w"; c2.transform.invert_phases = "A"; c2.transform.reconstruct_3w = True
        c2.source.kind = "csv_file"; c2.source.path = f; c2.source.file_speed = 0.0; c2.nilm.enabled = True; c2.nilm.save = False
        c2.nilm.channels = channels
        for a in c2.nilm.algorithms: c2.nilm.algorithms[a]["enabled"] = False
        for a in algos: c2.nilm.algorithms[a] = {"enabled": True}
        c2.nilm.profile_path = pp
        det = NilmDetector(c2, root=str(tmp_path)); evs = []
        with create_source(c2) as src:
            while True:
                b = src.read()
                if b is None:
                    if src.exhausted: break
                    continue
                evs += det.ingest(scale_block(b, c2.transform))
        return evs, det.summary()["errors"]

    evs, errs = run(["profile"], ["A"])
    assert not any("数据体检" in e for e in errs)
    stops = [e for e in evs if e.get("algorithm") == "profile" and e.get("profile_direction") == "STOP"]
    assert len(stops) >= 2
    evs, _ = run(["threshold"], ["B"])
    assert any(e.get("channel") == "B" for e in evs)   # 未重构时 B 相恒 0，不可能有事件
