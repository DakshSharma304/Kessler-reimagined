from pydantic import AwareDatetime,BaseModel,ConfigDict,Field
from app.physics.atmosphere import WeatherForcing
from app.physics.drag import ObjectAerodynamicProperties
from app.physics.persistence_scenarios import PersistenceSettings


class DensityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid",allow_inf_nan=False)
    timestamp: AwareDatetime
    latitude_deg: float = Field(ge=-90,le=90)
    longitude_deg: float = Field(ge=-180,le=180)
    altitude_m: float = Field(ge=0,le=1000000)
    space_weather: WeatherForcing | None = None


class PersistenceRequest(PersistenceSettings):
    aerodynamic_properties: ObjectAerodynamicProperties | None = None
    start_time: AwareDatetime | None = None
    visualization: bool = False


class SpaceWeatherStatus(BaseModel):
    status: str
    coverage: dict | None = None
    warnings: list[str] = Field(default_factory=list)
