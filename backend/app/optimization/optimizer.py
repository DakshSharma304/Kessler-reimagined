"""Coarse RTN search and local refinements, with explicit evaluation/time limits."""

from datetime import UTC, datetime, timedelta
import time
from typing import Literal

import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from scipy.optimize import minimize_scalar

from app.models.encounter import Encounter
from app.models.maneuver import ManeuverConstraints, Objective
from app.models.orbital import OrbitalRecord
from app.optimization.objectives import objective_key
from app.physics.encounters import BaselineAnalysis, ClosestApproach, CalculationUnavailable, analyze_encounter
from app.physics.maneuvers import MODEL_ASSUMPTIONS, MatchedDynamics, ManeuverError, simulate_maneuver
from app.physics.propagation import PropagationError


class SearchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    time_samples: int = Field(default=6, ge=1, le=8)
    magnitude_samples: int = Field(default=3, ge=1, le=5)
    max_evaluations: int = Field(default=150, ge=1, le=500)
    timeout_seconds: float = Field(default=25, gt=0, le=120)
    refinement_evaluations: int = Field(default=20, ge=0, le=60)


class ManeuverOption(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    maneuver_time: AwareDatetime
    delta_v_m_s: float
    delta_v_rtn_m_s: tuple[float, float, float]
    new_miss_distance_m: float
    change_in_miss_distance_m: float
    meets_target: bool
    is_clearance_improvement: bool
    calculated_tca: AwareDatetime
    matched_baseline_miss_distance_m: float


class OptimizationResult(BaseModel):
    encounter_id: str
    maneuvering_object_id: str
    status: Literal["COMPLETE", "PARTIAL", "NO_FEASIBLE_SOLUTION"]
    result_label: Literal["Best evaluated maneuvers; no global optimality guarantee"] = "Best evaluated maneuvers; no global optimality guarantee"
    objective: Objective
    constraints: ManeuverConstraints
    search_settings: SearchSettings
    baseline: ClosestApproach
    sgp4_reference: BaselineAnalysis
    numerical_reference_epoch: AwareDatetime
    solutions: list[ManeuverOption]
    candidates_evaluated: int
    feasible_candidates: int
    target_feasible_candidates: int
    numerical_failures: int
    elapsed_seconds: float
    fuel_budget_delta_v_m_s: float | None
    model_assumptions: list[str]
    warnings: list[str]


class SearchLimitReached(Exception):
    pass


def optimize_maneuver(encounter: Encounter, first: OrbitalRecord, second: OrbitalRecord,
                       constraints: ManeuverConstraints, search: SearchSettings | None = None,
                       now: datetime | None = None) -> OptimizationResult:
    started = time.perf_counter()
    search = search or SearchSettings()
    now = now or datetime.now(UTC)
    earliest, latest = constraints.burn_window(encounter, now)
    reference = analyze_encounter(encounter, first, second)
    if reference.calculated.status != "COMPLETE":
        raise CalculationUnavailable("Optimization requires an interior SGP4 reference TCA")
    dynamics = MatchedDynamics(encounter, first, second, earliest, reference)
    if dynamics.baseline.status != "COMPLETE":
        raise CalculationUnavailable("Matched numerical baseline has no interior local TCA")
    deadline = started + search.timeout_seconds
    budget = constraints.effective_delta_v_budget_m_s
    target = constraints.target_miss_distance_km * 1000
    warnings = list(reference.warnings)
    evaluated = failures = 0
    partial = False
    memo: dict[tuple, ManeuverOption | None] = {}
    valid: list[ManeuverOption] = []

    def evaluate(at: datetime, vector) -> ManeuverOption | None:
        nonlocal evaluated, failures
        vector = np.array(vector, dtype=float)
        norm = float(np.linalg.norm(vector))
        if norm > budget + 1e-12 or norm < 0 or not earliest <= at <= latest:
            return None
        key = (at.isoformat(), *[round(float(value), 12) for value in vector])
        if key in memo:
            return memo[key]
        if evaluated >= search.max_evaluations or time.perf_counter() >= deadline:
            raise SearchLimitReached()
        evaluated += 1
        try:
            simulation = simulate_maneuver(encounter, first, second,
                constraints.maneuvering_object_id, at, tuple(vector), True, now=now,
                trajectory_samples=0, analysis=reference, shared_dynamics=dynamics)
            if simulation.modified.status != "COMPLETE":
                raise ManeuverError("Candidate minimum is at a search boundary")
            option = ManeuverOption(
                maneuver_time=at, delta_v_m_s=norm, delta_v_rtn_m_s=tuple(vector),
                new_miss_distance_m=simulation.modified.miss_distance_m,
                change_in_miss_distance_m=simulation.change_in_miss_distance_m,
                meets_target=simulation.modified.miss_distance_m >= target,
                is_clearance_improvement=simulation.change_in_miss_distance_m > .001,
                calculated_tca=simulation.modified.tca,
                matched_baseline_miss_distance_m=simulation.matched_baseline.miss_distance_m,
            )
            valid.append(option)
            memo[key] = option
            return option
        except (ManeuverError, PropagationError, CalculationUnavailable, ValueError) as error:
            failures += 1
            if failures <= 10:
                warnings.append(f"Candidate calculation failed: {error}")
            memo[key] = None
            return None

    def eligible():
        return [item for item in valid if constraints.objective != Objective.MINIMUM_DELTA_V or item.meets_target]

    times = [earliest + timedelta(seconds=float(offset))
             for offset in np.linspace(0, (latest-earliest).total_seconds(), search.time_samples)]
    directions = [sign * np.eye(3)[axis] for axis in (1, 0, 2) for sign in (1, -1)]
    try:
        evaluate(earliest, np.zeros(3))
        if budget > 0:
            for at in times:
                for magnitude in np.linspace(budget/search.magnitude_samples, budget, search.magnitude_samples):
                    for direction in directions:
                        evaluate(at, magnitude*direction)
        candidates = eligible()
        if candidates and search.refinement_evaluations:
            promising = sorted(candidates, key=lambda option: objective_key(option, constraints.objective))[0]
            refinement_start = evaluated
            vector = np.array(promising.delta_v_rtn_m_s)
            def refinement_evaluate(at, impulse):
                if evaluated - refinement_start >= search.refinement_evaluations:
                    raise SearchLimitReached()
                return evaluate(at, impulse)
            # Bounded local time refinement, with the true simulator as objective.
            center = (promising.maneuver_time-earliest).total_seconds()
            duration = (latest-earliest).total_seconds()
            spacing = duration/max(search.time_samples-1, 1)
            lower, upper = max(0, center-spacing/2), min(duration, center+spacing/2)
            if upper > lower:
                def time_loss(offset):
                    option = refinement_evaluate(earliest+timedelta(seconds=float(offset)), vector)
                    return float("inf") if option is None else -option.new_miss_distance_m
                minimize_scalar(time_loss, method="bounded", bounds=(lower, upper),
                                options={"maxiter": min(8, search.refinement_evaluations), "xatol": 1})
            # Explore lower effort and nearby directions using actual evaluations.
            for scale in (.5, .75):
                refinement_evaluate(promising.maneuver_time, vector*scale)
            if np.linalg.norm(vector) > 0:
                unit = vector/np.linalg.norm(vector)
                for axis in np.eye(3):
                    if abs(np.dot(unit, axis)) < .9:
                        for sign in (-1, 1):
                            direction = unit + sign*.1*axis
                            refinement_evaluate(promising.maneuver_time,
                                direction/np.linalg.norm(direction)*np.linalg.norm(vector))
    except SearchLimitReached:
        partial = True
        warnings.append("Search stopped at its evaluation, time, or local-refinement budget; results are partial.")
    candidates = sorted(eligible(), key=lambda option: objective_key(option, constraints.objective))
    solutions = []
    if candidates:
        alternatives = [candidates[0], min(candidates, key=lambda item: (item.delta_v_m_s, -item.new_miss_distance_m)),
                        max(candidates, key=lambda item: (item.new_miss_distance_m, -item.delta_v_m_s))]
        for option in alternatives:
            if not any(option.maneuver_time == item.maneuver_time and option.delta_v_rtn_m_s == item.delta_v_rtn_m_s for item in solutions):
                solutions.append(option)
    if constraints.objective == Objective.MAXIMUM_CLEARANCE and solutions and not solutions[0].meets_target:
        warnings.append("No evaluated candidate reached the requested target; returned clearance is the best evaluated within the hard budget/window constraints.")
    status = "PARTIAL" if partial else "COMPLETE" if solutions else "NO_FEASIBLE_SOLUTION"
    return OptimizationResult(
        encounter_id=encounter.id, maneuvering_object_id=constraints.maneuvering_object_id,
        status=status, objective=constraints.objective, constraints=constraints,
        search_settings=search, baseline=dynamics.baseline, sgp4_reference=reference,
        numerical_reference_epoch=earliest, solutions=solutions,
        candidates_evaluated=evaluated, feasible_candidates=len(eligible()),
        target_feasible_candidates=sum(item.meets_target for item in valid),
        numerical_failures=failures, elapsed_seconds=time.perf_counter()-started,
        fuel_budget_delta_v_m_s=constraints.fuel_budget_delta_v_m_s,
        model_assumptions=[*MODEL_ASSUMPTIONS, "All candidate burns share one numerical reference epoch and nominal trajectory.",
                          "Bounded deterministic samples plus local time/magnitude/direction exploration; no global optimum guarantee.",
                          "Clearance improvement flag requires >1 mm modeled change; no uncertainty inference."] ,
        warnings=warnings,
    )
