"""Actual source joins, transparent proxy arithmetic and independent knapsack oracle."""
from datetime import timedelta
from itertools import combinations
import json
from pathlib import Path
import time
import httpx
import pytest
from app.cleanup import (analyze_cleanup,build_candidates,calculate_priorities,
    optimize_cleanup_portfolio,record_persistence_evidence,screening_exposure)
from app.data.cache import FileCache,make_record
from app.data.catalog import parse_catalog
from app.data.metadata import MetadataClient,MetadataUnavailable,SATCAT_URL,parse_metadata
from app.data.socrates import SOCRATES_URL,parse_dataset
from app.engine import Engine
from app.models.cleanup import CleanupConstraints,PriorityPolicy
from app.persistence import analyze_orbital_persistence
from test_celestrak import FIXTURE,NOW
from test_encounters import FIXTURES
from test_decay import props
from test_persistence import assumed_settings,fixture_engine

RAW=(FIXTURES/'satcat_actual.csv').read_text()

def metadata(raw=RAW):
    return parse_metadata(make_record(raw,SATCAT_URL,NOW,NOW,'FETCH_TIME'))

def dataset():
    return parse_dataset(make_record((FIXTURES/'socrates_actual.csv').read_text(),SOCRATES_URL,NOW,NOW,'FETCH_TIME'))

def candidates():
    records,_,_=parse_catalog(make_record(json.dumps(FIXTURE),'fixture',NOW,NOW,'FETCH_TIME'))
    return build_candidates(records.values(),metadata(),dataset(),now=NOW)[0]

def decision_candidates():
    # Explicit synthetic decision inputs, not fabricated orbital/scientific outputs.
    base=next(c for c in candidates() if c.id=='34452')
    return [base.model_copy(update={'id':str(i+1),'screening_exposure':{'count':count,'encounter_ids':['shared']},
        'physical_metadata':base.physical_metadata | {'radar_cross_section_m2':rcs}})
        for i,(count,rcs) in enumerate([(9,.1),(6,10),(5,1),(3,2)])]

def test_actual_metadata_join_classification_altitudes_and_unknowns():
    objects={c.id:c for c in candidates()}
    assert objects['34452'].classification=='DEBRIS' and objects['34452'].eligible
    assert objects['53495'].classification=='PAYLOAD' and not objects['53495'].eligible
    assert objects['100033'].classification=='UNKNOWN' and not objects['100033'].eligible
    assert objects['34452'].orbit_metadata['satcat_apogee_km']==545
    assert objects['34452'].physical_metadata['mass_kg'] is None
    assert objects['34452'].physical_metadata['aerodynamic_area_m2'] is None
    assert objects['34452'].physical_metadata['radar_cross_section_m2']==.017
    assert metadata().records['12'].classification=='ROCKET_BODY'
    assert metadata().records['12'].eligibility_reason is None
    assert metadata().records['25338'].eligibility_reason # even non-operational payload excluded

@pytest.mark.parametrize('updates',[{'operational_status_code':'+'},{'decay_date':'2026-10-10'},
    {'orbit_center':'MO'},{'orbit_type':'DOC'},{'classification':'UNKNOWN'}])
def test_eligibility_is_conservative(updates):
    assert metadata().records['34452'].model_copy(update=updates).eligibility_reason

def test_parser_rejects_malformed_records_and_conflicting_duplicates():
    with pytest.raises(ValueError,match='columns'): metadata('NORAD_CAT_ID\n34452\n')
    with pytest.raises(ValueError,match='usable'): metadata(RAW.splitlines()[0]+'\n'+RAW.splitlines()[3].replace('0.0170','nan')+'\n')
    result=metadata(RAW+RAW.splitlines()[3].replace(',DEB,',',PAY,')+'\n')
    assert result.records['34452'].classification=='UNKNOWN'
    assert result.provenance['duplicate_records']==1

def test_metadata_cache_source_error_preserves_last_verified_data(tmp_path):
    calls=[]
    def fetch(request):
        calls.append(request)
        return httpx.Response(200,text=RAW) if len(calls)==1 else httpx.Response(403)
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        client=MetadataClient(FileCache(tmp_path),http)
        first=client.load(NOW)
        assert client.load(NOW+timedelta(hours=1))==first
        stale=client.load(NOW+timedelta(days=2))
        assert stale.provenance['retrieval_mode']=='STALE_CACHE'
        assert set(stale.records)==set(first.records)
        for identifier,item in stale.records.items():
            assert item.model_dump(exclude={'provenance'})==first.records[identifier].model_dump(exclude={'provenance'})
            assert item.provenance==first.records[identifier].provenance | {'retrieval_mode':'STALE_CACHE'}
        assert stale.provenance['content_sha256']==first.provenance['content_sha256']
        client.load(NOW+timedelta(days=3))
        assert len(calls)==2
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(403))) as http:
        with pytest.raises(MetadataUnavailable,match='403'): MetadataClient(FileCache(tmp_path/'empty'),http).load(NOW)

def test_source_exposure_deduplicates_shared_event_and_limits_coverage():
    source=dataset()
    original=source.encounters[0]
    duplicated=source.model_copy(update={'encounters':[original,original]})
    stats,coverage=screening_exposure(duplicated,NOW)
    assert stats[original.object_1_id]['count']==stats[original.object_2_id]['count']==1
    assert coverage['upcoming_unique_encounters']==1
    assert stats[original.object_1_id]['maximum_socrates_screening_metric']==1
    assert len(coverage['limitations'])==3
    unknown,_=screening_exposure(None,NOW)
    assert unknown=={}

