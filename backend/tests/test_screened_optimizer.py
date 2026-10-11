"""Checkpoint 7: original optimizer plus actual numerical finalist screening."""

from datetime import timedelta
from hashlib import sha256
import json

import numpy as np
import pytest

from app.data.cache import FileCache
from app.data.catalog import CatalogLoader
from app.models.catalog import CatalogMetadata, CatalogSelection
from app.models.maneuver import ManeuverConstraints
from app.models.screening import ScreeningSettings, ScreeningWindow, SecondaryOptimizationSettings
from app.optimization.optimizer import optimize_maneuver
from app.optimization.screened_optimizer import optimize_with_secondary_screening, screen_ranked_finalists
from app.physics.frames import rtn_basis
from app.physics.maneuvers import MU_EARTH, NumericalTrajectory
from app.physics.propagation import StateVector
from app.physics.secondary_comparison import compare_secondary_conjunctions
from app.physics.secondary_search import TrajectoryView
from test_constraints import constraint_input
from test_encounters import START, FIXTURES, actual_case
from test_optimizer import SMALL


def primary(**updates):
    encounter,first,second=actual_case()
    constraints=ManeuverConstraints(**constraint_input(max_lead_time_hours=.5,**updates))
    return optimize_maneuver(encounter,first,second,constraints,SMALL,START,retain_finalists=10)


def numerical_screening_callback(result,settings,unavailable=False):
    """Physical constructed-state fixture for finalist policy post-processing.

    Primary options/ranks are genuine Phase 1 outputs. Every secondary assessment
    applies that option's actual RTN impulse/time to controlled orbital states;
    this fixture tests policy mechanics, not agreement with a live GP orbit.
    Separate integration below uses selected GP differential trajectories.
    """
    encounter,*_=actual_case()
    anchor=result.numerical_reference_epoch
    end=encounter.time_of_closest_approach+timedelta(seconds=36)
    initial=StateVector(timestamp=anchor,position_m=(7e6,0,0),
        velocity_m_s=(0,float(np.sqrt(MU_EARTH/7e6)),0),frame="GCRS")
    pole=np.array([0.,0.,1.])
    zero=NumericalTrajectory(initial,end,pole)
    def modified(option):
        before=zero(option.maneuver_time)
        impulse=rtn_basis(before)@np.asarray(option.delta_v_rtn_m_s)
        after=before.model_copy(update={"velocity_m_s":tuple(np.asarray(before.velocity_m_s)+impulse)})
        changed=NumericalTrajectory(after,end,pole)
        return lambda at:zero(at) if at<option.maneuver_time else changed(at)
    target=encounter.time_of_closest_approach
    top=modified(result.evaluated_finalists[0])
    def other(position):
        state=StateVector(timestamp=target,position_m=tuple(position),
            velocity_m_s=tuple(np.asarray(zero(target).velocity_m_s)+[0,0,100]),frame="GCRS")
        return NumericalTrajectory(state,end,pole,start=anchor)
    original=other(np.asarray(zero(target).position_m)+[0,0,10])
    third=other(np.asarray(top(target).position_m)+[0,0,10])
    digest=sha256(json.dumps([list(original(anchor).position_m),list(third(anchor).position_m)]).encode()).hexdigest()
    metadata=CatalogMetadata(objects_available=0 if unavailable else 2,
        freshness_status="UNAVAILABLE" if unavailable else "FRESH",sources=[],snapshot_sha256=digest,
        assembled_at=START,oldest_element_epoch=None,newest_element_epoch=None,
        rejected_record_count=0,duplicate_count=0,
        coverage_limitations=["Controlled numerical orbital-state fixture, not live GP coverage"])
    def screen(option,deadline):
        window=ScreeningWindow(start=option.maneuver_time,end=end)
        catalog={} if unavailable else {
            "34452":TrajectoryView("34452",window,"GCRS",original,name="Constructed original counterpart"),
            "300001":TrajectoryView("300001",window,"GCRS",third,name="Constructed third object"),
        }
        config=ScreeningSettings(**settings.model_dump(exclude={"policy","max_finalists","total_timeout_seconds"}))
        return compare_secondary_conjunctions(TrajectoryView("53495",window,"GCRS",zero),
            TrajectoryView("53495",window,"GCRS",modified(option)),catalog,config,encounter.id,
            "34452",catalog_metadata=metadata,deadline=deadline)
    return screen


def policy_settings(**updates):
    return SecondaryOptimizationSettings(**(dict(policy="REJECT_NEW_ALERTS",max_finalists=3,
        alert_distance_km=.05,post_tca_horizon_hours=.01,coarse_step_seconds=30)|updates))


def test_optional_disabled_preserves_original_optimizer():
    encounter,first,second=actual_case()
    constraints=ManeuverConstraints(**constraint_input())
    original=optimize_maneuver(encounter,first,second,constraints,SMALL,START)
    unchanged=optimize_with_secondary_screening(encounter,first,second,constraints,SMALL,now=START)
    assert original.solutions==unchanged.solutions
    assert unchanged.secondary_screening is None
    assert original.candidates_evaluated==unchanged.candidates_evaluated==13


