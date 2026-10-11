"""Checkpoint 6: controlled physical states propagated by the real J2 solver."""

from datetime import timedelta
from hashlib import sha256
import json

import numpy as np
import pytest

from app.models.catalog import CatalogMetadata
from app.models.screening import ScreeningSettings, ScreeningWindow
from app.physics.maneuvers import MU_EARTH, NumericalTrajectory
from app.physics.propagation import StateVector
from app.physics.secondary_comparison import compare_secondary_conjunctions
from app.physics.secondary_search import TrajectoryView
from test_encounters import START

WINDOW=ScreeningWindow(start=START,end=START+timedelta(seconds=1800))
TCA=START+timedelta(seconds=1000)
POLE=np.array([0.,0.,1.])


@pytest.fixture(scope="module")
def numerical_orbits():
    initial=StateVector(timestamp=START,position_m=(7e6,0,0),
        velocity_m_s=(0,float(np.sqrt(MU_EARTH/7e6)),0),frame="GCRS")
    zero=NumericalTrajectory(initial,WINDOW.end,POLE)
    burned=NumericalTrajectory(initial.model_copy(update={"velocity_m_s":
        tuple(np.asarray(initial.velocity_m_s)+[0,1,0])}),WINDOW.end,POLE)
    displacement=np.subtract(burned(TCA).position_m,zero(TCA).position_m)
    unit=displacement/np.linalg.norm(displacement)
    def secondary(identifier,position):
        base=zero(TCA)
        state=StateVector(timestamp=TCA,position_m=tuple(position),
            velocity_m_s=tuple(np.asarray(base.velocity_m_s)+[0,0,100]),frame="GCRS")
        orbit=NumericalTrajectory(state,WINDOW.end,POLE,start=WINDOW.start)
        return TrajectoryView(identifier,WINDOW,"GCRS",orbit,name=f"Constructed numerical orbit {identifier}")
    original=secondary("2",np.asarray(zero(TCA).position_m)-10*unit)
    new_third=secondary("3",np.asarray(burned(TCA).position_m)+10*unit)
    improved_third=secondary("3",np.asarray(zero(TCA).position_m)-50*unit)
    worsened_third=secondary("3",np.asarray(burned(TCA).position_m)+30*unit)
    return zero,burned,original,new_third,improved_third,worsened_third


def compare(orbits,third=None,threshold=.1,zero_burn=False,missing=False):
    zero,burned,original,*_=orbits
    baseline=TrajectoryView("1",WINDOW,"GCRS",zero)
    changed=TrajectoryView("1",WINDOW,"GCRS",zero if zero_burn else burned)
    catalog={} if missing else {"2":original}
    if third is not None:
        catalog["3"]=third
    digest=sha256(json.dumps([(key,list(item.evaluate(START).position_m)) for key,item in catalog.items()]).encode()).hexdigest()
    metadata=CatalogMetadata(objects_available=len(catalog),freshness_status="UNAVAILABLE" if missing else "FRESH",
        sources=[],snapshot_sha256=digest,assembled_at=START,oldest_element_epoch=None,
        newest_element_epoch=None,rejected_record_count=0,duplicate_count=0,
        coverage_limitations=["Controlled constructed numerical orbital-state fixture, not a public full catalog."])
    return compare_secondary_conjunctions(baseline,changed,catalog,ScreeningSettings(
        alert_distance_km=threshold,coarse_step_seconds=20),"constructed-encounter","2",catalog_metadata=metadata)


def test_scenario_a_original_improved_no_additional_alert(numerical_orbits):
    result=compare(numerical_orbits)
    assert result.screening_status=="SCREENED_WITHIN_COVERAGE"
    assert result.screening_complete
    assert result.additional_close_approaches==0
    original=next(item for item in result.secondary_encounters if item.is_original_counterpart)
    assert original.change_in_miss_distance_m > 100
    assert original.classification=="IMPROVED_CLOSE_APPROACH"
    assert result.closest_additional_encounter is None


def test_scenario_b_original_improved_but_new_third_object_alert(numerical_orbits):
    result=compare(numerical_orbits,numerical_orbits[3])
    assert result.screening_status=="ALERTS_FOUND"
    assert result.additional_close_approaches==result.newly_introduced==1
    original=next(item for item in result.secondary_encounters if item.is_original_counterpart)
    third=next(item for item in result.secondary_encounters if not item.is_original_counterpart)
    assert original.change_in_miss_distance_m > 100
    assert third.classification=="NEW_CLOSE_APPROACH"
    assert third.baseline_miss_distance_m > 100
    assert third.maneuvered_miss_distance_m < 100
    assert result.closest_additional_encounter.secondary_object_id=="3"
    print("ACTUAL_NUMERICAL_ADVERSE_CASE "+third.model_dump_json())


def test_scenario_c_existing_secondary_worsened(numerical_orbits):
    result=compare(numerical_orbits,numerical_orbits[5],threshold=2)
    assert result.alert_distance_km == 2
    third=next(item for item in result.secondary_encounters if not item.is_original_counterpart)
    assert third.baseline_below_threshold and third.maneuvered_below_threshold
    assert third.classification=="WORSENED_CLOSE_APPROACH"
    assert result.worsened==1


def test_scenario_d_both_encounters_improved(numerical_orbits):
    result=compare(numerical_orbits,numerical_orbits[4])
    assert len(result.secondary_encounters)==2
    assert all(item.classification=="IMPROVED_CLOSE_APPROACH" for item in result.secondary_encounters)
    assert result.improved==1 and result.additional_close_approaches==0


def test_scenario_e_unavailable_and_incomplete_do_not_pass(numerical_orbits):
    unavailable=compare(numerical_orbits,missing=True)
    assert unavailable.screening_status=="UNAVAILABLE" and not unavailable.screening_complete
    zero,burned,original,*_=numerical_orbits
    baseline=TrajectoryView("1",WINDOW,"GCRS",zero)
    changed=TrajectoryView("1",WINDOW,"GCRS",burned)
    metadata=CatalogMetadata(objects_available=1,freshness_status="STALE",sources=[],
        snapshot_sha256="constructed-partial",assembled_at=START,oldest_element_epoch=None,
        newest_element_epoch=None,rejected_record_count=0,duplicate_count=0,
        failed_sources=["Required constructed dataset missing"],coverage_limitations=["Partial"])
    result=compare_secondary_conjunctions(baseline,changed,{"2":original},ScreeningSettings(),
        "constructed-encounter","2",catalog_metadata=metadata)
    assert result.screening_status=="INCOMPLETE" and not result.screening_complete


def test_scenario_f_zero_burn_does_not_invent_changes(numerical_orbits):
    result=compare(numerical_orbits,numerical_orbits[4],zero_burn=True)
    assert result.screening_complete
    assert all(item.classification=="UNCHANGED" for item in result.secondary_encounters)
    assert all(abs(item.change_in_miss_distance_m) < 1e-6 for item in result.secondary_encounters)
    assert result.newly_introduced==result.worsened==result.improved==0


def test_different_windows_are_rejected(numerical_orbits):
    zero,*_=numerical_orbits
    baseline=TrajectoryView("1",WINDOW,"GCRS",zero)
    other=TrajectoryView("1",ScreeningWindow(start=START,end=START+timedelta(seconds=100)),"GCRS",zero)
    with pytest.raises(ValueError,match="same primary"):
        compare_secondary_conjunctions(baseline,other,{},ScreeningSettings(),"fixture","2")
