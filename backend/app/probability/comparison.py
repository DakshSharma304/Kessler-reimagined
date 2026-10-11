"""Illustrative fixed-covariance comparison using the existing verified simulator."""
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict
from app.physics.frames import teme_to_gcrs
from app.physics.propagation import propagate_object
from app.probability.availability import (ILLUSTRATIVE_LABEL, ProbabilityInputs,
    check_object_identity, inertial_covariances)
from app.probability.covariance import UnsupportedCovariance
from app.probability.engine import ProbabilityResult, calculate_collision_probability


class FixedCovarianceScenario(ProbabilityInputs):
    fixed_covariance: Literal[True]


class ManeuverProbabilityComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    probability_status: Literal["SCENARIO_WITH_ASSUMED_COVARIANCE", "UNSUPPORTED_MODEL"]
    label: str = ILLUSTRATIVE_LABEL
    covariance_treatment: Literal["FIXED_INERTIAL_GCRS_AT_ORIGINAL_TCA"] = "FIXED_INERTIAL_GCRS_AT_ORIGINAL_TCA"
    original_tca: AwareDatetime
    published_tca: AwareDatetime
    covariance_epoch: AwareDatetime
    baseline_tca: AwareDatetime
    modified_tca: AwareDatetime
    baseline_tca_offset_seconds: float
    modified_tca_offset_seconds: float
    baseline_pc: float | None = None
    modified_scenario_pc: float | None = None
    delta_pc: float | None = None
    baseline_calculation: ProbabilityResult | None = None
    modified_calculation: ProbabilityResult | None = None
    assumptions: list[str]
    warnings: list[str]


def compare_maneuver_probability(encounter, first_record, second_record, simulation,
                                 scenario: FixedCovarianceScenario | dict) -> ManeuverProbabilityComparison:
    scenario = FixedCovarianceScenario.model_validate(scenario)
    inputs = ProbabilityInputs.model_validate(scenario.model_dump(exclude={"fixed_covariance"}))
    check_object_identity(inputs, encounter)
    if simulation.encounter_id != encounter.id or first_record.elements.object_id != encounter.object_1_id or second_record.elements.object_id != encounter.object_2_id:
        raise ValueError("Maneuver simulation and selected GP records must match the encounter")
    original = simulation.sgp4_reference.calculated.tca
    assumptions = ["Both object covariances rotated at original TCA using their own original states, then frozen in GCRS.",
        "No covariance propagation or maneuver execution uncertainty is available; BOTH probabilities are illustrative.",
        "Existing matched numerical zero-burn/post-burn trajectories supply the actual separate closest-approach geometries."]
    warnings = ["Original-TCA covariance is not claimed valid at baseline or modified TCA.",
        "Holding inertial covariance fixed is a user-acknowledged scenario, not an operationally calibrated prediction.",
        "Pc is not used as a clearance-optimizer objective; secondary probability changes are not assessed."]
    metadata = dict(original_tca=original, published_tca=simulation.sgp4_reference.published.tca,
        covariance_epoch=inputs.primary.epoch, baseline_tca=simulation.matched_baseline.tca,
        modified_tca=simulation.modified.tca,
        baseline_tca_offset_seconds=(simulation.matched_baseline.tca-original).total_seconds(),
        modified_tca_offset_seconds=(simulation.modified.tca-original).total_seconds(),
        assumptions=assumptions, warnings=warnings)
    try:
        if inputs.primary.epoch != original or inputs.secondary.epoch != original:
            raise UnsupportedCovariance("Fixed scenario requires both covariances at the original analyzed SGP4 TCA")
        states = [teme_to_gcrs(propagate_object(record, original)) for record in (first_record, second_record)]
        first, second, cross = inertial_covariances(inputs, *states, "GCRS")
        results = []
        for geometry in (simulation.matched_baseline, simulation.modified):
            if geometry.frame != "GCRS" or geometry.status != "COMPLETE":
                raise UnsupportedCovariance("Probability comparison requires complete GCRS closest approaches")
            results.append(calculate_collision_probability(geometry.relative_position_m,
                geometry.relative_velocity_m_s, first, second, inputs.combined_hard_body_radius_m,
                cross_covariance=cross, correlation=inputs.correlation, model_applicable=inputs.model_applicable))
        baseline, modified = results
        for result in results:
            warnings.extend(w for w in result.warnings if w not in warnings)
            assumptions.extend(a for a in result.assumptions if a not in assumptions)
        supported = all(r.status == "CALCULATED" for r in results)
        return ManeuverProbabilityComparison(probability_status="SCENARIO_WITH_ASSUMED_COVARIANCE" if supported else "UNSUPPORTED_MODEL",
            baseline_pc=baseline.calculated_pc, modified_scenario_pc=modified.calculated_pc,
            delta_pc=modified.calculated_pc-baseline.calculated_pc if supported else None,
            baseline_calculation=baseline, modified_calculation=modified, **metadata)
    except UnsupportedCovariance as error:
        warnings.append(str(error))
        return ManeuverProbabilityComparison(probability_status="UNSUPPORTED_MODEL", **metadata)