def test_ranked_retained_options_are_genuine_ordered_and_not_public_pool():
    result=primary()
    assert len(result.evaluated_finalists)==10
    assert result.evaluated_finalists[0]==result.solutions[0]
    assert [item.new_miss_distance_m for item in result.evaluated_finalists]==sorted(
        [item.new_miss_distance_m for item in result.evaluated_finalists],reverse=True)
    assert "evaluated_finalists" not in result.model_dump(mode="json")


def test_rejected_top_candidate_tries_next_calculated_option():
    result=primary()
    settings=policy_settings()
    screened=screen_ranked_finalists(result,settings,numerical_screening_callback(result,settings))
    summary=screened.secondary_screening
    assert summary.candidate_results[0].policy_passed is False
    assert summary.candidate_results[0].screening.newly_introduced>=1
    assert summary.candidates_screened>=2
    assert summary.selected_primary_rank>1
    assert screened.solutions and summary.candidate_results[-1].policy_passed is True
    assert summary.candidates_screened<=3<screened.candidates_evaluated
    assert screened.solutions[0].delta_v_m_s<=screened.constraints.effective_delta_v_budget_m_s+1e-12
    screened.constraints.validate_burn_time(actual_case()[0],screened.solutions[0].maneuver_time,START)


def test_report_only_preserves_primary_candidates_and_reports_alerts():
    result=primary()
    original=list(result.solutions)
    settings=policy_settings(policy="REPORT_ONLY")
    screened=screen_ranked_finalists(result,settings,numerical_screening_callback(result,settings))
    assert screened.solutions==original
    assert screened.secondary_screening.candidates_screened==1
    assert screened.secondary_screening.candidate_results[0].screening.newly_introduced>=1
    assert any("unscreened alternatives" in warning for warning in screened.secondary_screening.warnings)


def test_reject_all_alerts_and_no_acceptable_candidate_are_explicit():
    result=primary()
    settings=policy_settings(policy="REJECT_ALL_ALERTS",max_finalists=1)
    screened=screen_ranked_finalists(result,settings,numerical_screening_callback(result,settings))
    assert screened.status=="NO_ACCEPTABLE_SCREENED_SOLUTION"
    assert screened.solutions==[]
    assert screened.secondary_screening.candidate_results[0].policy_passed is False
    assert screened.secondary_screening.selected_primary_rank is None
    assert any("original counterpart" in warning for warning in screened.secondary_screening.warnings)


def test_incomplete_and_unavailable_are_never_policy_passes():
    for unavailable,max_objects in ((False,1),(True,100)):
        result=primary()
        settings=policy_settings(max_finalists=1,max_objects=max_objects)
        screened=screen_ranked_finalists(result,settings,numerical_screening_callback(result,settings,unavailable))
        assert screened.status==("UNAVAILABLE" if unavailable else "INCOMPLETE")
        assert not screened.solutions
        assert screened.secondary_screening.candidate_results[0].policy_passed is None


def test_screening_total_budget_has_no_silent_untested_pass():
    result=primary()
    settings=policy_settings(total_timeout_seconds=1e-9)
    screened=screen_ranked_finalists(result,settings,numerical_screening_callback(result,settings))
    assert screened.status=="INCOMPLETE"
    assert screened.secondary_screening.candidates_screened==0
    assert not screened.solutions


def test_minimum_effort_primary_objective_remains_respected():
    result=primary(objective="MINIMUM_DELTA_V",target_miss_distance_km=9.5)
    original=list(result.solutions)
    assert original and all(item.meets_target for item in original)
    settings=policy_settings(policy="REPORT_ONLY")
    screened=screen_ranked_finalists(result,settings,numerical_screening_callback(result,settings))
    assert screened.solutions==original
    assert screened.objective=="MINIMUM_DELTA_V"


def test_actual_selected_gp_differential_optimizer_integration(tmp_path):
    encounter,first,second=actual_case()
    catalog=CatalogLoader(FileCache(tmp_path)).load_screening_catalog(
        CatalogSelection(groups=(),local_files=(FIXTURES/"gp_actual.json",)),START)
    result=optimize_with_secondary_screening(encounter,first,second,
        ManeuverConstraints(**constraint_input(max_lead_time_hours=.5)),SMALL,
        SecondaryOptimizationSettings(policy="REPORT_ONLY",post_tca_horizon_hours=.01,
            coarse_step_seconds=120),catalog,START)
    assert result.solutions
    assert result.secondary_screening.candidates_screened==1
    assessment=result.secondary_screening.candidate_results[0]
    assert assessment.screening is not None
    assert assessment.screening.screening_complete,assessment.screening.model_dump_json(indent=2)
    assert assessment.screening.objects_screened==2
    assert all(item.frame=="TEME" for item in assessment.screening.secondary_encounters)
    assert assessment.delta_v_rtn_m_s==result.solutions[0].delta_v_rtn_m_s
    print("ACTUAL_GP_FINALIST_SCREEN "+assessment.model_dump_json())
