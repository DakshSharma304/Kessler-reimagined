"""Optional bounded finalist screening; retains the original primary optimizer."""

from datetime import UTC, datetime
import time

from app.models.screening import (CandidateScreeningAssessment, OptimizationScreeningSummary,
    ScreeningPolicy, ScreeningRequest, SecondaryOptimizationSettings)
from app.optimization.optimizer import optimize_maneuver
from app.physics.maneuvers import ManeuverError
from app.physics.propagation import PropagationError
from app.physics.secondary_search import CatalogPropagationCache
from app.secondary import screen_proposed_maneuver


def policy_passes(screening,policy):
    if not screening.screening_complete:
        return None
    if policy==ScreeningPolicy.REPORT_ONLY:
        return True
    if policy==ScreeningPolicy.REJECT_NEW_ALERTS:
        return screening.newly_introduced==0
    # The original counterpart is handled by the primary optimization objective,
    # not rejected a second time under the additional-object screening rule.
    return screening.additional_close_approaches==0


def screen_ranked_finalists(primary,settings,screen_candidate):
    """Post-process genuine ranked primary options using actual screening calls."""
    started=time.perf_counter()
    deadline=started+settings.total_timeout_seconds
    assessments=[]
    accepted=None
    incomplete=False
    unavailable=False
    for rank,option in enumerate(primary.evaluated_finalists[:settings.max_finalists],1):
        if time.perf_counter()>=deadline:
            incomplete=True
            break
        try:
            screening=screen_candidate(option,deadline)
            passed=policy_passes(screening,settings.policy)
            incomplete |= not screening.screening_complete
            unavailable |= screening.screening_status=="UNAVAILABLE"
            assessment=CandidateScreeningAssessment(primary_rank=rank,maneuver_time=option.maneuver_time,
                delta_v_rtn_m_s=option.delta_v_rtn_m_s,primary_miss_distance_m=option.new_miss_distance_m,
                primary_improvement_m=option.change_in_miss_distance_m,screening=screening,policy_passed=passed)
        except (ValueError,ManeuverError,PropagationError,TimeoutError) as error:
            incomplete=True
            assessment=CandidateScreeningAssessment(primary_rank=rank,maneuver_time=option.maneuver_time,
                delta_v_rtn_m_s=option.delta_v_rtn_m_s,primary_miss_distance_m=option.new_miss_distance_m,
                primary_improvement_m=option.change_in_miss_distance_m,screening=None,policy_passed=None,
                warnings=[f"Screening unavailable or incomplete: {error}"])
        assessments.append(assessment)
        if settings.policy==ScreeningPolicy.REPORT_ONLY or assessment.policy_passed is True:
            assessment.selected=True
            accepted=option
            break
    warnings=["Secondary screening checks only available catalog coverage and the selected prediction interval; no flight-safety guarantee.",
              "REJECT_ALL_ALERTS excludes the original counterpart; primary constraints/objective handle that encounter."]
    if settings.policy==ScreeningPolicy.REPORT_ONLY:
        warnings.append("REPORT_ONLY preserves primary options, including unscreened alternatives; consult candidate_results for each actual assessment.")
    if accepted is None:
        primary.solutions=[]
        status="UNAVAILABLE" if unavailable else "INCOMPLETE" if incomplete else "NO_ACCEPTABLE_SCREENED_SOLUTION"
        primary.status=status
    elif settings.policy==ScreeningPolicy.REPORT_ONLY:
        status="INCOMPLETE" if incomplete else "COMPLETE"
    else:
        primary.solutions=[accepted]
        status="COMPLETE"
    summary=OptimizationScreeningSummary(status=status,policy=settings.policy,
        max_finalists=settings.max_finalists,candidates_screened=len(assessments),
        selected_primary_rank=next((item.primary_rank for item in assessments if item.selected),None),
        candidate_results=assessments,elapsed_seconds=time.perf_counter()-started,warnings=warnings)
    primary.secondary_screening=summary
    primary.model_assumptions=[text for text in primary.model_assumptions if "Secondary encounters have not been assessed" not in text]
    primary.warnings=[text for text in primary.warnings if "Secondary encounters have not been assessed" not in text]
    primary.warnings.extend(warnings)
    primary.elapsed_seconds+=summary.elapsed_seconds
    return primary


def optimize_with_secondary_screening(encounter,first,second,constraints,search=None,
        secondary_settings: SecondaryOptimizationSettings | None = None,catalog=None,
        now: datetime | None = None,cache: CatalogPropagationCache | None = None):
    if secondary_settings is None:
        return optimize_maneuver(encounter,first,second,constraints,search,now)
    if catalog is None:
        raise ValueError("Explicit catalog snapshot required when screening is enabled")
    now=now or datetime.now(UTC)
    primary=optimize_maneuver(encounter,first,second,constraints,search,now,
                              retain_finalists=secondary_settings.max_finalists)
    cache=cache or CatalogPropagationCache()
    settings=secondary_settings.model_dump(exclude={"policy","max_finalists","total_timeout_seconds"})
    def screen(option,deadline):
        request=ScreeningRequest(**settings,encounter_id=encounter.id,
            maneuvering_object_id=constraints.maneuvering_object_id,maneuver_time=option.maneuver_time,
            delta_v_rtn_m_s=option.delta_v_rtn_m_s,hypothetical_capability_assumed=True)
        return screen_proposed_maneuver(encounter,first,second,request,catalog,
            primary.numerical_reference_epoch,now,cache,deadline)
    return screen_ranked_finalists(primary,secondary_settings,screen)
