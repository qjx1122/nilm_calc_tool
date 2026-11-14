import copy
import numpy as np
import pytest

from elec_tool.config import AppConfig
from elec_tool.nilm_profile import ProfileError, build_multi_profile, build_profile

FS, F, T0 = 6400, 50, 1700000000


def make_csv(path, start, running=7.0):
    t = np.arange(4 * FS) / FS
    amp = np.where(t < 2, 2.0 if start else running, running if start else 2.0)
    w = np.sqrt(2) * np.sin(2 * np.pi * F * t)
    with path.open('w', encoding='utf-8') as f:
        f.write('时间,A相电压,A相电流\n')
        for a,b,c in zip(T0+t, 230*w, amp*w):
            f.write(f'{a:.6f},{b:.6f},{c:.6f}\n')
    return str(path)


def config():
    c = AppConfig(); c.sampling.fs=FS; c.sampling.f_nom=F
    c.transform.pt_ratio=c.transform.ct_ratio=1
    return c


def options():
    return dict(single_phase_mode='current', branch_phase='A', bus_phase='A', pre_cycles=10, post_cycles=50)


def test_two_files_fit_independent_events(tmp_path):
    a=make_csv(tmp_path/'start.csv',True); b=make_csv(tmp_path/'stop.csv',False)
    sources=[dict(path=a,source_id='up',labels=f'{T0+2},开'),dict(path=b,source_id='down',labels=f'{T0+2},关')]
    cfg=config(); d=build_multi_profile(cfg,sources,device_id='mixer',**options())
    assert d['startup']['n']==d['shutdown']['n']==1
    assert d['startup']['mu'][0]==pytest.approx(5,abs=.02)
    assert d['shutdown']['mu'][0]==pytest.approx(-5,abs=.02)
    assert d['startup']['events'][0]['source_id']=='up' and d['shutdown']['events'][0]['source_id']=='down'
    assert len(d['startup']['events'][0]['template'])==16
    assert d['source_file']=='' and len(d['source_files'])==2 and d['steady']['level_first_window'] is None
    for src,key in zip(sources,['startup','shutdown']):
        single=build_profile(cfg,src['path'],labels=src['labels'],**options())
        assert d[key]['mu']==single[key]['mu'] and d[key]['template']==single[key]['template']
    ev=d['startup']['events'][0]['event_id']
    with pytest.raises(ProfileError,match='明确确认'):
        build_multi_profile(cfg,sources,selected=[ev],**options())
    partial=build_multi_profile(cfg,sources,selected=[ev],allow_single_direction=True,**options())
    assert partial['startup']['n']==1 and partial['shutdown'] is None
    with pytest.raises(ProfileError,match='不一致'):
        build_multi_profile(cfg,sources,selected=['missing'],**options())
    with pytest.raises(ProfileError,match='重复'):
        build_multi_profile(cfg,[sources[0],sources[0]],**options())
    c2=copy.deepcopy(cfg); c2.transform.ct_ratio=2
    with pytest.raises(ProfileError,match='pt_ct'):
        build_multi_profile(cfg,[sources[0],{**sources[1],'cfg':c2}],**options())


