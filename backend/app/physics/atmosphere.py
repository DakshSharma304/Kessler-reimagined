"""NRLMSIS 2.1 with explicit weather, UTC and WGS84 geodetic coordinates.

No implicit pymsis downloads/default flux values. Supplied solar assumptions
are scenario inputs, not observations. Model domain is explicitly 0–1000 km;
this does not certify physical accuracy throughout that interval.
"""
from datetime import UTC, date, datetime, timedelta
import math
from typing import Literal, Protocol

import astropy.units as u
from astropy.coordinates import CartesianRepresentation, EarthLocation, GCRS, ITRS
from astropy.time import Time
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
import pymsis

from app.data.space_weather import SpaceWeatherUnavailable, get_space_weather
from app.physics.frames import teme_to_gcrs
from app.physics.propagation import StateVector


class WeatherForcing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    date: date
    f107_previous_day_sfu: float = Field(gt=0, le=500)
    f107_center81_sfu: float = Field(gt=0, le=500)
    ap_history: tuple[float, float, float, float, float, float, float]
    geomagnetic_mode: Literal[-1, 1] = -1
    input_category: Literal["SOURCE_OBSERVATION", "SOURCE_FORECAST", "SOURCE_INTERPOLATED", "USER_SUPPLIED_ASSUMPTION"]
    provenance: dict
    warnings: list[str] = Field(default_factory=list)

    def checked(self, timestamp):
        if timestamp.tzinfo is None or timestamp.astimezone(UTC).date() != self.date:
            raise ValueError("Weather forcing requires matching UTC date and aware timestamp")
        if not all(0 <= a <= 400 for a in self.ap_history):
            raise ValueError("Ap values must be finite and between 0 and 400")
        return self


