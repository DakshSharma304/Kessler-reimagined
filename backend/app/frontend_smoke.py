"""HTTP-only six-workflow smoke test and genuine request/response capture.

python -m app.frontend_smoke --base-url http://127.0.0.1:8000
No frontend, no test doubles, no internal scientific function calls.
"""
import argparse
from datetime import UTC,datetime,timedelta
import json
import math
from pathlib import Path
import sys
import time
import httpx

class SmokeFailure(RuntimeError):
    pass

class Recorder:
    def __init__(self,client,progress=None):
        self.client=client
        self.entries=[]
        self.progress=progress

    def call(self,label,method,path,*,params=None,body=None):
        tick=time.perf_counter()
        response=self.client.request(method,path,params=params,json=body)
        elapsed=time.perf_counter()-tick
        if response.status_code!=200: raise SmokeFailure(f'{label}: HTTP{response.status_code}: {response.text[:2000]}')
        data=response.json()
        self.entries.append({'label':label,'method':method,'path':path,'params':params,'request':body,
            'status_code':response.status_code,'response':data,'elapsed_seconds':elapsed,'payload_bytes':len(response.content)})
        if self.progress: self.progress(f'{label}: HTTP200, {elapsed:.3f}s, {len(response.content)} bytes')
        return data

def require(condition,message):
    if not condition: raise SmokeFailure(message)

def parsed(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))

