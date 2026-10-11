"""Honest live Pc availability; SOCRATES MAX_PROB never becomes calculated Pc."""
from typing import Literal
import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from app.physics.frames import transform_states
from app.probability.cdm import Matrix3
from app.probability.covariance import (UnsupportedCovariance, covariance_in_frame,
    position_rotation, validate_covariance)
from app.probability.engine import ProbabilityResult, calculate_collision_probability

ILLUSTRATIVE_LABEL = "ILLUSTRATIVE — USER-SUPPLIED UNCERTAINTY ASSUMPTIONS."
ProbabilityStatus = Literal["CALCULATED_FROM_SUPPLIED_COVARIANCE", "SCENARIO_WITH_ASSUMED_COVARIANCE",
    "UNAVAILABLE_NO_COVARIANCE", "UNAVAILABLE_INVALID_COVARIANCE", "UNSUPPORTED_MODEL"]
InertialFrame = Literal["TEME", "GCRS", "EME2000", "GCRF"]


class PositionCovariance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    matrix_m2: Matrix3
    frame: Literal["RTN", "RIC", "TEME", "GCRS", "EME2000", "GCRF"]
    epoch: AwareDatetime
    units: Literal["m2"] = "m2"

    @field_validator("matrix_m2")
    @classmethod
    def valid_matrix(cls, value):
        validate_covariance(value)
        return value


class CrossCovariance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    matrix_m2: Matrix3
    frame: InertialFrame
    epoch: AwareDatetime
    units: Literal["m2"] = "m2"


class ProbabilityInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    kind: Literal["SUPPLIED", "ASSUMED"]
    primary: PositionCovariance
    secondary: PositionCovariance
    combined_hard_body_radius_m: float = Field(gt=0)
    primary_object_id: str | None = Field(default=None, pattern=r"^\d{1,9}$")
    secondary_object_id: str | None = Field(default=None, pattern=r"^\d{1,9}$")
    correlation: Literal["UNSPECIFIED", "INDEPENDENT", "CORRELATED"] = "UNSPECIFIED"
    cross_covariance: CrossCovariance | None = None
    model_applicable: bool = True


class ProbabilityAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    probability_status: ProbabilityStatus
    source: Literal["SOCRATES", "USER_SUPPLIED_GEOMETRY"] = "SOCRATES"
    socrates_max_probability: float | None = Field(default=None, ge=0, le=1)
    calculated_pc: float | None = Field(default=None, ge=0, le=1)
    tca: AwareDatetime | None = None
    frame: str | None = None
    label: str | None = None
    covariance_treatment: str = "NONE"
    calculation: ProbabilityResult | None = None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def inertial_covariances(inputs: ProbabilityInputs, primary_state, secondary_state, target: str):
    first = covariance_in_frame(inputs.primary.matrix_m2, inputs.primary.frame, primary_state, target, epoch=inputs.primary.epoch)
    second = covariance_in_frame(inputs.secondary.matrix_m2, inputs.secondary.frame, secondary_state, target, epoch=inputs.secondary.epoch)
    cross = None
    if inputs.cross_covariance is not None:
        if inputs.cross_covariance.epoch != primary_state.timestamp or inputs.cross_covariance.epoch != secondary_state.timestamp:
            raise UnsupportedCovariance("Cross-covariance epoch does not match both object states")
        rotation = position_rotation(inputs.cross_covariance.frame, target, inputs.cross_covariance.epoch)
        cross = rotation @ np.asarray(inputs.cross_covariance.matrix_m2) @ rotation.T
    return first, second, cross


def check_object_identity(inputs: ProbabilityInputs, encounter):
    for supplied, actual in ((inputs.primary_object_id, encounter.object_1_id),
                             (inputs.secondary_object_id, encounter.object_2_id)):
        if supplied is not None and int(supplied) != int(actual):
            raise ValueError("Covariance object identifier does not match the selected encounter")


def probability_report(result: ProbabilityResult, *, kind: str, **metadata) -> ProbabilityAnalysis:
    status = "UNSUPPORTED_MODEL" if result.status != "CALCULATED" else (
        "SCENARIO_WITH_ASSUMED_COVARIANCE" if kind == "ASSUMED" else "CALCULATED_FROM_SUPPLIED_COVARIANCE")
    return ProbabilityAnalysis(probability_status=status, calculated_pc=result.calculated_pc,
        label=ILLUSTRATIVE_LABEL if kind == "ASSUMED" else None, calculation=result,
        assumptions=result.assumptions, warnings=result.warnings + [
            "Supplied covariance provenance and realism are not independently verified; no operational calibration is claimed."], **metadata)


def analyze_live_probability(encounter, primary_state, secondary_state,
                             inputs: ProbabilityInputs | dict | None = None) -> ProbabilityAnalysis:
    if encounter.source != "SOCRATES":
        raise ValueError("Historical NASA reference encounters cannot be presented as live SOCRATES")
    metadata = dict(socrates_max_probability=encounter.socrates_max_probability,
                    tca=primary_state.timestamp, frame=primary_state.frame)
    if inputs is None:
        return ProbabilityAnalysis(probability_status="UNAVAILABLE_NO_COVARIANCE", **metadata,
            warnings=["SOCRATES provides MAX_PROB, a screening metric, not measured object covariances or calibrated Pc.",
                      "No covariance or hard-body radius has been fabricated."])
    try:
        inputs = ProbabilityInputs.model_validate(inputs)
        check_object_identity(inputs, encounter)
        if primary_state.timestamp != secondary_state.timestamp:
            raise UnsupportedCovariance("Object states must share the same TCA")
        first, second, cross = inertial_covariances(inputs, primary_state, secondary_state, primary_state.frame)
        if secondary_state.frame != primary_state.frame:
            secondary_state = transform_states([secondary_state], primary_state.frame)[0]
        result = calculate_collision_probability(np.array(secondary_state.position_m) - primary_state.position_m,
            np.array(secondary_state.velocity_m_s) - primary_state.velocity_m_s, first, second,
            inputs.combined_hard_body_radius_m, cross_covariance=cross, correlation=inputs.correlation,
            model_applicable=inputs.model_applicable)
        return probability_report(result, kind=inputs.kind, covariance_treatment="AT_SUPPLIED_TCA_NO_PROPAGATION", **metadata)
    except UnsupportedCovariance as error:
        return ProbabilityAnalysis(probability_status="UNSUPPORTED_MODEL", **metadata, warnings=[str(error)])
    except ValueError as error:
        return ProbabilityAnalysis(probability_status="UNAVAILABLE_INVALID_COVARIANCE", **metadata, warnings=[str(error)])