class GeodeticPosition(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    latitude_deg: float = Field(ge=-90, le=90)
    longitude_deg: float = Field(ge=-180, le=180)
    altitude_m: float
    ellipsoid: Literal["WGS84"] = "WGS84"


class DensityResult(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    density_kg_m3: float = Field(gt=0)
    position: GeodeticPosition
    model: Literal["NRLMSIS 2.1"] = "NRLMSIS 2.1"
    implementation: Literal["pymsis 0.12.0"] = "pymsis 0.12.0"
    space_weather: WeatherForcing
    assumptions: list[str]
    warnings: list[str]


def state_geodetic(state: StateVector) -> GeodeticPosition:
    state = teme_to_gcrs(state) if state.frame == "TEME" else state
    at = Time(state.timestamp)
    earth_fixed = GCRS(CartesianRepresentation(np.asarray(state.position_m)*u.m),
        obstime=at).transform_to(ITRS(obstime=at))
    lon, lat, height = EarthLocation.from_geocentric(*earth_fixed.cartesian.xyz).to_geodetic("WGS84")
    return GeodeticPosition(latitude_deg=float(lat.to_value(u.deg)),
        longitude_deg=float(lon.wrap_at(180*u.deg).to_value(u.deg)), altitude_m=float(height.to_value(u.m)))


def forcing_from_dataset(timestamp: datetime, dataset, *, as_of: datetime | None = None) -> WeatherForcing:
    current = get_space_weather(timestamp, dataset, as_of=as_of)
    previous = get_space_weather(timestamp-timedelta(days=1), dataset, as_of=as_of)
    if current.status != "AVAILABLE" or previous.status != "AVAILABLE":
        raise SpaceWeatherUnavailable(f"Incomplete MSIS weather: current={current.status}, previous-day={previous.status}")
    day = timestamp.astimezone(UTC).date()
    now = timestamp.astimezone(UTC)
    slot = now.replace(hour=(now.hour//3)*3, minute=0, second=0, microsecond=0)
    history = []
    categories = {current.record.flux_type, previous.record.flux_type}
    for lag in range(20):
        at = slot-timedelta(hours=3*lag)
        lookup = get_space_weather(at,dataset,as_of=as_of)
        if lookup.status != "AVAILABLE":
            raise SpaceWeatherUnavailable(f"Missing three-hourly Ap history at {at.isoformat()}: {lookup.status}")
        history.append(lookup.record.ap_3hourly[at.hour//3])
        categories.add(lookup.record.flux_type)
    ap = (current.record.ap_daily,*history[:4],float(np.mean(history[4:12])),float(np.mean(history[12:20])))
    category = "SOURCE_FORECAST" if "PRD" in categories else "SOURCE_INTERPOLATED" if "INT" in categories else "SOURCE_OBSERVATION"
    return WeatherForcing(date=day, f107_previous_day_sfu=previous.record.f107_observed_sfu,
        f107_center81_sfu=current.record.f107_observed_center81_sfu, ap_history=ap,
        input_category=category, provenance={"source_url":dataset.source_url,
            "fetched_at":dataset.fetched_at.isoformat(), "dataset_timestamp":dataset.dataset_timestamp.isoformat(),
            "content_sha256":dataset.content_sha256, "retrieval_mode":dataset.retrieval_mode,
            "solar_qualifiers":sorted(categories), "daily_flux_date":(day-timedelta(days=1)).isoformat(),
            "flux_convention":"Earth-distance F10.7_OBS; centered81 on modeled UTC date",
            "ap_history_slot":slot.isoformat()},
        warnings=[*dataset.warnings, "The centered 81-day solar average may include future forecast values; source issue times are not available per field."]).checked(timestamp)


def calculate_density(timestamp, latitude, longitude, altitude, space_weather: WeatherForcing) -> DensityResult:
    """Latitude/longitude degrees; WGS84 geodetic altitude metres; SI density."""
    if not isinstance(space_weather, WeatherForcing):
        space_weather = WeatherForcing.model_validate(space_weather)
    space_weather.checked(timestamp)
    if not all(math.isfinite(x) for x in (latitude,longitude,altitude)):
        raise ValueError("Finite geodetic coordinates required")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Geodetic latitude/longitude outside supported degree range")
    if not 0 <= altitude <= 1_000_000:
        raise ValueError("NRLMSIS supported geodetic altitude is 0–1000 km; no extrapolation")
    when = np.datetime64(timestamp.astimezone(UTC).replace(tzinfo=None), "us")
    output = pymsis.calculate([when], [longitude], [latitude], [altitude/1000],
        f107s=[space_weather.f107_previous_day_sfu], f107as=[space_weather.f107_center81_sfu],
        aps=[space_weather.ap_history], version=2.1, geomagnetic_activity=space_weather.geomagnetic_mode)
    density = float(output.reshape(-1,11)[0,pymsis.Variable.MASS_DENSITY])
    if not math.isfinite(density) or density <= 0:
        raise ValueError("NRLMSIS returned invalid mass density")
    return DensityResult(density_kg_m3=density,
        position=GeodeticPosition(latitude_deg=latitude,longitude_deg=longitude,altitude_m=altitude),
        space_weather=space_weather,
        assumptions=["Empirical NRLMSIS 2.1 neutral atmosphere; geographic WGS84 coordinates, UTC.",
            "Previous-day Earth-distance solar flux, centered 81-day average, explicit daily/storm-time Ap convention.",
            "Density is model-calculated, not observed or a calibrated prediction."],
        warnings=[*space_weather.warnings, "No atmospheric winds, attitude dynamics or calibrated density uncertainty are inferred."])


class DensityProvider(Protocol):
    def density(self, state: StateVector) -> float: ...
    def provenance(self) -> dict: ...


class MSISAtmosphere:
    def __init__(self, weather):
        self.weather = weather

    def density(self, state):
        geo = state_geodetic(state)
        forcing = self.weather(state.timestamp)
        return calculate_density(state.timestamp,geo.latitude_deg,geo.longitude_deg,geo.altitude_m,forcing).density_kg_m3

    def provenance(self):
        return {"model":"NRLMSIS 2.1", "implementation":"pymsis 0.12.0",
                "weather":"Explicit provider; each output must retain forcing provenance", "density_units":"kg/m3"}


class ConstantTestAtmosphere:
    """Controlled verification atmosphere, never selected by real-data defaults."""
    def __init__(self, density_kg_m3):
        if not math.isfinite(density_kg_m3) or density_kg_m3 < 0:
            raise ValueError("Finite nonnegative test density required")
        self.rho = density_kg_m3

    def density(self,state):
        return self.rho

    def provenance(self):
        return {"model":"CONTROLLED_CONSTANT_TEST_ATMOSPHERE", "density_kg_m3":self.rho,
                "warning":"Numerical verification only, not the default physical atmosphere"}
