"""SOCRATES source predictions; MAX_PROB is a screening metric only."""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Encounter(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    id: str
    object_1_id: str = Field(pattern=r"^[0-9]+$")
    object_1_name: str = Field(min_length=1)
    object_2_id: str = Field(pattern=r"^[0-9]+$")
    object_2_name: str = Field(min_length=1)
    time_of_closest_approach: AwareDatetime
    source_miss_distance_m: float = Field(ge=0)
    source_relative_speed_m_s: float = Field(ge=0)
    socrates_max_probability: float | None = Field(default=None, ge=0, le=1)
    source_dse_1_days: float | None = None
    source_dse_2_days: float | None = None
    source_dilution_m: float | None = Field(default=None, ge=0)
    source: Literal["SOCRATES"] = "SOCRATES"
    dataset_timestamp: AwareDatetime
    data_status: Literal["VALID", "STALE_CACHE"] = "VALID"


class EncounterDataset(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    encounters: list[Encounter]
    dataset_timestamp: AwareDatetime
    fetched_at: AwareDatetime
    source_url: str
    content_sha256: str
    timestamp_basis: Literal["HTTP_LAST_MODIFIED", "FETCH_TIME"]
    invalid_rows: int = 0
    duplicate_rows: int = 0
    warnings: list[str] = Field(default_factory=list)
    data_status: Literal["VALID", "STALE_CACHE"] = "VALID"
