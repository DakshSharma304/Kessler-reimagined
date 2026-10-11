"""Additive visualization contract: UTC, Earth-fixed ITRS, kilometers."""
from typing import Literal
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,field_validator
from app.api.schemas import SimulateRequest
from app.data.celestrak import validate_object_id
from app.data.metadata import ObjectClassification,ObjectMetadata
from app.models.catalog import CatalogMetadata
from app.models.orbital import OrbitalRecord
from app.physics.maneuvers import ManeuverSimulation
from app.probability.integration import ProbabilityManeuverSimulation


class ObjectSummary(BaseModel):
    id: str
    name: str
    classification: ObjectClassification
    element_epoch: AwareDatetime
    inclination_deg: float
    operational_status_code: str | None
    cleanup_eligible: bool
    apogee_km: float | None
    perigee_km: float | None


class CatalogPage(BaseModel):
    items: list[ObjectSummary]
    total: int
    offset: int
    limit: int
    next_offset: int | None
    catalog: CatalogMetadata
    metadata_source: dict | None
    warnings: list[str]


class ObjectInfo(BaseModel):
    object: ObjectSummary
    orbit: OrbitalRecord
    metadata: ObjectMetadata | None
    warnings: list[str]


class PositionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    object_ids: list[str] = Field(min_length=1)
    epoch: AwareDatetime | None = None

    @field_validator('object_ids',mode='before')
    @classmethod
    def canonical_ids(cls,values):
        if not isinstance(values,(list,tuple)) or not values:
            raise ValueError('Supply at least one ID before deduplication')
        return list(dict.fromkeys(validate_object_id(value) for value in values))


class PositionSample(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    epoch: AwareDatetime
    position_km: tuple[float,float,float] | None
    propagation_status: Literal['OK','SGP4_ERROR','UNSUPPORTED_EPOCH','NOT_IN_CATALOG']
    error: str | None = None


class ObjectPosition(PositionSample):
    id: str
    name: str | None
    classification: ObjectClassification
    frame: Literal['ITRS'] = 'ITRS'
    position_units: Literal['km'] = 'km'


class PositionBatch(BaseModel):
    items: list[ObjectPosition]
    epoch: AwareDatetime
    frame: Literal['ITRS'] = 'ITRS'
    position_units: Literal['km'] = 'km'
    catalog: CatalogMetadata
    metadata_source: dict | None
    warnings: list[str]


class ObjectTrajectory(BaseModel):
    id: str
    name: str
    frame: Literal['ITRS'] = 'ITRS'
    position_units: Literal['km'] = 'km'
    samples: list[PositionSample]
    provenance: dict
    model: str
    warnings: list[str]


class EncounterTrajectories(BaseModel):
    encounter_id: str
    participant_ids: tuple[str,str]
    trajectories: list[ObjectTrajectory]
    warnings: list[str]


class ManeuverTrajectoryRequest(SimulateRequest):
    sample_count: int = Field(default=121,ge=2)
    numerical_reference_epoch: AwareDatetime | None = None


class ManeuverTrajectories(BaseModel):
    encounter_id: str
    participant_ids: tuple[str,str]
    numerical_reference_epoch: AwareDatetime
    baseline: ObjectTrajectory
    modified: ObjectTrajectory
    counterpart: ObjectTrajectory
    simulation: ProbabilityManeuverSimulation | ManeuverSimulation
    warnings: list[str]