def run_smoke(client,*,encounter_object_id='27056',persistence_object_id='25544',min_positions=1000,progress=None):
    recorder=Recorder(client,progress)
    call=recorder.call
    now=datetime.now(UTC)
    call('health','GET','/api/health')
    call('status','GET','/api/status')
    schema=call('openapi','GET','/openapi.json')
    require(len(schema['paths'])==21,'Unexpected public API path set; update handoff contract deliberately')
    page=call('A.catalog','GET','/api/objects',params={'limit':500})
    ids=[o['id'] for o in page['items'] if abs((now-parsed(o['element_epoch'])).total_seconds())<=7*86400]
    offset=page['next_offset']
    while len(ids)<min_positions+200 and offset is not None:
        page=call('A.catalog.page','GET','/api/objects',params={'limit':500,'offset':offset})
        ids.extend(o['id'] for o in page['items'] if abs((now-parsed(o['element_epoch'])).total_seconds())<=7*86400)
        offset=page['next_offset']
        if offset is not None and offset>=5000: break # bounded discovery, not every object
    require(len(ids)>=min_positions,'Insufficient supported real objects in selected catalog')
    # Keep the documented copy-paste response small; benchmark bulk separately.
    selected=ids[0]
    positions=call('A.positions','POST','/api/positions',body={'object_ids':ids[:min(3,len(ids))],'epoch':now.isoformat()})
    valid=[o for o in positions['items'] if o['propagation_status']=='OK']
    require(valid and all(all(math.isfinite(x) for x in o['position_km']) for o in valid),'No finite actual positions')
    call('A.details','GET',f'/api/objects/{selected}/metadata')
    call('A.orbit','GET',f'/api/objects/{selected}/trajectory',params={'start_time':now.isoformat(),'sample_count':21})
    call('A.search','GET','/api/objects',params={'search':selected,'limit':1})
    call('catalog.status','GET','/api/catalog/status')
    if min_positions>=1000:
        batch=call('A.bulk_benchmark','POST','/api/positions',body={'object_ids':ids[:min(2000,min_positions+200)],'epoch':now.isoformat()})
        require(sum(o['propagation_status']=='OK' for o in batch['items'])>=min_positions,'Fewer than1000 successfully propagated real objects')
        require(all(o['position_km'] is None or all(math.isfinite(v) for v in o['position_km']) for o in batch['items']),'Nonfinite positions')
    encounters=call('B.encounters','GET','/api/encounters',params={'object_id':encounter_object_id,'sort':'minimum_separation','limit':1})
    require(encounters['items'],'No actual upcoming encounter for chosen object; choose another --encounter-object-id')
    event=encounters['items'][0];eid=event['id']
    call('B.detail','GET',f'/api/encounters/{eid}')
    call('B.object','GET',f"/api/objects/{event['object_1_id']}")
    analysis=call('B.analyze','POST',f'/api/encounters/{eid}/analyze',body={'probability_analysis':True})
    require(analysis['calculated']['status']=='COMPLETE','No supported interior nominal encounter minimum')
    probability=analysis['probability_analysis']
    require(probability['probability_status']=='UNAVAILABLE_NO_COVARIANCE' and probability['calculated_pc'] is None,'Live source must not fabricate covariance/Pc')
    require(probability['socrates_max_probability']==event['socrates_max_probability'],'Source screening metric changed')
    call('B.participants','GET',f'/api/encounters/{eid}/trajectories',params={'sample_count':21})
    constraints={'encounter_id':eid,'maneuvering_object_id':event['object_1_id'],'max_delta_v_m_s':.2,
        'min_lead_time_minutes':5,'max_lead_time_hours':.25,'target_miss_distance_km':10,
        'objective':'MAXIMUM_CLEARANCE','hypothetical_capability_assumed':True,
        'search':{'time_samples':1,'magnitude_samples':2,'max_evaluations':40,'refinement_evaluations':0,'timeout_seconds':25}}
    optimized=call('C.optimize','POST',f'/api/encounters/{eid}/optimize',body=constraints)
    require(optimized['solutions'],'No evaluated feasible maneuver')
    option=optimized['solutions'][0]
    maneuver={'maneuvering_object_id':event['object_1_id'],'maneuver_time':option['maneuver_time'],
        'delta_v_rtn_m_s':option['delta_v_rtn_m_s'],'hypothetical_capability_assumed':True}
    call('C.trajectories','POST',f'/api/encounters/{eid}/trajectories',body=maneuver | {'sample_count':21,
        'numerical_reference_epoch':optimized['numerical_reference_epoch']})
    screens=[]
    for index,alternative in enumerate(optimized['solutions'][:2]):
        proposal=maneuver | {'maneuver_time':alternative['maneuver_time'],'delta_v_rtn_m_s':alternative['delta_v_rtn_m_s']}
        screen=call(f'C.screen.{index+1}','POST',f'/api/encounters/{eid}/screen',body=proposal | {'max_objects':128,
            'max_refinements':50,'post_tca_horizon_hours':.01,'timeout_seconds':5})
        require(screen['catalog']['objects_available']>0 and screen['objects_screened']>0,'Secondary search did not execute')
        screens.append(screen['screening_status'])
    nasa_case='000025994_conj_000037558_20210324_151047_20210323_154356'
    reference=call('D.reference','POST','/api/probability/calculate',body={'reference_case':nasa_case,'independent_benchmark':True})
    require(reference['reference_only'] and abs(reference['relative_difference'])<=2e-9,'NASA reference comparison failed')
    epoch=analysis['calculated']['tca']
    covariance={'matrix_m2':[[1e6,0,0],[0,1e6,0],[0,0,1e6]],'epoch':epoch,'frame':'TEME'}
    assumptions={'kind':'ASSUMED','primary':covariance,'secondary':covariance,'combined_hard_body_radius_m':10}
    scenario=call('D.scenario','POST',f'/api/encounters/{eid}/analyze',body={'probability_inputs':assumptions})
    require(scenario['probability_analysis']['probability_status']=='SCENARIO_WITH_ASSUMED_COVARIANCE','Scenario mislabeled/unavailable')
    simulation=call('D.maneuver_scenario','POST',f'/api/encounters/{eid}/simulate',body=maneuver | {'probability_scenario':assumptions | {'fixed_covariance':True}})
    require(simulation['probability_comparison']['label'].startswith('ILLUSTRATIVE'),'Maneuver Pc lacks illustrative label')
    call('E.weather_status','GET','/api/space-weather/status')
    weather={'date':now.date().isoformat(),'f107_previous_day_sfu':150,'f107_center81_sfu':150,'ap_history':[15]*7,
        'input_category':'USER_SUPPLIED_ASSUMPTION','provenance':{'source':'EXPLICIT_SMOKE_SCENARIO'},'warnings':['Hypothetical constant solar history, not observed weather']}
    density=call('E.density','POST','/api/atmosphere/density',body={'timestamp':now.isoformat(),'latitude_deg':0,'longitude_deg':0,'altitude_m':400000,'space_weather':weather})
    require(density['density_kg_m3']>0,'Actual NRLMSIS density not calculated')
    persistence_body={'start_time':now.isoformat(),'horizon_days':.001,'scenario_mode':'COMPARE','visualization':True,
        'weather_mode':'HYPOTHETICAL_CONSTANT','nominal_f107_sfu':150,'nominal_ap':15,
        'aerodynamic_properties':{'input_category':'HYPOTHETICAL_ASSUMPTION','cd_area_over_mass_m2_kg':.022}}
    persistence=call('E.persistence','POST',f'/api/objects/{persistence_object_id}/persistence',body=persistence_body)
    require(set(persistence['trajectories'])=={'LOW_DRAG','NOMINAL','HIGH_DRAG'},'Atmospheric scenario calculation failed')
    call('E.decay','POST',f'/api/objects/{persistence_object_id}/decay',body=persistence_body | {'scenario_mode':'NOMINAL'})
    debris=call('F.debris','GET','/api/objects',params={'classification':'DEBRIS','limit':5})
    debris_ids=[o['id'] for o in debris['items'] if o['cleanup_eligible']]
    require(debris_ids,'No eligible debris in selected real catalog')
    portfolio=call('F.cleanup','POST','/api/cleanup/optimize',body={'candidate_ids':debris_ids,'constraints':{'max_targets':2,'max_candidates':5}})
    require(portfolio['selected_objects'] and len(portfolio['selected_objects'])<=2,'No valid cleanup portfolio')
    require(all(o['classification']=='DEBRIS' and o['physical_metadata']['mass_kg'] is None for o in portfolio['selected_objects']),'Classification/unknown physical data corrupted')
    return {'status':'PASSED','recorded_at':now.isoformat(),'input_mode':'ACTUAL_HTTP_API; live/cache provenance retained in responses',
        'workflow_results':{'A':'PASSED','B':'PASSED','C':'PASSED','D':'PASSED','E':'PASSED','F':'PASSED'},
        'encounter_id':eid,'secondary_screening_statuses':screens,
        'live_probability_status':probability['probability_status'],'nasa_relative_difference':reference['relative_difference'],
        'cleanup_selected_ids':[o['id'] for o in portfolio['selected_objects']],'entries':recorder.entries}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--encounter-object-id',default='27056')
    parser.add_argument('--persistence-object-id',default='25544')
    parser.add_argument('--record-examples',type=Path)
    args=parser.parse_args()
    try:
        with httpx.Client(base_url=args.base_url,timeout=240,trust_env=False) as client:
            report=run_smoke(client,encounter_object_id=args.encounter_object_id,persistence_object_id=args.persistence_object_id,progress=lambda s:print(s,flush=True))
        if args.record_examples: args.record_examples.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='entries'},indent=2))
        return 0
    except (SmokeFailure,httpx.HTTPError,ValueError) as error:
        print(f'FRONTEND API SMOKE FAILED: {error}',file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
