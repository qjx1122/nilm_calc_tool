"""Mode B regression: bounded composite starts remain uncertain and auditable."""
import copy

import numpy as np
import pytest

import elec_tool.nilm as nm
from elec_tool.config import AppConfig
from tests.test_profile_truncated_template import fixture


ON = 300


def samples():
    t = np.arange(1000, dtype=float) / 50
    x = np.full(1000, 1.1); x[ON:ON + 30] = 90.; x[ON + 30:] = 7.1
    h = np.full(1000, .1); h[ON:] = .5
    return t, x, h


def test_composite_metrics_use_earlier_and_later_windows():
    t, x, h = samples()
    flag, data = nm._composite_start_metrics(t, x, h, ON, 50)
    assert flag == 'composite_start_settled_unattributed'
    assert data['steady_delta_ia'] == pytest.approx(6.)
    assert data['steady_delta_ih'] == pytest.approx(.4)


def test_composite_metrics_fail_closed_for_short_run_noisy_or_missing_data():
    t, x, h = samples()
    assert nm._composite_start_metrics(t[:ON + 199], x[:ON + 199], h[:ON + 199], ON, 50)[0] == 'composite_start_window_unavailable'
    short = x.copy(); short[ON + 30:] = 1.1
    assert nm._composite_start_metrics(t, short, h, ON, 50)[0] == 'composite_start_no_sustained_rise'
    noisy = x.copy(); noisy[ON + 150:ON + 200] = np.tile([3., 9.], 25)
    assert nm._composite_start_metrics(t, noisy, h, ON, 50)[0] == 'composite_start_window_unstable'
    bad = t.copy(); bad[ON + 80:] += .1
    assert nm._composite_start_metrics(bad, x, h, ON, 50)[0] == 'composite_start_window_unavailable'
    h[ON + 50] = np.nan
    assert nm._composite_start_metrics(t, x, h, ON, 50)[0] == 'composite_start_window_unavailable'


def make_detector(monkeypatch, *, members=1, nearby=False):
    p, _, _ = fixture(); p.update(phases='A', f_nom=50.)
    cfg = AppConfig(); cfg.nilm.save = False; cfg.nilm.quantity = 'i'
    cfg.nilm.algorithms['profile'].update(enabled=True, max_scale=1, min_scale=1, state_check=1, stage_free=0)
    d = nm.NilmDetector(cfg); d._joint_active = True
    profiles = [copy.deepcopy(p) for _ in range(members)]
    for k, prof in enumerate(profiles): prof['device_id'] = 'dev-' + str(k)
    d._profiles = [dict(profile=prof, path='', state='unknown', last_end=-10**9, hist={}) for prof in profiles]
    d._i_phase_seen[0] = True
    t, x, h = samples(); d._t = t
    d._i = np.zeros((4, len(t))); d._i[0] = d._i[1] = x
    d._ih = np.zeros_like(d._i); d._ih[0] = d._ih[1] = h
    d._p = np.zeros_like(d._i); d._q = d._p.copy()
    scan = {'present': True}
    def candidate(on, end, *, accepted, direction='START'):
        delta = 6. if direction == 'START' else -6.
        vec = dict(d_ia=delta, d_ib=0., d_ic=0., d_p=0., d_q=0., peak_ratio=12., dur_cycles=end-on, d_ih=.4)
        feat = dict(vec=vec, pre=dict(p=0., ia=1.1, ib=0., ic=0.),
                    post=dict(p=0., ia=7.1, ib=0., ic=0.), d_it=delta)
        match = dict(direction=direction, d2=7., d2_per_dim=1.75, margin=2., contrib={})
        return dict(onset=on, end=end, feat=feat, match=match, confidence=.9 if accepted else .11,
                    flags=[] if accepted else ['trajectory_deviates'], accepted=accepted,
                    status='confirmed' if accepted else 'rejected', post_wait=50, source='x')
    def fake(*args, **kwargs):
        found = [candidate(ON, ON+14, accepted=False)] if scan['present'] else []
        if nearby: found.append(candidate(ON+50, ON+55, accepted=True, direction='STOP'))
        return found
    monkeypatch.setattr(nm, 'detect_profile', fake)
    return d, scan


