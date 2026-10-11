from datetime import UTC,datetime,timedelta
import json
import time
import astropy.units as u
from astropy.coordinates import TEME,ITRS,CartesianRepresentation
from astropy.time import Time
from fastapi.testclient import TestClient
import httpx
import numpy as np
import pytest
from app.api.routes import get_engine
from app.data.metadata import SATCAT_URL
from app.engine import Engine
from app.main import app
from app.models.visualization import PositionRequest,ManeuverTrajectoryRequest
from app.models.orbital import GPElements
from app.physics.propagation import propagate_object
from app.visualization import bulk_positions,itrs_positions,maneuver_trajectories
from test_cleanup import RAW
from test_encounters import FIXTURES,START,actual_case
from test_constraints import constraint_input
from test_optimizer import SMALL

@pytest.fixture
def visual_api(tmp_path):
    records=json.loads((FIXTURES/'gp_actual.json').read_text())
    def fetch(request):
        if str(request.url)==SATCAT_URL: return httpx.Response(200,text=RAW)
        if '/SOCRATES/' in request.url.path: return httpx.Response(200,text=(FIXTURES/'socrates_actual.csv').read_text())
        identifier=request.url.params.get('CATNR')
        return httpx.Response(200,json=records if identifier is None else [r for r in records if str(r['NORAD_CAT_ID'])==identifier])
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        engine=Engine(tmp_path,http)
        app.dependency_overrides[get_engine]=lambda:engine
        try:
            with TestClient(app) as client: yield client,engine
        finally: app.dependency_overrides.clear()

def test_actual_catalog_browser_and_details(visual_api):
    client,_=visual_api
    data=client.get('/api/objects',params={'limit':1}).json()
    assert data['total']==3 and len(data['items'])==1 and data['next_offset']==1
    assert client.get('/api/objects',params={'search':'STARLINK'}).json()['items'][0]['id']=='53495'
    assert client.get('/api/objects',params={'search':'34452'}).json()['items'][0]['classification']=='DEBRIS'
    assert client.get('/api/objects',params={'classification':'UNKNOWN'}).json()['items'][0]['id']=='100033'
    assert client.get('/api/objects',params={'classification':'DEBRIS'}).json()['total']==1
    assert client.get('/api/objects',params={'offset':3}).json()['items']==[]
    info=client.get('/api/objects/34452/metadata')
    assert info.status_code==200,info.text
    assert info.json()['object']['cleanup_eligible'] and info.json()['metadata']['mass_kg'] is None
    assert info.json()['orbit']['elements']['object_id']=='34452'

def test_actual_itrs_units_and_independent_astropy_transform(visual_api):
    client,engine=visual_api
    result=client.post('/api/positions',json={'object_ids':['053495','34452','99999999'],'epoch':START.isoformat()})
    assert result.status_code==200,result.text
    data=result.json();first=data['items'][0]
    assert first['id']=='53495' and first['frame']=='ITRS' and first['position_units']=='km'
    state=propagate_object(engine.public_catalog().records['53495'],START)
    direct=TEME(CartesianRepresentation(np.array(state.position_m)*u.m),obstime=Time(START)).transform_to(ITRS(obstime=Time(START)))
    np.testing.assert_allclose(first['position_km'],direct.cartesian.xyz.to_value(u.km),atol=1e-8,rtol=0)
    assert np.linalg.norm(first['position_km'])==pytest.approx(np.linalg.norm(state.position_m)/1000,rel=1e-12)
    assert data['items'][2]['position_km'] is None and data['items'][2]['propagation_status']=='NOT_IN_CATALOG'
    later=client.post('/api/positions',json={'object_ids':['53495'],'epoch':(START+timedelta(minutes=1)).isoformat()}).json()['items'][0]
    assert np.linalg.norm(np.array(first['position_km'])-later['position_km'])>100
    stale_response=client.post('/api/positions',json={'object_ids':['53495'],'epoch':(START+timedelta(days=30)).isoformat()}).json()
    stale=stale_response['items'][0]
    assert stale['propagation_status']=='OK' and np.isfinite(stale['position_km']).all()
    assert any('may be unreliable' in warning for warning in stale_response['warnings'])

def test_real_sgp4_failure_is_isolated_without_mocking_physics(visual_api):
    _,engine=visual_api
    catalog=engine.public_catalog()
    record=catalog.records['53495']
    # Deliberately invalid operational orbit (perigee inside Earth), valid GP schema.
    elements=GPElements.model_validate(record.elements.model_dump() | {'eccentricity':.99})
    catalog.records['53495']=record.model_copy(update={'elements':elements})
    result=bulk_positions(engine,PositionRequest(object_ids=['53495','34452'],epoch=START))
    assert result.items[0].propagation_status=='SGP4_ERROR' and result.items[0].position_km is None
    assert result.items[1].propagation_status=='OK' and np.isfinite(result.items[1].position_km).all()

