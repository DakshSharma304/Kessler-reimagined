"""Hypothetical user constraints; no inferred propulsion or fuel reserves."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.encounter import Encounter

G0 = 9.80665  # exact standard gravity, m/s^2


class Objective(StrEnum):
    MINIMUM_DELTA_V = "MINIMUM_DELTA_V"
    MAXIMUM_CLEARANCE = "MAXIMUM_CLEARANCE"


class ManeuverConstraints(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    encounter_id: str
    maneuvering_object_id: str = Field(pattern=r"^[0-9]+$")
    max_delta_v_m_s: float = Field(ge=0, description="Maximum allowed velocity impulse magnitude, m/s")
    min_lead_time_minutes: float = Field(gt=0, description="Minimum preparation time between maneuver and published TCA")
    max_lead_time_hours: float = Field(gt=0, le=48, description="Maximum lead time; J2-only model limited to 48 hours")
    target_miss_distance_km: float = Field(gt=0, description="Desired modeled closest separation, km; not an operational safety threshold")
    objective: Objective
    hypothetical_capability_assumed: Literal[True] = Field(description="Explicit assumption that the selected object can perform the hypothetical maneuver")
    initial_mass_kg: float | None = Field(default=None, gt=0)
    available_propellant_mass_kg: float | None = Field(default=None, ge=0)
    specific_impulse_s: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def physical_constraints(self):
        if self.max_lead_time_hours * 60 <= self.min_lead_time_minutes:
            raise ValueError("Maximum lead time must exceed minimum preparation time")
        propulsion = [self.initial_mass_kg, self.available_propellant_mass_kg, self.specific_impulse_s]
        if any(value is not None for value in propulsion):
            if any(value is None for value in propulsion):
                raise ValueError("Fuel conversion requires initial mass, available propellant mass, and specific impulse")
            if self.available_propellant_mass_kg >= self.initial_mass_kg:
                raise ValueError("Propellant mass must be less than initial spacecraft mass")
        return self

    @property
    def fuel_budget_delta_v_m_s(self) -> float | None:
        if self.initial_mass_kg is None:
            return None
        final_mass = self.initial_mass_kg - self.available_propellant_mass_kg
        return self.specific_impulse_s * G0 * math.log(self.initial_mass_kg / final_mass)

    @property
    def effective_delta_v_budget_m_s(self) -> float:
        fuel = self.fuel_budget_delta_v_m_s
        return self.max_delta_v_m_s if fuel is None else min(self.max_delta_v_m_s, fuel)

    def burn_window(self, encounter: Encounter, now: datetime | None = None) -> tuple[datetime, datetime]:
        if self.encounter_id != encounter.id:
            raise ValueError("Constraints refer to a different encounter")
        if self.maneuvering_object_id not in {encounter.object_1_id, encounter.object_2_id}:
            raise ValueError("Maneuvering object is not in the selected encounter")
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Current time must be timezone-aware")
        tca = encounter.time_of_closest_approach
        earliest = max(now, tca - timedelta(hours=self.max_lead_time_hours))
        latest = tca - timedelta(minutes=self.min_lead_time_minutes)
        if earliest > latest:
            raise ValueError("Maneuver window has expired; burns cannot be in the past")
        return earliest, latest

    def validate_burn_time(self, encounter: Encounter, timestamp: datetime,
                           now: datetime | None = None) -> None:
        earliest, latest = self.burn_window(encounter, now)
        if timestamp.tzinfo is None or not earliest <= timestamp <= latest:
            raise ValueError("Burn time is outside the future constrained window")
