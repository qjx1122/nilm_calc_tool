"""Explicit per-profile single-phase scope, end-to-end and legacy compatibility."""
import numpy as np
import pytest

from elec_tool.blocks import SampleBlock
from elec_tool.config import AppConfig
from elec_tool.nilm import NilmDetector
from elec_tool.nilm_profile import (FEATURES, ProfileError, build_profile, detect_profile,
                                    save_profile, validate_profile)

FS, F, EPOCH = 6400.0, 50.0, 1791878400.0


def config():
    c = AppConfig(); c.sampling.fs = FS; c.sampling.f_nom = F
    c.transform.pt_ratio = c.transform.ct_ratio = 1
    c.nilm.save = False
    return c


def device_csv(tmp_path):
    p = tmp_path / 'device.csv'
    t = np.arange(4 * int(FS)) / FS
    w = np.sqrt(2) * np.sin(2 * np.pi * F * t)
    a = np.where(t >= 2, 8, 5)
    with p.open('w', encoding='utf-8') as f:
        f.write('时间,A相电压,A相电流\n')
        for tt, u, i in zip(t, 230*w, a*w):
            f.write(f'{EPOCH+tt:.6f},{u:.6f},{i:.6f}\n')
    return str(p)


def build(tmp_path, mode):
    return build_profile(config(), device_csv(tmp_path), labels=f'{EPOCH+2},开',
                         label_tol_s=.2, single_phase_mode=mode, branch_phase='A', bus_phase='B')


@pytest.mark.parametrize('mode', ['current', 'voltage_current'])
def test_extraction_and_mapped_bus_phase(tmp_path, mode):
    d = build(tmp_path, mode)
    assert d['single_phase'] == dict(version=1, mode=mode, branch_phase='A', bus_phase='B')
    mu = dict(zip(FEATURES, d['startup']['mu']))
    assert mu['d_ia'] == pytest.approx(3, abs=.1)
    assert mu['d_p'] == pytest.approx(0 if mode == 'current' else 690, abs=30)
    # Online B-phase is the target. A and C vary concurrently, strongly and in the opposite direction.
    L = 1000; i = np.full((4, L), 5.0); p = np.zeros((4, L)); q = np.zeros((4, L)); h = np.zeros((4, L))
    i[2, 400:] += 3; p[2, 400:] += 690
    i[1] = 50; i[1, 400:] = 20; i[3] = 50; i[3, 400:] = 20
    p[1, 400:] = -5000; p[3, 400:] = -5000; q[1, 400:] = -5000
    i[0] = np.sqrt((i[1:]**2).sum(axis=0)); p[0] = p[1:].sum(axis=0); q[0] = q[1:].sum(axis=0)
    prm = dict(phase_map=6, max_scale=1, min_scale=1, k_sigma=4, state_check=0)
    hits = detect_profile(p,q,i,d,prm,mode == 'voltage_current',ih4=h)
    hit = next(x for x in hits if x['onset'] == 400)
    assert hit['accepted'] and 'sign_flip' not in hit['flags']
    assert hit['feat']['d_it'] == pytest.approx(3)
    assert hit['feat']['vec']['d_p'] == pytest.approx(0 if mode == 'current' else 690)
    if mode == 'current':
        assert hit['match']['contrib']['d_p'] == 0 and hit['match']['contrib']['d_q'] == 0
    # On branch, same profile must use explicitly configured A, not B.
    assert not any(x['accepted'] for x in detect_profile(p,q,i,d,prm,mode == 'voltage_current',ih4=h,detection_phase='C'))


@pytest.mark.parametrize('mode', ['current', 'voltage_current'])
@pytest.mark.parametrize('side', [0, 1])
def test_engine_channel_and_independent_global_quantity(tmp_path, mode, side):
    doc = build(tmp_path, mode); path = tmp_path / 'profile.json'; save_profile(doc, str(path))
    c = config(); c.output.source_id = side
    c.nilm.quantity = 'p' if mode == 'current' else 'i'
    c.nilm.profile_path = str(path); c.nilm.window_cycles = 300
    for key in c.nilm.algorithms: c.nilm.algorithms[key]['enabled'] = key == 'profile'
    c.nilm.algorithms['profile'].update(max_scale=1, min_scale=1, state_check=0)
    c.validate(); det = NilmDetector(c)
    t = np.arange(6 * int(FS)) / FS; w = 2*np.pi*F*t
    u = np.array([230*np.sqrt(2)*np.sin(w+ph) for ph in (0,-2*np.pi/3,2*np.pi/3)])
    i = np.array([5*np.sqrt(2)*np.sin(w+ph) for ph in (0,-2*np.pi/3,2*np.pi/3)])
    phase = 0 if side else 1
    i[phase] *= np.where(t >= 2, 8/5, 1)
    ev = []
    for a in range(0, len(t), 640):
        ev += det.ingest(SampleBlock(t=EPOCH+t[a:a+640],u=u[:,a:a+640],i=i[:,a:a+640]))
    events = [x for x in ev if x['algorithm'] == 'profile']
    assert events, det.errors
    event = events[0]
    assert event['channel'] == ('A' if side else 'B')
    assert event['quantity'] == ('i' if mode == 'current' else 'p')
    assert event['magnitude'] == pytest.approx(3 if mode == 'current' else 690, rel=.07)
    assert event['delta_i_a'] == pytest.approx(3, abs=.2)


