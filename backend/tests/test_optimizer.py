from datetime import timedelta

import numpy as np
import pytest

from app.models.maneuver import ManeuverConstraints
from app.optimization.optimizer import SearchSettings, optimize_maneuver
from app.physics.maneuvers import ManeuverError
from test_constraints import constraint_input
from test_encounters import START, actual_case

SMALL = SearchSettings(time_samples=2, magnitude_samples=1, max_evaluations=20,
                       timeout_seconds=25, refinement_evaluations=0)


def optimize(search=SMALL, **changes):
    encounter, first, second = actual_case()
    return optimize_maneuver(encounter, first, second, ManeuverConstraints(**constraint_input(**changes)), search, START)


def test_actual_simulations_bounds_and_computed_outcomes(monkeypatch):
    import app.optimization.optimizer as module
    simulator = module.simulate_maneuver
    calls = []
    def observed(*args, **kwargs):
        result = simulator(*args, **kwargs)
        calls.append(result)
        return result
    monkeypatch.setattr(module, "simulate_maneuver", observed)
    result = optimize()
    encounter, *_ = actual_case()
    assert result.status == "COMPLETE"
    assert result.candidates_evaluated == len(calls) == 13
    assert result.solutions
    for option in result.solutions:
        result.constraints.validate_burn_time(encounter, option.maneuver_time, START)
        assert np.linalg.norm(option.delta_v_rtn_m_s) <= .2 + 1e-12
        matching = next(item for item in calls if item.maneuver_time == option.maneuver_time and item.delta_v_rtn_m_s == option.delta_v_rtn_m_s)
        assert option.new_miss_distance_m == matching.modified.miss_distance_m
        assert option.meets_target == (option.new_miss_distance_m >= 10000)
        assert option.is_clearance_improvement == (option.change_in_miss_distance_m > .001)
    assert all(item.matched_baseline.miss_distance_m == result.baseline.miss_distance_m for item in calls)


def test_changed_budget_and_warning_time_change_search():
    first = optimize(max_delta_v_m_s=.05)
    larger = optimize(max_delta_v_m_s=.3)
    shorter = optimize(max_lead_time_hours=.5)
    assert larger.solutions[0].new_miss_distance_m > first.solutions[0].new_miss_distance_m
    assert larger.solutions[0].delta_v_m_s != first.solutions[0].delta_v_m_s
    assert shorter.numerical_reference_epoch != first.numerical_reference_epoch
    assert shorter.solutions[0].maneuver_time >= actual_case()[0].time_of_closest_approach-timedelta(hours=.5)


def test_objective_and_no_feasible_target():
    minimum = optimize(objective="MINIMUM_DELTA_V", target_miss_distance_km=10)
    assert minimum.solutions
    assert all(item.meets_target for item in minimum.solutions)
    assert minimum.solutions[0].delta_v_m_s == min(item.delta_v_m_s for item in minimum.solutions)
    impossible = optimize(objective="MINIMUM_DELTA_V", target_miss_distance_km=100000, max_delta_v_m_s=0)
    assert impossible.status == "NO_FEASIBLE_SOLUTION"
    assert impossible.solutions == []


def test_reproducible_and_zero_budget_not_fabricated_improvement():
    one, two = optimize(max_delta_v_m_s=0), optimize(max_delta_v_m_s=0)
    assert one.solutions == two.solutions
    assert one.candidates_evaluated == two.candidates_evaluated == 1
    assert one.solutions[0].delta_v_m_s == 0
    assert not one.solutions[0].is_clearance_improvement


def test_numerical_failures_do_not_crash_search(monkeypatch):
    import app.optimization.optimizer as module
    actual = module.simulate_maneuver
    def fail_nonzero(*args, **kwargs):
        if np.linalg.norm(args[5]) > 0:
            raise ManeuverError("Injected integration failure")
        return actual(*args, **kwargs)
    monkeypatch.setattr(module, "simulate_maneuver", fail_nonzero)
    result = optimize()
    assert result.numerical_failures == 12
    assert result.solutions[0].delta_v_m_s == 0
    assert any("Injected" in warning for warning in result.warnings)


def test_timeout_returns_honest_partial_results():
    result = optimize(SearchSettings(timeout_seconds=1e-6, refinement_evaluations=0))
    assert result.status == "PARTIAL"
    assert result.candidates_evaluated == 0
    assert not result.solutions


def test_default_bounded_search_and_refinement_benchmark():
    result = optimize(SearchSettings())
    assert result.solutions
    assert result.candidates_evaluated <= 150
    assert all(item.delta_v_m_s <= .2 + 1e-12 for item in result.solutions)
    print(f"Optimizer benchmark: {result.candidates_evaluated} evaluations; "
          f"{result.feasible_candidates} feasible; {result.numerical_failures} failures; "
          f"runtime {result.elapsed_seconds:.3f}s; status {result.status}; "
          f"best clearance {result.solutions[0].new_miss_distance_m:.3f}m; "
          f"delta-v {result.solutions[0].delta_v_m_s:.6f}m/s")