def test_wait_bounded_and_preserve_vanished_candidate(monkeypatch):
    d, scan = make_detector(monkeypatch, members=2)
    assert not d._evaluate_profile('i', 10, ON + 195)
    assert len(d._joint_pending_starts) == 2
    scan['present'] = False
    assert not d._evaluate_profile('i', 10, ON + 198)
    events = d._evaluate_profile('i', 10, ON + 199)
    assert len(events) == 1 and events[0].status == 'unknown'
    assert 'composite_start_settled_unattributed' in events[0].quality_flags
    assert {c['device_id'] for c in events[0].candidate_devices} == {'dev-0', 'dev-1'}
    assert all(c['composite_metrics']['steady_delta_ia'] == pytest.approx(6.) for c in events[0].candidate_devices)
    assert all(s['state'] == 'unknown' for s in d._profiles)
    assert not d._joint_pending_starts
    assert not d._evaluate_profile('i', 10, ON + 205)


def test_neighbouring_possible_action_is_not_confirmed_or_deleted(monkeypatch):
    d, _ = make_detector(monkeypatch, nearby=True)
    events = d._evaluate_profile('i', 10, ON + 300)
    assert len(events) == 2
    assert all(e.status == 'unknown' and not e.device_id for e in events)
    assert 'composite_start_nearby_action_uncertain' in events[1].quality_flags
    assert events[1].candidate_devices[0]['direction'] == 'STOP'
    assert d._profiles[0]['state'] == 'unknown'


def test_cache_too_small_fails_closed(monkeypatch):
    d, _ = make_detector(monkeypatch)
    d.ncfg.window_cycles = 100
    monkeypatch.setattr(d, '_profile_window_need', lambda: 100)
    ev = d._evaluate_profile('i', 10, ON + 195)
    assert len(ev) == 1 and ev[0].status == 'unknown'
    assert 'composite_start_window_unavailable' in ev[0].quality_flags
    assert d._profiles[0]['state'] == 'unknown'


def test_scope_and_accepted_candidates_do_not_trigger(monkeypatch):
    d, _ = make_detector(monkeypatch)
    r = nm.detect_profile(d._p, d._q, d._i, d._profiles[0]['profile'], {}, False)[0]
    c = dict(result=r, slot=d._profiles[0])
    assert nm._composite_start_trigger(c, True) is False
    c['result'] = {**r, 'accepted': True}
    assert nm._composite_start_trigger(c, False) is False


def test_reset_discards_pending_observations(monkeypatch):
    d, _ = make_detector(monkeypatch)
    assert not d._evaluate_profile('i', 10, ON + 195)
    assert d._joint_pending_starts and d._joint_composite_intervals
    d._reset_joint_window(d.cfg)
    assert not d._joint_pending_starts and not d._joint_composite_intervals


def test_pending_survives_cache_offset_and_is_not_duplicated(monkeypatch):
    d, scan = make_detector(monkeypatch)
    assert not d._evaluate_profile('i', 10, ON + 195)
    scan['present'] = False
    cut = 100
    d._t = d._t[cut:]; d._i = d._i[:, cut:]; d._ih = d._ih[:, cut:]
    d._p = d._p[:, cut:]; d._q = d._q[:, cut:]; d._g0 += cut
    ev = d._evaluate_profile('i', 10, ON + 199)
    assert len(ev) == 1 and ev[0].g_start == ON and ev[0].status == 'unknown'
    assert ev[0].candidate_devices[0]['composite_metrics']['steady_delta_ia'] == pytest.approx(6.)
    assert not d._evaluate_profile('i', 10, ON + 220)


