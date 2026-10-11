from datetime import UTC, datetime, timedelta
import astropy.units as u
from astropy.coordinates import CartesianRepresentation, EarthLocation, GCRS, ITRS
from astropy.time import Time
import numpy as np
import pymsis
import pytest
from app.config import settings
from app.data.cache import FileCache
from app.data.space_weather import SpaceWeatherClient, SpaceWeatherUnavailable
from app.physics.atmosphere import (WeatherForcing, calculate_density, forcing_from_dataset,
    state_geodetic, MSISAtmosphere, ConstantTestAtmosphere)
from app.physics.frames import transform_states
from app.physics.propagation import StateVector

AT = datetime(2026,10,9,12,tzinfo=UTC)


def weather(f107=150,ap=15):
    return WeatherForcing(date=AT.date(),f107_previous_day_sfu=f107,
        f107_center81_sfu=f107,ap_history=(ap,)*7,input_category="USER_SUPPLIED_ASSUMPTION",
        provenance={"source":"controlled test, constant solar history"})


def test_real_msis_units_independent_call_and_repeatability():
    result = calculate_density(AT,40,-105,400000,weather())
    independent = pymsis.calculate([np.datetime64("2026-10-09T12:00:00")],[-105],[40],[400],
        f107s=[150], f107as=[150], aps=[[15]*7], version=2.1,geomagnetic_activity=-1)
    assert result.density_kg_m3 > 0 and np.isfinite(result.density_kg_m3)
    assert result.density_kg_m3 == float(independent[0,pymsis.Variable.MASS_DENSITY])
    assert result == calculate_density(AT,40,-105,400000,weather())
    assert result.model == "NRLMSIS 2.1"
    assert 1e-14 < result.density_kg_m3 < 1e-10
    print("ACTUAL_MSIS_DENSITY", result.density_kg_m3, "kg/m3", pymsis.__version__)


def test_altitude_and_solar_response():
    densities = [calculate_density(AT,0,0,h,weather()).density_kg_m3 for h in (200000,400000,800000)]
    assert densities[0] > densities[1] > densities[2]
    low = calculate_density(AT,0,0,400000,weather(80,4)).density_kg_m3
    high = calculate_density(AT,0,0,400000,weather(220,40)).density_kg_m3
    assert high > low


@pytest.mark.parametrize("values", [(91,0,400000),(0,181,400000),(0,0,-1),(0,0,1000001),(float("nan"),0,400000)])
def test_invalid_coordinates(values):
    with pytest.raises(ValueError): calculate_density(AT,*values,weather())


@pytest.mark.parametrize("change", [{"f107_previous_day_sfu":0},{"f107_center81_sfu":float("inf")},
    {"ap_history":(-1,)*7},{"ap_history":(float("nan"),)*7},{"date":AT.date()-timedelta(days=1)}])
def test_invalid_weather(change):
    with pytest.raises(ValueError):
        calculate_density(AT,0,0,400000,weather().model_dump()|change)


@pytest.mark.parametrize("lat,lon,alt", [(0,0,400000),(60,-105,250000),(-35,179.8,800000),(89,45,400000)])
def test_wgs84_geodetic_frame_roundtrip(lat,lon,alt):
    location = EarthLocation.from_geodetic(lon*u.deg,lat*u.deg,alt*u.m)
    gcrs = ITRS(location.get_itrs(obstime=Time(AT)).cartesian,obstime=Time(AT)).transform_to(GCRS(obstime=Time(AT)))
    state = StateVector(timestamp=AT,frame="GCRS",position_m=tuple(gcrs.cartesian.xyz.to_value(u.m)),velocity_m_s=(0,0,0))
    geo = state_geodetic(state)
    assert geo.latitude_deg == pytest.approx(lat,abs=1e-9)
    assert geo.longitude_deg == pytest.approx(lon,abs=1e-9)
    assert geo.altitude_m == pytest.approx(alt,abs=1e-6)
    teme = transform_states([state],"TEME")[0]
    assert state_geodetic(teme).altitude_m == pytest.approx(alt,abs=1e-6)
    atmosphere = MSISAtmosphere(lambda at:weather())
    assert atmosphere.density(state) == pytest.approx(calculate_density(AT,lat,lon,alt,weather()).density_kg_m3,rel=1e-6)


@pytest.mark.live
def test_real_weather_temporal_conventions():
    dataset = SpaceWeatherClient(FileCache(settings.cache_directory)).load_space_weather()
    forcing = forcing_from_dataset(AT,dataset)
    assert forcing.f107_previous_day_sfu == dataset.records[(AT-timedelta(days=1)).date()].f107_observed_sfu
    assert forcing.f107_center81_sfu == dataset.records[AT.date()].f107_observed_center81_sfu
    indices = []
    for i in range(20):
        timestamp = AT-timedelta(hours=3*i)
        indices.append(dataset.records[timestamp.date()].ap_3hourly[timestamp.hour//3])
    assert forcing.ap_history == (dataset.records[AT.date()].ap_daily,*indices[:4],np.mean(indices[4:12]),np.mean(indices[12:20]))
    result = calculate_density(AT,0,0,400000,forcing)
    assert result.density_kg_m3 > 0
    with pytest.raises(SpaceWeatherUnavailable): forcing_from_dataset(datetime(2041,10,1,tzinfo=UTC),dataset)
    with pytest.raises(SpaceWeatherUnavailable): forcing_from_dataset(AT,dataset,as_of=AT)


def test_controlled_density_provider_is_explicit():
    provider = ConstantTestAtmosphere(0)
    assert provider.density(None) == 0
    assert provider.provenance()["model"] == "CONTROLLED_CONSTANT_TEST_ATMOSPHERE"
    with pytest.raises(ValueError): ConstantTestAtmosphere(-1)
