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
    simulate = commands.add_parser("simulate", help="Simulate one actual hypothetical velocity impulse")
    simulate.add_argument("--encounter-id", required=True)
    simulate.add_argument("--object-id", required=True)
    simulate.add_argument("--maneuver-time", required=True, help="ISO timestamp; timezone omitted means UTC")
    simulate.add_argument("--delta-v-rtn", nargs=3, type=float, required=True, metavar=("R", "T", "N"))
    simulate.add_argument("--assume-capability", action="store_true")
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


def main(argv=None, engine: Engine | None = None, input_fn=None, output=None, error_output=None) -> int:
    output = output or sys.stdout
    error_output = error_output or sys.stderr
    input_fn = input_fn or input
    args = parser().parse_args(argv)
    engine = engine or Engine(args.cache_dir)
    try:
        if args.command is None:
            if args.json:
                raise ValueError("JSON mode requires list, analyze, simulate, optimize, screen, or catalog command")
            interactive(engine, input_fn, output)
            return 0
        if args.command == "catalog":
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
            elif args.command == "simulate":
                result = simulate_maneuver(encounter, first, second, args.object_id,
                    parse_utc(args.maneuver_time), tuple(args.delta_v_rtn), args.assume_capability)
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
            if not args.json and args.command not in {"optimize", "screen"}:
                print(result.model_dump_json(indent=2), file=output)
        if args.json:
            payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
            print(json.dumps(payload, allow_nan=False), file=output)
        return 0
    except (SourceUnavailable, OrbitalUnavailable, EncounterNotFound, CalculationUnavailable,
            ManeuverError, PropagationError, ValueError) as error:
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
