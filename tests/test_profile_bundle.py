import copy
import json
import pytest
from elec_tool.nilm_profile import (BUNDLE_SCHEMA, FEATURES, ProfileError, build_profile_bundle,
                                    load_profile_bundle, validate_profile_bundle)


def profile(device, dims=8):
    return {'schema':'nilm_profile/1','version':'1.0','device_id':device,'quantity':'i','unit':'A',
            'features':FEATURES[:dims], 'pre_cycles':10,'post_cycles':50,'phases':'A',
            'startup':{'n':1,'mu':[1.0]*dims,'sigma':[1.0]*dims,'template':[1.0]*16},'shutdown':None}


def test_bundle_self_contained_legacy_validation_and_tampering(tmp_path):
    original=[profile('seven',7),profile('eight',8)]
    bundle=build_profile_bundle(original,'set1')
    assert bundle['schema']==BUNDLE_SCHEMA and [m['device_id'] for m in bundle['members']]==['seven','eight']
    assert [len(m['profile']['features']) for m in bundle['members']]==[7,8]
    original[0]['startup']['mu'][0]=123
    assert bundle['members'][0]['profile']['startup']['mu'][0]==1
    p=tmp_path/'bundle.json'; p.write_text(json.dumps(bundle),encoding='utf8')
    assert load_profile_bundle(str(p))==bundle
    tampered=copy.deepcopy(bundle); tampered['members'][0]['profile']['startup']['mu'][0]=2
    with pytest.raises(ProfileError,match='校验失败'): validate_profile_bundle(tampered)
    tampered=copy.deepcopy(bundle); tampered['members'][0]['device_id']='other'
    with pytest.raises(ProfileError,match='校验失败'): validate_profile_bundle(tampered)
    with pytest.raises(ProfileError,match='重复'): build_profile_bundle([profile('x'),profile('x')])
    with pytest.raises(ProfileError,match='1～8'): build_profile_bundle([profile(str(x)) for x in range(9)])
    with pytest.raises(ProfileError,match='不允许嵌套'): build_profile_bundle([bundle])
    bad=profile('bad'); bad['startup']['mu'][0]=float('nan')
    with pytest.raises(ProfileError): build_profile_bundle([bad])


