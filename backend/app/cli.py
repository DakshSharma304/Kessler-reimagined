"""Interactive terminal demonstration and JSON commands using the actual engine."""

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys

from app.data.celestrak import OrbitalUnavailable
from app.data.discovery import EncounterNotFound
from app.data.socrates import SourceUnavailable, parse_utc
from app.engine import Engine
from app.models.maneuver import ManeuverConstraints, Objective
from app.models.catalog import CatalogSelection
from app.models.screening import ScreeningPolicy, ScreeningRequest, SecondaryOptimizationSettings
from app.optimization.optimizer import OptimizationResult, SearchSettings, optimize_maneuver
from app.optimization.screened_optimizer import optimize_with_secondary_screening, screen_ranked_finalists
from app.physics.encounters import CalculationUnavailable, analyze_encounter
from app.physics.maneuvers import ManeuverError, simulate_maneuver
from app.physics.propagation import PropagationError
from app.secondary import screen_proposed_maneuver
from app.probability.availability import ProbabilityInputs
from app.probability.cdm import reference_cases
from app.probability.integration import (DirectProbabilityRequest, with_live_probability,
    with_maneuver_probability, calculate_request)
from app.probability.reference import ReferenceComparison, evaluate_reference
from app.data.space_weather import SpaceWeatherUnavailable
from app.data.celestrak import validate_object_id
from app.physics.drag import ObjectAerodynamicProperties
from app.physics.decay import SolverSettings
from app.physics.persistence_scenarios import PersistenceSettings
from app.persistence import analyze_orbital_persistence


def screening_arguments(command):
    command.add_argument("--catalog-group", action="append", help="Verified public GP group; repeatable")
    command.add_argument("--catalog-file", type=Path, action="append", help="Local OMM JSON/CSV; repeatable; defaults to local-only scope")
    command.add_argument("--include-cached-records", action="store_true")
    command.add_argument("--alert-distance-km", type=float, default=5)
    command.add_argument("--post-tca-horizon-hours", type=float, default=6)
    command.add_argument("--coarse-step-seconds", type=float, default=30)
    command.add_argument("--screen-timeout-seconds", type=float, default=30)
    command.add_argument("--screen-max-objects", type=int, default=50000)
    command.add_argument("--screen-max-refinements", type=int, default=1000)


