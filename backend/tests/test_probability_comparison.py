from datetime import timedelta
import pytest
from app.physics.maneuvers import simulate_maneuver
from app.models.maneuver import ManeuverConstraints
from app.optimization.optimizer import optimize_maneuver
from app.probability.comparison import compare_maneuver_probability
from app.probability.availability import ILLUSTRATIVE_LABEL
from app.probability.engine import calculate_collision_probability
from test_probability_availability import covariance_inputs
from test_encounters import START, actual_case
from test_optimizer import SMALL
from test_constraints import constraint_input


@pytest.mark.parametrize("dv", [0., .1])
def test_actual_simulation_zero_and_nonzero_fixed_scenario(dv):
    e, a, b = actual_case()
    simulation = simulate_maneuver(e, a, b, e.object_1_id, e.time_of_closest_approach-timedelta(hours=2), (0, dv, 0), True, now=START)
    before = simulation.model_dump(mode="json")
    values = covariance_inputs(e, simulation.sgp4_reference.calculated.tca) | {"fixed_covariance": True}
    result = compare_maneuver_probability(e, a, b, simulation, values)
    assert result.probability_status == "SCENARIO_WITH_ASSUMED_COVARIANCE"
    assert result.label == ILLUSTRATIVE_LABEL
    assert result.covariance_treatment == "FIXED_INERTIAL_GCRS_AT_ORIGINAL_TCA"
    assert result.original_tca == simulation.sgp4_reference.calculated.tca
    assert result.baseline_tca == simulation.matched_baseline.tca
    assert result.modified_tca == simulation.modified.tca
    assert result.modified_tca_offset_seconds == (result.modified_tca-result.original_tca).total_seconds()
    assert any("not claimed valid" in w for w in result.warnings)
    assert any("own original states" in a for a in result.assumptions)
    assert before == simulation.model_dump(mode="json")
    if dv == 0:
        assert result.baseline_pc == pytest.approx(result.modified_scenario_pc, rel=3e-8)
    else:
        assert simulation.change_in_miss_distance_m > 100
        assert result.baseline_pc != result.modified_scenario_pc
        assert result.delta_pc == result.modified_scenario_pc - result.baseline_pc
        assert result.modified_tca != result.original_tca
        # Isotropic supplied covariances stay isotropic under the exact rotations.
        expected = calculate_collision_probability(simulation.modified.relative_position_m,
            simulation.modified.relative_velocity_m_s, values["primary"]["matrix_m2"],
            values["secondary"]["matrix_m2"], values["combined_hard_body_radius_m"])
        assert result.modified_scenario_pc == pytest.approx(expected.calculated_pc, rel=1e-10)


def test_fixed_covariance_ack_required_and_wrong_epoch_unsupported():
    e, a, b = actual_case()
    simulation = simulate_maneuver(e, a, b, e.object_1_id, e.time_of_closest_approach-timedelta(hours=2), (0, .1, 0), True, now=START)
    values = covariance_inputs(e, simulation.sgp4_reference.calculated.tca)
    with pytest.raises(ValueError, match="fixed_covariance"):
        compare_maneuver_probability(e, a, b, simulation, values)
    values["fixed_covariance"] = True
    values["primary"]["epoch"] = simulation.modified.tca.isoformat()
    result = compare_maneuver_probability(e, a, b, simulation, values)
    assert result.probability_status == "UNSUPPORTED_MODEL"
    assert result.baseline_pc is result.modified_scenario_pc is result.delta_pc is None


def test_default_optimizer_unchanged_and_requires_no_covariance():
    e, a, b = actual_case()
    result = optimize_maneuver(e, a, b, ManeuverConstraints(**constraint_input()), SMALL, START)
    assert result.status == "COMPLETE"
    assert result.candidates_evaluated == 13
    assert result.solutions[0].new_miss_distance_m > result.baseline.miss_distance_m
    assert "probability_comparison" not in result.model_dump()
