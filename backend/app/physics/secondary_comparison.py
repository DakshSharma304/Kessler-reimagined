"""Same-snapshot/time-window nominal and modified conjunction comparison."""

from datetime import timedelta
import time

import numpy as np
from scipy.optimize import minimize_scalar

from app.models.catalog import CatalogMetadata, ScreeningCatalog
from app.models.orbital import OrbitalRecord
from app.models.screening import (ConjunctionClassification as Classification,
    ScreeningResult, ScreeningSettings, ScreeningStatus, SecondaryConjunction)
from app.physics.propagation import PropagationError, propagate_object
from app.physics.secondary_search import (CatalogPropagationCache, RefinedSecondaryApproach,
    TrajectoryView, screen_trajectory_against_catalog)


def _nearby_reference(primary, orbit, center, settings, deadline):
    """Calculate a counterfactual only near the same event, not an unrelated TCA."""
    start,end = primary.window.start,primary.window.end
    duration=(end-start).total_seconds()
    offset=(center-start).total_seconds()
    lo=max(0,offset-settings.event_matching_tolerance_seconds)
    hi=min(duration,offset+settings.event_matching_tolerance_seconds)
    evaluate=orbit.evaluate if isinstance(orbit,TrajectoryView) else lambda at:propagate_object(orbit,at)
    def relative(seconds):
        if time.perf_counter() >= deadline:
            raise TimeoutError("Baseline/modified event comparison budget exhausted")
        at=start+timedelta(seconds=float(seconds))
        one,two=primary.evaluate(at),evaluate(at)
        if one.timestamp != at or two.timestamp != at or one.frame != two.frame or one.frame != primary.frame:
            raise ValueError("Incompatible counterfactual frames or timestamps")
        relative_position=np.subtract(one.position_m,two.position_m)
        return float(relative_position@relative_position),float(np.linalg.norm(np.subtract(one.velocity_m_s,two.velocity_m_s)))
    result=minimize_scalar(lambda at:relative(at)[0],method="bounded",bounds=(lo,hi),
                           options={"xatol":1e-5,"maxiter":80})
    if not result.success or not np.isfinite(result.fun):
        raise ValueError("Counterfactual local refinement failed")
    seconds,value=min([(float(result.x),float(result.fun)),(lo,relative(lo)[0]),(hi,relative(hi)[0])],key=lambda item:item[1])
    source=orbit.source if isinstance(orbit,TrajectoryView) else {"url":orbit.source_url,
        "sha256":orbit.content_sha256,"element_epoch":orbit.elements.epoch.isoformat()}
    name=orbit.name if isinstance(orbit,TrajectoryView) else orbit.elements.object_name
    identifier=orbit.primary_object_id if isinstance(orbit,TrajectoryView) else orbit.elements.object_id
    boundary=seconds<=lo+1e-4 or seconds>=hi-1e-4
    return RefinedSecondaryApproach(object_id=identifier,object_name=name,
        tca=start+timedelta(seconds=seconds),distance_m=float(np.sqrt(value)),
        relative_speed_m_s=relative(seconds)[1],frame=primary.frame,source=source,
        warnings=["Counterfactual minimum is constrained to a nearby event window; no corresponding interior local minimum was established."] if boundary else [])


def _classify(baseline, modified, settings):
    threshold=settings.alert_distance_km*1000
    if modified.distance_m < threshold and baseline.distance_m >= threshold:
        return Classification.NEW_CLOSE_APPROACH
    change=modified.distance_m-baseline.distance_m
    if change < -settings.classification_tolerance_m:
        return Classification.WORSENED_CLOSE_APPROACH
    if change > settings.classification_tolerance_m:
        return Classification.IMPROVED_CLOSE_APPROACH
    return Classification.UNCHANGED


