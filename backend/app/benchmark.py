"""Actual-machine performance report: python -m app.benchmark."""

import argparse
from datetime import timedelta
import json
import platform
import time

from app.engine import Engine
from app.models.maneuver import ManeuverConstraints
from app.optimization.optimizer import optimize_maneuver
from app.physics.encounters import analyze_encounter
from app.physics.maneuvers import simulate_maneuver
from app.physics.propagation import propagate_trajectory


def benchmark_engine(engine: Engine | None = None, encounter_id: str | None = None) -> dict:
    engine = engine or Engine()
    started = time.perf_counter()
    encounter = engine.discovery.get_encounter(encounter_id) if encounter_id else engine.discovery.list_encounters(limit=1)[0]
    load_seconds = time.perf_counter()-started
    started = time.perf_counter()
    engine.discovery.get_encounter(encounter.id)
    lookup_seconds = time.perf_counter()-started
    first, second = engine.celestrak.get_encounter_objects(encounter)
    started = time.perf_counter()
    engine.celestrak.get_encounter_objects(encounter)
    cached_gp_seconds = time.perf_counter()-started
    started = time.perf_counter()
    baseline = analyze_encounter(encounter, first, second)
    baseline_seconds = time.perf_counter()-started
    burn = encounter.time_of_closest_approach-timedelta(hours=1)
    started = time.perf_counter()
    simulation = simulate_maneuver(encounter, first, second, encounter.object_1_id, burn, (0,.1,0), True)
    simulation_seconds = time.perf_counter()-started
    propagation = {}
    for count in (100, 1000):
        started = time.perf_counter()
        states = propagate_trajectory(first, first.elements.epoch, first.elements.epoch+timedelta(hours=1), count)
        propagation[str(count)] = {"states":len(states), "seconds":time.perf_counter()-started}
    constraints = ManeuverConstraints(encounter_id=encounter.id, maneuvering_object_id=encounter.object_1_id,
        max_delta_v_m_s=.2, min_lead_time_minutes=15, max_lead_time_hours=2,
        target_miss_distance_km=10, objective="MAXIMUM_CLEARANCE", hypothetical_capability_assumed=True)
    optimized = optimize_maneuver(encounter, first, second, constraints)
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "source_encounters": len(engine.socrates.get_dataset().encounters),
        "encounter_id": encounter.id, "object_ids":[encounter.object_1_id,encounter.object_2_id],
        "initial_dataset_load_and_index_seconds":load_seconds,
        "indexed_lookup_seconds":lookup_seconds, "cached_orbit_pair_seconds":cached_gp_seconds,
        "baseline_seconds":baseline_seconds, "maneuver_seconds":simulation_seconds,
        "propagations":propagation, "optimizer_seconds":optimized.elapsed_seconds,
        "optimizer_status":optimized.status, "candidates_evaluated":optimized.candidates_evaluated,
        "feasible_candidates":optimized.feasible_candidates, "numerical_failures":optimized.numerical_failures,
        "best_solution":None if not optimized.solutions else optimized.solutions[0].model_dump(mode="json"),
        "published_separation_m":baseline.published.miss_distance_m,
        "sgp4_separation_m":baseline.calculated.miss_distance_m,
        "single_burn_matched_baseline_m":simulation.matched_baseline.miss_distance_m,
        "single_burn_separation_m":simulation.modified.miss_distance_m,
        "targets_seconds":{"indexed_lookup":1,"cached_orbits":1,"baseline_preferred":3,
                           "maneuver_preferred":3,"optimization_target":30},
        "limitations":optimized.model_assumptions, "warnings":optimized.warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encounter-id")
    args = parser.parse_args()
    print(json.dumps(benchmark_engine(encounter_id=args.encounter_id), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
