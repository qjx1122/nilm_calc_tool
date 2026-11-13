"""保守小扰动核验；合成数据，现场验收仍以用户回传为准。"""
import numpy as np
import pytest

from elec_tool.nilm_profile import _filter_small_transients, auto_locate_events, build_profile
from tests.test_r212_profile_auto_alternation import (_steps, _series, _inrush, _two_stage_stop, R3)

PRE, POST = 10, 50


def example(scale=1.0):
    x = np.full(10000, 7.0)
    x[1000:] -= .2
    x[2000:2050] -= 1.7
    x[3000:] -= 5.5
    x[5000:] += 5.5
    x[5000:5060] += 4
    x[6000:6030] += 2.3
    x[8000:] -= 5.5
    events = [(1000,1001,'auto:two_window'), (2000,2001,'auto:two_window'),
              (3000,3001,'auto:two_window'), (5000,5001,'auto:two_window'),
              (6000,6001,'auto:two_window'), (8000,8001,'auto:steady_state')]
    return x * scale, events


@pytest.mark.parametrize('scale', [0.01, 1, 1000])
def test_sustained_small_and_two_recovered_excursions_are_reported(scale):
    x, events = example(scale)
    kept, removed = _filter_small_transients(x, events, PRE, POST)
    assert [e[0] for e in kept] == [3000, 5000, 8000]
    assert [e['onset'] for e in removed] == [1000, 2000, 6000]
    assert all(e['reference'] == pytest.approx(5.5 * scale) for e in removed)


def test_short_run_or_nearby_events_and_big_excursion_are_preserved():
    x, events = example()
    # A nearby second candidate makes the decision ambiguous, even for a small pulse.
    extra = (2070, 2071, 'auto:two_window')
    kept, removed = _filter_small_transients(x, events + [extra], PRE, POST)
    assert events[1] in kept and extra in kept
    assert 2000 not in [r['onset'] for r in removed]
    # A full-amplitude short run could be genuine even if only one candidate was located.
    x[6000:6030] += 5
    kept, removed = _filter_small_transients(x, events, PRE, POST)
    assert events[4] in kept


def test_no_reference_boundary_and_non_two_window_are_conservative():
    x, events = example()
    assert _filter_small_transients(x, events[:2], PRE, POST) == (events[:2], [])
    # Only same-direction large events do not establish a reference.
    assert _filter_small_transients(x, [events[0], events[2], events[5]], PRE, POST)[1] == []
    edge = (9900, 9901, 'auto:two_window')
    steady = (1000,1001,'auto:steady_state')
    kept, removed = _filter_small_transients(x, [steady] + events[1:] + [edge], PRE, POST)
    assert edge in kept and steady in kept
    assert all(r['onset'] not in (1000, 9900) for r in removed)


@pytest.mark.parametrize('x', [
    _steps(8000, [(1000,5), (1800,5), (3000,-10), (5000,5), (5800,5), (7000,-10)]),
    _steps(9000, [(800,5), (1600,5), (2400,-5), (3200,-5), (5000,5), (5800,5), (6600,-5), (7400,-5)]),
    _steps(6000, [(1000,10), (1030,-10), (3000,10), (4500,-10)]),
    _series(9000, R3, fluct=0, inrush=_inrush),
    _two_stage_stop(9000, R3),
])
def test_existing_staged_short_inrush_and_slow_stop_scenarios(x):
    old, _ = auto_locate_events(x, 50, PRE, POST)
    new, info = auto_locate_events(x, 50, PRE, POST, filter_small_transients=True)
    assert new == old
    assert not info['filtered_transients']


def test_build_profile_only_filters_current_auto_and_reports_each_candidate(monkeypatch):
    from types import SimpleNamespace
    import elec_tool.nilm_profile as module
    from elec_tool.config import AppConfig
    x, candidates = example()
    c = AppConfig()
    c.sampling.f_nom = 50
    t = 1700000000 + np.arange(len(x)) / 50
    i = np.zeros((4, len(x))); i[0] = i[1] = x
    p = i * 230; q = np.zeros_like(i); h = np.zeros_like(i)
    feat = SimpleNamespace(n_cycle=200, u_phases_present=np.array([True, False, False]))
    monkeypatch.setattr(module, 'load_cycles', lambda *a, **kw: (c, feat, t, p, q, i, h, True))
    calls = []

    def locate(data, cps, pre, post, *, filter_small_transients=False):
        calls.append(filter_small_transients)
        ev, removed = _filter_small_transients(data, candidates, pre, post) if filter_small_transients else (candidates, [])
        return ev, dict(n_two_window=sum(s == 'auto:two_window' for _, _, s in ev), n_refined=0,
                        n_alternation=0, alternation_unresolved=[], filtered_transients=removed)
    monkeypatch.setattr(module, 'auto_locate_events', locate)
    current = build_profile(c, 'example', single_phase_mode='current', branch_phase='A', bus_phase='A', merge_gap_s=0)
    notes = [note for note in current['notes'] if '未直接纳入画像' in note]
    assert len(notes) == 3 and all('人工启停标签' in note and '参考启停幅值' in note for note in notes)
    assert current['startup']['n'] == 1 and current['shutdown']['n'] == 2
    voltage = build_profile(c, 'example', single_phase_mode='voltage_current', branch_phase='A', bus_phase='A', merge_gap_s=0)
    legacy = build_profile(c, 'example', quantity='i', merge_gap_s=0)
    assert calls == [True, False, False]
    assert not any('未直接纳入画像' in n for doc in (voltage, legacy) for n in doc['notes'])
    labeled = build_profile(c, 'example', single_phase_mode='current', branch_phase='A', bus_phase='A',
                            labels=f'{t[3000]},关')
    assert labeled['label_mode'] == 'labels' and calls == [True, False, False]
    assert not any('未直接纳入画像' in n for n in labeled['notes'])


def test_missing_pre_window_and_nonfinite_data_are_not_filtered():
    x, events = example()
    edge = (5, 6, 'auto:two_window')
    x[6100] = np.nan
    kept, removed = _filter_small_transients(x, [edge] + events, PRE, POST)
    assert edge in kept and events[4] in kept
    assert all(r['onset'] not in (5, 6000) for r in removed)