def screening_settings(args):
    selection = CatalogSelection(local_files=tuple(args.catalog_file or ()),
        include_cached_records=args.include_cached_records,
        **({"groups":tuple(args.catalog_group)} if args.catalog_group else
           {"groups":()} if args.catalog_file else {}))
    return dict(catalog_selection=selection, alert_distance_km=args.alert_distance_km,
        post_tca_horizon_hours=args.post_tca_horizon_hours, coarse_step_seconds=args.coarse_step_seconds,
        timeout_seconds=args.screen_timeout_seconds, max_objects=args.screen_max_objects,
        max_refinements=args.screen_max_refinements)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Kessler hypothetical orbital avoidance engine")
    root.add_argument("--json", action="store_true", help="Machine-readable JSON on stdout; put this before the command")
    root.add_argument("--cache-dir", type=Path, help="Persistent public-source cache directory")
    commands = root.add_subparsers(dest="command")
    listing = commands.add_parser("list", help="List actual upcoming predicted close approaches")
    listing.add_argument("--sort", choices=["screening", "max_probability", "minimum_separation", "time"], default="screening")
    listing.add_argument("--limit", type=int, default=10)
    listing.add_argument("--object-id")
    listing.add_argument("--name")
    analyze = commands.add_parser("analyze", help="Recalculate a selected encounter with current GP elements")
    analyze.add_argument("--encounter-id", required=True)
    analyze.add_argument("--probability", action="store_true", help="Report honest covariance-based Pc availability")
    analyze.add_argument("--covariance-file", type=Path, help="Explicit SUPPLIED/ASSUMED covariance-input JSON at analyzed TCA")
    simulate = commands.add_parser("simulate", help="Simulate one actual hypothetical velocity impulse")
    simulate.add_argument("--encounter-id", required=True)
    simulate.add_argument("--object-id", required=True)
    simulate.add_argument("--maneuver-time", required=True, help="ISO timestamp; timezone omitted means UTC")
    simulate.add_argument("--delta-v-rtn", nargs=3, type=float, required=True, metavar=("R", "T", "N"))
    simulate.add_argument("--assume-capability", action="store_true")
    simulate.add_argument("--probability-scenario-file", type=Path, help="Covariance JSON including fixed_covariance=true; always illustrative")
    probability = commands.add_parser("probability", help="NASA independent-model validation or live Pc availability/scenario")
    selection = probability.add_mutually_exclusive_group(required=True)
    selection.add_argument("--reference-case", choices=reference_cases())
    selection.add_argument("--encounter-id")
    selection.add_argument("--list-reference-cases", action="store_true")
    selection.add_argument("--input-file", type=Path, help="Direct common-inertial-frame Pc request JSON")
    probability.add_argument("--independent-benchmark", action="store_true", help="Explicitly acknowledge NASA reference benchmark omits known DCP correlations")
    probability.add_argument("--covariance-file", type=Path, help="Live SUPPLIED/ASSUMED covariance-input JSON")
    screen = commands.add_parser("screen", help="Compare nominal/modified trajectories within declared catalog coverage")
    screen.add_argument("--encounter-id", required=True)
    screen.add_argument("--object-id", required=True)
    screen.add_argument("--maneuver-time", required=True)
    screen.add_argument("--delta-v-rtn", nargs=3, type=float, required=True, metavar=("R", "T", "N"))
    screen.add_argument("--assume-capability", action="store_true")
    screening_arguments(screen)
    catalog = commands.add_parser("catalog", help="Explicitly load a declared catalog and report metadata")
    screening_arguments(catalog)
    optimize = commands.add_parser("optimize", help="Search bounded hypothetical maneuver candidates")
    optimize.add_argument("--encounter-id", required=True)
    optimize.add_argument("--object-id", required=True)
    optimize.add_argument("--max-delta-v", type=float, required=True, help="Maximum impulse magnitude, m/s")
    optimize.add_argument("--min-lead-minutes", type=float, default=15)
    optimize.add_argument("--max-lead-hours", type=float, default=2)
    optimize.add_argument("--target-km", type=float, required=True)
    optimize.add_argument("--objective", choices=[objective.value for objective in Objective], default=Objective.MAXIMUM_CLEARANCE.value)
    optimize.add_argument("--assume-capability", action="store_true")
    optimize.add_argument("--initial-mass-kg", type=float)
    optimize.add_argument("--propellant-mass-kg", type=float)
    optimize.add_argument("--specific-impulse-s", type=float)
    optimize.add_argument("--time-samples", type=int, default=6)
    optimize.add_argument("--magnitude-samples", type=int, default=3)
    optimize.add_argument("--max-evaluations", type=int, default=150)
    optimize.add_argument("--timeout-seconds", type=float, default=25)
    optimize.add_argument("--refinement-evaluations", type=int, default=20)
    optimize.add_argument("--secondary-screening", choices=[policy.value for policy in ScreeningPolicy],
                          help="Enable bounded finalist screening with this policy")
    optimize.add_argument("--screen-max-finalists", type=int, default=3)
    optimize.add_argument("--screen-total-timeout-seconds", type=float, default=90)
    screening_arguments(optimize)
    weather = commands.add_parser("space-weather",help="Show source/cache coverage; --load explicitly retrieves data")
    weather.add_argument("--load",action="store_true")
    for name in ("decay","persistence"):
        decay = commands.add_parser(name,help="Analyze orbital decay / persistence; omit ID for interactive input")
        decay.add_argument("--object-id")
        decay.add_argument("--mass-kg",type=float)
        decay.add_argument("--area-m2",type=float)
        decay.add_argument("--drag-coefficient",type=float)
        decay.add_argument("--cd-area-over-mass",type=float)
        decay.add_argument("--assume-properties",action="store_true",help="Explicitly acknowledge supplied properties are hypothetical, not catalog measurements")
        decay.add_argument("--horizon-days",type=float,default=1)
        decay.add_argument("--boundary-km",type=float,default=120)
        decay.add_argument("--scenario-mode",choices=["NOMINAL","COMPARE"],default="NOMINAL")
        decay.add_argument("--weather-mode",choices=["SOURCE_ONLY","HYPOTHETICAL_CONSTANT","SOURCE_WITH_EXPLICIT_FALLBACK"],default="SOURCE_ONLY")
        decay.add_argument("--nominal-f107",type=float)
        decay.add_argument("--nominal-ap",type=float)
        decay.add_argument("--min-cd-area-over-mass",type=float)
        decay.add_argument("--max-cd-area-over-mass",type=float)
        decay.add_argument("--start-time")
        decay.add_argument("--sample-step-seconds",type=float,default=600)
        decay.add_argument("--timeout-seconds",type=float,default=180)
    return root


