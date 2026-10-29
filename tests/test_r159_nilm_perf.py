"""v0.99.17：负荷辨识评估节流 / 自适应统计缓存 / 尾部切片——结果与逐块整窗评估等价，耗时显著下降。"""
import time
import numpy as np

from elec_tool.config import AppConfig
from elec_tool.nilm import NilmDetector, _lookback_cycles
from elec_tool.blocks import SampleBlock


def _run(tmp_path, every, auto_every, blocks=900):
    cfg = AppConfig(); cfg.nilm.enabled = True; cfg.nilm.save = False; cfg.nilm.auto_params = True
    cfg.nilm.window_cycles = 3000; cfg.nilm.channels = ["total"]; cfg.transform.enabled = False
    cfg.nilm.eval_every_cycles = every; cfg.nilm.auto_stats_every_cycles = auto_every
    det = NilmDetector(cfg, root=str(tmp_path))
    fs, n = 10000, 640; rng = np.random.default_rng(0); t0 = 0.0; ev = []
    t_s = time.time()
    for _ in range(blocks):
        t = t0 + np.arange(n) / fs; t0 += n / fs; w = 2 * np.pi * 50 * t
        amp = 1.0 + 0.5 * (t > 15) + 0.8 * (t > 30) - 0.5 * (t > 45)
        u = np.vstack([230 * np.sqrt(2) * np.sin(w + ph) for ph in (0, -2.094, 2.094)])
        i = np.vstack([amp * np.sqrt(2) * np.sin(w + ph - 0.3) + rng.normal(0, 0.01, n) for ph in (0, -2.094, 2.094)])
        ev += det.ingest(SampleBlock(t=t, u=u, i=i, scaled=True, source="b"))
    return ev, time.time() - t_s, det


def test_throttled_equals_per_block(tmp_path):
    ev1, dt1, d1 = _run(tmp_path / "a", 1, 1)
    ev10, dt10, d10 = _run(tmp_path / "b", 10, 50)
    k = lambda ev: sorted((e["algorithm"], round(e["t_start"], 1), int(np.sign(e["delta_p_w"]))) for e in ev)
    assert len(ev1) >= 12 and k(ev1) == k(ev10)
    assert d10.eval_count <= d1.eval_count * 0.6
    assert dt10 < dt1                                        # 节流 + 切片更快（通常 ≥ 3×）


def test_lookback_positive():
    from elec_tool.config import NILM_ALGO_DEFAULTS
    for a, prm in NILM_ALGO_DEFAULTS.items():
        if a != "profile":
            assert _lookback_cycles(a, prm) > 0


def test_config_defaults_and_clamp():
    cfg = AppConfig(); assert cfg.nilm.eval_every_cycles == 10 and cfg.nilm.auto_stats_every_cycles == 50
    cfg.nilm.eval_every_cycles = 0; cfg.nilm.auto_stats_every_cycles = -3; cfg.validate()
    assert cfg.nilm.eval_every_cycles == 1 and cfg.nilm.auto_stats_every_cycles == 1
