"""Independent atmosphere-relative drag component in GCRS, SI units."""
import math
from typing import Literal
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

EARTH_ANGULAR_SPEED_RAD_S = 7.292115e-5


class ObjectAerodynamicProperties(BaseModel):
    model_config = ConfigDict(frozen=True,extra="forbid",allow_inf_nan=False)
    input_category: Literal["USER_SUPPLIED", "HYPOTHETICAL_ASSUMPTION"]
    mass_kg: float | None = Field(default=None,gt=0)
    area_m2: float | None = Field(default=None,ge=0)
    drag_coefficient: float | None = Field(default=None,gt=0,le=5)
    cd_area_over_mass_m2_kg: float | None = Field(default=None,ge=0,le=100)

    @model_validator(mode="after")
    def complete_properties(self):
        physical = (self.mass_kg,self.area_m2,self.drag_coefficient)
        if self.cd_area_over_mass_m2_kg is None:
            if any(x is None for x in physical):
                raise ValueError("Supply mass, area and Cd together, or explicit Cd*A/m; BSTAR is not a physical substitute")
        elif any(x is not None for x in physical):
            raise ValueError("Supply physical properties OR Cd*A/m, not conflicting representations")
        if not math.isfinite(self.effective_ratio) or self.effective_ratio > 100:
            raise ValueError("Cd*A/m exceeds supported finite 0–100 m²/kg range")
        return self

    @property
    def effective_ratio(self):
        return self.cd_area_over_mass_m2_kg if self.cd_area_over_mass_m2_kg is not None else self.drag_coefficient*self.area_m2/self.mass_kg


def acceleration_drag(state, density_kg_m3, properties: ObjectAerodynamicProperties, pole):
    """m/s² = −½ ρ (Cd*A/m) |v−ω×r| (v−ω×r), co-rotating/no winds."""
    if state.frame != "GCRS":
        raise ValueError("Drag component requires a transformed GCRS state")
    if not math.isfinite(density_kg_m3) or density_kg_m3 < 0:
        raise ValueError("Density must be finite, nonnegative kg/m³")
    pole = np.asarray(pole,dtype=float)
    if pole.shape != (3,) or not np.isfinite(pole).all() or not np.isclose(np.linalg.norm(pole),1,rtol=0,atol=1e-10):
        raise ValueError("Unit GCRS Earth pole required for atmospheric co-rotation")
    atmosphere_velocity = np.cross(EARTH_ANGULAR_SPEED_RAD_S*pole,np.asarray(state.position_m))
    relative = np.asarray(state.velocity_m_s)-atmosphere_velocity
    result = -.5*density_kg_m3*properties.effective_ratio*np.linalg.norm(relative)*relative
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite drag acceleration")
    return result
