import copy
import json
from elec_tool.nilm_profile import build_profile_bundle, load_profile
from tests.test_r173_harmonic_multi_profile import _write_pair, _cfg_with, _run


def bundle(tmp_path, profiles):
    p=tmp_path/'pack.json'; p.write_text(json.dumps(build_profile_bundle(profiles,'site')),encoding='utf8'); return str(p)


def test_same_device_signatures_remain_ambiguous_without_state_transition(tmp_path):
    a,_=_write_pair(tmp_path); pa=load_profile(a); pb=copy.deepcopy(pa); pb['device_id']='B'
    path=bundle(tmp_path,[pa,pb]); cfg=_cfg_with(path)
    events,det=_run(cfg,[(1,1000),(5,-1000)],dur_s=10)
    events=[e for e in events if e['algorithm']=='profile']
    assert len(events)==2, events
    assert [e['status'] for e in events]==['ambiguous','ambiguous']
    assert [e['profile_direction'] for e in events]==['START','STOP']
    assert all(not e['device_id'] and {c['device_id'] for c in e['candidate_devices']}=={'A','B'} for e in events)
    assert all(x['state']=='unknown' for x in det._profiles)
    assert all('ambiguous_device' in e['quality_flags'] for e in events)


def test_distinguishable_devices_stay_independent(tmp_path):
    a,b=_write_pair(tmp_path); path=bundle(tmp_path,[load_profile(a),load_profile(b)])
    cfg=_cfg_with(path); events,det=_run(cfg,[(1,1000),(5,3000,12)],dur_s=10)
    events=[e for e in events if e['algorithm']=='profile']
    assert [(e['device_id'],e['status']) for e in events]==[('A','confirmed'),('B','confirmed')], events
    assert [s['state'] for s in det._profiles]==['on','on']


def test_ambiguity_survives_csv_and_reload(tmp_path, monkeypatch):
    from elec_tool.replay_load import load_nilm_events
    from elec_tool.nilm import NilmDetector
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'
    cfg=_cfg_with(bundle(tmp_path,[p,q])); cfg.nilm.save=True
    monkeypatch.setenv('ELEC_TOOL_NILM_DIR',str(tmp_path/'events'))
    events,det=_run(cfg,[(1,1000)],dur_s=8); det.writer.close()
    replay=[e for e in load_nilm_events(str(tmp_path/'events'),0) if e['algorithm']=='profile']
    assert len(replay)==1 and replay[0]['status']=='ambiguous'
    assert {v['device_id'] for v in replay[0]['candidate_devices']}=={'A','B'}
    new=NilmDetector(cfg); assert new.load_events(replay)==1
    assert len(new.list()[0]['candidate_devices'])==2