def test_multi_source_api_preview_save_confirmation_and_revision(tmp_path, monkeypatch):
    import json
    from fastapi.testclient import TestClient
    import app.server as srv
    monkeypatch.setenv('ELEC_TOOL_AUTOSTART', '')
    monkeypatch.setenv('ELEC_TOOL_NILM_DIR', str(tmp_path))
    src=make_csv(tmp_path/'start.csv',True)
    data=dict(sources=[dict(path=src,labels=f'{T0+2},开')], device_id='pump',
              base={'fs':FS, 'f_nom':F, 'pt_ratio':1, 'ct_ratio':1}, **options())
    with TestClient(srv.app) as c:
        r=c.post('/api/process/nilm_profile_multi',json=data)
        assert r.status_code==200, r.text
        j=r.json(); assert len(j['events'])==1 and j['saved_to'] is None
        save={**data,'action':'save','revision':j['revision'],'selected':[j['events'][0]['event_id']], 'name':'combined.json'}
        assert c.post('/api/process/nilm_profile_multi',json=save).status_code==400
        r=c.post('/api/process/nilm_profile_multi',json={**save,'allow_single_direction':True})
        assert r.status_code==200, r.text
        doc=json.loads((tmp_path/'combined.json').read_text())
        from elec_tool.nilm_profile import load_profile
        assert load_profile(str(tmp_path/'combined.json'))['startup']['n']==1
        assert doc['device_id']=='pump' and doc['shutdown'] is None
        assert c.post('/api/process/nilm_profile_multi',json={**save,'pre_cycles':11,'allow_single_direction':True}).status_code==400
        # 修改内容但保留原大小和 mtime，也不能沿用旧预览。
        import os
        stat = os.stat(src)
        with open(src,'r+b') as f:
            content=f.read(); at=content.index(b'1700000000'); f.seek(at); f.write(b'1700000001')
        os.utime(src,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        assert c.post('/api/process/nilm_profile_multi',json={**save,'allow_single_direction':True}).status_code==400


def test_same_direction_uses_each_event_not_average_of_profiles(tmp_path):
    paths=[make_csv(tmp_path/f'{i}.csv',True,running=v) for i,v in enumerate((5,7,11))]
    sources=[dict(path=p, labels=f'{T0+2},开') for p in paths]
    doc=build_multi_profile(config(),sources,allow_single_direction=True,**options())
    g=doc['startup']; assert g['n']==3
    values=np.array([e['vec']['d_ia'] for e in g['events']])
    assert g['mu'][0]==pytest.approx(values.mean())
    assert g['sigma'][0]==pytest.approx(values.std(ddof=1))
    assert len({e['source_id'] for e in g['events']})==3
    with pytest.raises(ProfileError, match='同一事件'):
        build_multi_profile(config(),[dict(path=paths[0],labels=f'{T0+2},开\n{T0+2},关')],allow_single_direction=True,**options())


def test_source_content_duplicates_and_limits(tmp_path):
    import shutil
    a=make_csv(tmp_path/'a.csv',True); b=str(tmp_path/'b.csv'); shutil.copyfile(a,b)
    with pytest.raises(ProfileError, match='内容重复'):
        build_multi_profile(config(),[dict(path=a),dict(path=b)],allow_single_direction=True,**options())
    with pytest.raises(ProfileError, match='有限数'):
        build_multi_profile(config(),[dict(path=a)],allow_single_direction=True,merge_gap_s=float('nan'),**options())


def test_each_file_independent_column_map(tmp_path):
    from elec_tool.wave_preview import apply_col_map
    a=make_csv(tmp_path/'start.csv', True)
    b=make_csv(tmp_path/'stop.csv', False)
    lines=(tmp_path/'stop.csv').read_text(encoding='utf8').splitlines()
    with open(b,'w',encoding='utf8') as f:
        f.write('timestamp,ia,ua\n')
        for line in lines[1:]:
            t,u,i=line.split(','); f.write(f'{t},{i},{u}\n')
    c2=config()
    apply_col_map(c2,True,{'timestamp':'1','ua':'3','ia':'2','ub':'','ib':'','uc':'','ic':''},err=ProfileError)
    d=build_multi_profile(config(),[{'path':a,'labels':f'{T0+2},开'},
            {'path':b,'cfg':c2,'labels':f'{T0+2},关'}],**options())
    assert d['startup']['mu'][0]==pytest.approx(5,abs=.02)
    assert d['shutdown']['mu'][0]==pytest.approx(-5,abs=.02)
    assert d['source_files'][1]['columns']['mapping']['ia']=='2'


def test_parallel_build_limit():
    import app.server as srv
    sem=srv._MULTI_PROFILE_BUILD_SLOTS
    assert sem.acquire(blocking=False) and sem.acquire(blocking=False)
    try:
        result=srv._limited_multi_profile_request({})
        assert result.status_code==400 and '并发上限'.encode() in result.body
    finally:
        sem.release(); sem.release()


def test_whole_request_limit_includes_hashing(tmp_path, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    import elec_tool.nilm_profile as npf
    import app.server as srv
    src=make_csv(tmp_path/'sample.csv',True)
    data=dict(sources=[dict(path=src,labels=f'{T0+2},开')],device_id='pump',
              base={'fs':FS,'f_nom':F,'pt_ratio':1,'ct_ratio':1},**options())
    original=npf.profile_source_sha256
    lock=threading.Lock(); ready=threading.Event(); release=threading.Event(); count=[0]
    def slow_hash(path):
        with lock:
            count[0]+=1
            if count[0]==2: ready.set()
        if not release.wait(10): raise TimeoutError('test hash was not released')
        return original(path)
    monkeypatch.setattr(npf,'profile_source_sha256',slow_hash)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(srv._limited_multi_profile_request,data) for _ in range(2)]
        try:
            assert ready.wait(10), 'two jobs did not begin hashing'
            rejected=srv._limited_multi_profile_request(data)
            assert rejected.status_code==400 and '并发上限'.encode() in rejected.body
            assert count[0]==2
        finally:
            release.set()
        results=[f.result(timeout=30) for f in futures]
    assert all(r['ok'] and r['revision'] for r in results)


def test_cancelled_api_request_keeps_slot_until_worker_finishes(monkeypatch):
    import asyncio, threading
    import app.server as srv
    started=threading.Event(); release=threading.Event(); finished=threading.Event()
    def work(_payload):
        started.set()
        try:
            assert release.wait(10)
            return {'ok':True}
        finally:
            finished.set()
    monkeypatch.setattr(srv,'_process_multi_profile_request',work)
    async def scenario():
        task=asyncio.create_task(srv.process_nilm_profile_multi({}))
        try:
            assert await asyncio.to_thread(started.wait,5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
            assert srv._MULTI_PROFILE_BUILD_SLOTS.acquire(blocking=False)
            try:
                assert not srv._MULTI_PROFILE_BUILD_SLOTS.acquire(blocking=False)
            finally:
                srv._MULTI_PROFILE_BUILD_SLOTS.release()
        finally:
            release.set()
        assert await asyncio.to_thread(finished.wait,5)
    asyncio.run(scenario())


def test_multi_profile_worker_keeps_side_context(monkeypatch):
    import asyncio
    import app.server as srv
    monkeypatch.setattr(srv,'_process_multi_profile_request',lambda payload: {'side':srv.current_side()})
    async def scenario():
        token=srv._SIDE.set('branch')
        try: assert await srv.process_nilm_profile_multi({})=={'side':'branch'}
        finally: srv._SIDE.reset(token)
    asyncio.run(scenario())


@pytest.mark.parametrize('row_index,shift',[(1000,1.0),(1280,1.0),(1280,-1.0)])
def test_multi_source_rejects_obvious_internal_time_discontinuity(tmp_path,row_index,shift):
    path=tmp_path/'gapped.csv'; make_csv(path,True)
    lines=path.read_text(encoding='utf8').splitlines()
    for k in range(row_index+1,len(lines)):
        t,u,i=lines[k].split(','); lines[k]=f'{float(t)+shift:.6f},{u},{i}'
    path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    with pytest.raises(ProfileError,match='时标.*不连续'):
        build_multi_profile(config(),[{'path':str(path),'labels':f'{T0+2+shift},开'}],allow_single_direction=True,**options())


def test_multi_source_retains_interpolation_warning(tmp_path):
    path=tmp_path/'missing.csv'; make_csv(path,True)
    lines=path.read_text(encoding='utf8').splitlines(); t,u,_=lines[900].split(','); lines[900]=f'{t},{u},'
    path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    doc=build_multi_profile(config(),[{'path':str(path),'labels':f'{T0+2},开'}],allow_single_direction=True,**options())
    assert doc['source_files'][0]['quality']['interpolated_blocks']>0
    assert any('插值' in note for note in doc['notes'])


def test_synthetic_time_warns_it_cannot_verify_source_gaps(tmp_path):
    path=tmp_path/'gapped.csv'; make_csv(path,True)
    lines=path.read_text(encoding='utf8').splitlines()
    for k in range(1001,len(lines)):
        t,u,i=lines[k].split(','); lines[k]=f'{float(t)+1:.6f},{u},{i}'
    path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    c=config(); c.source.custom_time=True; c.source.custom_time_start=str(T0)
    doc=build_multi_profile(c,[{'path':str(path),'labels':f'{T0+2},开'}],allow_single_direction=True,**options())
    quality=doc['source_files'][0]['quality']
    assert quality['synthetic_time_blocks']>0
    assert any('不能据此核验' in note for note in doc['notes'])


def test_source_gap_rejection_does_not_write_output(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app.server as srv
    monkeypatch.setenv('ELEC_TOOL_AUTOSTART',''); monkeypatch.setenv('ELEC_TOOL_NILM_DIR',str(tmp_path))
    path=tmp_path/'gapped.csv'; make_csv(path,True)
    lines=path.read_text(encoding='utf8').splitlines()
    for k in range(1001,len(lines)):
        t,u,i=lines[k].split(','); lines[k]=f'{float(t)+1:.6f},{u},{i}'
    path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    data=dict(sources=[{'path':str(path),'labels':f'{T0+3},开'}],device_id='p',base={'fs':FS,'f_nom':F,'pt_ratio':1,'ct_ratio':1},**options())
    with TestClient(srv.app) as client:
        result=client.post('/api/process/nilm_profile_multi',json=data)
        assert result.status_code==400 and '不连续' in result.json()['error']
    assert not list(tmp_path.glob('*.json')) and not list(tmp_path.glob('.nilm-profile-*'))


def test_multi_source_preserves_sampling_rate_mismatch_warning(tmp_path):
    path=tmp_path/'wrong-rate.csv'; make_csv(path,True)
    lines=path.read_text(encoding='utf8').splitlines()
    for k in range(1,len(lines)):
        t,u,i=lines[k].split(','); t=T0+(float(t)-T0)*1.2; lines[k]=f'{t:.6f},{u},{i}'
    path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    doc=build_multi_profile(config(),[{'path':str(path),'labels':f'{T0+2.4},开'}],allow_single_direction=True,**options())
    assert doc['source_files'][0]['quality']['fs_mismatch_blocks']>0
    assert any('采样率' in note and '偏差' in note for note in doc['notes'])


def test_quantized_millisecond_timestamps_remain_accepted(tmp_path):
    path=tmp_path/'millisecond.csv'; make_csv(path,True)
    lines=path.read_text(encoding='utf8').splitlines()
    for k in range(1,len(lines)):
        t,u,i=lines[k].split(','); lines[k]=f'{float(t):.3f},{u},{i}'
    path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    doc=build_multi_profile(config(),[{'path':str(path),'labels':f'{T0+2},开'}],allow_single_direction=True,**options())
    assert doc['startup']['n']==1
    assert doc['source_files'][0]['quality']['synthetic_time_blocks']==0


def test_changed_content_with_restored_stat_during_extraction_is_rejected(tmp_path, monkeypatch):
    import os
    import elec_tool.nilm_profile as npf
    path=tmp_path/'source.csv'; make_csv(path,True)
    original=npf.build_profile
    def changed_after_read(*args,**kwargs):
        doc=original(*args,**kwargs)
        st=os.stat(path)
        with path.open('r+b') as f:
            data=f.read(); where=data.index(b'1700000000'); f.seek(where); f.write(b'1700000001')
        os.utime(path,ns=(st.st_atime_ns,st.st_mtime_ns))
        return doc
    monkeypatch.setattr(npf,'build_profile',changed_after_read)
    with pytest.raises(ProfileError,match='读取期间发生变化'):
        build_multi_profile(config(),[{'path':str(path),'labels':f'{T0+2},开'}],allow_single_direction=True,**options())


def test_api_preview_revision_binds_side(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app.server as srv
    monkeypatch.setenv('ELEC_TOOL_AUTOSTART',''); monkeypatch.setenv('ELEC_TOOL_NILM_DIR',str(tmp_path))
    src=make_csv(tmp_path/'source.csv',True)
    data=dict(sources=[dict(path=src,labels=f'{T0+2},开')],device_id='pump',base={'fs':FS,'f_nom':F,'pt_ratio':1,'ct_ratio':1},**options())
    with TestClient(srv.app) as client:
        response=client.post('/api/process/nilm_profile_multi',json=data)
        assert response.status_code==200, response.text
        preview=response.json()
        save={**data,'action':'save','revision':preview['revision'],'selected':[preview['events'][0]['event_id']],'allow_single_direction':True,'name':'side.json'}
        crossed=client.post('/api/branch/process/nilm_profile_multi',json=save)
        assert crossed.status_code==400 and '重新预览' in crossed.json()['error']
        assert not (tmp_path/'side.json').exists()
        correct=client.post('/api/process/nilm_profile_multi',json=save)
        assert correct.status_code==200, correct.text


def test_exclusive_save_failure_cleans_temporary_and_preserves_existing(tmp_path, monkeypatch):
    import json
    import os
    import app.server as srv
    target=tmp_path/'p.json'; target.write_text('existing',encoding='utf8')
    with pytest.raises(FileExistsError): srv._save_json_exclusive(str(target),{'a':1})
    assert target.read_text()=='existing' and not list(tmp_path.glob('.nilm-profile-*'))
    target.unlink()
    def fail(*args): raise OSError('link unavailable')
    monkeypatch.setattr(os,'link',fail)
    with pytest.raises(OSError,match='link unavailable'): srv._save_json_exclusive(str(target),{'a':1})
    assert not target.exists() and not list(tmp_path.glob('.nilm-profile-*'))


def test_exclusive_save_concurrent_creators_do_not_overwrite(tmp_path):
    import json
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import app.server as srv
    target=tmp_path/'p.json'; barrier=threading.Barrier(2)
    def save(value):
        barrier.wait(timeout=5)
        try:
            srv._save_json_exclusive(str(target),{'value':value}); return True
        except FileExistsError: return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        result=list(pool.map(save,[1,2]))
    assert sorted(result)==[False,True] and json.loads(target.read_text())['value'] in (1,2)
    assert not list(tmp_path.glob('.nilm-profile-*'))


def test_exclusive_save_fsync_failure_leaves_no_file(tmp_path, monkeypatch):
    import os
    import app.server as srv
    def fail(_fd): raise OSError('fsync failed')
    monkeypatch.setattr(os,'fsync',fail)
    target=tmp_path/'p.json'
    with pytest.raises(OSError,match='fsync failed'):
        srv._save_json_exclusive(str(target),{'a':1})
    assert not target.exists() and not list(tmp_path.glob('.nilm-profile-*'))
