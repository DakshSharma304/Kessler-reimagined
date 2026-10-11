from datetime import timedelta
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.optimize import brentq
from app.data.space_weather import SpaceWeatherUnavailable
from app.physics.atmosphere import ConstantTestAtmosphere,state_geodetic
from app.physics.boundary import estimate_boundary_crossing
from app.physics.decay import SolverSettings,propagate_orbital_decay
from app.physics.frames import earth_pole_gcrs
from app.physics.maneuvers import EARTH_RADIUS,MU_EARTH,NumericalTrajectory
from test_decay import AT,orbit,props


def crossing_orbit():
    initial = orbit(170000)
    ra,rp = EARTH_RADIUS+170000,EARTH_RADIUS+90000
    speed = np.sqrt(2*MU_EARTH*rp/(ra*(ra+rp)))
    return initial.model_copy(update={"velocity_m_s":(0,speed,0)})


def test_actual_event_matches_independent_existing_trajectory_and_converges():
    initial = crossing_orbit()
    result = estimate_boundary_crossing(initial,props(),ConstantTestAtmosphere(0),3000)
    assert result.prediction_status == "BOUNDARY_REACHED"
    assert result.crossing_occurred and result.crossing_time is not None
    trajectory = NumericalTrajectory(initial,AT+timedelta(seconds=3000),earth_pole_gcrs(AT),rtol=1e-11)
    expected = brentq(lambda t:state_geodetic(trajectory(AT+timedelta(seconds=t))).altitude_m-120000,0,2400,xtol=1e-5)
    assert result.modeled_time_until_crossing_seconds == pytest.approx(expected,abs=.002)
    final = result.propagation.samples[-1]
    assert final.geodetic.altitude_m == pytest.approx(120000,abs=.02)
    assert all(s.state.timestamp <= result.crossing_time for s in result.propagation.samples)
    tight = estimate_boundary_crossing(initial,props(),ConstantTestAtmosphere(0),3000,
        solver_settings=SolverSettings(rtol=1e-11,position_atol_m=1e-6,velocity_atol_m_s=1e-9,max_step_seconds=60))
    assert tight.prediction_status == "BOUNDARY_REACHED"
    assert tight.modeled_time_until_crossing_seconds == pytest.approx(result.modeled_time_until_crossing_seconds,abs=.002)
    earlier = estimate_boundary_crossing(initial,props(),ConstantTestAtmosphere(0),3000,boundary_altitude_m=130000)
    assert earlier.modeled_time_until_crossing_seconds < result.modeled_time_until_crossing_seconds
    assert not any("impact" in key for key in result.model_dump())
    print("ACTUAL_BOUNDARY",result.modeled_time_until_crossing_seconds,result.crossing_time.isoformat(),"independent",expected)


def test_no_crossing_is_not_infinite_lifetime():
    result = estimate_boundary_crossing(orbit(),props(),ConstantTestAtmosphere(0),3600)
    assert result.prediction_status == "NOT_REACHED_WITHIN_HORIZON"
    assert result.crossing_time is None and result.modeled_time_until_crossing_seconds is None
    assert not result.crossing_occurred
    assert result.prediction_horizon_days == pytest.approx(1/24)
    assert any("does not imply" in w for w in result.warnings)


def test_initial_below_boundary_and_missing_inputs_are_explicit():
    result = estimate_boundary_crossing(orbit(110000),props(),ConstantTestAtmosphere(0),3600)
    assert result.prediction_status == "INITIAL_STATE_UNSUPPORTED" and result.propagation is None
    assert estimate_boundary_crossing(orbit(),None,ConstantTestAtmosphere(0),3600).prediction_status == "INSUFFICIENT_OBJECT_PROPERTIES"
    assert estimate_boundary_crossing(orbit(),props(),None,3600).prediction_status == "INSUFFICIENT_ENVIRONMENT_DATA"


def test_solver_failure_is_explicit(monkeypatch):
    monkeypatch.setattr("app.physics.decay.solve_ivp",lambda *a,**kw:SimpleNamespace(success=False,message="controlled solver failure"))
    result = estimate_boundary_crossing(orbit(),props(),ConstantTestAtmosphere(0),3600)
    assert result.prediction_status == "NUMERICAL_FAILURE"
    assert result.crossing_time is None and result.propagation is None
    assert any("controlled solver failure" in w for w in result.warnings)


def test_missing_weather_and_budget_exhaustion_visible():
    class Missing(ConstantTestAtmosphere):
        def density(self,state): raise SpaceWeatherUnavailable("no forecast for modeled day")
    result = estimate_boundary_crossing(orbit(),props(),Missing(0),3600)
    assert result.prediction_status == "INSUFFICIENT_ENVIRONMENT_DATA"
    result = estimate_boundary_crossing(orbit(),props(),ConstantTestAtmosphere(0),3600,
        solver_settings=SolverSettings(timeout_seconds=1e-8))
    assert result.prediction_status == "NUMERICAL_FAILURE"


@pytest.mark.parametrize("boundary", [float("nan"),-1,70000,600000])
def test_invalid_boundary_rejected_without_fake_crossing(boundary):
    with pytest.raises(ValueError):
        propagate_orbital_decay(orbit(),AT,100,props(),ConstantTestAtmosphere(0),boundary_altitude_m=boundary)