def test_explicit_phases_and_invalid_profiles(tmp_path):
    f = device_csv(tmp_path)
    with pytest.raises(ProfileError, match='明确指定'):
        build_profile(config(), f, labels=f'{EPOCH+2},开', single_phase_mode='current', branch_phase='A')
    with pytest.raises(ProfileError, match='电流'):
        build_profile(config(), f, labels=f'{EPOCH+2},开', single_phase_mode='current', branch_phase='B', bus_phase='A')
    d = build(tmp_path, 'current'); d['single_phase']['bus_phase'] = ''
    with pytest.raises(ProfileError, match='明确指定'):
        validate_profile(d)


def test_api_single_phase_and_required_fields(tmp_path, monkeypatch):
    monkeypatch.setenv('ELEC_TOOL_AUTOSTART', '')
    monkeypatch.setenv('ELEC_TOOL_NILM_DIR', str(tmp_path))
    from fastapi.testclient import TestClient
    from app.server import app
    path = device_csv(tmp_path)
    payload = {'path': path, 'labels': f'{EPOCH+2},开', 'base': {'fs': FS, 'f_nom': F, 'pt_ct_enabled': False},
               'single_phase_mode': 'voltage_current', 'branch_phase': 'A', 'bus_phase': 'B'}
    with TestClient(app) as client:
        r = client.post('/api/process/nilm_profile', json=payload)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j['profile']['single_phase']['bus_phase'] == 'B'
        assert '--single-phase-mode voltage_current' in j['command'] and '--branch-phase A' in j['command'] and '--bus-phase B' in j['command']
        r = client.post('/api/process/nilm_profile', json={**payload, 'bus_phase': ''})
        assert r.status_code == 400 and '明确指定' in r.text


def test_missing_target_voltage_is_rejected(tmp_path):
    d = build(tmp_path, 'voltage_current'); path = tmp_path / 'p.json'; save_profile(d, str(path))
    c = config(); c.nilm.profile_path = str(path); c.nilm.quantity = 'i'
    for key in c.nilm.algorithms: c.nilm.algorithms[key]['enabled'] = key == 'profile'
    c.validate(); det = NilmDetector(c)
    t = np.arange(20000)/FS
    u = np.zeros((3, len(t))); u[0] = 230*np.sqrt(2)*np.sin(2*np.pi*F*t)
    i = np.zeros_like(u); i[1] = 5*np.sqrt(2)*np.sin(2*np.pi*F*t)
    for a in range(0,len(t),640): det.ingest(SampleBlock(t=EPOCH+t[a:a+640],u=u[:,a:a+640],i=i[:,a:a+640]))
    assert any('B 的电压不可用' in err for err in det.errors)
    assert not det.list(algos=['profile'])


def test_skipped_dimensions_do_not_affect_single_phase_regularization(tmp_path):
    import copy
    from elec_tool.nilm_profile import match_event
    d = build(tmp_path, 'current')
    g = d['startup']
    vec = dict(zip(FEATURES, g['mu'])); vec['d_ia'] += 1.0
    feat = {'vec': vec, 'template': g['template']}
    for stage_free in (False, True):
        first = match_event(d, feat, stage_free=stage_free)
        altered = copy.deepcopy(d)
        for name in ('d_ib','d_ic','d_p','d_q'):
            altered['startup']['sigma'][FEATURES.index(name)] *= 1e6
        second = match_event(altered, feat, stage_free=stage_free)
        assert first['d2'] == pytest.approx(second['d2'])


@pytest.mark.parametrize('mode', ['current', 'voltage_current'])
def test_all_nine_phase_mappings(tmp_path, mode):
    import copy
    original = build(tmp_path, mode)
    prm = {'max_scale': 1, 'min_scale': 1, 'state_check': 0}
    for devphase in 'ABC':
        doc = copy.deepcopy(original)
        doc['phases'] = devphase; doc['single_phase']['branch_phase'] = devphase
        g = doc['startup']; a = FEATURES.index('d_ia'); b = FEATURES.index('d_i' + devphase.lower())
        g['mu'][a], g['mu'][b] = g['mu'][b], g['mu'][a]
        g['sigma'][a], g['sigma'][b] = g['sigma'][b], g['sigma'][a]
        validate_profile(doc)
        for busphase in 'ABC':
            doc['single_phase']['bus_phase'] = busphase
            i = np.full((4,800), 5.0); p = np.zeros_like(i); q = np.zeros_like(i)
            k = 'ABC'.index(busphase)+1
            i[k,300:] += 3; p[k,300:] += 690
            i[0] = np.sqrt((i[1:]**2).sum(axis=0)); p[0] = p[1:].sum(axis=0)
            hits = detect_profile(p,q,i,doc,prm,mode == 'voltage_current')
            assert any(x['accepted'] and x['onset'] == 300 for x in hits), (mode,devphase,busphase)


