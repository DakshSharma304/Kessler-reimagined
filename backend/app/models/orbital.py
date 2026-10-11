"""Validated CelesTrak GP elements, their provenance, and explicit suitability."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sgp4.api import Satrec, SGP4_ERRORS
from sgp4 import omm

from app.data.socrates import parse_utc


class GPElements(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True, allow_inf_nan=False)

    object_id: str = Field(alias="NORAD_CAT_ID", serialization_alias="object_id", pattern=r"^[0-9]{1,9}$")
    object_name: str = Field(default="", alias="OBJECT_NAME", serialization_alias="object_name")
    international_designator: str = Field(default="", alias="OBJECT_ID", serialization_alias="international_designator")
    epoch: AwareDatetime = Field(alias="EPOCH", serialization_alias="epoch")
    mean_motion_rev_day: float = Field(alias="MEAN_MOTION", serialization_alias="mean_motion_rev_day", gt=0, le=20)
    eccentricity: float = Field(alias="ECCENTRICITY", serialization_alias="eccentricity", ge=0, lt=1)
    inclination_deg: float = Field(alias="INCLINATION", serialization_alias="inclination_deg", ge=0, le=180)
    raan_deg: float = Field(alias="RA_OF_ASC_NODE", serialization_alias="raan_deg", ge=0, lt=360)
    argument_of_pericenter_deg: float = Field(alias="ARG_OF_PERICENTER", serialization_alias="argument_of_pericenter_deg", ge=0, lt=360)
    mean_anomaly_deg: float = Field(alias="MEAN_ANOMALY", serialization_alias="mean_anomaly_deg", ge=0, lt=360)
    bstar: float = Field(alias="BSTAR", serialization_alias="bstar")
    mean_motion_dot: float = Field(alias="MEAN_MOTION_DOT", serialization_alias="mean_motion_dot")
    mean_motion_ddot: float = Field(alias="MEAN_MOTION_DDOT", serialization_alias="mean_motion_ddot")
    ephemeris_type: Literal[0] = Field(alias="EPHEMERIS_TYPE", serialization_alias="ephemeris_type")
    classification: str = Field(alias="CLASSIFICATION_TYPE", serialization_alias="classification", min_length=1, max_length=1)
    element_set_number: int = Field(alias="ELEMENT_SET_NO", serialization_alias="element_set_number", ge=0)
    revolutions_at_epoch: int = Field(alias="REV_AT_EPOCH", serialization_alias="revolutions_at_epoch", ge=0)
    center: Literal["EARTH"] = Field(default="EARTH", alias="CENTER_NAME", serialization_alias="center")
    frame: Literal["TEME"] = Field(default="TEME", alias="REF_FRAME", serialization_alias="frame")
    time_system: Literal["UTC"] = Field(default="UTC", alias="TIME_SYSTEM", serialization_alias="time_system")
    mean_element_theory: Literal["SGP4"] = Field(default="SGP4", alias="MEAN_ELEMENT_THEORY", serialization_alias="mean_element_theory")

    @field_validator("object_id", mode="before")
    @classmethod
    def catalog_string(cls, value):
        if isinstance(value, bool):
            raise ValueError("Invalid catalog ID")
        return str(value)

    @field_validator("epoch", mode="before")
    @classmethod
    def utc_epoch(cls, value):
        return parse_utc(value) if isinstance(value, str) else value

    def initialize_sgp4(self) -> Satrec:
        # OMM input names are distinct from normalized HTTP/CLI output names.
        fields = {field.alias or name: getattr(self, name)
                  for name, field in type(self).model_fields.items()}
        fields["EPOCH"] = self.epoch.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")
        satellite = Satrec()
        omm.initialize(satellite, fields)
        if satellite.error:
            raise ValueError(f"SGP4 initialization error: {SGP4_ERRORS.get(satellite.error, satellite.error)}")
        return satellite


class OrbitalRecord(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    elements: GPElements
    source: Literal["CelesTrak GP"] = "CelesTrak GP"
    source_url: str
    fetched_at: AwareDatetime
    content_sha256: str
    data_status: Literal["VALID", "STALE_CACHE"] = "VALID"
    warnings: list[str] = Field(default_factory=list)


def epoch_suitability(record: OrbitalRecord, tca: datetime,
                      max_epoch_distance_days: float = 7) -> tuple[bool, list[str]]:
    if tca.tzinfo is None:
        raise ValueError("Encounter time must be timezone-aware")
    age = abs((tca - record.elements.epoch).total_seconds()) / 86400
    warnings = [
        "Current GP elements may differ from the elements used for the published SOCRATES prediction.",
        *record.warnings,
    ]
    if age > max_epoch_distance_days:
        warnings.append(f"Element epoch is {age:.3f} days from TCA; exceeds the conservative {max_epoch_distance_days:g}-day modeling limit.")
        return False, warnings
    return True, warnings
