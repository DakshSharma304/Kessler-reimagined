from datetime import UTC,datetime,timedelta
import numpy as np
import pytest
from app.config import settings as config
from app.data.cache import FileCache
from app.data.space_weather import SpaceWeatherClient
from app.physics.atmosphere import MSISAtmosphere
from app.physics.boundary import estimate_boundary_crossing
from app.physics.persistence_scenarios import (PersistenceSettings,compare_persistence_scenarios,
    scenario_weather,constant_weather)
from test_decay import AT,orbit,props


def assumptions(**changes):
    return PersistenceSettings(**({"horizon_days":.0625,"scenario_mode":"COMPARE",
        "weather_mode":"HYPOTHETICAL_CONSTANT","nominal_f107_sfu":150,"nominal_ap":15}|changes))


def test_actual_three_msis_propagations_and_envelope():
    result = compare_persistence_scenarios(orbit(250000),props(),assumptions())
    assert result.status == "COMPLETE"
    assert [r.scenario for r in result.scenarios] == ["LOW_DRAG","NOMINAL","HIGH_DRAG"]
    losses = [-r.total_specific_energy_change_j_kg for r in result.scenarios]
    assert losses[2] > losses[1] > losses[0] > 0
    densities = [r.boundary.propagation.samples[0].density_kg_m3 for r in result.scenarios]
    assert densities[2] > densities[1] > densities[0]
    assert all(r.boundary.prediction_status == "NOT_REACHED_WITHIN_HORIZON" for r in result.scenarios)
    assert result.scenario_envelope["crossing_seconds_min"] is None
    assert result.scenario_envelope["valid_scenarios"] == 3
    assert "NOT a statistical" in result.scenario_envelope["interpretation"]
    for scenario in result.scenarios:
        forcing = scenario.boundary.propagation.environment["forcing_samples"][0]
        assert forcing["input_category"] == "USER_SUPPLIED_ASSUMPTION"
        assert forcing["provenance"]["source"] == "USER_SELECTED_HYPOTHETICAL_CONSTANT_SOLAR_HISTORY"
    print("ACTUAL_SCENARIOS_ENERGY_LOSS",losses,"J/kg")


def test_ballistic_range_is_supplied_and_changes_physics():
    settings = assumptions(min_cd_area_over_mass_m2_kg=.011,max_cd_area_over_mass_m2_kg=.044)
    result = compare_persistence_scenarios(orbit(250000),props(),settings)
    assert [r.aerodynamic_properties.effective_ratio for r in result.scenarios] == [.011,.022,.044]
    with pytest.raises(ValueError): compare_persistence_scenarios(orbit(),props(.5),settings)
    weather = lambda at:constant_weather(at,150,15,scenario="TEST",reason="Controlled fixed weather")
    low = estimate_boundary_crossing(orbit(250000),props(.011),MSISAtmosphere(weather),5400)
    high = estimate_boundary_crossing(orbit(250000),props(.044),MSISAtmosphere(weather),5400)
    low_loss = low.propagation.samples[0].total_specific_energy_j_kg-low.propagation.samples[-1].total_specific_energy_j_kg
    high_loss = high.propagation.samples[0].total_specific_energy_j_kg-high.propagation.samples[-1].total_specific_energy_j_kg
    assert high_loss > low_loss


def test_missing_and_failed_nominal_scenario_are_not_hidden():
    settings = PersistenceSettings(horizon_days=.01,scenario_mode="COMPARE",weather_mode="SOURCE_ONLY")
    result = compare_persistence_scenarios(orbit(),props(),settings,dataset=None)
    assert result.status == "PARTIAL"
    assert result.scenarios[1].boundary.prediction_status == "INSUFFICIENT_ENVIRONMENT_DATA"
    assert result.scenario_envelope["failed_scenarios"] == ["NOMINAL"]
    assert result.scenario_envelope["valid_scenarios"] == 2
    missing = compare_persistence_scenarios(orbit(),None,settings)
    assert missing.status == "UNAVAILABLE" and missing.scenarios == []
    assert missing.scenario_envelope["reason"] == "INSUFFICIENT_OBJECT_PROPERTIES"


@pytest.mark.live
def test_beyond_forecast_requires_explicit_assumptions():
    dataset = SpaceWeatherClient(FileCache(config.cache_directory)).load_space_weather()
    future = datetime(2027,1,2,tzinfo=UTC)
    initial = orbit().model_copy(update={"timestamp":future})
    source = PersistenceSettings(horizon_days=.001,weather_mode="SOURCE_ONLY")
    unavailable = compare_persistence_scenarios(initial,props(),source,dataset)
    assert unavailable.status == "UNAVAILABLE"
    assert unavailable.scenarios[0].boundary.prediction_status == "INSUFFICIENT_ENVIRONMENT_DATA"
    explicit = assumptions(horizon_days=.001,scenario_mode="NOMINAL",weather_mode="SOURCE_WITH_EXPLICIT_FALLBACK")
    result = compare_persistence_scenarios(initial,props(),explicit,dataset)
    assert result.status == "COMPLETE"
    forcing = result.scenarios[0].boundary.propagation.environment["forcing_samples"][0]
    assert "explicit fallback" in forcing["provenance"]["reason"]
    assert forcing["input_category"] == "USER_SUPPLIED_ASSUMPTION"
    now = datetime(2026,10,12,tzinfo=UTC)
    lookup,_ = scenario_weather("NOMINAL",source,dataset)
    assert lookup(now).input_category == "SOURCE_FORECAST"


@pytest.mark.parametrize("change", [{"nominal_ap":None},{"nominal_f107_sfu":None},
    {"min_cd_area_over_mass_m2_kg":.1},{"min_cd_area_over_mass_m2_kg":.1,"max_cd_area_over_mass_m2_kg":.01},
    {"horizon_days":91},{"nominal_f107_sfu":-1}])
def test_invalid_assumptions_rejected(change):
    with pytest.raises(ValueError): assumptions(**change)