def show_encounters(encounters, output):
    print("Upcoming predicted close approaches:", file=output)
    for index, encounter in enumerate(encounters, 1):
        print(f"{index}. {encounter.object_1_name} / {encounter.object_2_name}\n"
              f"   ID: {encounter.id}\n"
              f"   Published separation: {encounter.source_miss_distance_m:.3f} m\n"
              f"   TCA: {encounter.time_of_closest_approach.isoformat()}\n"
              f"   SOCRATES MAX_PROB screening metric: {encounter.socrates_max_probability}", file=output)
    print("MAX_PROB is not a calibrated collision probability.", file=output)


def show_probability(result, output):
    if isinstance(result, ReferenceComparison):
        print(f"Historical NASA independent-model benchmark: {result.reference_case}\n"
              f"Published precise Pc2D: {result.published_reference_pc:.12g}\n"
              f"CDM rounded Pc: {result.cdm_rounded_reference_pc}\n"
              f"Independent Kessler Pc: {result.calculated_pc}\n"
              f"Numerical difference: {result.numerical_difference}\n"
              f"Relative difference: {result.relative_difference}\n"
              f"Linear TCA rounding correction: {result.linear_tca_offset_seconds:.9g} s", file=output)
    else:
        print(f"Probability status: {result.probability_status}\n"
              f"SOCRATES MAX_PROB screening metric (not Pc): {result.socrates_max_probability}\n"
              f"Covariance-based Pc: {result.calculated_pc}", file=output)
        if result.label:
            print(result.label, file=output)
    for explanation in [*result.assumptions, *result.warnings]:
        print("  - " + explanation, file=output)


def show_results(result: OptimizationResult, output):
    print(f"\nRESULTS — {result.status}\nEncounter: {result.encounter_id}\n"
          f"Maneuvering object: {result.maneuvering_object_id}\n"
          f"Matched baseline separation: {result.baseline.miss_distance_m:.3f} m\n"
          f"Candidates evaluated: {result.candidates_evaluated}; "
          f"feasible: {result.feasible_candidates}; runtime: {result.elapsed_seconds:.3f} s", file=output)
    if not result.solutions:
        print("No feasible evaluated solution returned.", file=output)
    for index, solution in enumerate(result.solutions):
        print("\nBest evaluated maneuver:" if index == 0 else "\nDistinct evaluated alternative:", file=output)
        print(f"  Burn time: {solution.maneuver_time.isoformat()}\n"
              f"  Delta-v: {solution.delta_v_m_s:.6f} m/s; RTN: {solution.delta_v_rtn_m_s}\n"
              f"  Predicted separation: {solution.new_miss_distance_m:.3f} m\n"
              f"  Clearance change: {solution.change_in_miss_distance_m:+.3f} m\n"
              f"  Meets target: {'Yes' if solution.meets_target else 'No'}", file=output)
    if result.secondary_screening is not None:
        summary = result.secondary_screening
        print(f"\nSecondary policy: {summary.policy}; status: {summary.status}\n"
              f"Maneuvers screened: {summary.candidates_screened}/{summary.max_finalists}; "
              f"selected primary rank: {summary.selected_primary_rank}", file=output)
        for assessment in summary.candidate_results:
            print(f"  Primary rank {assessment.primary_rank}; policy pass: {assessment.policy_passed}; "
                  f"selected: {assessment.selected}", file=output)
            if assessment.screening is not None:
                show_screening(assessment.screening, output)
            for warning in assessment.warnings:
                print("  Warning: " + warning, file=output)
    print("\nModel assumptions and limitations:", file=output)
    for explanation in [*result.model_assumptions, *result.warnings]:
        print(f"  - {explanation}", file=output)


