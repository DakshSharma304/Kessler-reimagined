"""Bounded secondary-screening contracts, never a generic safety declaration."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data.celestrak import validate_object_id
from app.models.catalog import CatalogMetadata, CatalogSelection
from app.models.encounter import Encounter


class ScreeningStatus(StrEnum):
    SCREENED_WITHIN_COVERAGE = "SCREENED_WITHIN_COVERAGE"
    ALERTS_FOUND = "ALERTS_FOUND"
    INCOMPLETE = "INCOMPLETE"
    UNAVAILABLE = "UNAVAILABLE"


class ConjunctionClassification(StrEnum):
    NEW_CLOSE_APPROACH = "NEW_CLOSE_APPROACH"
    WORSENED_CLOSE_APPROACH = "WORSENED_CLOSE_APPROACH"
    IMPROVED_CLOSE_APPROACH = "IMPROVED_CLOSE_APPROACH"
    UNCHANGED = "UNCHANGED"


class ScreeningPolicy(StrEnum):
    REPORT_ONLY = "REPORT_ONLY"
    REJECT_NEW_ALERTS = "REJECT_NEW_ALERTS"
    REJECT_ALL_ALERTS = "REJECT_ALL_ALERTS"


class ScreeningWindow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def supported_interval(self):
        duration = (self.end-self.start).total_seconds()
        if not 0 < duration <= 48*3600:
            raise ValueError("Screening interval must increase and span at most 48 hours")
        return self


class ScreeningSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    alert_distance_km: float = Field(default=5, gt=0, le=1000,
        description="Illustrative proximity threshold, not a universal safe distance")
    post_tca_horizon_hours: float = Field(default=6, gt=0, le=24)
    coarse_step_seconds: float = Field(default=30, gt=0, le=120)
    relative_acceleration_margin_m_s2: float = Field(default=40, gt=0, le=1000,
        description="Broad-phase curvature allowance; heuristic, not a proven completeness bound")
    batch_size: int = Field(default=256, ge=1)
    max_objects: int = Field(default=50000, ge=1)
    max_refinements: int = Field(default=1000, ge=1)
    timeout_seconds: float = Field(default=30, gt=0)
    max_epoch_distance_days: float = Field(default=7, gt=0)
    classification_tolerance_m: float = Field(default=1, ge=.001, le=100,
        description="Numerical classification tolerance, not physical uncertainty")
    event_matching_tolerance_seconds: float = Field(default=120, ge=1, le=600)
    catalog_selection: CatalogSelection = Field(default_factory=CatalogSelection)


class ScreeningRequest(ScreeningSettings):
    encounter_id: str
    maneuvering_object_id: str
    maneuver_time: AwareDatetime
    delta_v_rtn_m_s: tuple[float, float, float]
    hypothetical_capability_assumed: Literal[True]

    @field_validator("maneuvering_object_id", mode="before")
    @classmethod
    def canonical_id(cls, value):
        return validate_object_id(value)

    def screening_window(self, encounter: Encounter, now: datetime | None = None) -> ScreeningWindow:
        if self.encounter_id != encounter.id:
            raise ValueError("Screening request refers to a different encounter")
        if self.maneuvering_object_id not in {
            validate_object_id(encounter.object_1_id), validate_object_id(encounter.object_2_id)
        }:
            raise ValueError("Maneuvering object must participate in the selected encounter")
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Current time must be timezone-aware")
        if not now <= self.maneuver_time < encounter.time_of_closest_approach:
            raise ValueError("Screening requires a future maneuver before original TCA")
        return ScreeningWindow(start=self.maneuver_time,
            end=encounter.time_of_closest_approach+timedelta(hours=self.post_tca_horizon_hours))


class SecondaryConjunction(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    primary_object_id: str
    secondary_object_id: str
    secondary_object_name: str
    is_original_counterpart: bool
    time_of_closest_approach: AwareDatetime
    baseline_time_of_closest_approach: AwareDatetime | None
    baseline_miss_distance_m: float | None = Field(ge=0)
    maneuvered_miss_distance_m: float = Field(ge=0)
    change_in_miss_distance_m: float | None
    change_in_tca_seconds: float | None
    relative_speed_m_s: float = Field(ge=0)
    classification: ConjunctionClassification
    baseline_below_threshold: bool | None
    maneuvered_below_threshold: bool
    screening_window: ScreeningWindow
    frame: Literal["TEME", "GCRS"]
    source: dict[str, str]
    warnings: list[str] = Field(default_factory=list)


SCREENING_LIMITATIONS = [
    "Screening checks only the declared available catalog snapshot and selected prediction interval; catalog coverage is partial.",
    "Alert distance is an illustrative proximity threshold, not a universal safe distance or a calibrated collision probability.",
    "Differential approximation: nominal SGP4 plus matched numerical maneuver-minus-zero-burn position and velocity in a common frame.",
    "Central gravity/J2 impulse model excludes drag, higher harmonics, third-body forces and unmodeled real maneuvers; installed offline IERS data are used.",
    "Segment filtering uses a documented curvature margin and bounded refinement; mathematical completeness and physical uncertainty bounds are not established.",
    "Classification and event-matching tolerances are numerical rules, not measured orbital uncertainty.",
    "Secondary screening does not certify operational flight safety; results are hypothetical calculations, not spacecraft commands.",
]


class ScreeningResult(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    encounter_id: str
    maneuvering_object_id: str
    alert_distance_km: float = Field(default=5, gt=0, le=1000,
        description="Applied illustrative threshold, not a universal safe distance")
    screening_status: ScreeningStatus
    screening_complete: bool = Field(description="Complete computation within declared available coverage, not full-population completeness")
    catalog: CatalogMetadata
    screening_window: ScreeningWindow
    objects_screened: int = Field(ge=0)
    candidate_objects_refined: int = Field(ge=0)
    additional_close_approaches: int = Field(ge=0)
    newly_introduced: int = Field(ge=0)
    worsened: int = Field(ge=0)
    improved: int = Field(ge=0)
    closest_additional_encounter: SecondaryConjunction | None
    secondary_encounters: list[SecondaryConjunction]
    skipped_objects: dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: float = Field(ge=0)
    timings_seconds: dict[str, float] = Field(default_factory=dict)
    model_limitations: list[str] = Field(default_factory=lambda: list(SCREENING_LIMITATIONS))
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def honest_status(self):
        unavailable = self.catalog.objects_available == 0
        incomplete = bool(self.skipped_objects or self.catalog.failed_sources or
                          self.catalog.rejected_record_count)
        if self.screening_complete and (unavailable or incomplete):
            raise ValueError("Unavailable, skipped or rejected catalog data cannot constitute complete screening")
        if self.screening_complete != (self.screening_status in {
            ScreeningStatus.SCREENED_WITHIN_COVERAGE, ScreeningStatus.ALERTS_FOUND
        }):
            raise ValueError("Screening status and completeness disagree")
        if self.objects_screened > self.catalog.objects_available:
            raise ValueError("Cannot screen more objects than available in the declared snapshot")
        if self.candidate_objects_refined > self.objects_screened:
            raise ValueError("Refined count cannot exceed screened count")
        if unavailable and self.screening_status != ScreeningStatus.UNAVAILABLE:
            raise ValueError("Empty catalog must be labeled UNAVAILABLE")
        return self


class SecondaryOptimizationSettings(ScreeningSettings):
    policy: ScreeningPolicy = ScreeningPolicy.REPORT_ONLY
    max_finalists: int = Field(default=3, ge=1)
    total_timeout_seconds: float = Field(default=90, gt=0)


class CandidateScreeningAssessment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    primary_rank: int = Field(ge=1)
    maneuver_time: AwareDatetime
    delta_v_rtn_m_s: tuple[float, float, float]
    primary_miss_distance_m: float
    primary_improvement_m: float
    screening: ScreeningResult | None
    policy_passed: bool | None = Field(description="Null means unassessed/incomplete, never a pass")
    selected: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def no_incomplete_pass(self):
        if self.policy_passed is True and (self.screening is None or not self.screening.screening_complete):
            raise ValueError("Incomplete or absent screening cannot pass policy")
        return self


class OptimizationScreeningSummary(BaseModel):
    status: Literal["COMPLETE", "INCOMPLETE", "NO_ACCEPTABLE_SCREENED_SOLUTION", "UNAVAILABLE"]
    policy: ScreeningPolicy
    max_finalists: int
    candidates_screened: int
    selected_primary_rank: int | None
    candidate_results: list[CandidateScreeningAssessment]
    elapsed_seconds: float
    warnings: list[str]
