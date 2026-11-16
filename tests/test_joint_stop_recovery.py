"""Conservative recovery guard: synthetic inputs; mode B execution is user-side."""
import copy

import numpy as np
import pytest

import elec_tool.nilm as nm
from elec_tool.config import AppConfig
from tests.test_profile_truncated_template import fixture


def guard(x, onset=300, end=310, post_hi=None):
    return nm._joint_stop_recovery_flag(x, onset, end, 10, 50, 50, post_hi)


def pulse(length=1000, onset=300, end=310, baseline=6.5, peak=10.):
    x = np.full(length, baseline)
    x[onset-10:onset] = peak
    return x


def test_recovered_impulse_is_uncertain_and_true_stop_is_not():
    x = pulse()
    assert guard(x) == 'stop_recovery_suspected'
    x = np.full(1000, 6.5); x[310:] = 1.1
    assert guard(x) == ''


def test_short_real_run_is_not_silently_declared_noise():
    x = np.full(1000, 1.1); x[290:310] = 6.5
    # Indistinguishable from a pulse on this single observation: unknown, not reject.
    assert guard(x) == 'stop_recovery_suspected'


def test_unavailable_unstable_or_contaminated_windows_are_uncertain():
    x = pulse()
    assert guard(x, 20, 30) == 'stop_recovery_window_unavailable'
    assert guard(x, post_hi=320) == 'stop_recovery_window_unavailable'
    x[240:290] = np.tile([2., 9.], 25)
    assert guard(x) == 'stop_recovery_baseline_unstable'
    x[250] = np.nan
    assert guard(x) == 'stop_recovery_window_unavailable'


def test_scale_invariance_and_tolerance():
    for scale in (0.01, 1., 1000.):
        x = pulse(baseline=6.5*scale, peak=10*scale)
        assert guard(x) == 'stop_recovery_suspected'
        x[310:] = 2*scale
        assert guard(x) == ''


def detector(monkeypatch, x, *, members=1, stage_free=0, candidates=None):
    p, _, _ = fixture(); p.update(phases='A', f_nom=50.0)
    cfg = AppConfig(); cfg.nilm.save = False; cfg.nilm.quantity = 'i'
    cfg.nilm.algorithms['profile'].update(enabled=True, max_scale=1, min_scale=1,
                                          state_check=1, stage_free=stage_free)
    d = nm.NilmDetector(cfg); d._joint_active = True
    profiles = [copy.deepcopy(p) for _ in range(members)]
    for k, prof in enumerate(profiles): prof['device_id'] = 'dev-' + str(k)
    d._profiles = [dict(profile=prof, path='', state='on', last_end=-10**9, hist={}) for prof in profiles]
    d._i_phase_seen[0] = True
    d._t = np.arange(len(x), dtype=float) / 50
    d._i = np.zeros((4, len(x))); d._i[0] = d._i[1] = x
    d._p = np.zeros_like(d._i); d._q = d._p.copy(); d._ih = d._p.copy()
    candidates = candidates or [(300, 310)]
    def fake(p4, q4, i4, prof, prm, use_p, *args, **kwargs):
        result = []
        for onset, end in candidates:
            pre = float(np.median(i4[1, onset-10:onset]))
            post = float(np.median(i4[1, end:end+50]))
            v = dict(d_ia=post-pre, d_ib=0., d_ic=0., d_p=0., d_q=0., peak_ratio=1., dur_cycles=end-onset, d_ih=0.)
            feat = dict(vec=v, pre=dict(p=0., ia=pre, ib=0., ic=0.),
                        post=dict(p=0., ia=post, ib=0., ic=0.), d_it=post-pre)
            match = dict(direction='STOP', d2=1., d2_per_dim=.25, margin=2., contrib={})
            result.append(dict(onset=onset, end=end, feat=feat, match=match, confidence=.9,
                               flags=[], accepted=True, status='confirmed', post_wait=50,
                               stage_scale=1., post_hi=None))
        return result
    monkeypatch.setattr(nm, 'detect_profile', fake)
    return d


@pytest.mark.parametrize('members', [1, 2])
def test_joint_recovery_reports_unknown_with_candidates_and_preserves_state(monkeypatch, members):
    d = detector(monkeypatch, pulse(), members=members)
    events = d._evaluate_profile('i', 10, 999)
    assert len(events) == 1 and events[0].status == 'unknown'
    assert events[0].device_id == '' and not events[0].profile_direction
    assert 'stop_recovery_suspected' in events[0].quality_flags
    assert {c['device_id'] for c in events[0].candidate_devices} == {'dev-' + str(k) for k in range(members)}
    assert all(slot['state'] == 'on' for slot in d._profiles)
    assert not d._evaluate_profile('i', 10, 999)


def test_real_stop_after_unknown_is_not_suppressed(monkeypatch):
    x = pulse(); x[660:] = 1.1
    d = detector(monkeypatch, x, candidates=[(300, 310), (650, 660)])
    events = d._evaluate_profile('i', 10, 999)
    assert [e.status for e in events] == ['unknown', 'confirmed']
    assert events[1].device_id == 'dev-0' and events[1].profile_direction == 'STOP'
    assert d._profiles[0]['state'] == 'off'


def test_free_stage_does_not_apply_recovery_guard(monkeypatch):
    d = detector(monkeypatch, pulse(), stage_free=1)
    def forbidden(*args, **kwargs):
        raise AssertionError('stage-free must not run recovery guard')
    monkeypatch.setattr(nm, '_joint_stop_recovery_flag', forbidden)
    events = d._evaluate_profile('i', 10, 999)
    assert events and events[0].status == 'confirmed'


def test_only_applicable_joint_scope_invokes_guard(monkeypatch):
    d = detector(monkeypatch, pulse())
    # Legacy, voltage/current, standalone and START paths are not changed here.
    d._profiles[0]['profile'].pop('single_phase')
    d._profiles[0]['profile']['quantity'] = 'i'
    def forbidden(*args, **kwargs):
        raise AssertionError('legacy profile must not run recovery guard')
    monkeypatch.setattr(nm, '_joint_stop_recovery_flag', forbidden)
    events = d._evaluate_profile('i', 10, 999)
    assert events and events[0].status == 'confirmed'


def test_unknown_candidate_details_survive_csv_reload(tmp_path, monkeypatch):
    from elec_tool.replay_load import load_nilm_events
    d = detector(monkeypatch, pulse(), members=2)
    d.ncfg.save = True
    d.writer = nm.NilmWriter(d.ncfg, source_id=0, dir_override=str(tmp_path))
    events = d._evaluate_profile('i', 10, 999)
    d.writer.write(events[0]); d.writer.close()
    assert not d.writer.errors
    rows = load_nilm_events(str(tmp_path), 0)
    assert len(rows) == 1 and rows[0]['status'] == 'unknown'
    assert 'stop_recovery_suspected' in rows[0]['quality_flags']
    assert {c['device_id'] for c in rows[0]['candidate_devices']} == {'dev-0', 'dev-1'}


def test_recovery_guard_uses_selected_branch_phase(monkeypatch):
    d = detector(monkeypatch, pulse())
    d.cfg.output.source_id = 1
    d._profiles[0]['profile']['single_phase']['branch_phase'] = 'B'
    d._profiles[0]['profile']['phases'] = 'B'
    d._i[2] = d._i[1]; d._i[1] = 0.; d._i_phase_seen[1] = True
    # The fake detector reads row 1 for features, but the guard must inspect row 2.
    events = d._evaluate_profile('i', 10, 999)
    assert len(events) == 1 and events[0].status == 'unknown'
    assert 'stop_recovery_suspected' in events[0].quality_flags