def show_screening(result, output):
    print(f"\nSecondary screening: {result.screening_status}; complete within declared scope: {result.screening_complete}\n"
          f"Catalog objects screened: {result.objects_screened}/{result.catalog.objects_available}; "
          f"refined: {result.candidate_objects_refined}; coverage: {result.catalog.coverage}\n"
          f"Illustrative alert threshold: {result.alert_distance_km:g} km (not a universal safe distance)\n"
          f"Screening horizon (UTC): {result.screening_window.start.isoformat()} → {result.screening_window.end.isoformat()}\n"
          f"Additional below-threshold approaches: {result.additional_close_approaches}; "
          f"new: {result.newly_introduced}; worsened: {result.worsened}; improved: {result.improved}", file=output)
    for event in result.secondary_encounters:
        label = "original counterpart" if event.is_original_counterpart else "additional object"
        baseline = "unavailable" if event.baseline_miss_distance_m is None else f"{event.baseline_miss_distance_m:.3f} m"
        print(f"  {event.secondary_object_id} ({event.secondary_object_name}; {label}): "
              f"{event.classification}, {baseline} → {event.maneuvered_miss_distance_m:.3f} m "
              f"at {event.time_of_closest_approach.isoformat()}", file=output)
    closest = result.closest_additional_encounter
    if closest is not None:
        print(f"Closest calculated additional approach: {closest.secondary_object_id}, "
              f"{closest.maneuvered_miss_distance_m:.3f} m at {closest.time_of_closest_approach.isoformat()}", file=output)
    else:
        print("No calculated closest-additional result available; inspect completeness and coverage.", file=output)
    for limitation in [*result.model_limitations, *result.warnings]:
        print("  - " + limitation, file=output)


def ask_choice(prompt, choices, input_fn, output):
    while True:
        answer = input_fn(prompt).strip()
        if answer in choices:
            return answer
        print("Invalid choice; please choose one of: " + ", ".join(choices), file=output)


def ask_number(prompt, input_fn, output, minimum=0, inclusive=False):
    while True:
        try:
            number = float(input_fn(prompt))
            if math.isfinite(number) and (number >= minimum if inclusive else number > minimum):
                return number
        except ValueError:
            pass
        print("Invalid number; provide a finite value in the allowed range.", file=output)


