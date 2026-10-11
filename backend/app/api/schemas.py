from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models.encounter import Encounter
from app.models.maneuver import ManeuverConstraints
from app.models.catalog import CatalogMetadata
from app.models.screening import ScreeningRequest, SecondaryOptimizationSettings
from app.optimization.optimizer import SearchSettings


class ScreenedEncounter(Encounter):
    warnings: list[str]


class EncounterListResponse(BaseModel):
    items: list[ScreenedEncounter]
    sort: str
    dataset_timestamp: AwareDatetime
    data_status: Literal["VALID", "STALE_CACHE"]
    source_url: str
    content_sha256: str


class StatusResponse(BaseModel):
    service: Literal["Kessler"] = "Kessler"
    version: Literal["0.1.0"] = "0.1.0"
    source_status: Literal["NOT_LOADED", "VALID", "STALE_CACHE"]
    encounters_loaded: int
    cache_directory: str
    warnings: list[str]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    half_window_seconds: float = Field(default=300, gt=0, le=1800)


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    maneuvering_object_id: str = Field(pattern=r"^[0-9]+$")
    maneuver_time: AwareDatetime
    delta_v_rtn_m_s: tuple[float, float, float]
    hypothetical_capability_assumed: Literal[True]


class OptimizeRequest(ManeuverConstraints):
    search: SearchSettings = Field(default_factory=SearchSettings)
    secondary_screening: SecondaryOptimizationSettings | None = None


class ScreenRequest(ScreeningRequest):
    # The route supplies identity; an explicitly supplied body ID must match.
    encounter_id: str | None = None


class CatalogStatusResponse(BaseModel):
    status: Literal["NOT_LOADED", "LOADED"]
    catalog: CatalogMetadata | None
    warnings: list[str]