def test_line_voltage_requires_reconstruction(tmp_path):
    c = config(); c.transform.voltage_input = 'line'
    with pytest.raises(ProfileError, match='需要相电压'):
        build_profile(c, device_csv(tmp_path), labels=f'{EPOCH+2},开', single_phase_mode='voltage_current', branch_phase='A', bus_phase='A')


def test_mixed_profiles_and_channel_filter(tmp_path):
    one = build(tmp_path, 'current'); two = build(tmp_path, 'voltage_current')
    one['device_id'] = 'current'; two['device_id'] = 'power'; two['single_phase']['bus_phase'] = 'C'
    p1 = tmp_path/'current.json'; p2 = tmp_path/'power.json'; save_profile(one,str(p1)); save_profile(two,str(p2))
    c = config(); c.nilm.quantity = 'p'; c.nilm.profile_path = f'{p1};{p2}'; c.nilm.window_cycles = 300
    for key in c.nilm.algorithms: c.nilm.algorithms[key]['enabled'] = key == 'profile'
    c.nilm.algorithms['profile'].update(max_scale=1, min_scale=1, state_check=0)
    c.validate(); det = NilmDetector(c)
    t = np.arange(6 * int(FS)) / FS; w = 2*np.pi*F*t
    u = np.array([230*np.sqrt(2)*np.sin(w+ph) for ph in (0,-2*np.pi/3,2*np.pi/3)])
    i = np.array([5*np.sqrt(2)*np.sin(w+ph) for ph in (0,-2*np.pi/3,2*np.pi/3)])
    for k in (1,2): i[k] *= np.where(t>=2, 8/5, 1)
    for a in range(0,len(t),640):
        det.ingest(SampleBlock(t=EPOCH+t[a:a+640], u=u[:,a:a+640], i=i[:,a:a+640]))
    events = det.list(algos=['profile']); assert {(e['device_id'], e['channel'],e['unit']) for e in events} == {('current','B','A'),('power','C','W')}
    assert [e['device_id'] for e in det.list(algos=['profile'],channel='B')] == ['current']
    assert [e['device_id'] for e in det.list(algos=['profile'],channel='C')] == ['power']


def test_current_profile_runs_when_global_p_and_no_voltage(tmp_path):
    d = build(tmp_path, 'current'); path = tmp_path/'p.json'; save_profile(d,str(path))
    c = config(); c.nilm.quantity = 'p'; c.nilm.profile_path = str(path); c.nilm.window_cycles=300
    for key in c.nilm.algorithms: c.nilm.algorithms[key]['enabled'] = key == 'profile'
    c.nilm.algorithms['profile'].update(max_scale=1, min_scale=1, state_check=0)
    c.validate(); det = NilmDetector(c)
    t = np.arange(6*int(FS))/FS; u = np.zeros((3,len(t))); i=np.zeros_like(u)
    i[1] = np.where(t>=2,8,5)*np.sqrt(2)*np.sin(2*np.pi*F*t)
    for a in range(0,len(t),640):
        det.ingest(SampleBlock(t=EPOCH+t[a:a+640], u=u[:,a:a+640], i=i[:,a:a+640]))
    assert any(e['channel']=='B' and e['unit']=='A' for e in det.list(algos=['profile'])), det.errors


def test_cli_single_phase_flags(tmp_path):
    import json
    import os
    import subprocess
    import sys
    root = os.path.dirname(os.path.dirname(__file__))
    cfg = tmp_path/'cfg.json'; cfg.write_text(json.dumps(config().to_dict()), encoding='utf8')
    out = tmp_path/'result.json'
    cmd = [sys.executable, os.path.join(root,'tools','nilm_profile.py'), '--config', str(cfg), '--file', device_csv(tmp_path),
           '--labels', f'{EPOCH+2},开', '--single-phase-mode', 'current', '--branch-phase', 'A', '--bus-phase', 'B', '--out', str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    assert r.returncode == 0, r.stderr
    d = json.loads(out.read_text(encoding='utf8'))
    assert d['single_phase']['mode'] == 'current' and d['single_phase']['bus_phase'] == 'B'
    assert '--single-phase-mode current' in d['command'] and '--bus-phase B' in d['command']


def test_selected_phase_harmonics_and_q(tmp_path):
    d = build(tmp_path, 'voltage_current'); L = 1000
    i = np.full((4,L),5.0); p = np.zeros_like(i); q = np.zeros_like(i); h = np.zeros_like(i)
    i[2,400:] += 3; p[2,400:] += 690; h[2,400:] += 4
    q[1,400:] += 10000; h[1,400:] += 100
    i[0]=np.sqrt((i[1:]**2).sum(axis=0)); p[0]=p[1:].sum(axis=0); q[0]=q[1:].sum(axis=0);h[0]=h[1:].mean(axis=0)
    hits = detect_profile(p,q,i,d,{'max_scale':1, 'min_scale':1, 'state_check':0},True,ih4=h)
    hit = next(x for x in hits if x['onset']==400)
    assert hit['feat']['vec']['d_ih'] == pytest.approx(4)
    assert hit['feat']['vec']['d_q'] == pytest.approx(0)
