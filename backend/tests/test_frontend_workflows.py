"""All six workflows execute the existing real scientific services via HTTP."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.probability.cdm import reference_cases,reference_table
from test_visualization import visual_api
from test_encounters import START,FIXTURES
from test_constraints import constraint_input
from test_optimizer import SMALL

def successful(response):
    assert response.status_code==200,response.text
    return response.json()

def test_all_six_frontend_workflows_from_genuine_inputs(visual_api):
    client,engine=visual_api
    # A: no physics in frontend, actual source metadata + SGP4 + ITRS.
    catalog=successful(client.get('/api/objects',params={'classification':'DEBRIS'}))
    selected=catalog['items'][0]['id']
    positions=successful(client.post('/api/positions',json={'object_ids':[selected],'epoch':START.isoformat()}))
    assert positions['items'][0]['propagation_status']=='OK'
    assert successful(client.get(f'/api/objects/{selected}/metadata'))['object']['classification']=='DEBRIS'
    assert successful(client.get(f'/api/objects/{selected}/trajectory',params={'start_time':START.isoformat(),'sample_count':5}))['frame']=='ITRS'
    # B + D: source metric is never called measured Pc.
    encounter=successful(client.get('/api/encounters'))['items'][0];identifier=encounter['id']
    successful(client.get(f'/api/encounters/{identifier}'))
    analyzed=successful(client.post(f'/api/encounters/{identifier}/analyze',json={'probability_analysis':True}))
    assert analyzed['probability_analysis']['probability_status']=='UNAVAILABLE_NO_COVARIANCE'
    assert analyzed['probability_analysis']['calculated_pc'] is None
    assert analyzed['probability_analysis']['socrates_max_probability']==encounter['socrates_max_probability']
    successful(client.get(f'/api/encounters/{identifier}/trajectories',params={'sample_count':5}))
    for case in reference_cases():
        probability=successful(client.post('/api/probability/calculate',json={'reference_case':case,'independent_benchmark':True}))
        assert probability['calculated_pc']==pytest.approx(reference_table()[case]['Pc2D'],rel=2e-9,abs=0)
    # C: actual optimizer, same-anchor displayed alternative, actual secondary search.
    optimized=successful(client.post(f'/api/encounters/{identifier}/optimize',json=constraint_input() | {'search':SMALL.model_dump()}))
    best=optimized['solutions'][0]
    maneuver={'maneuvering_object_id':encounter['object_1_id'],'maneuver_time':best['maneuver_time'],
        'delta_v_rtn_m_s':best['delta_v_rtn_m_s'],'hypothetical_capability_assumed':True}
    paths=successful(client.post(f'/api/encounters/{identifier}/trajectories',json=maneuver | {'sample_count':11,'numerical_reference_epoch':optimized['numerical_reference_epoch']}))
    assert paths['simulation']['modified']['miss_distance_m']==pytest.approx(best['new_miss_distance_m'],abs=.001)
    screen=successful(client.post(f'/api/encounters/{identifier}/screen',json=maneuver | {'max_objects':3,'timeout_seconds':5,'post_tca_horizon_hours':.01,
        'catalog_selection':{'groups':['active']}}))
    assert screen['catalog']['objects_available']==3
    assert screen['screening_status'] in {'SCREENED_WITHIN_COVERAGE','ALERTS_FOUND','INCOMPLETE'}
    assert screen['objects_screened']>=1
    # Explicit covariance scenario; zero-filled missing data is never substituted.
    covariance={'matrix_m2':(1e6*np.eye(3)).tolist(),'frame':'TEME','epoch':analyzed['calculated']['tca']}
    assumptions={'kind':'ASSUMED','primary':covariance,'secondary':covariance,'combined_hard_body_radius_m':10}
    scenario=successful(client.post(f'/api/encounters/{identifier}/analyze',json={'probability_inputs':assumptions}))
    assert scenario['probability_analysis']['probability_status']=='SCENARIO_WITH_ASSUMED_COVARIANCE'
    supplied=successful(client.post(f'/api/encounters/{identifier}/analyze',json={'probability_inputs':assumptions | {'kind':'SUPPLIED'}}))
    assert supplied['probability_analysis']['probability_status']=='CALCULATED_FROM_SUPPLIED_COVARIANCE'
    simulated=successful(client.post(f'/api/encounters/{identifier}/simulate',json=maneuver | {'probability_scenario':assumptions | {'fixed_covariance':True}}))
    assert simulated['probability_comparison']['label'].startswith('ILLUSTRATIVE')
    # E: actual MSIS/drag scenarios and compact real ITRS samples.
    body={'start_time':START.isoformat(),'horizon_days':.001,'scenario_mode':'COMPARE',
        'weather_mode':'HYPOTHETICAL_CONSTANT','nominal_f107_sfu':150,'nominal_ap':15,
        'aerodynamic_properties':{'input_category':'HYPOTHETICAL_ASSUMPTION','cd_area_over_mass_m2_kg':.022},'visualization':True}
    persistence=successful(client.post(f'/api/objects/{selected}/persistence',json=body))
    assert set(persistence['trajectories'])=={'LOW_DRAG','NOMINAL','HIGH_DRAG'}
    assert all(np.isfinite(s['position_km']).all() for t in persistence['trajectories'].values() for s in t['samples'])
    assert persistence['analysis']['scenario_analysis']['scenarios'][0]['boundary']['propagation']['samples'] is None
    # F: persistence result is actually retained and used by the cleanup model.
    cleanup=successful(client.post('/api/cleanup/optimize',json={'candidate_ids':[selected,encounter['object_1_id']],
        'constraints':{'max_targets':1,'max_candidates':2},'policy':{'persistence_weight':1}}))
    assert [o['id'] for o in cleanup['selected_objects']]==[selected]
    assert cleanup['selected_objects'][0]['persistence']['censored_at_horizon']
    assert selected in cleanup['selection_reasons']
    assert cleanup['total_abstract_resource_expenditure']==1
    assert engine.space_weather.dataset is None # explicit assumptions, no hidden weather download

def test_no_data_invalid_inputs_and_calculation_errors(visual_api):
    client,engine=visual_api
    missing=successful(client.post('/api/cleanup/optimize',json={'candidate_ids':['99999999']}))
    assert not missing['selected_objects'] and missing['excluded_objects']['99999999']
    unrankable=successful(client.post('/api/cleanup/optimize',json={'candidate_ids':['34452'],'policy':{'persistence_weight':1}}))
    assert unrankable['status']=='UNAVAILABLE' and unrankable['priority_ranking'][0]['score'] is None
    no_properties=successful(client.post('/api/objects/34452/persistence',json={'horizon_days':.001,'visualization':True}))
    assert no_properties['prediction_status']=='INSUFFICIENT_OBJECT_PROPERTIES' and no_properties['trajectories']=={}
    for request in ({'constraints':{'effort_budget':1}}, {'policy':{'exposure_weight':0}}, {'candidate_ids':['0']},
        {'candidate_ids':['34452','53495'],'constraints':{'max_candidates':1}}):
        assert client.post('/api/cleanup/optimize',json=request).status_code==422
    assert client.get('/api/encounters',params={'start_time':'2026-10-15T00:00:00Z','end_time':'2026-10-11T00:00:00Z'}).status_code==422
    listed=successful(client.get('/api/encounters',params={'sort':'time','limit':2}))['items']
    page=successful(client.get('/api/encounters',params={'sort':'time','offset':1,'limit':1}))['items']
    assert page==listed[1:2]
    assert successful(client.get('/api/encounters',params={'end_time':START.isoformat()}))['items']==[]
    assert client.post('/api/probability/calculate',json={'reference_case':'invalid','independent_benchmark':True}).status_code==422
    assert client.post('/api/cleanup/optimize',json={'candidate_ids':['34452']}).status_code==200

def test_three_concurrent_real_analyses_have_no_application_capacity_rejection(visual_api):
    client,_=visual_api
    identifier=successful(client.get('/api/encounters'))['items'][0]['id']
    def analyze():
        return client.post(f'/api/encounters/{identifier}/analyze',json={'probability_analysis':True})
    with ThreadPoolExecutor(max_workers=3) as workers:
        responses=list(workers.map(lambda _: analyze(),range(3)))
    results=[successful(response) for response in responses]
    misses=[result['calculated']['miss_distance_m'] for result in results]
    assert all(np.isfinite(value) and value>0 for value in misses)
    assert misses==pytest.approx([misses[0]]*3,abs=1e-6)

def test_cors_config_and_local_real_data_paths(tmp_path,monkeypatch):
    config=Settings(cache_directory=tmp_path/'cache',data_directory=FIXTURES,
        catalog_files=(FIXTURES/'gp_actual.json',),metadata_file=FIXTURES/'satcat_actual.csv',allowed_origins=('http://localhost:5173',))
    application=create_app(config)
    with TestClient(application) as client:
        allowed=client.options('/api/positions',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type'})
        assert allowed.status_code==200 and allowed.headers['access-control-allow-origin']=='http://localhost:5173'
        blocked=client.options('/api/positions',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
        assert blocked.status_code==400 and 'access-control-allow-origin' not in blocked.headers
        real=successful(client.get('/api/objects'))
        assert real['total']==3 and real['metadata_source']['retrieval_mode']=='LOCAL'
        assert all(s['retrieval_mode']=='LOCAL' for s in real['catalog']['sources'])
        assert 'offline' in ' '.join(real['warnings']).lower()
    monkeypatch.setenv('KESSLER_ENV','production')
    assert Settings.from_environment().allowed_origins==()
    monkeypatch.setenv('KESSLER_DATA_DIR',str(FIXTURES))
    monkeypatch.setenv('KESSLER_CATALOG_FILES','["gp_actual.json"]')
    monkeypatch.setenv('KESSLER_METADATA_FILE','satcat_actual.csv')
    assert Settings.from_environment().catalog_files==(FIXTURES/'gp_actual.json',)

@pytest.mark.parametrize('variable,value',[
    ('KESSLER_PORT','0'),('KESSLER_HOST','http://localhost'),
    ('KESSLER_ALLOWED_ORIGINS','["*"]'),('KESSLER_ALLOWED_ORIGINS','["https://example.com/path"]'),
    ('KESSLER_ALLOWED_ORIGINS','oops'),('KESSLER_CATALOG_FILES','["absent.json"]')])
def test_invalid_environment_fails_clearly(monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with pytest.raises(ValueError): Settings.from_environment()