def test_bundle_api_preview_and_exclusive_save(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app.server as srv
    monkeypatch.setenv('ELEC_TOOL_AUTOSTART','')
    monkeypatch.setenv('ELEC_TOOL_NILM_DIR',str(tmp_path))
    paths=[]
    for dev,n in [('a',7),('b',8)]:
        p=tmp_path/f'{dev}.json'; p.write_text(json.dumps(profile(dev,n)),encoding='utf8'); paths.append(str(p))
    with TestClient(srv.app) as c:
        p={'paths':paths,'bundle_id':'pair'}
        r=c.post('/api/process/nilm_profile_bundle',json=p)
        assert r.status_code==200, r.text
        data=r.json(); assert [m['device_id'] for m in data['members']]==['a','b']
        save={**p,'action':'save','revision':data['revision'],'name':'pack.json'}
        (tmp_path/'a.json').write_text(json.dumps(profile('changed',7)),encoding='utf8')
        assert c.post('/api/process/nilm_profile_bundle',json=save).status_code==400
        r=c.post('/api/process/nilm_profile_bundle',json=p); save['revision']=r.json()['revision']
        r=c.post('/api/process/nilm_profile_bundle',json=save)
        assert r.status_code==200, r.text
        assert [m['device_id'] for m in load_profile_bundle(str(tmp_path/'pack.json'))['members']]==['changed','b']
        assert c.post('/api/process/nilm_profile_bundle',json=save).status_code==400
        assert not list(tmp_path.glob('.nilm-profile-*'))


@pytest.mark.parametrize('mutate',[
    lambda p: p.update(startup=['bad']),
    lambda p: p['startup'].pop('n'),
    lambda p: p['startup'].update(template_spread=float('inf')),
    lambda p: p['startup'].update(dur_cycles={'max':'wrong'}),
    lambda p: p['startup'].update(template=[float('nan')]*16),
    lambda p: p['startup'].update(mu=['1']*8),
])
def test_malformed_bundle_member_rejected(mutate):
    p=profile('broken'); mutate(p)
    with pytest.raises(ProfileError): build_profile_bundle([p])


def detector_config(paths):
    from elec_tool.config import AppConfig
    c=AppConfig(); c.nilm.profile_paths=list(map(str,paths)); c.nilm.save=False
    for a in c.nilm.algorithms: c.nilm.algorithms[a]['enabled']=(a=='profile')
    c.nilm.quantity='i'; c.validate(); return c


def test_detector_expands_bundle_and_hot_reload(tmp_path):
    from elec_tool.nilm import NilmDetector
    p=tmp_path/'pack.json'; b=build_profile_bundle([profile('old',7),profile('new',8)],'set')
    p.write_text(json.dumps(b),encoding='utf8')
    c=detector_config([p]); d=NilmDetector(c)
    assert d._joint_active and not d._joint_blocked
    assert [x['profile']['device_id'] for x in d._profiles]==['old','new']
    assert [len(x['profile']['_features']) for x in d._profiles]==[7,8]
    d._profiles[0]['state']='on'; d.update_config(c); assert d._profiles[0]['state']=='on'
    b2=build_profile_bundle([profile('old',7),profile('newer',8)],'set')
    p.write_text(json.dumps(b2),encoding='utf8'); d.update_config(c)
    assert [x['profile']['device_id'] for x in d._profiles]==['old','newer']
    assert all(x['state']=='unknown' for x in d._profiles)
    p.write_text('{"schema":"unknown"}',encoding='utf8'); d.update_config(c)
    assert d._joint_blocked and d._profile is None and '加载失败' in d._profile_err


def test_bundle_mixed_paths_fail_closed_on_duplicate_and_expanded_limit(tmp_path):
    from elec_tool.nilm import NilmDetector
    bundle=tmp_path/'pack.json'; solo=tmp_path/'solo.json'
    bundle.write_text(json.dumps(build_profile_bundle([profile('a'),profile('b')])),encoding='utf8')
    solo.write_text(json.dumps(profile('b')),encoding='utf8')
    d=NilmDetector(detector_config([bundle,solo]))
    assert d._joint_blocked and not d._profile and '重复' in d._profile_err
    bundle.write_text(json.dumps(build_profile_bundle([profile(str(i)) for i in range(8)])),encoding='utf8')
    solo.write_text(json.dumps(profile('extra')),encoding='utf8')
    d=NilmDetector(detector_config([bundle,solo]))
    assert d._joint_blocked and not d._profile and '最多支持 8' in d._profile_err
    solo.unlink(); d=NilmDetector(detector_config([bundle,solo]))
    assert d._joint_blocked and not d._profile


def test_unknown_bundle_schema_with_other_profile_fails_closed(tmp_path):
    from elec_tool.nilm import NilmDetector
    b=tmp_path/'future.json'; b.write_text(json.dumps({'schema':'nilm_profile_bundle/2','bundle_id':'future','members':[]}),encoding='utf8')
    s=tmp_path/'single.json'; s.write_text(json.dumps(profile('single')),encoding='utf8')
    d=NilmDetector(detector_config([b,s]))
    assert d._joint_active and d._joint_blocked and d._profile is None


def test_joint_window_resource_limit_rejects_before_ingest(tmp_path):
    from elec_tool.nilm import NilmDetector
    p=profile('long'); p['pre_cycles']=100000; p['post_cycles']=100000
    path=tmp_path/'large.json'; path.write_text(json.dumps(build_profile_bundle([p])),encoding='utf8')
    d=NilmDetector(detector_config([path]))
    assert d._joint_blocked and '400000' in d._profile_err
    assert d._profile_window_need()==0


def test_joint_semantics_hot_update_resets_states_and_observation_window(tmp_path):
    import numpy as np
    from elec_tool.nilm import NilmDetector
    from elec_tool.config import AppConfig
    p=tmp_path/'pack.json'; p.write_text(json.dumps(build_profile_bundle([profile('a')])),encoding='utf8')
    c=detector_config([p]); d=NilmDetector(c)
    d._profiles[0]['state']='on'; d._t=np.arange(20.); d._g0=100
    changed=AppConfig.from_dict(c.to_dict()); changed.transform.ct_ratio=2
    d.update_config(changed)
    assert d._profiles[0]['state']=='unknown' and len(d._t)==0 and d._g0==120


def test_joint_signature_detects_in_place_config_mutation(tmp_path):
    from elec_tool.nilm import NilmDetector
    p=tmp_path/'pack.json'; p.write_text(json.dumps(build_profile_bundle([profile('a')])),encoding='utf8')
    c=detector_config([p]); d=NilmDetector(c); d._profiles[0]['state']='on'
    c.transform.ct_ratio=2; d.update_config(c)
    assert d._profiles[0]['state']=='unknown'


def test_corrupted_bundle_remains_blocked_on_repeated_reload_and_recovers(tmp_path):
    from elec_tool.nilm import NilmDetector
    pack=tmp_path/'pack.json'; single=tmp_path/'solo.json'
    content=json.dumps(build_profile_bundle([profile('a')]))
    pack.write_text(content,encoding='utf8'); single.write_text(json.dumps(profile('b')),encoding='utf8')
    cfg=detector_config([pack,single]); d=NilmDetector(cfg)
    assert d._joint_active and not d._joint_blocked
    pack.write_text('{broken',encoding='utf8')
    for _ in range(3):
        d.update_config(cfg)
        assert d._joint_active and d._joint_blocked and d._profile is None
    pack.write_text(content,encoding='utf8'); d.update_config(cfg)
    assert d._joint_active and not d._joint_blocked
    assert {s['profile']['device_id'] for s in d._profiles}=={'a','b'}
    assert all(s['state']=='unknown' for s in d._profiles)


def test_initial_malformed_bundle_marker_blocks_mixed_run(tmp_path):
    from elec_tool.nilm import NilmDetector
    broken=tmp_path/'broken.json'; broken.write_text('{"schema":"nilm_profile_bundle/1",broken',encoding='utf8')
    solo=tmp_path/'solo.json'; solo.write_text(json.dumps(profile('b')),encoding='utf8')
    cfg=detector_config([broken,solo]); d=NilmDetector(cfg)
    for _ in range(2):
        assert d._joint_active and d._joint_blocked and d._profile is None
        d.update_config(cfg)


def test_bundle_reload_never_replays_old_observation_window(tmp_path):
    import numpy as np
    from elec_tool.nilm import NilmDetector
    p=tmp_path/'pack.json'; p.write_text(json.dumps(build_profile_bundle([profile('a')])),encoding='utf8')
    cfg=detector_config([p]); d=NilmDetector(cfg)
    d._t=np.arange(20.); d._p=np.zeros((4,20)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    d._g0=100; d._profiles[0]['state']='on'
    p.write_text(json.dumps(build_profile_bundle([profile('new')])),encoding='utf8'); d.update_config(cfg)
    assert d._g0==120 and len(d._t)==0 and d._profiles[0]['state']=='unknown'


def test_bundle_failure_and_recovery_drop_pre_failure_window(tmp_path):
    import numpy as np
    from elec_tool.nilm import NilmDetector
    p=tmp_path/'pack.json'; content=json.dumps(build_profile_bundle([profile('a')]))
    p.write_text(content,encoding='utf8'); cfg=detector_config([p]); d=NilmDetector(cfg)
    def add_window(n):
        d._t=np.arange(n,dtype=float); d._p=np.zeros((4,n)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    add_window(20); p.write_text('{broken',encoding='utf8'); d.update_config(cfg)
    assert d._joint_blocked and not len(d._t) and d._g0==20
    add_window(30); p.write_text(content,encoding='utf8'); d.update_config(cfg)
    assert not d._joint_blocked and not len(d._t) and d._g0==50


def test_switching_legacy_to_bundle_and_sampling_resets_global_offset(tmp_path):
    import numpy as np
    from elec_tool.config import AppConfig
    from elec_tool.nilm import NilmDetector
    legacy=tmp_path/'legacy.json'; legacy.write_text(json.dumps(profile('old')),encoding='utf8')
    pack=tmp_path/'pack.json'; pack.write_text(json.dumps(build_profile_bundle([profile('new')])),encoding='utf8')
    cfg=detector_config([legacy]); d=NilmDetector(cfg); assert not d._joint_active
    d._g0=100; d._t=np.arange(20.); d._p=np.zeros((4,20)); d._q=d._p.copy(); d._i=d._p.copy(); d._ih=d._p.copy()
    new=AppConfig.from_dict(cfg.to_dict()); new.nilm.profile_paths=[str(pack)]; new.sampling.fs=12800; new.validate()
    d.update_config(new)
    assert d._joint_active and d._g0==120 and len(d._t)==0 and d.feat.fs==12800