def interactive(engine, input_fn, output):
    print("====================================\n             KESSLER\n     Orbital Avoidance Engine\n====================================", file=output)
    encounters = engine.discovery.list_encounters(limit=10)
    if not encounters:
        raise SourceUnavailable("No upcoming encounters available in the actual source dataset")
    show_encounters(encounters, output)
    choice = ask_choice("Choose encounter number: ", [str(index) for index in range(1, len(encounters)+1)], input_fn, output)
    encounter, first, second = engine.selected_case(encounters[int(choice)-1].id)
    baseline = analyze_encounter(encounter, first, second)
    print(f"\nSelected: {encounter.object_1_name} vs {encounter.object_2_name}\n"
          f"Published closest approach: {baseline.published.miss_distance_m:.3f} m\n"
          f"SGP4 calculated closest approach: {baseline.calculated.miss_distance_m:.3f} m\n"
          f"Relative speed: {baseline.calculated.relative_speed_m_s:.3f} m/s\n"
          f"Calculated TCA: {baseline.calculated.tca.isoformat()}", file=output)
    for warning in baseline.warnings:
        print("Warning: " + warning, file=output)
    object_choice = ask_choice(f"Maneuvering object (1={encounter.object_1_id}, 2={encounter.object_2_id}): ", ["1", "2"], input_fn, output)
    assumption = ask_choice("Explicitly assume this object has hypothetical maneuver capability? (yes/no): ", ["yes", "no"], input_fn, output)
    if assumption != "yes":
        raise ValueError("An explicit hypothetical capability assumption is required")
    budget = ask_number("Maximum velocity change (m/s): ", input_fn, output, inclusive=True)
    maximum_lead = ask_number("Maximum maneuver lead time (hours, ≤48): ", input_fn, output)
    preparation = ask_number("Minimum preparation time (minutes): ", input_fn, output)
    target = ask_number("Target separation (km): ", input_fn, output)
    objective = ask_choice("Priority: 1=Minimum velocity change, 2=Maximum modeled clearance: ", ["1", "2"], input_fn, output)
    constraints = ManeuverConstraints(
        encounter_id=encounter.id, maneuvering_object_id=encounter.object_1_id if object_choice == "1" else encounter.object_2_id,
        max_delta_v_m_s=budget, min_lead_time_minutes=preparation, max_lead_time_hours=maximum_lead,
        target_miss_distance_km=target, objective=Objective.MINIMUM_DELTA_V if objective == "1" else Objective.MAXIMUM_CLEARANCE,
        hypothetical_capability_assumed=True)
    print("Calculating actual hypothetical maneuvers...", file=output)
    result = optimize_maneuver(encounter, first, second, constraints, retain_finalists=3)
    show_results(result, output)
    if not result.solutions:
        return result
    try:
        choice = ask_choice("Screen this maneuver against other cataloged objects? (yes/no): ", ["yes", "no"], input_fn, output)
    except (EOFError, StopIteration):
        # Optional EOF preserves the completed Phase 1 workflow, not a screening pass.
        print("Secondary screening not requested; maneuver remains unassessed against additional objects.", file=output)
        return result
    if choice == "yes":
        policy = ask_choice("Screening policy (REPORT_ONLY/REJECT_NEW_ALERTS/REJECT_ALL_ALERTS): ",
                            [policy.value for policy in ScreeningPolicy], input_fn, output)
        threshold = ask_number("Illustrative proximity threshold (km, not a safe distance): ", input_fn, output)
        horizon = ask_number("Screen until hours after original TCA (≤24): ", input_fn, output)
        scope = ask_choice("Catalog: 1=default public GP groups, 2=local OMM JSON/CSV: ", ["1", "2"], input_fn, output)
        selection = CatalogSelection() if scope == "1" else CatalogSelection(
            groups=(), local_files=(Path(input_fn("Local OMM filename: ").strip()),))
        settings = SecondaryOptimizationSettings(policy=policy, alert_distance_km=threshold,
            post_tca_horizon_hours=horizon, catalog_selection=selection)
        catalog = engine.catalog.load_screening_catalog(selection)
        base = settings.model_dump(exclude={"policy", "max_finalists", "total_timeout_seconds"})
        def screen_candidate(option, deadline):
            request = ScreeningRequest(**base, encounter_id=encounter.id,
                maneuvering_object_id=constraints.maneuvering_object_id,
                maneuver_time=option.maneuver_time, delta_v_rtn_m_s=option.delta_v_rtn_m_s,
                hypothetical_capability_assumed=True)
            return screen_proposed_maneuver(encounter, first, second, request, catalog,
                result.numerical_reference_epoch, cache=engine.catalog_propagation_cache, deadline=deadline)
        result = screen_ranked_finalists(result, settings, screen_candidate)
        show_results(result, output)
    return result