def test_deterministic_scores_and_weight_changes():
    objects=decision_candidates()
    first=optimize_cleanup_portfolio(objects,CleanupConstraints(max_targets=1))
    second=optimize_cleanup_portfolio(objects,CleanupConstraints(max_targets=1),policy=PriorityPolicy(exposure_weight=0,radar_cross_section_weight=1))
    assert first.selected_objects[0].id=='1' and second.selected_objects[0].id=='2'
    assert first==optimize_cleanup_portfolio(objects,CleanupConstraints(max_targets=1))
    assert first.priority_ranking[0].score==pytest.approx(.9)

def test_unknown_weighted_evidence_is_not_zero_or_renormalized():
    scored=calculate_priorities(candidates(),PriorityPolicy(persistence_weight=1))['34452']
    assert scored.score is None and scored.status=='INSUFFICIENT_EVIDENCE'
    assert scored.components['modeled_persistence']['contribution'] is None
    assert scored.components['screening_exposure']['weight']==.5
    assert scored.score_interval[1]-scored.score_interval[0]==pytest.approx(.5)

@pytest.mark.parametrize('constraints',[CleanupConstraints(max_targets=0),
    CleanupConstraints(effort_costs={'1':0,'2':1},effort_budget=0)])
def test_zero_resources_select_none(constraints):
    result=optimize_cleanup_portfolio(decision_candidates(),constraints)
    assert not result.selected_objects and result.total_abstract_resource_expenditure==0

def test_heterogeneous_budget_matches_independently_enumerated_optimum():
    objects=decision_candidates()
    costs={'1':5,'2':3,'3':2,'4':2}
    constraints=CleanupConstraints(max_targets=2,effort_costs=costs,effort_budget=5)
    scores=calculate_priorities(objects)
    oracle=max(sum(scores[c.id].score for c in subset) for count in range(3)
        for subset in combinations(objects,count) if sum(costs[c.id] for c in subset)<=5)
    result=optimize_cleanup_portfolio(objects,constraints)
    assert result.status=='OPTIMAL_WITHIN_CANDIDATE_POOL'
    assert result.total_priority_proxy==pytest.approx(oracle)
    assert {c.id for c in result.selected_objects}=={'2','3'}
    assert result.total_abstract_resource_expenditure<=5 and result.budget_remaining==0

def test_duplicates_exclusions_missing_cost_and_shared_events():
    objects=decision_candidates()
    result=optimize_cleanup_portfolio(objects+[objects[0]],CleanupConstraints(max_targets=4))
    assert len(result.selected_objects)==4
    assert result.unique_screening_encounters_represented==1 and result.shared_screening_encounter_ids==['shared']
    assert not any('prevented_collisions' in key for key in result.model_dump())
    limited=optimize_cleanup_portfolio(objects,CleanupConstraints(excluded_ids=('01',),effort_costs={'1':1,'2':1},effort_budget=2))
    assert [c.id for c in limited.selected_objects]==['2']
    assert '3' in limited.excluded_objects and '1' in limited.excluded_objects
    with pytest.raises(ValueError,match='bound'): optimize_cleanup_portfolio(objects,CleanupConstraints(max_candidates=2))

def test_actual_computed_persistence_reused_without_inventing_lifetime(tmp_path):
    engine=fixture_engine(tmp_path)
    result=analyze_orbital_persistence('34452',props(),assumed_settings(horizon_days=.001,scenario_mode='NOMINAL'),engine=engine,start_time=NOW)
    record_persistence_evidence(engine,result)
    evidence=engine.persistence_evidence['34452']
    assert evidence.modeled_duration_days==pytest.approx(.001)
    assert evidence.censored_at_horizon and evidence.boundary_status=='NOT_REACHED_WITHIN_HORIZON'
    records,_,_=parse_catalog(make_record(json.dumps(FIXTURE),'fixture',NOW,NOW,'FETCH_TIME'))
    objects,_=build_candidates(records.values(),metadata(),dataset(),engine.persistence_evidence,NOW)
    score=calculate_priorities(objects,PriorityPolicy(persistence_weight=1))['34452']
    assert score.score is not None and score.components['modeled_persistence']['value']==pytest.approx(.001/30)
    stale,_=build_candidates(records.values(),metadata(),dataset(),engine.persistence_evidence,NOW+timedelta(days=2))
    assert next(c for c in stale if c.id=='34452').persistence is None

@pytest.mark.live
def test_actual_cleanup_prioritization():
    started=time.perf_counter()
    result=analyze_cleanup(Engine(),CleanupConstraints(max_targets=3,max_candidates=200))
    assert result.status=='OPTIMAL_WITHIN_CANDIDATE_POOL',result.warnings
    assert len(result.selected_objects)==3
    assert all(c.classification in {'DEBRIS','ROCKET_BODY'} and c.eligible for c in result.selected_objects)
    print('ACTUAL_CLEANUP',json.dumps([{'id':c.id,'name':c.name,'classification':c.classification,
        'screening_count':c.screening_exposure['count']} for c in result.selected_objects]),
        'scope',result.coverage['scope'],'truncated',result.coverage['candidate_pool_truncated'],
        'elapsed_seconds',time.perf_counter()-started)
