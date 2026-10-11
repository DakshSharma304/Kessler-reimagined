"""Explicit MSIS weather/ballistic scenarios, not confidence intervals.

LOW/HIGH presets are hypothetical constant solar histories (80/220 sfu,
Ap 4/40); NOMINAL can use the actual source forecast or explicit assumptions.
These labels do not guarantee density ordering for every real storm/orbit.
"""
from datetime import UTC,timedelta
from typing import Literal
import numpy as np
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.physics.atmosphere import MSISAtmosphere,WeatherForcing,forcing_from_dataset
from app.physics.boundary import BoundaryAnalysis,estimate_boundary_crossing
from app.physics.decay import SolverSettings
from app.physics.drag import ObjectAerodynamicProperties
from app.data.space_weather import SpaceWeatherUnavailable


class PersistenceSettings(BaseModel):
    model_config = ConfigDict(frozen=True,extra="forbid",allow_inf_nan=False)
    horizon_days: float = Field(default=1,gt=0,le=90)
    boundary_altitude_m: float = Field(default=120000,ge=80000,le=500000)
    scenario_mode: Literal["NOMINAL","COMPARE"] = "NOMINAL"
    weather_mode: Literal["SOURCE_ONLY","HYPOTHETICAL_CONSTANT","SOURCE_WITH_EXPLICIT_FALLBACK"] = "SOURCE_ONLY"
    nominal_f107_sfu: float | None = Field(default=None,gt=0,le=500)
    nominal_ap: float | None = Field(default=None,ge=0,le=400)
    min_cd_area_over_mass_m2_kg: float | None = Field(default=None,ge=0,le=100)
    max_cd_area_over_mass_m2_kg: float | None = Field(default=None,ge=0,le=100)
    solver: SolverSettings = Field(default_factory=SolverSettings)

    @model_validator(mode="after")
    def assumptions_complete(self):
        if self.weather_mode == "SOURCE_ONLY":
            if self.nominal_f107_sfu is not None or self.nominal_ap is not None:
                raise ValueError("Solar assumptions require an explicitly selected hypothetical/fallback weather mode")
        elif self.nominal_f107_sfu is None or self.nominal_ap is None:
            raise ValueError("Explicit nominal F10.7 and Ap assumptions are required for hypothetical/fallback weather")
        low,high = self.min_cd_area_over_mass_m2_kg,self.max_cd_area_over_mass_m2_kg
        if (low is None) != (high is None) or (low is not None and low > high):
            raise ValueError("Supply an ordered minimum and maximum Cd*A/m pair")
        if low is not None and self.scenario_mode != "COMPARE":
            raise ValueError("Ballistic scenario range requires COMPARE mode")
        return self


class ScenarioResult(BaseModel):
    scenario: Literal["LOW_DRAG","NOMINAL","HIGH_DRAG"]
    aerodynamic_properties: ObjectAerodynamicProperties
    environment_assumptions: dict
    boundary: BoundaryAnalysis
    total_specific_energy_change_j_kg: float | None = None
    semimajor_axis_change_m: float | None = None
    initial_period_mean_semimajor_axis_m: float | None = None
    final_period_mean_semimajor_axis_m: float | None = None
    warnings: list[str] = Field(default_factory=list)


class ScenarioAnalysis(BaseModel):
    settings: PersistenceSettings
    scenarios: list[ScenarioResult]
    status: Literal["COMPLETE","PARTIAL","UNAVAILABLE"]
    scenario_envelope: dict
    assumptions: list[str]
    warnings: list[str]


def constant_weather(timestamp,f107,ap,*,scenario,reason):
    return WeatherForcing(date=timestamp.astimezone(UTC).date(),f107_previous_day_sfu=f107,
        f107_center81_sfu=f107,ap_history=(ap,)*7,input_category="USER_SUPPLIED_ASSUMPTION",
        provenance={"source":"USER_SELECTED_HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
            "scenario":scenario,"reason":reason,"f107_convention":"Earth-distance sfu; constant previous/center81 history",
            "ap_convention":"Constant daily and all storm-time history components"},
        warnings=["ILLUSTRATIVE — USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
            "Constant solar history is a scenario, not observed conditions or a forecast beyond source coverage."])


def scenario_weather(scenario,settings,dataset):
    if scenario != "NOMINAL":
        flux,ap = (80,4) if scenario == "LOW_DRAG" else (220,40)
        return (lambda at:constant_weather(at,flux,ap,scenario=scenario,reason="Explicit COMPARE preset")),{
            "treatment":"HYPOTHETICAL_CONSTANT_SOLAR_HISTORY","f107_sfu":flux,"ap":ap,
            "label":"ILLUSTRATIVE — USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
            "density_treatment":"Actual NRLMSIS response, not a constant density multiplier"}
    assumptions = {"treatment":settings.weather_mode,"f107_sfu":settings.nominal_f107_sfu,"ap":settings.nominal_ap,
        "source_snapshot":None if dataset is None else dataset.coverage()}
    def weather(at):
        if settings.weather_mode != "HYPOTHETICAL_CONSTANT":
            try:
                if dataset is None: raise SpaceWeatherUnavailable("No space-weather dataset supplied")
                return forcing_from_dataset(at,dataset)
            except SpaceWeatherUnavailable:
                if settings.weather_mode == "SOURCE_ONLY": raise
        return constant_weather(at,settings.nominal_f107_sfu,settings.nominal_ap,
            scenario=scenario,reason="Explicit constant scenario" if settings.weather_mode == "HYPOTHETICAL_CONSTANT"
            else "Source unavailable/outside complete daily coverage; explicit fallback, not forecast extrapolation")
    return weather,assumptions


