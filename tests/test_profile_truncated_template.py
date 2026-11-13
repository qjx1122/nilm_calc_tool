"""Short post window: compare equivalent trajectory geometry without discarding neighbour boundaries."""
import copy
import numpy as np
import pytest

import elec_tool.nilm_profile as npf
from elec_tool.nilm_profile import FEATURES, _aligned_short_post_template, detect_profile, event_features, fit_group, template_distance

PRE, POST, ON, DUR, N = 10, 50, 1000, 49, 2000


def fixture(scale=1.0):
    t = np.arange(130)
    x = np.full(N, 1.1)
    # Large inrush, then a noisy running level. Only synthetic data are used.
    x[ON:ON+130] = 6.6 + 75 * np.exp(-t / 14) + .55 * np.sin(t / 3)
    x[ON+130:] = 6.6
    x *= scale
    i = np.zeros((4, N)); i[0] = i[1] = x
    z = np.zeros_like(i)
    f = event_features(z, z, i, ON, ON+DUR, PRE, POST)
    g = fit_group([{**f, 'onset': ON, 'end': ON+DUR}])
    stop_vec = dict(f['vec']); stop_vec['d_ia'] *= -1; stop_vec['peak_ratio'] = 1; stop_vec['dur_cycles'] = 1
    down = fit_group([{'vec': stop_vec, 'template': [1.0] * 16}])
    p = {'schema': 'nilm_profile/1', 'device_id': 'synthetic', 'version': '1', 'quantity': 'i', 'unit': 'A',
         'features': list(FEATURES), 'pre_cycles': PRE, 'post_cycles': POST, 'startup': g, 'shutdown': down,
         'single_phase': {'version': 1, 'mode': 'current', 'branch_phase': 'A', 'bus_phase': 'A'}}
    return p, z, i


def truncated(p, z, i, n=30):
    return event_features(z, z, i, ON, ON+DUR, PRE, POST, post_hi=ON+DUR+n)


@pytest.mark.parametrize('scale', [.01, 1, 1000])
def test_aligned_reference_uses_same_prefix_and_is_scale_independent(scale):
    p, z, i = fixture(scale)
    f = truncated(p, z, i)
    old = template_distance(f['template'], p['startup']['template'])
    td = _aligned_short_post_template(p, f, ON, ON+DUR, ON+DUR+30, None, N, PRE, POST)
    assert td is not None and td < old
    assert f['vec']['d_ia'] == pytest.approx(truncated(p, z, i)['vec']['d_ia'])


def test_unreliable_reference_or_geometry_does_not_align():
    p, z, i = fixture(); f = truncated(p, z, i); end = ON+DUR
    calc = lambda p, end=end, hi=end+30, pre=None, length=N: _aligned_short_post_template(p, f, ON, end, hi, pre, length, PRE, POST)
    assert calc(p, hi=None) is None                     # no truncation
    assert calc(p, hi=end+24) is None                   # insufficient post
    assert calc(p, hi=end+50) is None                   # full post
    assert calc(p, pre=ON-PRE+1) is None               # pre-window contaminated
    assert calc(p, length=end+POST) is None             # wait for complete data
    assert calc(p, end=end+10, hi=end+40) is None      # duration not comparable
    p2 = copy.deepcopy(p); p2['startup']['n'] = 2
    assert calc(p2) is None                             # averaged template geometry ambiguous
    p2 = copy.deepcopy(p); p2['startup']['mu'][FEATURES.index('peak_ratio')] = 2.0
    assert calc(p2) is None                             # no strong startup impulse
    p2 = copy.deepcopy(p); p2['startup']['template'][5] = float('nan')
    assert calc(p2) is None
    p2 = copy.deepcopy(p); p2['startup']['template'] = [0.0] * 16
    assert calc(p2) is None                             # untrustworthy normalization


def test_detection_aligns_only_template_not_bounds_delta_threshold_or_state(monkeypatch):
    p, z, i = fixture(); boundary = ON+DUR+30
    # Model an independent change just outside the own-transition window. It is STILL a boundary.
    monkeypatch.setattr(npf, '_two_window_candidates', lambda x, pre, post, min_d, k: [(ON, ON+DUR, 6.0)])
    monkeypatch.setattr(npf, 'change_points', lambda x, pre, post, min_d, k: [(boundary+10, -3.0)])
    args = (z, z, i, p, {'max_scale': 1, 'min_scale': 1}, False)
    r = detect_profile(*args, device_state='off', detection_phase='A')[0]
    assert r['post_hi'] == boundary
    assert r['feat']['vec'] == truncated(p, z, i)['vec']
    assert 'post_window_truncated' in r['flags']
    assert r['accepted'] and r['status'] == 'low_confidence'
    # State mismatch and a stricter configured confidence threshold still apply.
    wrong = detect_profile(*args, device_state='on', detection_phase='A')[0]
    assert 'state_mismatch' in wrong['flags']
    assert wrong['confidence'] == pytest.approx(r['confidence'] * .5)
    strict = detect_profile(z, z, i, p, {'max_scale': 1, 'min_scale': 1, 'min_confidence': 1.0}, False,
                            'off', detection_phase='A')[0]
    assert not strict['accepted']
    # An unrelated waveform with different features cannot be rescued from D² rejection.
    alien = i.copy(); alien[0, ON:ON+DUR+POST] *= 10; alien[1] = alien[0]
    bad = detect_profile(z, z, alien, p, {'max_scale': 1, 'min_scale': 1}, False,
                         'off', detection_phase='A')[0]
    assert 'd2_exceeds' in bad['flags'] and not bad['accepted']


