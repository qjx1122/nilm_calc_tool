"""EOF/stop fallback for already captured composite starts."""
import numpy as np

import elec_tool.nilm as nm
from tests.test_joint_composite_start import ON, make_detector


def test_close_reports_captured_incomplete_start_once_without_state(monkeypatch):
    d, _ = make_detector(monkeypatch, members=2)
    n = ON + 180
    d._t = d._t[:n]; d._p = d._p[:, :n]; d._q = d._q[:, :n]
    d._i = d._i[:, :n]; d._ih = d._ih[:, :n]
    assert not d._evaluate_profile('i', 10, n-1)
    assert d._joint_pending_starts
    d.close()
    rows = d.list()
    assert len(rows) == 1 and rows[0]['status'] == 'unknown'
    assert 'composite_start_window_unavailable' in rows[0]['quality_flags']
    assert {v['device_id'] for v in rows[0]['candidate_devices']} == {'dev-0', 'dev-1'}
    assert all(v['evidence_type'] == 'original_profile_candidate' for v in rows[0]['candidate_devices'])
    assert all(s['state'] == 'unknown' for s in d._profiles)
    d.close()
    assert len(d.list()) == 1


def test_csv_reload_preserves_composite_candidate_metadata(monkeypatch, tmp_path):
    from elec_tool.replay_load import load_nilm_events
    d, _ = make_detector(monkeypatch, members=2)
    d.ncfg.save = True
    d.writer = nm.NilmWriter(d.ncfg, source_id=0, dir_override=str(tmp_path))
    ev = d._evaluate_profile('i', 10, ON + 300)
    assert len(ev) == 1
    d.writer.write(ev[0]); d.close()
    rows = load_nilm_events(str(tmp_path), 0)
    assert len(rows) == 1 and rows[0]['status'] == 'unknown'
    assert len(rows[0]['candidate_devices']) == 2
    assert all(v['status'] == 'rejected' and np.isclose(v['composite_metrics']['steady_delta_ia'], 6.)
               for v in rows[0]['candidate_devices'])


def test_evicted_pending_is_unknown_with_saved_timestamps(monkeypatch):
    d, scan = make_detector(monkeypatch, members=2)
    assert not d._evaluate_profile('i', 10, ON + 195)
    start_time = d._t[ON]
    scan['present'] = False
    cut = ON + 20
    d._t = d._t[cut:]; d._i = d._i[:, cut:]; d._ih = d._ih[:, cut:]
    d._p = d._p[:, cut:]; d._q = d._q[:, cut:]; d._g0 += cut
    ev = d._evaluate_profile('i', 10, ON + 200)
    assert len(ev) == 1 and ev[0].status == 'unknown'
    assert ev[0].t_start == start_time
    assert 'composite_start_cache_expired' in ev[0].quality_flags
    assert {v['device_id'] for v in ev[0].candidate_devices} == {'dev-0', 'dev-1'}
    assert all(s['state'] == 'unknown' for s in d._profiles)
