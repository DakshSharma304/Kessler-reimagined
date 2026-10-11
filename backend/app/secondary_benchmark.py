"""Measured real-catalog pipeline: python -m app.secondary_benchmark --profile.

Defaults deliberately use a short (36-second post-TCA) interval, with a
30-second screening budget. The normal API/CLI horizon remains six hours.
Incomplete screens are measurements, not evidence of absent conjunctions.
"""

import argparse
from collections import Counter
import cProfile
import json
import platform
import pstats
import sys
import time

from app.engine import Engine
from app.models.maneuver import ManeuverConstraints
from app.models.screening import SecondaryOptimizationSettings
from app.optimization.optimizer import SearchSettings
from app.optimization.screened_optimizer import optimize_with_secondary_screening
from app.physics.encounters import analyze_encounter


def benchmark_secondary(engine=None, encounter_id=None, object_id=None,
                        secondary_settings=None, search=None):
    engine = engine or Engine()
    started = time.perf_counter()
    encounter = engine.discovery.get_encounter(encounter_id) if encounter_id else engine.discovery.list_encounters(
        sort="minimum_separation", object_id=object_id, limit=1)[0]
    first, second = engine.celestrak.get_encounter_objects(encounter)
    baseline = analyze_encounter(encounter, first, second)
    primary_load_seconds = time.perf_counter()-started
    settings = secondary_settings or SecondaryOptimizationSettings(
        policy="REPORT_ONLY", post_tca_horizon_hours=.01, coarse_step_seconds=30,
        timeout_seconds=30, total_timeout_seconds=35, max_finalists=3)
    tick = time.perf_counter()
    catalog = engine.catalog.load_screening_catalog(settings.catalog_selection)
    load_seconds = time.perf_counter()-tick
    constraints = ManeuverConstraints(encounter_id=encounter.id,
        maneuvering_object_id=object_id or encounter.object_1_id, max_delta_v_m_s=.2,
        min_lead_time_minutes=10,max_lead_time_hours=.25,target_miss_distance_km=10,
        objective="MAXIMUM_CLEARANCE",hypothetical_capability_assumed=True)
    tick = time.perf_counter()
    result = optimize_with_secondary_screening(encounter,first,second,constraints,
        search=search,secondary_settings=settings,catalog=catalog,cache=engine.catalog_propagation_cache)
    optimizer_screen_seconds = time.perf_counter()-tick
    candidates = []
    for assessment in result.secondary_screening.candidate_results:
        screen = assessment.screening
        candidates.append({"primary_rank":assessment.primary_rank,
            "policy_passed":assessment.policy_passed,"selected":assessment.selected,
            "maneuver_time":assessment.maneuver_time.isoformat(),
            "primary_separation_m":assessment.primary_miss_distance_m,
            "primary_improvement_m":assessment.primary_improvement_m,
            "status":None if screen is None else screen.screening_status,
            "screening_catalog_snapshot":None if screen is None else screen.catalog.snapshot_sha256,
            "screening_catalog_objects":None if screen is None else screen.catalog.objects_available,
            "objects_considered":0 if screen is None else screen.objects_screened,
            "objects_refined":0 if screen is None else screen.candidate_objects_refined,
            "screening_seconds":None if screen is None else screen.elapsed_seconds,
            "timings_seconds":{} if screen is None else screen.timings_seconds,
            "screening_window":None if screen is None else screen.screening_window.model_dump(mode="json"),
            "skipped_reasons":{} if screen is None else dict(Counter(screen.skipped_objects.values())),
            "additional_alerts":None if screen is None else screen.additional_close_approaches,
            "new_alerts":None if screen is None else screen.newly_introduced,
            "worsened":None if screen is None else screen.worsened,
            "closest_additional":None if screen is None or screen.closest_additional_encounter is None else
                screen.closest_additional_encounter.model_dump(mode="json"),
            "calculated_events":[] if screen is None else [item.model_dump(mode="json") for item in screen.secondary_encounters],
            "warnings":assessment.warnings if screen is None else screen.warnings})
    return {"python":platform.python_version(),"platform":platform.platform(),
        "encounter_id":encounter.id,"object_ids":[first.elements.object_id,second.elements.object_id],
        "source_encounters":len(engine.socrates.get_dataset().encounters),
        "selected_orbital_records":[first.model_dump(mode="json"),second.model_dump(mode="json")],
        "socrates_source_checksum":engine.socrates.get_dataset().content_sha256,
        "published_distance_m":baseline.published.miss_distance_m,
        "sgp4_distance_m":baseline.calculated.miss_distance_m,
        "source_model_disagreement":baseline.source_model_disagreement,
        "primary_load_seconds":primary_load_seconds,"catalog_load_seconds":load_seconds,
        "catalog":catalog.metadata.model_dump(mode="json"),
        "settings":settings.model_dump(mode="json"),
        "primary_candidates_evaluated":result.candidates_evaluated,
        "primary_baseline_m":result.baseline.miss_distance_m,
        "optimizer_and_screening_seconds":optimizer_screen_seconds,
        "end_to_end_seconds":time.perf_counter()-started,
        "primary_status":result.status,"secondary_status":result.secondary_screening.status,
        "maneuvers_screened":result.secondary_screening.candidates_screened,
        "selected_primary_rank":result.secondary_screening.selected_primary_rank,
        "solutions":[item.model_dump(mode="json") for item in result.solutions],
        "candidates":candidates,"warnings":result.warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encounter-id")
    parser.add_argument("--object-id")
    parser.add_argument("--profile",action="store_true",help="Print cumulative-time profile to stderr")
    parser.add_argument("--post-tca-horizon-hours",type=float,default=.01)
    parser.add_argument("--coarse-step-seconds",type=float,default=30)
    parser.add_argument("--screen-timeout-seconds",type=float,default=30)
    parser.add_argument("--max-objects",type=int,default=50000)
    args = parser.parse_args()
    settings = SecondaryOptimizationSettings(post_tca_horizon_hours=args.post_tca_horizon_hours,
        coarse_step_seconds=args.coarse_step_seconds,timeout_seconds=args.screen_timeout_seconds,
        total_timeout_seconds=args.screen_timeout_seconds+5,max_objects=args.max_objects)
    profile = cProfile.Profile() if args.profile else None
    if profile:
        profile.enable()
    report = benchmark_secondary(encounter_id=args.encounter_id,object_id=args.object_id,
                                 secondary_settings=settings)
    if profile:
        profile.disable()
        pstats.Stats(profile,stream=sys.stderr).sort_stats("cumulative").print_stats(20)
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