def test_scope_or_missing_evidence_uses_original_comparison(monkeypatch):
    p, z, i = fixture(); boundary = ON+DUR+30
    monkeypatch.setattr(npf, '_two_window_candidates', lambda x, pre, post, min_d, k: [(ON, ON+DUR, 6.0)])
    monkeypatch.setattr(npf, 'change_points', lambda x, pre, post, min_d, k: [(boundary+10, -3.0)])
    p['startup']['n'] = 2
    r = detect_profile(z, z, i, p, {'max_scale': 1, 'min_scale': 1}, False, 'off', detection_phase='A')[0]
    assert r['post_hi'] == boundary and 'post_window_truncated' not in r['flags']
    assert r['match']['template_dist'] == pytest.approx(template_distance(r['feat']['template'], p['startup']['template']))


@pytest.mark.parametrize('foreign_step', [-50.0, 50.0])
def test_neighbour_after_boundary_is_not_included_in_feature_or_template(monkeypatch, foreign_step):
    p, z, i = fixture(); boundary = ON+DUR+30
    monkeypatch.setattr(npf, '_two_window_candidates', lambda x, pre, post, min_d, k: [(ON, ON+DUR, 6.0)])
    monkeypatch.setattr(npf, 'change_points', lambda x, pre, post, min_d, k: [(boundary+10, foreign_step)])
    params = {'max_scale': 1, 'min_scale': 1}
    ref = detect_profile(z, z, i, p, params, False, 'off', detection_phase='A')[0]
    neighbour = i.copy(); neighbour[0, boundary+10:] += foreign_step; neighbour[1] = neighbour[0]
    hit = detect_profile(z, z, neighbour, p, params, False, 'off', detection_phase='A')[0]
    assert hit['post_hi'] == boundary
    assert hit['feat']['vec'] == ref['feat']['vec']
    assert hit['feat']['template'] == ref['feat']['template']
    assert hit['status'] == 'low_confidence' and 'post_window_truncated' in hit['flags']


def test_legacy_and_free_stage_do_not_use_new_alignment(monkeypatch):
    p, z, i = fixture(); boundary = ON+DUR+30
    monkeypatch.setattr(npf, '_two_window_candidates', lambda x, pre, post, min_d, k: [(ON, ON+DUR, 6.0)])
    monkeypatch.setattr(npf, 'change_points', lambda x, pre, post, min_d, k: [(boundary+10, -3.0)])
    legacy = copy.deepcopy(p); del legacy['single_phase']
    results = [detect_profile(z, z, i, legacy, {'max_scale': 1, 'min_scale': 1}, False, 'off')[0],
               detect_profile(z, z, i, p, {'max_scale': 1, 'min_scale': 1, 'stage_free': 1}, False,
                              'off', detection_phase='A')[0]]
    for r in results:
        assert r['post_hi'] == boundary and 'post_window_truncated' not in r['flags']
        assert r['match']['template_dist'] == pytest.approx(template_distance(r['feat']['template'], p['startup']['template']))


def test_voltage_current_and_stop_candidates_do_not_invoke_alignment(monkeypatch):
    p, z, i = fixture(); boundary = ON+DUR+30
    monkeypatch.setattr(npf, '_two_window_candidates', lambda x, pre, post, min_d, k: [(ON, ON+DUR, 6.0)])
    monkeypatch.setattr(npf, 'change_points', lambda x, pre, post, min_d, k: [(boundary+10, -3.0)])
    def unexpected(*args, **kwargs):
        raise AssertionError('alignment must not run for this scope/direction')
    monkeypatch.setattr(npf, '_aligned_short_post_template', unexpected)
    p2 = copy.deepcopy(p); p2['quantity'] = 'p'; p2['single_phase']['mode'] = 'voltage_current'
    r = detect_profile(i * 230, z, i, p2, {'max_scale': 1, 'min_scale': 1}, True, 'off', detection_phase='A')[0]
    assert 'post_window_truncated' not in r['flags']
    # Supply a real stop waveform and its own reference, without changing detector scope.
    i2 = i.copy(); i2[0] = 100 - i2[0]; i2[1] = i2[0]
    stop = event_features(z, z, i2, ON, ON+DUR, PRE, POST)
    p2 = copy.deepcopy(p); p2['startup'] = None
    p2['shutdown'] = fit_group([{**stop, 'onset': ON, 'end': ON+DUR}])
    r = detect_profile(z, z, i2, p2, {'max_scale': 1, 'min_scale': 1}, False, 'on', detection_phase='A')[0]
    assert r['match']['direction'] == 'STOP' and 'post_window_truncated' not in r['flags']