def compare_secondary_conjunctions(baseline_trajectory: TrajectoryView,
        maneuvered_trajectory: TrajectoryView, catalog: ScreeningCatalog | dict,
        settings: ScreeningSettings, encounter_id: str, original_counterpart_id: str,
        cache: CatalogPropagationCache | None = None,
        catalog_metadata: CatalogMetadata | None = None, deadline: float | None = None) -> ScreeningResult:
    started=time.perf_counter()
    deadline=min(deadline or float("inf"),started+settings.timeout_seconds)
    if (baseline_trajectory.window != maneuvered_trajectory.window or
        baseline_trajectory.frame != maneuvered_trajectory.frame or
        baseline_trajectory.primary_object_id != maneuvered_trajectory.primary_object_id):
        raise ValueError("Comparison requires the same primary object, interval and frame")
    records=catalog.records if isinstance(catalog,ScreeningCatalog) else catalog
    metadata=catalog.metadata if isinstance(catalog,ScreeningCatalog) else catalog_metadata
    if metadata is None or metadata.objects_available != len(records):
        raise ValueError("Explicit matching catalog-snapshot metadata required")
    if not records:
        return ScreeningResult(encounter_id=encounter_id,maneuvering_object_id=baseline_trajectory.primary_object_id,
            alert_distance_km=settings.alert_distance_km,
            screening_status="UNAVAILABLE",screening_complete=False,catalog=metadata,
            screening_window=baseline_trajectory.window,objects_screened=0,candidate_objects_refined=0,
            additional_close_approaches=0,newly_introduced=0,worsened=0,improved=0,
            closest_additional_encounter=None,secondary_encounters=[],elapsed_seconds=time.perf_counter()-started,
            warnings=["Catalog unavailable: an empty result is not evidence of absent conjunctions."])
    cache=cache or CatalogPropagationCache()
    baseline=screen_trajectory_against_catalog(baseline_trajectory,catalog,settings,cache,deadline,original_counterpart_id)
    modified=screen_trajectory_against_catalog(maneuvered_trajectory,catalog,settings,cache,deadline,original_counterpart_id)
    skipped=baseline.skipped_objects | modified.skipped_objects
    if original_counterpart_id not in records:
        skipped[original_counterpart_id]="Original encounter counterpart missing from the declared snapshot"
    warnings=[*metadata.warnings,*metadata.failed_sources]
    events=[]
    baseline_events=list(baseline.approaches)
    used=set()
    comparison_seconds=time.perf_counter()

    def event(one,two):
        return SecondaryConjunction(primary_object_id=baseline_trajectory.primary_object_id,
            secondary_object_id=two.object_id,secondary_object_name=two.object_name,
            is_original_counterpart=two.object_id==original_counterpart_id,
            time_of_closest_approach=two.tca,baseline_time_of_closest_approach=one.tca,
            baseline_miss_distance_m=one.distance_m,maneuvered_miss_distance_m=two.distance_m,
            change_in_miss_distance_m=two.distance_m-one.distance_m,
            change_in_tca_seconds=(two.tca-one.tca).total_seconds(),relative_speed_m_s=two.relative_speed_m_s,
            classification=_classify(one,two,settings),
            baseline_below_threshold=one.distance_m<settings.alert_distance_km*1000,
            maneuvered_below_threshold=two.distance_m<settings.alert_distance_km*1000,
            screening_window=baseline_trajectory.window,frame=two.frame,source=two.source,
            warnings=list(dict.fromkeys([*one.warnings,*two.warnings])))

    for two in modified.approaches:
        matches=[(abs((two.tca-one.tca).total_seconds()),index,one)
                 for index,one in enumerate(baseline_events) if index not in used and one.object_id==two.object_id
                 and abs((two.tca-one.tca).total_seconds()) <= settings.event_matching_tolerance_seconds]
        try:
            if matches:
                _,index,one=min(matches,key=lambda item:(item[0],item[1]))
                used.add(index)
            else:
                one=_nearby_reference(baseline_trajectory,records[two.object_id],two.tca,settings,deadline)
            events.append(event(one,two))
        except (ValueError,PropagationError,TimeoutError) as error:
            skipped[two.object_id]=f"Event comparison incomplete: {error}"
    for index,one in enumerate(baseline_events):
        if index in used:
            continue
        try:
            two=_nearby_reference(maneuvered_trajectory,records[one.object_id],one.tca,settings,deadline)
            if not any(prior.secondary_object_id==two.object_id and
                       abs((prior.time_of_closest_approach-two.tca).total_seconds())<=.001 for prior in events):
                events.append(event(one,two))
        except (ValueError,PropagationError,TimeoutError) as error:
            skipped[one.object_id]=f"Event comparison incomplete: {error}"
    closest=None
    if modified.closest is not None:
        two=modified.closest
        try:
            matches=[item for item in events if item.secondary_object_id==two.object_id and
                     abs((item.time_of_closest_approach-two.tca).total_seconds())<=.001]
            closest=matches[0] if matches else event(
                _nearby_reference(baseline_trajectory,records[two.object_id],two.tca,settings,deadline),two)
        except (ValueError,PropagationError,TimeoutError) as error:
            skipped[two.object_id]=f"Closest-event comparison incomplete: {error}"
    elapsed_comparison=time.perf_counter()-comparison_seconds
    complete=baseline.complete and modified.complete and not skipped and not (
        metadata.failed_sources or metadata.rejected_record_count)
    additional=[item for item in events if not item.is_original_counterpart]
    alerts=[item for item in additional if item.maneuvered_below_threshold]
    status=ScreeningStatus.INCOMPLETE if not complete else ScreeningStatus.ALERTS_FOUND if alerts else ScreeningStatus.SCREENED_WITHIN_COVERAGE
    if not complete:
        warnings.append("Screening incomplete: missing/stale/failed records or exhausted workload; empty detections do not establish absent conjunctions.")
    else:
        warnings.append("Completed only within the declared partial catalog and prediction interval, not the full orbiting population.")
    events.sort(key=lambda item:(item.time_of_closest_approach,item.secondary_object_id))
    screened=baseline.objects_screened & modified.objects_screened
    timings={key:baseline.timings_seconds[key]+modified.timings_seconds[key] for key in baseline.timings_seconds}
    timings["comparison"]=elapsed_comparison
    return ScreeningResult(encounter_id=encounter_id,maneuvering_object_id=baseline_trajectory.primary_object_id,
        alert_distance_km=settings.alert_distance_km,
        screening_status=status,screening_complete=complete,catalog=metadata,
        screening_window=baseline_trajectory.window,objects_screened=len(screened),
        candidate_objects_refined=len((baseline.objects_refined|modified.objects_refined)&screened),
        additional_close_approaches=len(alerts),
        newly_introduced=sum(item.classification==Classification.NEW_CLOSE_APPROACH for item in alerts),
        worsened=sum(item.classification==Classification.WORSENED_CLOSE_APPROACH for item in additional),
        improved=sum(item.classification==Classification.IMPROVED_CLOSE_APPROACH for item in additional),
        closest_additional_encounter=closest,secondary_encounters=events,skipped_objects=skipped,
        elapsed_seconds=time.perf_counter()-started,timings_seconds=timings,warnings=warnings)
