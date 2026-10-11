"""Declared catalog selection and honest snapshot coverage/provenance."""

from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.models.orbital import OrbitalRecord

# Verified against https://celestrak.org/NORAD/elements/ on 2026-10-11.
# This deliberately is not an invented GROUP=ALL or a completeness claim.
SUPPORTED_GROUPS = frozenset({
    "active", "stations", "visual", "analyst", "last-30-days", "weather",
    "science", "geo", "gnss", "cosmos-2251-debris", "iridium-33-debris",
    "fengyun-1c-debris", "radar",
})
DEFAULT_GROUPS = ("active", "cosmos-2251-debris", "iridium-33-debris",
                  "fengyun-1c-debris", "visual")


class CatalogSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    groups: tuple[str, ...] = DEFAULT_GROUPS
    local_files: tuple[Path, ...] = ()
    include_cached_records: bool = False

    @field_validator("groups")
    @classmethod
    def supported_groups(cls, values):
        normalized = tuple(dict.fromkeys(value.lower() for value in values))
        if any(value not in SUPPORTED_GROUPS for value in normalized):
            raise ValueError("Unsupported GP group; select a verified public group or supply local OMM data")
        return normalized


class CatalogSource(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_url: str
    content_sha256: str
    retrieved_at: AwareDatetime
    dataset_timestamp: AwareDatetime
    timestamp_basis: str
    retrieval_mode: Literal["HTTP", "CACHE", "LOCAL", "STALE_CACHE"]
    usable_records: int = Field(ge=0)
    rejected_records: int = Field(ge=0)
    duplicate_records: int = Field(ge=0)


class CatalogMetadata(BaseModel):
    objects_available: int = Field(ge=0)
    coverage: Literal["PARTIAL"] = "PARTIAL"
    freshness_status: Literal["FRESH", "STALE", "UNAVAILABLE"]
    sources: list[CatalogSource]
    snapshot_sha256: str
    assembled_at: AwareDatetime
    oldest_element_epoch: AwareDatetime | None
    newest_element_epoch: AwareDatetime | None
    rejected_record_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    failed_sources: list[str] = Field(default_factory=list)
    coverage_limitations: list[str]
    warnings: list[str] = Field(default_factory=list)


class ScreeningCatalog(BaseModel):
    records: dict[str, OrbitalRecord]
    metadata: CatalogMetadata