def persistence_command(args,engine,input_fn,output):
    if args.object_id is None:
        if args.json:
            raise ValueError("JSON persistence requires --object-id")
        print("Analyze orbital decay / persistence — hypothetical properties, not measured object data.",file=output)
        args.object_id = validate_object_id(input_fn("NORAD catalog ID: ").strip())
        record = engine.celestrak.get_object(args.object_id)
        print(f"{record.elements.object_name}; GP epoch {record.elements.epoch.isoformat()}",file=output)
        args.mass_kg = ask_number("Assumed mass (kg): ",input_fn,output)
        args.area_m2 = ask_number("Assumed effective area (m²): ",input_fn,output,inclusive=True)
        args.drag_coefficient = ask_number("Assumed Cd: ",input_fn,output)
        args.horizon_days = ask_number("Prediction horizon (days, at most 90): ",input_fn,output)
        choice = ask_choice("Scenarios: 1 nominal source weather; 2 LOW/NOMINAL/HIGH comparison: ",{"1","2"},input_fn,output)
        args.scenario_mode = "NOMINAL" if choice == "1" else "COMPARE"
        args.assume_properties = True
    supplied = any(x is not None for x in (args.mass_kg,args.area_m2,args.drag_coefficient,args.cd_area_over_mass))
    if supplied and not args.assume_properties:
        raise ValueError("Use --assume-properties to explicitly label hypothetical aerodynamic inputs")
    properties = None if not supplied else ObjectAerodynamicProperties(input_category="HYPOTHETICAL_ASSUMPTION",
        mass_kg=args.mass_kg,area_m2=args.area_m2,drag_coefficient=args.drag_coefficient,
        cd_area_over_mass_m2_kg=args.cd_area_over_mass)
    settings = PersistenceSettings(horizon_days=args.horizon_days,boundary_altitude_m=args.boundary_km*1000,
        scenario_mode=args.scenario_mode,weather_mode=args.weather_mode,
        nominal_f107_sfu=args.nominal_f107,nominal_ap=args.nominal_ap,
        min_cd_area_over_mass_m2_kg=args.min_cd_area_over_mass,max_cd_area_over_mass_m2_kg=args.max_cd_area_over_mass,
        solver=SolverSettings(sample_step_seconds=args.sample_step_seconds,timeout_seconds=args.timeout_seconds))
    result = analyze_orbital_persistence(args.object_id,properties,settings,engine=engine,
        start_time=None if args.start_time is None else parse_utc(args.start_time))
    if not args.json:
        print(f"{result.object_name} ({result.object_id}) — {result.prediction_status}\n"
              f"GP epoch: {result.gp_epoch.isoformat()}; modeled horizon: {result.prediction_horizon_days:g} days",file=output)
        print("ILLUSTRATIVE — USER-SUPPLIED AERODYNAMIC ASSUMPTIONS. Not an operational reentry prediction.",file=output)
        for scenario in [] if result.scenario_analysis is None else result.scenario_analysis.scenarios:
            print(f"{scenario.scenario}: {scenario.boundary.prediction_status}; cutoff {scenario.boundary.boundary_altitude_m/1000:g} km; "
                  f"crossing time: {scenario.boundary.crossing_time}; specific energy change: {scenario.total_specific_energy_change_j_kg} J/kg",file=output)
            print(f"  Environment: {scenario.environment_assumptions}",file=output)
        for warning in [*result.assumptions,*result.warnings]: print(f"  - {warning}",file=output)
    return result