def compare_persistence_scenarios(initial_state,properties,settings: PersistenceSettings,dataset=None) -> ScenarioAnalysis:
    names = ["NOMINAL"] if settings.scenario_mode == "NOMINAL" else ["LOW_DRAG","NOMINAL","HIGH_DRAG"]
    if properties is None:
        boundary = estimate_boundary_crossing(initial_state,None,None,settings.horizon_days*86400,
            boundary_altitude_m=settings.boundary_altitude_m)
        return ScenarioAnalysis(settings=settings,scenarios=[],status="UNAVAILABLE",
            scenario_envelope={"reason":boundary.prediction_status},assumptions=[],warnings=boundary.warnings)
    low,high = settings.min_cd_area_over_mass_m2_kg,settings.max_cd_area_over_mass_m2_kg
    if low is not None and not low <= properties.effective_ratio <= high:
        raise ValueError("Nominal supplied Cd*A/m must lie inside the explicit ballistic scenario range")
    results = []
    for name in names:
        selected = properties
        if low is not None and name != "NOMINAL":
            selected = ObjectAerodynamicProperties(input_category="HYPOTHETICAL_ASSUMPTION",
                cd_area_over_mass_m2_kg=low if name == "LOW_DRAG" else high)
        weather,assumptions = scenario_weather(name,settings,dataset)
        boundary = estimate_boundary_crossing(initial_state,selected,MSISAtmosphere(weather),settings.horizon_days*86400,
            boundary_altitude_m=settings.boundary_altitude_m,solver_settings=settings.solver)
        result = ScenarioResult(scenario=name,aerodynamic_properties=selected,environment_assumptions=assumptions,
            boundary=boundary,warnings=["Scenario labels are nominal presets, not guaranteed ordering for all geometries or actual storm conditions."])
        if boundary.propagation is not None:
            samples = boundary.propagation.samples
            result.total_specific_energy_change_j_kg = samples[-1].total_specific_energy_j_kg-samples[0].total_specific_energy_j_kg
            result.semimajor_axis_change_m = samples[-1].semimajor_axis_m-samples[0].semimajor_axis_m
            from app.physics.maneuvers import MU_EARTH
            period = 2*np.pi*np.sqrt(samples[0].semimajor_axis_m**3/MU_EARTH)
            offsets = np.array([(s.state.timestamp-initial_state.timestamp).total_seconds() for s in samples])
            axes = np.array([s.semimajor_axis_m for s in samples])
            first,last = offsets <= period, offsets >= offsets[-1]-period
            # Output-sample means are not independent orbit determination.
            result.initial_period_mean_semimajor_axis_m = float(np.mean(axes[first]))
            result.final_period_mean_semimajor_axis_m = float(np.mean(axes[last]))
            result.warnings.append("Period-window sample means reduce J2 short-period effects; short horizons/windows overlap and are not a secular lifetime extrapolation.")
        results.append(result)
    valid = [r for r in results if r.boundary.propagation is not None]
    crossing = [r.boundary.modeled_time_until_crossing_seconds for r in valid if r.boundary.crossing_occurred]
    energy = [r.total_specific_energy_change_j_kg for r in valid]
    envelope = {"interpretation":"Scenario range only; NOT a statistical confidence interval or probability distribution",
        "valid_scenarios":len(valid),"failed_scenarios":[r.scenario for r in results if r not in valid],
        "crossed_scenarios":[r.scenario for r in valid if r.boundary.crossing_occurred],
        "not_reached_within_horizon":[r.scenario for r in valid if not r.boundary.crossing_occurred],
        "crossing_seconds_min":min(crossing) if crossing else None,"crossing_seconds_max":max(crossing) if crossing else None,
        "crossing_range_covers_only_reached_scenarios":True,
        "energy_change_range_j_kg":[min(energy),max(energy)] if energy else None}
    return ScenarioAnalysis(settings=settings,scenarios=results,
        status="COMPLETE" if len(valid)==len(results) else "PARTIAL" if valid else "UNAVAILABLE",
        scenario_envelope=envelope,
        assumptions=["Actual separate gravity/J2/drag/MSIS propagations; no precomputed lifetime answers.",
            "LOW/HIGH compare explicit constant solar/Ap histories; nominal weather source/treatment is disclosed.",
            "Physical and weather scenario envelope is not a calibrated statistical interval."],
        warnings=["Unknown physical properties, long-term space weather and initial orbit uncertainty prevent precise operational reentry predictions.",
            "Failed scenarios remain visible and are excluded only from numerical envelope endpoints."])