def test_composite_uses_branch_phase_not_unrelated_phase(monkeypatch):
    d, _ = make_detector(monkeypatch)
    d.cfg.output.source_id = 1
    prof = d._profiles[0]['profile']
    prof['single_phase']['branch_phase'] = prof['phases'] = 'B'
    d._i[2] = d._i[1]; d._ih[2] = d._ih[1]; d._i[1] = 0.; d._ih[1] = 0.
    d._i_phase_seen[1] = True
    # Adjust the fake profile feature to reflect the declared phase.
    old = nm.detect_profile
    def phase_b(*args, **kwargs):
        found = old(*args, **kwargs)
        for r in found:
            r['feat']['vec']['d_ib'] = r['feat']['vec']['d_ia']
            r['feat']['vec']['d_ia'] = 0.
            r['feat']['pre']['ib'] = r['feat']['pre']['ia']
            r['feat']['post']['ib'] = r['feat']['post']['ia']
        return found
    monkeypatch.setattr(nm, 'detect_profile', phase_b)
    ev = d._evaluate_profile('i', 10, ON + 300)
    assert len(ev) == 1 and ev[0].channel == 'B'
    assert ev[0].candidate_devices[0]['composite_metrics']['steady_delta_ia'] == pytest.approx(6.)


def test_competing_accepted_member_is_not_promoted_early(monkeypatch):
    d, _ = make_detector(monkeypatch, members=2)
    original = nm.detect_profile
    def competing(*args, **kwargs):
        found = original(*args, **kwargs)
        if args[3]['device_id'] == 'dev-1':
            for r in found:
                r.update(accepted=True, status='confirmed', confidence=.9, flags=[])
        return found
    monkeypatch.setattr(nm, 'detect_profile', competing)
    ev = d._evaluate_profile('i', 10, ON + 300)
    assert len(ev) == 1 and ev[0].status == 'unknown'
    assert {v['device_id'] for v in ev[0].candidate_devices} == {'dev-0', 'dev-1'}
    assert {v['status'] for v in ev[0].candidate_devices} == {'rejected', 'confirmed'}
    assert all(s['state'] == 'unknown' for s in d._profiles)


def test_known_action_after_composite_horizon_can_advance(monkeypatch):
    d, _ = make_detector(monkeypatch)
    original = nm.detect_profile
    def later(*args, **kwargs):
        found = original(*args, **kwargs)
        extra = copy.deepcopy(found[0]); extra.update(onset=ON+210, end=ON+212,
                                                    accepted=True, status='confirmed', confidence=.9, flags=[])
        return found + [extra]
    monkeypatch.setattr(nm, 'detect_profile', later)
    ev = d._evaluate_profile('i', 10, ON + 500)
    assert [v.status for v in ev] == ['unknown', 'confirmed']
    assert ev[1].device_id == 'dev-0' and d._profiles[0]['state'] == 'on'


def test_initial_rejection_survives_accepted_rescan(monkeypatch):
    d, _ = make_detector(monkeypatch)
    original = nm.detect_profile
    changed = {'value': False}
    def rescan(*args, **kwargs):
        rows = original(*args, **kwargs)
        if changed['value']:
            for r in rows: r.update(accepted=True, status='confirmed', confidence=.9, flags=[])
        return rows
    monkeypatch.setattr(nm, 'detect_profile', rescan)
    assert not d._evaluate_profile('i', 10, ON + 195)
    changed['value'] = True
    ev = d._evaluate_profile('i', 10, ON + 199)
    assert len(ev) == 1 and ev[0].status == 'unknown'
    evidence = ev[0].candidate_devices
    assert {x['status'] for x in evidence} == {'rejected', 'confirmed'}
    assert any(x['evidence_type'] == 'initial_rejected_candidate' for x in evidence)
    assert d._profiles[0]['state'] == 'unknown'
