"""第 213 轮：波形预览右键查看原始采样与逐周波有效值。"""
import pathlib

import numpy as np
import pytest
from starlette.testclient import TestClient

from elec_tool.selftest import HarmSpec, build_signal
from tests.conftest import write_csv

ROOT = pathlib.Path(__file__).resolve().parents[1]
T0 = 1_700_000_000.0


@pytest.fixture(scope='module')
def wave(tmp_path_factory):
    path = tmp_path_factory.mktemp('r213') / 'wave.csv'
    t, u, i = build_signal([HarmSpec(1, 60.0, 5.0, phi_deg=0)], 1600, 3.0, t0=T0)
    write_csv(str(path), t, u, i)
    return str(path)


@pytest.fixture(scope='module')
def client():
    from app.server import app
    with TestClient(app) as c:
        yield c


def test_detail_endpoints_same_window_and_scaling(client, wave):
    args = {'path': wave, 't_start': str(T0 + 1), 't_end': str(T0 + 2),
            'channels': 'Ua,Ub,Uc', 'pt_ratio': '2', 'ct_ratio': '3'}
    instant = client.get('/api/process/wave/load', params={**args, 'max_points': 200000}).json()
    rms = client.get('/api/process/wave/rms', params={**args, 'agg_cycles': 1, 'max_points': 1000}).json()
    assert instant['ok'] and rms['ok']
    assert 1600 <= instant['n'] <= 1601 and rms['n'] == 50 and rms['agg_cycles'] == 1
    assert set(instant['channels']) == {'Ua', 'Ub', 'Uc'} == set(rms['channels'])
    assert min(instant['channels']['Ua']) < -160 and max(instant['channels']['Ua']) > 160
    assert np.allclose(rms['channels']['Ua'], 120, atol=.2)
    assert abs(instant['t'][0] - rms['t'][0]) < 1 / 1600


def test_detail_current_and_missing_file(client, wave, tmp_path):
    args = {'path': wave, 't_start': str(T0 + .5), 't_end': str(T0 + 1), 'channels': 'Ia,Ib,Ic', 'ct_ratio': '3'}
    d = client.get('/api/process/wave/rms', params={**args, 'agg_cycles': 1}).json()
    assert d['ok'] and d['n'] == 25 and set(d['channels']) == {'Ia', 'Ib', 'Ic'}
    assert np.allclose(d['channels']['Ia'], 15, atol=.05)
    assert client.get('/api/process/wave/info', params={'path': str(tmp_path / 'missing.csv')}).status_code == 400


def test_wave_board_only_wires_new_menu_and_module_owned_state():
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    board = js[js.index('/* ------------------------------------------------------------------ 数据处理 · 波形预览（v0.99.51'):js.index('/* v0.96 / v0.97：数据处理 · 估计 CT')]
    for token in ('显示周波瞬时采样曲线', '显示周波有效值曲线', "'mon-raw-path'", "'detail-cycles'", 'function wbLoadDetail',
                  "'/api/process/wave/info?'", "q.agg_cycles = 1", 'WB_DETAIL_MAX_SAMPLES', 'cv.__onSeriesToggle', 'wbClearDetail(m)'):
        assert token in board
    assert "rt.loadedOffline" in board and "center < info.t_start || center > info.t_end" in board
    assert "window.wpLoadCycleWindow" not in board
