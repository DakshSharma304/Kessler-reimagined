"""Actual-source/MSIS persistence measurements, not operational lifetimes.

Run from backend: python -m app.persistence_benchmark [--profile]
The explicitly hypothetical benchmark properties are mass=100 kg, area=1 m²,
Cd=2.2, applied to actual ISS/NOAA 15 GP initial states, not claimed properties
of either spacecraft. Real spacecraft operations are intentionally unmodeled.
"""
import argparse
import cProfile
from datetime import UTC, datetime, timedelta
import json
import pstats
import sys
import time

import numpy as np

from app.engine import Engine
from app.persistence import analyze_orbital_persistence
from app.physics.atmosphere import calculate_density, forcing_from_dataset, state_geodetic
from app.physics.decay import EarthOrientation, SolverSettings
from app.physics.drag import ObjectAerodynamicProperties
from app.physics.persistence_scenarios import PersistenceSettings


def benchmark_persistence(engine=None, *, progress=None):
    engine = engine or Engine()
    start = datetime.now(UTC)
    report = {"start_time": start.isoformat(),
        "interpretation": "MODEL-CALCULATED research scenarios, NOT observed decay or operational reentry forecasts",
        "timings_seconds": {}, "objects": {}, "propagations": []}
    properties = ObjectAerodynamicProperties(input_category="HYPOTHETICAL_ASSUMPTION",
        mass_kg=100, area_m2=1, drag_coefficient=2.2)
    report["hypothetical_properties"] = properties.model_dump(mode="json")

    def announce(value):
        if progress is not None:
            progress(value)

    tick = time.perf_counter()
    dataset = engine.space_weather.load_space_weather()
    report["timings_seconds"]["weather_load"] = time.perf_counter()-tick
    report["space_weather"] = dataset.coverage()
    forcing = forcing_from_dataset(start, dataset)
    tick = time.perf_counter()
    for _ in range(100):
        density = calculate_density(start, 0, 0, 400000, forcing)
    report["timings_seconds"]["density_100_evaluations"] = time.perf_counter()-tick
    report["density_control_kg_m3"] = density.density_kg_m3

    def run(identifier, days, **changes):
        announce(f"Starting actual GP/MSIS {identifier}, {days}-day run: {changes}")
        tick = time.perf_counter()
        selected = changes.pop("properties", properties)
        result = analyze_orbital_persistence(identifier, selected,
            PersistenceSettings(horizon_days=days, **changes), engine=engine, start_time=start)
        elapsed = time.perf_counter()-tick
        entries = []
        if result.scenario_analysis is not None:
            for scenario in result.scenario_analysis.scenarios:
                curve = scenario.boundary.propagation
                entries.append({"scenario": scenario.scenario,
                    "status": scenario.boundary.prediction_status,
                    "crossing_time": None if scenario.boundary.crossing_time is None else scenario.boundary.crossing_time.isoformat(),
                    "warnings": scenario.boundary.warnings,
                    "energy_change_j_kg": scenario.total_specific_energy_change_j_kg,
                    "semimajor_axis_change_m": scenario.semimajor_axis_change_m,
                    "initial_period_mean_semimajor_axis_m": scenario.initial_period_mean_semimajor_axis_m,
                    "final_period_mean_semimajor_axis_m": scenario.final_period_mean_semimajor_axis_m,
                    "first_density_kg_m3": None if curve is None else curve.samples[0].density_kg_m3,
                    "last_density_kg_m3": None if curve is None else curve.samples[-1].density_kg_m3,
                    "propagation_seconds": None if curve is None else curve.elapsed_seconds,
                    "derivative_evaluations": None if curve is None else curve.derivative_evaluations,
                    "environment": None if curve is None else curve.environment,
                    "final_state": None if curve is None else curve.samples[-1].state.model_dump(mode="json")})
        report["objects"][identifier] = {"name":result.object_name, "gp_epoch":result.gp_epoch.isoformat(),
            "initial_geodetic_altitude_m":result.initial_orbit["geodetic_altitude_m"],
            "provenance":result.provenance}
        record = {"object_id":identifier, "horizon_days":days,
            "settings":result.scenario_analysis.settings.model_dump(mode="json") if result.scenario_analysis else None,
            "properties":selected.model_dump(mode="json"), "elapsed_seconds":elapsed,
            "status":result.prediction_status, "scenarios":entries}
        report["propagations"].append(record)
        announce(f"Finished {identifier}, {days} days: {result.prediction_status}, {elapsed:.3f} s")
        return result

    ordinary = run("25544", 1)
    for days in (7, 30):
        result = run("25544", days)
        if result.scenario_analysis.status != "COMPLETE":
            # Do not hide a failed mandatory long-horizon run behind later work.
            report["benchmark_status"] = "BLOCKED"
            return report
    high = run("25338", 1)
    comparison = run("25544", 1, scenario_mode="COMPARE")
    report["timings_seconds"]["scenario_comparison"] = report["propagations"][-1]["elapsed_seconds"]
    stronger = ObjectAerodynamicProperties(input_category="HYPOTHETICAL_ASSUMPTION",
        cd_area_over_mass_m2_kg=.044)
    run("25544", 1, properties=stronger)
    tight = run("25544", 1, solver=SolverSettings(rtol=1e-11, position_atol_m=1e-6,
        velocity_atol_m_s=1e-9, max_step_seconds=60))
    if any(r.scenario_analysis.status != "COMPLETE" for r in (ordinary,high,comparison,tight)):
        report["benchmark_status"] = "BLOCKED"
        return report
    a = ordinary.scenario_analysis.scenarios[0].boundary.propagation
    b = tight.scenario_analysis.scenarios[0].boundary.propagation
    report["one_day_convergence_position_m"] = float(np.linalg.norm(
        np.array(a.samples[-1].state.position_m)-np.array(b.samples[-1].state.position_m)))
    tick = time.perf_counter()
    for _ in range(100):
        state_geodetic(ordinary.initial_state)
    report["timings_seconds"]["direct_coordinates_100_evaluations"] = time.perf_counter()-tick
    orientation = EarthOrientation(start,start+timedelta(days=1))
    tick = time.perf_counter()
    for _ in range(100):
        orientation.geodetic(ordinary.initial_state)
    report["timings_seconds"]["prepared_coordinates_100_evaluations"] = time.perf_counter()-tick
    report["benchmark_status"] = "COMPLETE"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",action="store_true")
    args = parser.parse_args()
    profiler = cProfile.Profile() if args.profile else None
    if profiler:
        profiler.enable()
    report = benchmark_persistence(progress=lambda s:print(s,file=sys.stderr,flush=True))
    if profiler:
        profiler.disable()
        pstats.Stats(profiler,stream=sys.stderr).sort_stats("cumulative").print_stats(25)
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["benchmark_status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
