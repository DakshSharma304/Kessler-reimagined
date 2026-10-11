from datetime import timedelta
import json
import math

import pytest

from app.models.maneuver import G0, ManeuverConstraints
from test_encounters import START, actual_case


def constraint_input(**changes):
    encounter, *_ = actual_case()
    values = dict(encounter_id=encounter.id, maneuvering_object_id=encounter.object_1_id,
                  max_delta_v_m_s=.2, min_lead_time_minutes=15, max_lead_time_hours=2,
                  target_miss_distance_km=10, objective="MAXIMUM_CLEARANCE",
                  hypothetical_capability_assumed=True)
    return values | changes


@pytest.mark.parametrize("changes", [
    {"max_delta_v_m_s": -1}, {"max_delta_v_m_s": float("nan")},
    {"max_lead_time_hours": .1}, {"min_lead_time_minutes": 0},
    {"target_miss_distance_km": 0}, {"objective": "BALANCED"},
    {"hypothetical_capability_assumed": False}, {"initial_mass_kg": 1000},
    {"initial_mass_kg": 1000, "available_propellant_mass_kg": 1000, "specific_impulse_s": 300},
])
def test_invalid_physical_constraints_rejected(changes):
    with pytest.raises(ValueError):
        ManeuverConstraints(**constraint_input(**changes))


def test_object_membership_and_expired_window():
    encounter, *_ = actual_case()
    constraints = ManeuverConstraints(**constraint_input(maneuvering_object_id="999999"))
    with pytest.raises(ValueError, match="not in"):
        constraints.burn_window(encounter, START)
    constraints = ManeuverConstraints(**constraint_input())
    with pytest.raises(ValueError, match="expired"):
        constraints.burn_window(encounter, encounter.time_of_closest_approach)
    with pytest.raises(ValueError, match="outside"):
        constraints.validate_burn_time(encounter, START-timedelta(seconds=1), START)


def test_fuel_budget_analytical_reference_and_independent_direct_budget():
    constraints = ManeuverConstraints(**constraint_input(max_delta_v_m_s=400,
        initial_mass_kg=1000, available_propellant_mass_kg=100, specific_impulse_s=300))
    expected = 300 * 9.80665 * math.log(10/9)
    assert constraints.fuel_budget_delta_v_m_s == pytest.approx(expected, rel=1e-14)
    assert constraints.effective_delta_v_budget_m_s == constraints.fuel_budget_delta_v_m_s
    direct = ManeuverConstraints(**constraint_input())
    assert direct.fuel_budget_delta_v_m_s is None
    assert direct.effective_delta_v_budget_m_s == .2


def test_constraints_serialize_and_window_bounds():
    encounter, *_ = actual_case()
    constraints = ManeuverConstraints(**constraint_input())
    output = json.loads(constraints.model_dump_json())
    assert output["objective"] == "MAXIMUM_CLEARANCE"
    assert output["available_propellant_mass_kg"] is None
    first, last = constraints.burn_window(encounter, START)
    assert first == encounter.time_of_closest_approach-timedelta(hours=2)
    assert last == encounter.time_of_closest_approach-timedelta(minutes=15)
    constraints.validate_burn_time(encounter, first, START)