def test_actual_orbit_and_encounter_trajectories(visual_api):
    client,_=visual_api
    orbit=client.get('/api/objects/34452/trajectory',params={'start_time':START.isoformat(),'sample_count':21})
    assert orbit.status_code==200,orbit.text
    assert len(orbit.json()['samples'])==21 and all(s['propagation_status']=='OK' for s in orbit.json()['samples'])
    event=client.get('/api/encounters').json()['items'][0]
    result=client.get(f"/api/encounters/{event['id']}/trajectories",params={'sample_count':5})
    assert result.status_code==200,result.text
    assert result.json()['participant_ids']==[event['object_1_id'],event['object_2_id']]
    assert all(t['frame']=='ITRS' and len(t['samples'])==5 for t in result.json()['trajectories'])

@pytest.mark.parametrize('method,path,kwargs',[
    ('get','/api/objects',{'params':{'limit':0}}),
    ('get','/api/objects',{'params':{'classification':'OPERATIONAL'}}),
    ('post','/api/positions',{'json':{'object_ids':['0']}}),
    ('post','/api/positions',{'json':{'object_ids':['53495'],'epoch':'2026-10-11T00:00:00'}}),
    ('post','/api/positions',{'json':{'object_ids':[]}}),
    ('get','/api/objects/53495/trajectory',{'params':{'sample_count':1}}),
    ('get','/api/objects/53495/trajectory',{'params':{'start_time':'not-a-time'}}),
    ('get','/api/objects/53495/trajectory',{'params':{'start_time':START.isoformat(),'end_time':(START+timedelta(days=2)).isoformat()}})])
def test_invalid_visualization_requests(visual_api,method,path,kwargs):
    response=getattr(visual_api[0],method)(path,**kwargs)
    assert response.status_code==422,response.text

def test_optimizer_visualization_reuses_reference_and_real_simulator(visual_api):
    client,engine=visual_api
    event,*_=actual_case()
    result=client.post(f'/api/encounters/{event.id}/optimize',json=constraint_input() | {'search':SMALL.model_dump()})
    assert result.status_code==200,result.text
    optimization=result.json();option=optimization['solutions'][0]
    request={'maneuvering_object_id':event.object_1_id,'maneuver_time':option['maneuver_time'],
        'delta_v_rtn_m_s':option['delta_v_rtn_m_s'],'hypothetical_capability_assumed':True,'sample_count':31,
        'numerical_reference_epoch':optimization['numerical_reference_epoch']}
    paths=client.post(f'/api/encounters/{event.id}/trajectories',json=request)
    assert paths.status_code==200,paths.text
    data=paths.json()
    assert data['simulation']['modified']['miss_distance_m']==pytest.approx(option['new_miss_distance_m'],abs=.001)
    assert len(data['baseline']['samples'])==31 and data['modified']['samples']!=data['baseline']['samples']
    zero=maneuver_trajectories(engine,event.id,ManeuverTrajectoryRequest(**(request | {'delta_v_rtn_m_s':[0,0,0]})))
    np.testing.assert_allclose([s.position_km for s in zero.baseline.samples],[s.position_km for s in zero.modified.samples],rtol=0,atol=1e-5)

@pytest.mark.live
def test_actual_thousand_object_batch_and_payload_benchmark():
    engine=Engine();catalog=engine.public_catalog()
    at=datetime.now(UTC)
    ids=[i for i,r in catalog.records.items() if abs((at-r.elements.epoch).total_seconds())<=7*86400][:1200]
    assert len(ids)>=1000,'Actual available supported public catalog required'
    engine.metadata.load() # cold ingestion reported separately, not hidden as batch propagation
    started=time.perf_counter();result=bulk_positions(engine,PositionRequest(object_ids=ids,epoch=at));elapsed=time.perf_counter()-started
    valid=[i for i in result.items if i.propagation_status=='OK']
    assert len(valid)>=1000 and all(np.isfinite(i.position_km).all() for i in valid)
    payload=result.model_dump_json()
    assert len(payload.encode())<1000000
    print('ACTUAL_BATCH',len(result.items),'OK',len(valid),'elapsed_seconds',elapsed,'payload_bytes',len(payload.encode()),'frame',result.frame,'units',result.position_units)
