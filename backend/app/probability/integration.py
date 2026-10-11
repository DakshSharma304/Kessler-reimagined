"""Opt-in adapters; legacy analysis/simulation responses stay unchanged."""
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from typing import Literal
from app.physics.encounters import BaselineAnalysis
from app.physics.maneuvers import ManeuverSimulation
from app.physics.propagation import propagate_object
from app.probability.availability import (InertialFrame, ProbabilityAnalysis,
    analyze_live_probability, probability_report)
from app.probability.cdm import Matrix3, Vector3
from app.probability.comparison import ManeuverProbabilityComparison, compare_maneuver_probability
from app.probability.covariance import validate_covariance
from app.probability.engine import calculate_collision_probability
from app.probability.reference import evaluate_reference


class ProbabilityBaselineAnalysis(BaselineAnalysis):
    probability_analysis: ProbabilityAnalysis


class ProbabilityManeuverSimulation(ManeuverSimulation):
    probability_comparison: ManeuverProbabilityComparison


class DirectProbabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["SUPPLIED", "ASSUMED"]
    tca: AwareDatetime
    frame: InertialFrame
    relative_position_m: Vector3
    relative_velocity_m_s: Vector3
    covariance_primary_m2: Matrix3
    covariance_secondary_m2: Matrix3
    combined_hard_body_radius_m: float = Field(gt=0)
    cross_covariance_m2: Matrix3 | None = None
    correlation: Literal["UNSPECIFIED", "INDEPENDENT", "CORRELATED"] = "UNSPECIFIED"
    relative_tolerance: float = Field(default=1e-9, ge=1e-12, le=1e-4)
    model_applicable: bool = True

    @field_validator("covariance_primary_m2", "covariance_secondary_m2")
    @classmethod
    def covariance_valid(cls, value):
        validate_covariance(value)
        return value


class ReferenceProbabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference_case: str
    independent_benchmark: Literal[True]


def calculate_request(request: DirectProbabilityRequest | ReferenceProbabilityRequest):
    if isinstance(request, ReferenceProbabilityRequest):
        return evaluate_reference(request.reference_case, independent_benchmark=request.independent_benchmark)
    result = calculate_collision_probability(request.relative_position_m, request.relative_velocity_m_s,
        request.covariance_primary_m2, request.covariance_secondary_m2, request.combined_hard_body_radius_m,
        cross_covariance=request.cross_covariance_m2, correlation=request.correlation,
        relative_tolerance=request.relative_tolerance, model_applicable=request.model_applicable)
    return probability_report(result, kind=request.kind, source="USER_SUPPLIED_GEOMETRY", tca=request.tca,
        frame=request.frame, covariance_treatment="SUPPLIED_COMMON_FRAME_AT_TCA")


def with_live_probability(case, baseline, inputs=None) -> ProbabilityBaselineAnalysis:
    encounter, first, second = case
    states = [propagate_object(record, baseline.calculated.tca) for record in (first, second)]
    return ProbabilityBaselineAnalysis(**baseline.model_dump(),
        probability_analysis=analyze_live_probability(encounter, *states, inputs))


def with_maneuver_probability(case, simulation, scenario) -> ProbabilityManeuverSimulation:
    return ProbabilityManeuverSimulation(**simulation.model_dump(),
        probability_comparison=compare_maneuver_probability(*case, simulation, scenario))