def main(argv=None, engine: Engine | None = None, input_fn=None, output=None, error_output=None) -> int:
    output = output or sys.stdout
    error_output = error_output or sys.stderr
    input_fn = input_fn or input
    args = parser().parse_args(argv)
    engine = engine or Engine(args.cache_dir)
    try:
        if args.command is None:
            if args.json:
                raise ValueError("JSON mode requires list, analyze, simulate, optimize, screen, catalog, or probability command")
            interactive(engine, input_fn, output)
            return 0
        if args.command in {"decay","persistence"}:
            result = persistence_command(args,engine,input_fn,output)
        elif args.command == "space-weather":
            data = engine.space_weather.load_space_weather() if args.load else engine.space_weather.dataset
            result = {"status":"NOT_LOADED" if data is None else data.retrieval_mode,"coverage":None if data is None else data.coverage()}
            if not args.json: print(json.dumps(result,indent=2),file=output)
        elif args.command == "probability" and (args.reference_case or args.list_reference_cases or args.input_file):
            if args.covariance_file:
                raise ValueError("--covariance-file is only supported with a live --encounter-id")
            if args.list_reference_cases:
                result = {"source": "NASA_CARA_HISTORICAL_REFERENCE", "reference_cases": reference_cases()}
                if not args.json:
                    print(json.dumps(result, indent=2), file=output)
            elif args.input_file:
                result = calculate_request(DirectProbabilityRequest.model_validate_json(args.input_file.read_text()))
                if not args.json:
                    show_probability(result, output)
            else:
                result = evaluate_reference(args.reference_case, independent_benchmark=args.independent_benchmark)
                if not args.json:
                    show_probability(result, output)
        elif args.command == "catalog":
            result = engine.catalog.load_screening_catalog(screening_settings(args)["catalog_selection"]).metadata
            if not args.json:
                print(result.model_dump_json(indent=2), file=output)
        elif args.command == "list":
            encounters = engine.discovery.list_encounters(args.sort, args.limit, args.object_id, args.name)
            dataset = engine.socrates.get_dataset()
            result = {"items": [encounter.model_dump(mode="json") for encounter in encounters],
                      "total_source_encounters": len(dataset.encounters), "data_status": dataset.data_status,
                      "source_url": dataset.source_url, "dataset_timestamp": dataset.dataset_timestamp.isoformat(),
                      "content_sha256": dataset.content_sha256, "warnings": dataset.warnings}
            if not args.json:
                show_encounters(encounters, output)
        else:
            encounter, first, second = engine.selected_case(args.encounter_id)
            if args.command == "analyze":
                result = analyze_encounter(encounter, first, second)
                if args.probability or args.covariance_file:
                    inputs = None if args.covariance_file is None else ProbabilityInputs.model_validate_json(args.covariance_file.read_text())
                    result = with_live_probability((encounter, first, second), result, inputs)
            elif args.command == "probability":
                inputs = None if args.covariance_file is None else ProbabilityInputs.model_validate_json(args.covariance_file.read_text())
                result = with_live_probability((encounter, first, second), analyze_encounter(encounter, first, second), inputs).probability_analysis
                if not args.json:
                    show_probability(result, output)
            elif args.command == "simulate":
                result = simulate_maneuver(encounter, first, second, args.object_id,
                    parse_utc(args.maneuver_time), tuple(args.delta_v_rtn), args.assume_capability)
                if args.probability_scenario_file:
                    result = with_maneuver_probability((encounter, first, second), result,
                        json.loads(args.probability_scenario_file.read_text()))
            elif args.command == "screen":
                request = ScreeningRequest(**screening_settings(args), encounter_id=args.encounter_id,
                    maneuvering_object_id=args.object_id, maneuver_time=parse_utc(args.maneuver_time),
                    delta_v_rtn_m_s=tuple(args.delta_v_rtn), hypothetical_capability_assumed=args.assume_capability)
                request.screening_window(encounter)
                catalog = engine.catalog.load_screening_catalog(request.catalog_selection)
                result = screen_proposed_maneuver(encounter, first, second, request, catalog,
                    cache=engine.catalog_propagation_cache)
                if not args.json:
                    show_screening(result, output)
            else:
                constraints = ManeuverConstraints(encounter_id=args.encounter_id, maneuvering_object_id=args.object_id,
                    max_delta_v_m_s=args.max_delta_v, min_lead_time_minutes=args.min_lead_minutes,
                    max_lead_time_hours=args.max_lead_hours, target_miss_distance_km=args.target_km,
                    objective=args.objective, hypothetical_capability_assumed=args.assume_capability,
                    initial_mass_kg=args.initial_mass_kg, available_propellant_mass_kg=args.propellant_mass_kg,
                    specific_impulse_s=args.specific_impulse_s)
                search = SearchSettings(time_samples=args.time_samples, magnitude_samples=args.magnitude_samples,
                    max_evaluations=args.max_evaluations, timeout_seconds=args.timeout_seconds,
                    refinement_evaluations=args.refinement_evaluations)
                if args.secondary_screening is None:
                    result = optimize_maneuver(encounter, first, second, constraints, search)
                else:
                    settings = SecondaryOptimizationSettings(**screening_settings(args), policy=args.secondary_screening,
                        max_finalists=args.screen_max_finalists, total_timeout_seconds=args.screen_total_timeout_seconds)
                    catalog = engine.catalog.load_screening_catalog(settings.catalog_selection)
                    result = optimize_with_secondary_screening(encounter, first, second, constraints, search,
                        secondary_settings=settings, catalog=catalog, cache=engine.catalog_propagation_cache)
                if not args.json:
                    show_results(result, output)
            if not args.json and args.command not in {"optimize", "screen", "probability"}:
                print(result.model_dump_json(indent=2), file=output)
        if args.json:
            payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
            print(json.dumps(payload, allow_nan=False), file=output)
        return 0
    except (SourceUnavailable, OrbitalUnavailable, EncounterNotFound, CalculationUnavailable,
            ManeuverError, PropagationError, ValueError, OSError,SpaceWeatherUnavailable) as error:
        if args.json:
            print(json.dumps({"status": "UNAVAILABLE" if isinstance(error, (SourceUnavailable, OrbitalUnavailable))
                              else "ERROR", "detail": str(error)}), file=output)
        else:
            print("Kessler error: " + str(error), file=error_output)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("Kessler input cancelled.", file=error_output)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