def test_joint_waits_for_all_candidate_onsets_and_rescans_idempotently(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'
    cfg=_cfg_with(bundle(tmp_path,[p,q])); d=nm.NilmDetector(cfg)
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    def fake(*args,**kwargs):
        prof=args[3]; on=100 if prof['device_id']=='A' else 103
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feature=dict(vec=vec, pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={})
        return [dict(onset=on,end=on+2,feat=feature,match=match,confidence=.9,flags=[],accepted=True,status='confirmed',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    prm=cfg.nilm.params('profile'); hold=d._profile_need_one(d._profiles[0]['profile'],1)
    assert d._evaluate_profile('p',10,100+hold)==[]
    assert d._evaluate_profile('p',10,103+hold)==[]
    events=d._evaluate_profile('p',10,105+hold)
    assert len(events)==1 and events[0].status=='ambiguous'
    assert len(events[0].candidate_devices)==2 and all(s['state']=='unknown' for s in d._profiles)
    assert d._evaluate_profile('p',10,106+hold)==[]


def test_partially_overlapping_phase_groups_fail_closed(tmp_path):
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q.update(device_id='B', phases='A')
    cfg=_cfg_with(bundle(tmp_path,[p,q])); events,d=_run(cfg,[(1,1000)],dur_s=8)
    assert not [e for e in events if e['algorithm']=='profile']
    assert any('部分重叠' in e for e in d.errors)
    assert all(s['state']=='unknown' for s in d._profiles)


def test_disjoint_phases_same_time_are_not_suppressed(tmp_path):
    import numpy as np
    from elec_tool.blocks import SampleBlock
    from elec_tool.nilm import NilmDetector
    from tests.test_r226_single_phase_scope import build, config, FS, F, EPOCH
    p=build(tmp_path,'current'); p['device_id']='B'; q=copy.deepcopy(p); q['device_id']='C'; q['single_phase']['bus_phase']='C'
    cfg=config(); cfg.nilm.quantity='i'; cfg.nilm.profile_path=bundle(tmp_path,[p,q]); cfg.nilm.window_cycles=300
    for key in cfg.nilm.algorithms: cfg.nilm.algorithms[key]['enabled']=(key=='profile')
    cfg.nilm.algorithms['profile'].update(max_scale=1,min_scale=1,state_check=0)
    cfg.validate(); det=NilmDetector(cfg)
    t=np.arange(8*int(FS))/FS; w=2*np.pi*F*t
    u=np.array([230*np.sqrt(2)*np.sin(w+ph) for ph in (0,-2*np.pi/3,2*np.pi/3)])
    i=np.array([5*np.sqrt(2)*np.sin(w+ph) for ph in (0,-2*np.pi/3,2*np.pi/3)])
    for k in (1,2): i[k]*=np.where(t>=2,8/5,1)
    out=[]
    for x in range(0,len(t),640): out+=det.ingest(SampleBlock(t=EPOCH+t[x:x+640],u=u[:,x:x+640],i=i[:,x:x+640]))
    events=[e for e in out if e['algorithm']=='profile']
    assert {(e['device_id'],e['channel']) for e in events}=={('B','B'),('C','C')}, events
    assert all(e['status']!='ambiguous' for e in events)
    assert [s['state'] for s in det._profiles]==['on','on']


def test_runtime_snapshot_uses_loaded_bundle_bytes(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from elec_tool.nilm import NilmDetector
    import app.server as srv
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'
    path=bundle(tmp_path,[p,q]); cfg=_cfg_with(path); det=NilmDetector(cfg)
    original=open(path,'rb').read()
    open(path,'wb').write(b'changed after detector load')
    runner=SimpleNamespace(cfg=cfg,persist_path=None,cfg_path=None,engine=SimpleNamespace(nilm=det))
    monkeypatch.setattr(srv,'RUNNERS',{'bus':runner})
    run=tmp_path/'run'; run.mkdir(); srv._dump_run_configs(str(run),'bus')
    info=json.loads((run/'run_info.json').read_text(encoding='utf8'))['sides']['bus']
    assert (run/info['profile_file']).read_bytes()==original
    assert info['profile_snapshot_mode']=='detector_loaded_bytes'
    assert {x['device_id'] for x in info['profile_members']}=={'A','B'}


def test_different_windows_do_not_confirm_competing_early(tmp_path):
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'; q['post_cycles']=80
    cfg=_cfg_with(bundle(tmp_path,[p,q])); events,det=_run(cfg,[(1,1000)],dur_s=12)
    events=[e for e in events if e['algorithm']=='profile']
    assert len(events)==1 and events[0]['status']=='ambiguous', events
    assert {v['device_id'] for v in events[0]['candidate_devices']}=={'A','B'}
    assert all(s['state']=='unknown' for s in det._profiles)


def test_single_member_state_follows_unique_events_once(tmp_path):
    a,_=_write_pair(tmp_path); p=load_profile(a)
    cfg=_cfg_with(bundle(tmp_path,[p])); events,det=_run(cfg,[(1,1000),(5,-1000),(9,1000)],dur_s=14)
    ev=[e for e in events if e['algorithm']=='profile']
    assert [e['profile_direction'] for e in ev]==['START','STOP','START'], ev
    assert all('state_mismatch' not in e['quality_flags'] for e in ev)
    assert det._profiles[0]['state']=='on'


def test_nearby_distinct_candidates_are_not_grouped_on_time_alone(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'
    cfg=_cfg_with(bundle(tmp_path,[p,q])); d=nm.NilmDetector(cfg)
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    def fake(*args,**kwargs):
        on=100 if args[3]['device_id']=='A' else 120
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feature=dict(vec=vec, pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        return [dict(onset=on,end=on+2,feat=feature,match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={}),confidence=.9,flags=[],accepted=True,status='confirmed',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    ev=d._evaluate_profile('p',10,400)
    assert [e.device_id for e in ev]==['A','B'] and all(e.status=='confirmed' for e in ev)


def test_incompatible_nominal_frequency_fails_closed(tmp_path):
    a,_=_write_pair(tmp_path); p=load_profile(a); p['f_nom']=60
    cfg=_cfg_with(bundle(tmp_path,[p])); events,d=_run(cfg,[(1,1000)],dur_s=8)
    assert not [e for e in events if e['algorithm']=='profile']
    assert '额定频率' in d._joint_runtime_error and d._profiles[0]['state']=='unknown'


def test_unmatched_step_reports_unknown_without_advancing_state(tmp_path):
    a,b=_write_pair(tmp_path); cfg=_cfg_with(bundle(tmp_path,[load_profile(a),load_profile(b)]))
    events,d=_run(cfg,[(1,2000)],dur_s=9)
    ev=[e for e in events if e['algorithm']=='profile']
    assert len(ev)==1 and ev[0]['status']=='unknown', ev
    assert not ev[0]['device_id'] and not ev[0]['candidate_devices']
    assert 'unknown_device' in ev[0]['quality_flags']
    assert all(slot['state']=='unknown' for slot in d._profiles)


def test_unknown_observation_does_not_suppress_nearby_known_action(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); cfg=_cfg_with(bundle(tmp_path,[p])); d=nm.NilmDetector(cfg)
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    def fake(*args,**kwargs):
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feature=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={})
        return [dict(onset=on,end=on+2,feat=feature,match=match,confidence=.9,flags=([] if ok else ['d2_exceeds']),accepted=ok,status=('confirmed' if ok else 'rejected'),post_wait=40) for on,ok in [(100,False),(120,True)]]
    monkeypatch.setattr(nm,'detect_profile',fake)
    ev=d._evaluate_profile('p',50,400)
    assert [(x.status,x.device_id) for x in ev]==[('unknown',''),('confirmed','A')]
    assert d._profiles[0]['state']=='on' and not d._evaluate_profile('p',50,401)


def test_end_to_end_multisource_api_bundle_and_runtime(tmp_path, monkeypatch):
    import numpy as np
    from fastapi.testclient import TestClient
    import app.server as srv
    from elec_tool.blocks import SampleBlock
    from elec_tool.nilm import NilmDetector
    from tests.test_multi_source_profile import make_csv, options, config, FS, F, T0
    monkeypatch.setenv('ELEC_TOOL_AUTOSTART',''); monkeypatch.setenv('ELEC_TOOL_NILM_DIR',str(tmp_path))
    src=make_csv(tmp_path/'start.csv',True); paths=[]
    with TestClient(srv.app) as client:
        for dev in ['a','b']:
            req={'sources':[{'path':src,'labels':f'{T0+2},开'}],'device_id':dev,'base':{'fs':FS,'f_nom':F,'pt_ratio':1,'ct_ratio':1},**options()}
            r=client.post('/api/process/nilm_profile_multi',json=req); assert r.status_code==200,r.text
            preview=r.json(); selected=[e['event_id'] for e in preview['events']]
            r=client.post('/api/process/nilm_profile_multi',json={**req,'action':'save','revision':preview['revision'],'selected':selected,'allow_single_direction':True,'name':f'{dev}.json'})
            assert r.status_code==200,r.text; paths.append(r.json()['saved_to'])
        r=client.post('/api/process/nilm_profile_bundle',json={'paths':paths,'bundle_id':'site'}); assert r.status_code==200,r.text
        r=client.post('/api/process/nilm_profile_bundle',json={'paths':paths,'bundle_id':'site','action':'save','revision':r.json()['revision'],'name':'site.json'}); assert r.status_code==200,r.text
        packed=r.json()['saved_to']
    cfg=config(); cfg.nilm.quantity='i'; cfg.nilm.profile_path=packed; cfg.nilm.window_cycles=300
    for key in cfg.nilm.algorithms: cfg.nilm.algorithms[key]['enabled']=(key=='profile')
    cfg.nilm.algorithms['profile'].update(max_scale=1,min_scale=1); cfg.validate(); d=NilmDetector(cfg)
    t=np.arange(8*FS)/FS; w=np.sqrt(2)*np.sin(2*np.pi*F*t)
    u=np.zeros((3,len(t))); i=np.zeros_like(u); u[0]=230*w; i[0]=np.where(t>=2,7,2)*w
    out=[]
    for k in range(0,len(t),640): out+=d.ingest(SampleBlock(t=T0+t[k:k+640],u=u[:,k:k+640],i=i[:,k:k+640]))
    ev=[e for e in out if e['algorithm']=='profile']
    assert len(ev)==1 and ev[0]['status']=='ambiguous', ev
    assert {x['device_id'] for x in ev[0]['candidate_devices']}=={'a','b'}
    assert all(x['state']=='unknown' for x in d._profiles)


def test_deduplicated_candidate_remains_competing_evidence(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'
    d=nm.NilmDetector(_cfg_with(bundle(tmp_path,[p,q])))
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    d._profiles[0]['last_end']=102
    def fake(*args,**kwargs):
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feat=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        return [dict(onset=100,end=102,feat=feat,match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={}),confidence=.9,flags=[],accepted=True,status='confirmed',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    ev=d._evaluate_profile('p',10,400)
    assert len(ev)==1 and ev[0].status=='ambiguous'
    assert {c['device_id'] for c in ev[0].candidate_devices}=={'A','B'}
    assert d._profiles[1]['state']=='unknown'


def test_shared_run_preserves_joint_snapshot_for_each_side_start(tmp_path, monkeypatch):
    import hashlib
    from types import SimpleNamespace
    from elec_tool.nilm import NilmDetector
    import app.server as srv
    a,_=_write_pair(tmp_path); p=load_profile(a)
    path=bundle(tmp_path,[p]); cfg=_cfg_with(path); bus=NilmDetector(cfg); original=open(path,'rb').read()
    runner=lambda detector: SimpleNamespace(cfg=cfg,persist_path=None,cfg_path=None,engine=SimpleNamespace(nilm=detector),thread=SimpleNamespace(is_alive=lambda: True))
    branch=NilmDetector(cfg)
    monkeypatch.setattr(srv,'RUNNERS',{'bus':runner(bus),'branch':runner(branch)})
    run=tmp_path/'run'; run.mkdir(); srv._dump_run_configs(str(run),'bus')
    p2=copy.deepcopy(p); p2['device_id']='new'; open(path,'w',encoding='utf8').write(json.dumps(build_profile_bundle([p2],'site')))
    bus.update_config(cfg)
    srv._dump_run_configs(str(run),'branch')
    info=json.loads((run/'run_info.json').read_text(encoding='utf8'))
    saved=info['sides']['bus']; assert (run/saved['profile_file']).read_bytes()==original
    assert saved['profile_snapshot_sha256']==[hashlib.sha256(original).hexdigest()]
    assert info['starts'][0]['profile_files']==saved['profile_files']
    assert (run/info['starts'][1]['profile_files'][0]).read_bytes()==original
    srv.RUNNERS['bus'].engine.nilm=NilmDetector(cfg)  # 重启创建新的检测器实例
    srv._dump_run_configs(str(run),'bus')
    info=json.loads((run/'run_info.json').read_text(encoding='utf8'))
    assert (run/info['starts'][0]['profile_files'][0]).read_bytes()==original
    assert (run/info['starts'][2]['profile_files'][0]).read_bytes()==open(path,'rb').read()


def test_blocked_joint_snapshot_reports_no_loaded_model(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from elec_tool.nilm import NilmDetector
    import app.server as srv
    a,_=_write_pair(tmp_path); path=bundle(tmp_path,[load_profile(a)])
    cfg=_cfg_with(path); open(path,'w').write('{"schema":"nilm_profile_bundle/1",broken'); d=NilmDetector(cfg)
    runner=SimpleNamespace(cfg=cfg,persist_path=None,cfg_path=None,engine=SimpleNamespace(nilm=d))
    monkeypatch.setattr(srv,'RUNNERS',{'bus':runner})
    run=tmp_path/'run'; run.mkdir(); srv._dump_run_configs(str(run),'bus')
    info=json.loads((run/'run_info.json').read_text(encoding='utf8'))['sides']['bus']
    assert info['profile_snapshot_mode']=='detector_load_failed'
    assert info['profile_files']==[] and '加载失败' in info['profile_error']


def test_reload_does_not_reemit_pre_update_action_in_stream(tmp_path):
    from elec_tool.nilm import NilmDetector
    from tests.test_r173_harmonic_multi_profile import _power_block, FS
    a,_=_write_pair(tmp_path); p=load_profile(a); path=bundle(tmp_path,[p]); cfg=_cfg_with(path)
    d=NilmDetector(cfg); events=[]
    for b in range(int(8*FS/640)):
        t=b*640/FS; events+=d.ingest(_power_block(500 if t<1 else 1500,1.79e9+t))
    assert [(e['device_id'],e['profile_direction']) for e in events if e['algorithm']=='profile']==[('A','START')]
    p['device_id']='new'; open(path,'w',encoding='utf8').write(json.dumps(build_profile_bundle([p],'site')))
    d.update_config(cfg); after=[]
    for b in range(int(8*FS/640),int(16*FS/640)):
        t=b*640/FS; after+=d.ingest(_power_block(1500,1.79e9+t))
    assert not [e for e in after if e['algorithm']=='profile']
    assert d._profiles[0]['state']=='unknown'


def test_shared_run_concurrent_snapshots_remain_valid(tmp_path, monkeypatch):
    import hashlib
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from elec_tool.nilm import NilmDetector
    import app.server as srv
    a,b=_write_pair(tmp_path)
    paths=[]; configs=[]; runners={}
    for side,src in [('bus',a),('branch',b)]:
        path=tmp_path/f'{side}.json'; path.write_text(json.dumps(build_profile_bundle([load_profile(src)],side)),encoding='utf8')
        cfg=_cfg_with(str(path)); configs.append(cfg); paths.append(path)
        runners[side]=SimpleNamespace(cfg=cfg,persist_path=None,cfg_path=None,engine=SimpleNamespace(nilm=NilmDetector(cfg)),thread=SimpleNamespace(is_alive=lambda: True))
    monkeypatch.setattr(srv,'RUNNERS',runners); run=tmp_path/'run'; run.mkdir()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda side:srv._dump_run_configs(str(run),side),('bus','branch')))
    info=json.loads((run/'run_info.json').read_text(encoding='utf8'))
    assert {x['side'] for x in info['starts']}=={'bus','branch'}
    for entry in info['starts']:
        side=entry['side']; raw=paths[0 if side=='bus' else 1].read_bytes()
        assert (run/entry['profile_files'][0]).read_bytes()==raw
        assert entry['profile_snapshot_sha256']==[hashlib.sha256(raw).hexdigest()]


def test_snapshot_write_failure_is_recorded(tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace
    from elec_tool.nilm import NilmDetector
    import app.server as srv
    a,_=_write_pair(tmp_path); path=bundle(tmp_path,[load_profile(a)]); cfg=_cfg_with(path)
    d=NilmDetector(cfg); runner=SimpleNamespace(cfg=cfg,persist_path=None,cfg_path=None,engine=SimpleNamespace(nilm=d))
    monkeypatch.setattr(srv,'RUNNERS',{'bus':runner}); run=tmp_path/'run'; run.mkdir()
    original=os.replace
    def fail_snapshot(src,dst):
        if 'profile_bus' in str(dst): raise OSError('disk full')
        return original(src,dst)
    monkeypatch.setattr(srv.os,'replace',fail_snapshot)
    srv._dump_run_configs(str(run),'bus')
    info=json.loads((run/'run_info.json').read_text(encoding='utf8'))
    assert info['sides']['bus']['profile_snapshot_mode']=='snapshot_write_failed'
    assert 'disk full' in info['sides']['bus']['profile_error']
    assert info['starts'][0]['profile_snapshot_mode']=='snapshot_write_failed'
    assert not list((run/'nilm').glob('.profile-snapshot-*'))


def test_legacy_csv_rotation_preserves_multiple_backups_and_shared_writers(tmp_path, monkeypatch):
    import csv
    from concurrent.futures import ThreadPoolExecutor
    from elec_tool.nilm import NilmWriter, NilmEvent, _CSV_FIELDS
    from elec_tool.config import AppConfig
    import elec_tool.nilm as nm
    monkeypatch.setattr(nm,'wall_day',lambda:'20990101')
    old=tmp_path/'nilm_events_20990101.csv'; old.write_text('unit,run_id\nA,old\n',encoding='utf8')
    backup=tmp_path/'nilm_events_20990101.pre-v090.csv'; backup.write_text('prior backup',encoding='utf8')
    cfg=AppConfig().nilm; cfg.save=True
    writers=[NilmWriter(cfg,source_id=k,dir_override=str(tmp_path)) for k in (0,1)]
    def send(k):
        ev=NilmEvent(id=k+1,algorithm='profile',channel='total',t_start=1,t_end=2,direction='up',magnitude_w=1,
                     delta_p_w=1,delta_q_var=0,delta_i_a=0,pre_p_w=0,post_p_w=1,cycles=1,score=1)
        writers[k].write(ev)
    with ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(send,(0,1)))
    for writer in writers: writer.close(); assert not writer.errors
    rows=list(csv.reader(old.open(encoding='utf-8-sig',newline='')))
    assert rows[0]==_CSV_FIELDS and len(rows)==3 and {r[0] for r in rows[1:]}=={'0','1'}
    assert backup.read_text(encoding='utf8')=='prior backup'
    assert (tmp_path/'nilm_events_20990101.pre-v090-1.csv').read_text(encoding='utf8')=='unit,run_id\nA,old\n'


def test_rotation_failure_never_appends_new_rows_under_old_header(tmp_path, monkeypatch):
    from elec_tool.nilm import NilmWriter, NilmEvent
    from elec_tool.config import AppConfig
    import elec_tool.nilm as nm
    import elec_tool.events as events
    monkeypatch.setattr(nm,'wall_day',lambda:'20990101')
    path=tmp_path/'nilm_events_20990101.csv'; path.write_text('unit,run_id\nA,old\n',encoding='utf8')
    monkeypatch.setattr(events.os,'replace',lambda *a: (_ for _ in ()).throw(OSError('denied')))
    cfg=AppConfig().nilm; cfg.save=True; w=NilmWriter(cfg,dir_override=str(tmp_path))
    w.write(NilmEvent(id=1,algorithm='profile',channel='total',t_start=1,t_end=2,direction='up',magnitude_w=1,
                      delta_p_w=1,delta_q_var=0,delta_i_a=0,pre_p_w=0,post_p_w=1,cycles=1,score=1))
    assert path.read_text(encoding='utf8')=='unit,run_id\nA,old\n'
    assert w.errors and 'denied' in w.errors[0]


def test_snapshot_pins_startup_even_if_detector_reloads_before_dump(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from elec_tool.nilm import NilmDetector
    import app.server as srv
    a,_=_write_pair(tmp_path); p=load_profile(a); path=bundle(tmp_path,[p]); cfg=_cfg_with(path)
    det=NilmDetector(cfg); original=open(path,'rb').read()
    p['device_id']='later'; open(path,'w',encoding='utf8').write(json.dumps(build_profile_bundle([p],'site')))
    det.update_config(cfg)
    runner=SimpleNamespace(cfg=cfg,persist_path=None,cfg_path=None,engine=SimpleNamespace(nilm=det))
    monkeypatch.setattr(srv,'RUNNERS',{'bus':runner}); run=tmp_path/'run'; run.mkdir()
    srv._dump_run_configs(str(run),'bus')
    info=json.loads((run/'run_info.json').read_text(encoding='utf8'))['sides']['bus']
    assert (run/info['profile_file']).read_bytes()==original
    assert info['profile_members'][0]['device_id']=='A'


def test_overlapping_late_competitor_prevents_premature_confirmation(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'
    d=nm.NilmDetector(_cfg_with(bundle(tmp_path,[p,q])))
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    seen={'late':False}
    def fake(*args,**kwargs):
        dev=args[3]['device_id']
        if dev=='B' and not seen['late']: return []
        onset,end=(100,180) if dev=='A' else (130,200)
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feat=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        return [dict(onset=onset,end=end,feat=feat,match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={}),confidence=.9,flags=[],accepted=True,status='confirmed',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    assert d._evaluate_profile('p',10,220)==[]
    assert all(s['state']=='unknown' for s in d._profiles)
    seen['late']=True
    hold=d._profile_need_one(d._profiles[0]['profile'],1)
    ev=d._evaluate_profile('p',10,200+hold)
    assert len(ev)==1 and ev[0].status=='ambiguous'
    assert {c['device_id'] for c in ev[0].candidate_devices}=={'A','B'}
    assert all(s['state']=='unknown' for s in d._profiles)
    assert not d._evaluate_profile('p',10,201+hold)


def test_unique_candidate_rejected_by_state_is_reported_unknown(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); cfg=_cfg_with(bundle(tmp_path,[p])); d=nm.NilmDetector(cfg)
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    d._profiles[0]['state']='on'
    def fake(*args,**kwargs):
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feat=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        return [dict(onset=100,end=102,feat=feat,match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={}),confidence=.4,flags=[],accepted=True,status='confirmed',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    ev=d._evaluate_profile('p',10,300)
    assert len(ev)==1 and ev[0].status=='unknown' and not ev[0].device_id
    assert 'state_mismatch' in ev[0].quality_flags and d._profiles[0]['state']=='on'
    assert not d._evaluate_profile('p',10,301)


def test_continuous_slow_ramp_unknown_is_not_repeated(tmp_path):
    from elec_tool.nilm import NilmDetector
    from tests.test_r173_harmonic_multi_profile import _power_block, FS, N
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p)
    q.update(device_id='B',pre_cycles=10,post_cycles=160)
    cfg=_cfg_with(bundle(tmp_path,[p,q])); d=NilmDetector(cfg); out=[]
    for b in range(int(24*FS/(3*N))):
        t=b*3*N/FS; amp=1000*min(1,max(0,(t-1)/1.2))
        out+=d.ingest(_power_block(500+amp,1.79e9+t))
    events=[e for e in out if e['algorithm']=='profile']
    assert len(events)==1 and events[0]['status']=='unknown',events
    assert all(s['state']=='unknown' for s in d._profiles)


def test_excessive_transition_warns_if_cache_cannot_cover_wait(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); cfg=_cfg_with(bundle(tmp_path,[p])); d=nm.NilmDetector(cfg)
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    def fake(*args,**kwargs):
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=300.,d_ih=0.)
        feat=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        return [dict(onset=50,end=400,feat=feat,match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={}),confidence=.9,flags=[],accepted=True,status='confirmed',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    assert d._evaluate_profile('p',10,490)==[]
    assert '缓存' in d._joint_runtime_error and '漏报' in d._joint_runtime_error
    assert d._profiles[0]['state']=='unknown'


def test_distinct_unknown_intervals_remain_separate(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); d=nm.NilmDetector(_cfg_with(bundle(tmp_path,[load_profile(a)])))
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    def fake(*args,**kwargs):
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feat=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        return [dict(onset=on,end=on+2,feat=feat,match=dict(direction='START',d2=12.,d2_per_dim=2.,margin=2.,contrib={}),confidence=.1,flags=['d2_exceeds'],accepted=False,status='rejected',post_wait=40) for on in (100,120)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    ev=d._evaluate_profile('p',10,400)
    assert [e.status for e in ev]==['unknown','unknown']
    assert [e.g_start for e in ev]==[100,120]
    assert not d._evaluate_profile('p',10,401)


def test_unknown_interval_does_not_suppress_overlapping_later_known_candidate(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); d=nm.NilmDetector(_cfg_with(bundle(tmp_path,[load_profile(a)])))
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    phase={'known':False}
    def fake(*args,**kwargs):
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feat=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        on,end,ok=(120,122,True) if phase['known'] else (100,140,False)
        return [dict(onset=on,end=end,feat=feat,match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={}),confidence=.9,flags=[] if ok else ['d2_exceeds'],accepted=ok,status='confirmed' if ok else 'rejected',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    assert [e.status for e in d._evaluate_profile('p',10,400)]==['unknown']
    phase['known']=True
    ev=d._evaluate_profile('p',10,401)
    assert len(ev)==1 and ev[0].status=='confirmed' and ev[0].device_id=='A'


def test_candidate_limit_counts_sign_flip_rows_across_all_members(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); p=load_profile(a); q=copy.deepcopy(p); q['device_id']='B'
    d=nm.NilmDetector(_cfg_with(bundle(tmp_path,[p,q])))
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    row=dict(onset=100,end=102,accepted=False,flags=['sign_flip'])
    monkeypatch.setattr(nm,'detect_profile',lambda *args,**kwargs:[row]*600)
    assert d._evaluate_profile('p',10,400)==[]
    assert '1000' in d._joint_runtime_error
    assert all(s['state']=='unknown' for s in d._profiles)


def test_joint_observation_ledger_limit_fails_closed_and_recovers(tmp_path, monkeypatch):
    import numpy as np
    import elec_tool.nilm as nm
    a,_=_write_pair(tmp_path); d=nm.NilmDetector(_cfg_with(bundle(tmp_path,[load_profile(a)])))
    d._t=np.arange(500,dtype=float); d._p=np.zeros((4,500)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    d._joint_unknown_intervals=[{'phases':('A',),'start':i,'end':i} for i in range(5000)]
    def fake(*args,**kwargs):
        vec=dict(d_ia=1.,d_ib=1.,d_ic=1.,d_p=1000.,d_q=0.,peak_ratio=1.,dur_cycles=2.,d_ih=0.)
        feat=dict(vec=vec,pre=dict(p=0.,ia=1.,ib=1.,ic=1.),post=dict(p=1000.,ia=2.,ib=2.,ic=2.),d_it=1.)
        return [dict(onset=100,end=102,feat=feat,match=dict(direction='START',d2=1.,d2_per_dim=.1,margin=2.,contrib={}),confidence=.9,flags=[],accepted=True,status='confirmed',post_wait=40)]
    monkeypatch.setattr(nm,'detect_profile',fake)
    assert d._evaluate_profile('p',10,400)==[] and '账本' in d._joint_runtime_error
    assert d._profiles[0]['state']=='unknown'
    d._g0=6000
    ev=d._evaluate_profile('p',10,6400)
    assert len(ev)==1 and ev[0].device_id=='A' and not d._joint_runtime_error
