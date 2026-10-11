"""Independent-model NASA benchmark adapter, never a live data provider."""
from datetime import datetime, timedelta
from typing import Literal
import numpy as np
from pydantic import BaseModel, ConfigDict
from app.probability.cdm import NASA_URL, load_reference, reference_table
from app.probability.covariance import covariance_in_frame
from app.probability.engine import ProbabilityResult, calculate_collision_probability


class ReferenceComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    source: Literal["NASA_CARA_HISTORICAL_REFERENCE"] = "NASA_CARA_HISTORICAL_REFERENCE"
    reference_only: Literal[True] = True
    reference_case: str
    reference_url: str = NASA_URL
    source_sha256: str
    original_tca: datetime
    linear_closest_approach_tca: datetime
    linear_tca_offset_seconds: float
    state_frame: str
    covariance_frame: Literal["INDIVIDUAL_OBJECT_RTN"] = "INDIVIDUAL_OBJECT_RTN"
    reference_model: Literal["NASA_INDEPENDENT_2D_BENCHMARK"] = "NASA_INDEPENDENT_2D_BENCHMARK"
    published_reference_pc: float
    cdm_rounded_reference_pc: float | None
    calculated_pc: float | None
    numerical_difference: float | None
    relative_difference: float | None
    calculation: ProbabilityResult
    assumptions: list[str]
    warnings: list[str]


def evaluate_reference(case: str, *, independent_benchmark: bool = False,
                       relative_tolerance: float = 1e-9) -> ReferenceComparison:
    if independent_benchmark is not True:
        raise ValueError("Explicit independent_benchmark=true required: NASA benchmark omits known DCP correlations and is not operational risk")
    encounter = load_reference(case)
    primary, secondary = encounter.primary, encounter.secondary
    frame = primary.state.frame
    first = covariance_in_frame(primary.covariance_m2, primary.covariance_frame, primary.state, frame, epoch=encounter.tca)
    second = covariance_in_frame(secondary.covariance_m2, secondary.covariance_frame, secondary.state, frame, epoch=encounter.tca)
    position = np.array(secondary.state.position_m) - primary.state.position_m
    velocity = np.array(secondary.state.velocity_m_s) - primary.state.velocity_m_s
    speed_squared = float(velocity @ velocity)
    if speed_squared <= 1e-24:
        raise ValueError("NASA reference has no defined rectilinear closest approach")
    offset = -float(position @ velocity) / speed_squared
    if abs(offset) > .001:
        raise ValueError("NASA reference TCA correction exceeds 1 ms; fixed covariance rounding correction unsupported")
    # Original per-object bases at CDM TCA, frozen inertial covariance over the
    # tiny rounding correction, exactly the NASA comparison model definition.
    result = calculate_collision_probability(position + offset * velocity, velocity, first, second,
        encounter.combined_hard_body_radius_m, correlation="INDEPENDENT", relative_tolerance=relative_tolerance)
    # Published answers are read only after independently computing the result.
    metadata = reference_table()[case]
    reference_pc = float(metadata["Pc2D"])
    difference = None if result.calculated_pc is None else result.calculated_pc - reference_pc
    return ReferenceComparison(reference_case=case, source_sha256=encounter.source_sha256,
        original_tca=encounter.tca, linear_closest_approach_tca=encounter.tca + timedelta(seconds=offset),
        linear_tca_offset_seconds=offset, state_frame=frame, published_reference_pc=reference_pc,
        cdm_rounded_reference_pc=encounter.published_reference_pc, calculated_pc=result.calculated_pc,
        numerical_difference=difference, relative_difference=None if difference is None or reference_pc == 0 else difference/reference_pc,
        calculation=result, assumptions=result.assumptions + [
            "Explicit independent-model benchmark only: NASA PcMultiStep_FromCDM.m sets apply_covXcorr_corrections=false.",
            "Original inertial covariances fixed during sub-millisecond linear TCA rounding correction."],
        warnings=encounter.warnings + result.warnings + [
            "Known DCP correlation metadata is deliberately omitted ONLY for the explicitly selected NASA independent-model benchmark.",
            "This validation Pc is not an operational risk calculation for the correlated encounter."])
