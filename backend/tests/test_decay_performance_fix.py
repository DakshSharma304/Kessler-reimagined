"""Independent force agreement and unchanged actual-MSIS scalar propagation."""
from datetime import timedelta
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from app.physics.atmosphere import MSISAtmosphere,calculate_density
from app.physics.decay import EarthOrientation,propagate_orbital_decay
from app.physics.drag import EARTH_ANGULAR_SPEED_RAD_S,acceleration_drag
from app.physics.frames import earth_pole_gcrs
from app.physics.maneuvers import gravity_components
from app.physics.propagation import StateVector
from test_decay import AT,controlled_weather,orbit,props


def test_shared_geometry_and_density_are_identical(monkeypatch):
    orientation = EarthOrientation(AT,AT+timedelta(days=1))
    atmosphere = MSISAtmosphere(controlled_weather).prepare(orientation)
    original = orientation.rotation
    calls = []
    def counted(timestamp):
        calls.append(timestamp)
        return original(timestamp)
    monkeypatch.setattr(orientation,"rotation",counted)
    for seconds in (0,157,1199,86399):
        state = orbit().model_copy(update={"timestamp":AT+timedelta(seconds=seconds)})
        before = len(calls)
        geo,pole = orientation.geodetic_and_pole(state.timestamp,np.array(state.position_m))
        assert len(calls) == before+1
        assert geo == orientation.geodetic(state)
        np.testing.assert_array_equal(pole,orientation.pole(state.timestamp))
        density = atmosphere.density_at(state.timestamp,geo)
        assert density == atmosphere.density(state)
        independent = calculate_density(state.timestamp,geo.latitude_deg,geo.longitude_deg,
            geo.altitude_m,controlled_weather(state.timestamp)).density_kg_m3
        assert density == independent
    # The cache must not permit accidental mutation or retain another epoch.
    assert not orientation.rotation(AT).flags.writeable
    with pytest.raises(ValueError):
        orientation.rotation(AT)[0,0] = 2


def test_scalar_drag_matches_independent_numpy_cross_product():
    generator = np.random.default_rng(42)
    for _ in range(200):
        pole = generator.normal(size=3)
        pole /= np.linalg.norm(pole)
        position = generator.normal(size=3)*7e6
        velocity = generator.normal(size=3)*7500
        state = StateVector(timestamp=AT,frame="GCRS",position_m=tuple(position),velocity_m_s=tuple(velocity))
        rho = float(10**generator.uniform(-15,-9))
        relative = velocity-np.cross(EARTH_ANGULAR_SPEED_RAD_S*pole,position)
        expected = -.5*rho*.022*np.linalg.norm(relative)*relative
        np.testing.assert_array_equal(acceleration_drag(state,rho,props(),pole),expected)


def test_optimized_actual_msis_matches_independent_scalar_integrator():
    initial = orbit()
    duration = 5400
    result = propagate_orbital_decay(initial,AT,duration,props(),MSISAtmosphere(controlled_weather))
    orientation = EarthOrientation(AT,AT+timedelta(seconds=duration))
    atmosphere = MSISAtmosphere(controlled_weather).prepare(orientation)
    gravity_pole = earth_pole_gcrs(AT)
    def legacy_rhs(t,y):
        state = StateVector(timestamp=AT+timedelta(seconds=float(t)),frame="GCRS",
            position_m=tuple(y[:3]),velocity_m_s=tuple(y[3:]))
        central,j2 = gravity_components(y[:3],gravity_pole)
        rho = atmosphere.density(state)
        relative = y[3:]-np.cross(EARTH_ANGULAR_SPEED_RAD_S*orientation.pole(state.timestamp),y[:3])
        drag = -.5*rho*props().effective_ratio*np.linalg.norm(relative)*relative
        return np.concatenate([y[3:],central+j2+drag])
    legacy = solve_ivp(legacy_rhs,(0,duration),[*initial.position_m,*initial.velocity_m_s],
        method="DOP853",rtol=1e-9,atol=[1e-4]*3+[1e-7]*3,max_step=120,dense_output=True)
    assert legacy.success
    for sample in result.samples:
        t = (sample.state.timestamp-AT).total_seconds()
        np.testing.assert_allclose(sample.state.position_m,legacy.sol(t)[:3],rtol=0,atol=1e-5)
        np.testing.assert_allclose(sample.state.velocity_m_s,legacy.sol(t)[3:],rtol=0,atol=1e-8)
    assert result.solver_settings.timeout_seconds == 180
    assert result.solver_settings.rtol == 1e-9
    assert result.solver_settings.max_step_seconds == 120
