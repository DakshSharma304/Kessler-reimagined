"""Local closest-approach search; preserve source and calculated predictions."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Literal

import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from scipy.optimize import minimize_scalar

from app.models.encounter import Encounter
from app.models.orbital import OrbitalRecord, epoch_suitability
from app.physics.propagation import StateVector, propagate_object


class CalculationUnavailable(RuntimeError):
    pass


class ClosestApproach(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    tca: AwareDatetime
    miss_distance_m: float = Field(ge=0)
    relative_speed_m_s: float = Field(ge=0)
    relative_position_m: tuple[float, float, float]
    relative_velocity_m_s: tuple[float, float, float]
    frame: Literal["TEME", "GCRS"]
    searched_start: AwareDatetime
    searched_end: AwareDatetime
    sampled_minimum_m: float = Field(ge=0)
    status: Literal["COMPLETE", "SEARCH_BOUNDARY"]


class PublishedPrediction(BaseModel):
    tca: AwareDatetime
    miss_distance_m: float
    relative_speed_m_s: float
    max_probability_screening_metric: float | None


class BaselineAnalysis(BaseModel):
    encounter_id: str
    source: Literal["SOCRATES"] = "SOCRATES"
    published: PublishedPrediction
    calculated: ClosestApproach
    model: Literal["SGP4 / TEME / WGS72"] = "SGP4 / TEME / WGS72"
    element_epochs: tuple[AwareDatetime, AwareDatetime]
    orbital_source_checksums: tuple[str, str]
    source_model_disagreement: bool
    warnings: list[str]


Trajectory = Callable[[datetime], StateVector]


def refine_closest_approach(first: Trajectory, second: Trajectory,
                            start: datetime, end: datetime,
                            sample_count: int = 121) -> ClosestApproach:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Closest-approach interval must be timezone-aware")
    duration = (end - start).total_seconds()
    if not 0 < duration <= 3600 or not 3 <= sample_count <= 10001:
        raise ValueError("Use a bounded local interval of at most one hour and 3–10001 samples")
    def states(offset):
        timestamp = start + timedelta(seconds=float(offset))
        one, two = first(timestamp), second(timestamp)
        if one.frame != two.frame or one.timestamp != timestamp or two.timestamp != timestamp:
            raise CalculationUnavailable("Incompatible frames or timestamps in encounter calculation")
        return one, two
    def separation_squared(offset):
        one, two = states(offset)
        relative = np.subtract(one.position_m, two.position_m)
        value = float(np.dot(relative, relative))
        if not np.isfinite(value):
            raise CalculationUnavailable("Nonfinite relative separation")
        return value
    offsets = np.linspace(0, duration, sample_count)
    values = np.array([separation_squared(offset) for offset in offsets])
    sampled_index = int(np.argmin(values))
    best_offset, best_value = float(offsets[sampled_index]), float(values[sampled_index])
    # Refine all strictly bracketed sampled minima, not the entire orbital interval.
    for index in range(1, sample_count - 1):
        if values[index] <= values[index - 1] and values[index] <= values[index + 1] and (
                values[index] < values[index - 1] or values[index] < values[index + 1]):
            solution = minimize_scalar(separation_squared, method="bounded",
                                       bounds=(offsets[index - 1], offsets[index + 1]),
                                       options={"xatol": 1e-5, "maxiter": 100})
            if not solution.success or not np.isfinite(solution.fun):
                raise CalculationUnavailable("Closest-approach numerical refinement failed")
            if solution.fun < best_value:
                best_offset, best_value = float(solution.x), float(solution.fun)
    one, two = states(best_offset)
    relative_position = np.subtract(one.position_m, two.position_m)
    relative_velocity = np.subtract(one.velocity_m_s, two.velocity_m_s)
    boundary = best_offset <= 1e-4 or best_offset >= duration - 1e-4
    return ClosestApproach(
        tca=one.timestamp, miss_distance_m=float(np.linalg.norm(relative_position)),
        relative_speed_m_s=float(np.linalg.norm(relative_velocity)),
        relative_position_m=tuple(relative_position), relative_velocity_m_s=tuple(relative_velocity),
        frame=one.frame, searched_start=start, searched_end=end,
        sampled_minimum_m=float(np.sqrt(values[sampled_index])),
        status="SEARCH_BOUNDARY" if boundary else "COMPLETE",
    )


def analyze_encounter(encounter: Encounter, first: OrbitalRecord, second: OrbitalRecord,
                      half_window_seconds: float = 300) -> BaselineAnalysis:
    if not 0 < half_window_seconds <= 1800:
        raise ValueError("Analysis half-window must be 0–1800 seconds")
    if (first.elements.object_id, second.elements.object_id) != (encounter.object_1_id, encounter.object_2_id):
        raise CalculationUnavailable("Orbital records do not match the selected encounter")
    warnings = []
    for record in (first, second):
        supported, details = epoch_suitability(record, encounter.time_of_closest_approach)
        warnings.extend(details)
        if not supported:
            raise CalculationUnavailable("Unsupported orbital epoch: " + "; ".join(details))
    tca = encounter.time_of_closest_approach
    calculated = refine_closest_approach(
        lambda at: propagate_object(first, at), lambda at: propagate_object(second, at),
        tca - timedelta(seconds=half_window_seconds), tca + timedelta(seconds=half_window_seconds),
    )
    # Explicit reporting thresholds, not uncertainty estimates or agreement guarantees.
    separation_difference = abs(calculated.miss_distance_m - encounter.source_miss_distance_m)
    time_difference = abs((calculated.tca - tca).total_seconds())
    disagreement = separation_difference > 100 or time_difference > 60
    if disagreement:
        warnings.append("Source/model disagreement: miss distance differs by >100 m or TCA by >60 s; these are reporting thresholds, not uncertainty bounds.")
    if calculated.status == "SEARCH_BOUNDARY":
        warnings.append("Minimum occurs at the search boundary; no interior local closest approach was established.")
    if encounter.data_status != "VALID":
        warnings.append("Published encounter is from stale cached source data.")
    warnings.append("Secondary encounters have not been assessed; no calibrated collision probability or operational safety guarantee is provided.")
    return BaselineAnalysis(
        encounter_id=encounter.id,
        published=PublishedPrediction(tca=tca, miss_distance_m=encounter.source_miss_distance_m,
            relative_speed_m_s=encounter.source_relative_speed_m_s,
            max_probability_screening_metric=encounter.socrates_max_probability),
        calculated=calculated, element_epochs=(first.elements.epoch, second.elements.epoch),
        orbital_source_checksums=(first.content_sha256, second.content_sha256),
        source_model_disagreement=disagreement, warnings=list(dict.fromkeys(warnings)),
    )
