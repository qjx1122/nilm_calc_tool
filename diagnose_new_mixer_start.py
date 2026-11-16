"""Mode B: extract per-cycle diagnostics for the 2020-12-24 new mixer recording.

Run from the project root using the user's configured Python. The source CSV and
existing outputs are never modified. This is NOT an online replay or a test.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

from elec_tool.config import AppConfig
from elec_tool.nilm_profile import load_cycles

EXPECTED_SOURCE = '8b23e5b35c7496d01b781654fe6bfbb198093a41df8bd3fb8fadcd17c6254333'
EXPECTED_CONFIG = '2229e59a356ec0a9fe872c287a15a46dcdfe8b69b22ef793890e9bd438a3cd87'
EXPECTED_BUNDLE = '0d2ee61abc4bcf770e47b5e0f594d1f2790191e44a9381e06fc650339ff95870'
EXPECTED_RUN = '1794810344531'
# Event CSV's epoch, not a conversion from the workstation's timezone.
EVENT_EPOCH = 1608782425.506
MAX_CYCLES = 100001
OUTDIR = Path('diagnostic_joint_new_mixer_01')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def stop(message):
    raise SystemExit('STOP: ' + message)


def main():
    cfg_path = Path('tmp/config_branch.json')
    run_path = Path('tmp/run_info.json')
    if not cfg_path.is_file() or not run_path.is_file():
        stop('run from the project root with the supplied tmp snapshots')
    cfg_hash = sha256(cfg_path)
    if cfg_hash != EXPECTED_CONFIG:
        stop('config snapshot differs; report its SHA256: ' + cfg_hash)
    with run_path.open(encoding='utf-8-sig') as f:
        run = json.load(f)
    branch = run.get('sides', {}).get('branch', {})
    files = branch.get('profile_files') or []
    if len(files) != 1:
        stop('expected one bundle snapshot in run_info')
    bundle = Path('tmp') / files[0].replace('\\', '/')
    if not bundle.is_file() or sha256(bundle) != EXPECTED_BUNDLE:
        stop('bundle snapshot missing or changed')
    if branch.get('profile_snapshot_sha256') != [EXPECTED_BUNDLE]:
        stop('run_info bundle hash does not match')
    events_path = Path('tmp/nilm/nilm_events_20261116.csv')
    if not events_path.is_file():
        stop('event CSV missing')
    with events_path.open(encoding='utf-8-sig', newline='') as f:
        events = list(csv.DictReader(f))
    if ({r.get('run_id') for r in events} != {EXPECTED_RUN}
            or not any(r.get('algorithm') == 'profile'
                       and abs(float(r.get('t_start') or 0) - EVENT_EPOCH) < 0.002
                       for r in events)):
        stop('event CSV does not match the referenced run and event')
    cfg = AppConfig.load(str(cfg_path))
    if (cfg.source.kind != 'csv_file' or float(cfg.sampling.fs) != 10000
            or float(cfg.sampling.f_nom) != 50 or not cfg.columns.mapping_enabled
            or str(cfg.columns.mapping.get('timestamp')) != '1'
            or str(cfg.columns.mapping.get('ia')) != '4'):
        stop('unexpected source, frequency, or column mapping')
    source = Path(cfg.source.path).resolve()
    if not source.is_file():
        stop('configured source CSV not found: ' + str(source))
    if OUTDIR.exists():
        stop('output directory already exists; change OUTDIR to a NEW name; do not overwrite')
    try:
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        head = 'unavailable'
    print('Python:', sys.executable, 'numpy:', np.__version__, 'HEAD:', head, flush=True)
    print('Source:', source, flush=True)
    before = source.stat()
    digest = sha256(source)
    print('Source bytes:', before.st_size, 'SHA256:', digest, flush=True)
    if digest != EXPECTED_SOURCE:
        stop('source differs from user-reported new file; no export')
    print('Config SHA256:', cfg_hash, 'bundle SHA256:', EXPECTED_BUNDLE, flush=True)
    print('Reference run_id:', EXPECTED_RUN, '(run_info does not record input content SHA or code SHA)', flush=True)
    print('Extracting cycles, please wait...', flush=True)
    _, feat, t, _, _, i4, ih4, _ = load_cycles(
        cfg, str(source), max_cycles=MAX_CYCLES, _check_continuity=True)
    after = source.stat()
    if ((before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
            or sha256(source) != digest):
        stop('source changed during extraction; no export')
    if len(t) >= MAX_CYCLES:
        stop('cycle limit reached; data may be truncated; report this instead of exporting')
    if not (np.isfinite(t).all() and np.isfinite(i4[1]).all()
            and np.isfinite(ih4[1]).all() and np.all(np.diff(t) > 0)):
        stop('non-finite values or non-increasing cycle timestamps')
    if len(t) == 0 or t[0] > EVENT_EPOCH - 10 or t[-1] < EVENT_EPOCH + 20:
        stop('insufficient coverage around startup; cycles={} first={} last={}'.format(
            len(t), float(t[0]) if len(t) else None, float(t[-1]) if len(t) else None))
    quality = feat.source_quality
    print('Cycles:', len(t), 'first epoch:', float(t[0]), 'last epoch:', float(t[-1]), flush=True)
    print('Quality:', json.dumps(quality, ensure_ascii=True), flush=True)
    print('Relative intervals are seconds from event CSV 12:00:25.506; Ia includes DC.', flush=True)
    for a, b in [(-5, -1), (0, 0.2), (0.2, 0.6), (0.6, 1), (1, 2), (3, 5), (10, 20)]:
        mask = (t >= EVENT_EPOCH + a) & (t < EVENT_EPOCH + b)
        vals = i4[1, mask]
        if vals.size:
            print('Interval', a, b, 'cycles:', vals.size, 'Ia median:', round(float(np.median(vals)), 4),
                  'Ia max:', round(float(np.max(vals)), 4), flush=True)
    meta = {'source_sha256': digest, 'source_bytes': before.st_size, 'config_sha256': cfg_hash,
            'bundle_sha256': EXPECTED_BUNDLE, 'reference_run_id': EXPECTED_RUN,
            'analysis_head': head, 'event_epoch_reference': EVENT_EPOCH, 'quality': quality,
            'note': 'offline cycle extraction, not end-to-end replay; runtime source/code SHA not recorded'}
    # New directory + exclusive file: never overwrite previous results.
    try:
        OUTDIR.mkdir()
    except FileExistsError:
        stop('output directory appeared during extraction; no export')
    out = OUTDIR / 'cycles_new_mixer.npz'
    with out.open('xb') as f:
        np.savez_compressed(f, t=t, ia=i4[1], ih_a=ih4[1],
                            metadata_json=np.array(json.dumps(meta, ensure_ascii=True)))
    print('Saved:', out.resolve(), 'bytes:', out.stat().st_size, 'SHA256:', sha256(out), flush=True)
    print('DONE: diagnostic only; existing outputs and source not modified.', flush=True)


if __name__ == '__main__':
    main()
