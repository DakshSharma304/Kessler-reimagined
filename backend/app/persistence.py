"""Real GP→GCRS→MSIS/drag→bounded scenario persistence, no cleanup ranking."""
from datetime import UTC,datetime
from typing import Literal
import numpy as np
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field
from app.engine import Engine
from app.models.orbital import OrbitalRecord,epoch_suitability
from app.physics.atmosphere import state_geodetic
from app.physics.decay import orbital_quantities
from app.physics.drag import ObjectAerodynamicProperties
from app.physics.frames import earth_pole_gcrs,teme_to_gcrs
from app.physics.propagation import StateVector,propagate_object
from app.physics.persistence_scenarios import (PersistenceSettings,ScenarioAnalysis,compare_persistence_scenarios)
from app.data.space_weather import SpaceWeatherUnavailable


class AltitudeBand(BaseModel):
    model_config = ConfigDict(frozen=True,extra="forbid",allow_inf_nan=False)
    name: str
    lower_m: float = Field(ge=0)
    upper_m: float = Field(gt=0)


DEFAULT_BANDS = [AltitudeBand(name="120–250 km",lower_m=120000,upper_m=250000),
    AltitudeBand(name="250–500 km",lower_m=250000,upper_m=500000),
    AltitudeBand(name="500–1000 km",lower_m=500000,upper_m=1000000)]


class PersistenceAnalysis(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    object_id: str
    object_name: str
    gp_epoch: AwareDatetime
    initial_state: StateVector
    initial_orbit: dict
    assumed_physical_parameters: ObjectAerodynamicProperties | None
    prediction_status: str
    prediction_horizon_days: float
    scenario_analysis: ScenarioAnalysis | None
    persistence_metrics: list[dict]
    provenance: dict
    assumptions: list[str]
    warnings: list[str]


def time_in_altitude_bands(propagation,bands=None):
    """Piecewise-linear instantaneous geodetic altitude occupancy, seconds.

    This is an approximation from returned samples, not orbital-element
    categories or exact event-root integration. Disjoint half-open bands.
    """
    bands = DEFAULT_BANDS if bands is None else [AltitudeBand.model_validate(b) for b in bands]
    ordered = sorted(bands,key=lambda b:b.lower_m)
    if any(b.lower_m >= b.upper_m for b in ordered) or any(a.upper_m > b.lower_m for a,b in zip(ordered,ordered[1:])):
        raise ValueError("Altitude bands must be ordered nonempty and disjoint")
    seconds = {b.name:0.0 for b in bands}
    for a,b in zip(propagation.samples,propagation.samples[1:]):
        dt = (b.state.timestamp-a.state.timestamp).total_seconds()
        h0,h1 = a.geodetic.altitude_m,b.geodetic.altitude_m
        for band in bands:
            if h0 == h1:
                fraction = float(band.lower_m <= h0 < band.upper_m)
            else:
                ends = sorted(((band.lower_m-h0)/(h1-h0),(band.upper_m-h0)/(h1-h0)))
                fraction = max(0.0,min(1.0,ends[1])-max(0.0,ends[0]))
            seconds[band.name] += dt*fraction
    total = (propagation.integrated_end_time-propagation.start_time).total_seconds()
    return {"definition":"Piecewise-linear instantaneous WGS84 geodetic sample altitude; not perigee/apogee categories",
        "time_in_bands_seconds":seconds,"modeled_time_in_orbit_seconds":total,
        "unclassified_seconds":max(0,total-sum(seconds.values())),
        "sampling_step_seconds":propagation.solver_settings.sample_step_seconds,
        "limitations":"Sample-based occupancy approximation; no orbital-cycle averaging or statistical confidence implied"}


def analyze_orbital_persistence(object_id,properties,settings: PersistenceSettings,
        *,engine=None,start_time=None) -> PersistenceAnalysis:
    engine = engine or Engine()
    start = start_time or datetime.now(UTC)
    record = engine.celestrak.get_object(object_id)
    suitable,warnings = epoch_suitability(record,start)
    if not suitable:
        raise ValueError("Initial GP epoch is outside the supported seven-day initial-state window")
    state = teme_to_gcrs(propagate_object(record,start))
    pole = earth_pole_gcrs(start)
    initial = orbital_quantities(state,pole)
    initial["geodetic_altitude_m"] = state_geodetic(state).altitude_m
    provenance = {"gp":record.model_dump(mode="json"),"initial_state_method":"SGP4 WGS72 TEME transformed to GCRS with actual Astropy position/velocity conversion",
        "input_identity":"Actual cataloged object; supplied aerodynamic values are not verified object properties"}
    common = dict(object_id=record.elements.object_id,object_name=record.elements.object_name,gp_epoch=record.elements.epoch,
        initial_state=state,initial_orbit=initial,assumed_physical_parameters=properties,
        prediction_horizon_days=settings.horizon_days,provenance=provenance,
        assumptions=["Actual catalog GP supplies a single initial osculating state, not a precise long-horizon orbit determination.",
            "User-supplied constant aerodynamic parameters; BSTAR is not converted into Cd*A/m.",
            "Research persistence within a bounded horizon; no debris cleanup ranking."],
        warnings=[*warnings,"Increasing GP uncertainty, omitted forces/active control and unknown attitude/weather limit long-horizon fidelity.",
            "Modeled decay and boundary times are not observationally verified decay or operational reentry predictions."])
    if properties is None:
        return PersistenceAnalysis(prediction_status="INSUFFICIENT_OBJECT_PROPERTIES",scenario_analysis=None,persistence_metrics=[],**common)
    dataset = None
    if settings.weather_mode != "HYPOTHETICAL_CONSTANT":
        try:
            dataset = engine.space_weather.load_space_weather()
            provenance["space_weather"] = dataset.coverage()
        except SpaceWeatherUnavailable as error:
            common["warnings"].append(str(error))
            provenance["space_weather"] = {"status":"UNAVAILABLE","reason":str(error)}
    result = compare_persistence_scenarios(state,properties,settings,dataset)
    metrics = []
    for scenario in result.scenarios:
        curve = scenario.boundary.propagation
        if curve is None:
            metrics.append({"scenario":scenario.scenario,"status":scenario.boundary.prediction_status,"modeled_time_in_orbit_seconds":None})
        else:
            metrics.append({"scenario":scenario.scenario,"status":scenario.boundary.prediction_status,
                **time_in_altitude_bands(curve),"final_perigee_altitude_m":curve.samples[-1].perigee_altitude_m,
                "final_apogee_altitude_m":curve.samples[-1].apogee_altitude_m,
                "boundary_crossing_time":None if scenario.boundary.crossing_time is None else scenario.boundary.crossing_time.isoformat()})
    status = result.scenarios[0].boundary.prediction_status if len(result.scenarios)==1 else result.status
    return PersistenceAnalysis(prediction_status=status,scenario_analysis=result,persistence_metrics=metrics,**common)
