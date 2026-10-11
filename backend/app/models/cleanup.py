"""Illustrative, auditable cleanup assessment; no mission/collision economics."""
from typing import Literal
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,model_validator,field_validator
from app.data.celestrak import validate_object_id
from app.data.metadata import ObjectClassification


class PriorityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid",frozen=True,allow_inf_nan=False)
    exposure_weight: float = Field(default=1,ge=0,le=100)
    persistence_weight: float = Field(default=0,ge=0,le=100)
    radar_cross_section_weight: float = Field(default=0,ge=0,le=100)
    exposure_saturation_count: int = Field(default=10,ge=1,le=100000)
    persistence_saturation_days: float = Field(default=30,gt=0,le=90)
    radar_cross_section_saturation_m2: float = Field(default=10,gt=0,le=10000)

    @model_validator(mode="after")
    def positive_weight(self):
        if self.exposure_weight+self.persistence_weight+self.radar_cross_section_weight <= 0:
            raise ValueError("At least one priority weight must be positive")
        return self


class CleanupConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid",frozen=True,allow_inf_nan=False)
    max_targets: int = Field(default=3,ge=0,le=1000)
    max_candidates: int = Field(default=200,ge=1,le=1000)
    excluded_ids: tuple[str,...] = Field(default=(),max_length=1000)
    effort_costs: dict[str,float] | None = None
    effort_budget: float | None = Field(default=None,ge=0,le=1e12)
    solver_timeout_seconds: float = Field(default=10,gt=0,le=30)

    @field_validator("excluded_ids",mode="before")
    @classmethod
    def canonical_exclusions(cls,values):
        return tuple(dict.fromkeys(validate_object_id(v) for v in values))

    @field_validator("effort_costs")
    @classmethod
    def validated_costs(cls,values):
        import math
        if values is None: return None
        if len(values) > 1000: raise ValueError("At most 1000 abstract effort costs")
        result = {}
        for identifier,value in values.items():
            identifier = validate_object_id(identifier)
            if not math.isfinite(value) or not 0 <= value <= 1e9:
                raise ValueError("Abstract effort costs must be finite, nonnegative and bounded")
            if identifier in result: raise ValueError("Duplicate canonical effort-cost ID")
            result[identifier] = value
        return result

    @model_validator(mode="after")
    def costs_for_budget(self):
        if self.effort_budget is not None and self.effort_costs is None:
            raise ValueError("An effort budget requires explicitly supplied per-object abstract costs")
        return self


class PersistenceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True,allow_inf_nan=False)
    object_id: str
    initial_epoch: AwareDatetime
    modeled_duration_days: float = Field(ge=0,le=90)
    horizon_days: float = Field(gt=0,le=90)
    boundary_status: Literal["BOUNDARY_REACHED","NOT_REACHED_WITHIN_HORIZON"]
    censored_at_horizon: bool
    provenance: dict
    warnings: list[str]


class CleanupCandidate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    id: str
    name: str
    classification: ObjectClassification
    eligible: bool
    eligibility_reason: str | None
    element_epoch: AwareDatetime
    inclination_deg: float
    orbit_metadata: dict
    screening_exposure: dict
    persistence: PersistenceEvidence | None
    physical_metadata: dict
    missing_data: list[str]
    provenance: dict
    warnings: list[str]

    @field_validator("id",mode="before")
    @classmethod
    def canonical_id(cls,value):
        return validate_object_id(value)


class PriorityScore(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    id: str
    score: float | None = Field(ge=0,le=1)
    score_interval: tuple[float,float]
    status: Literal["RANKABLE","INSUFFICIENT_EVIDENCE","INELIGIBLE"]
    components: dict
    reasons: list[str]


class CleanupPortfolio(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    status: Literal["OPTIMAL_WITHIN_CANDIDATE_POOL","PARTIAL","UNAVAILABLE"]
    selected_objects: list[CleanupCandidate]
    priority_ranking: list[PriorityScore]
    candidates: list[CleanupCandidate]
    total_priority_proxy: float
    resource_model: Literal["TARGET_COUNT","USER_SUPPLIED_ABSTRACT_EFFORT"]
    targets_remaining: int
    total_abstract_resource_expenditure: float
    budget_remaining: float | None
    excluded_objects: dict[str,list[str]]
    unique_screening_encounters_represented: int
    shared_screening_encounter_ids: list[str]
    policy: PriorityPolicy
    constraints: CleanupConstraints
    coverage: dict
    model_assumptions: list[str]
    warnings: list[str]
