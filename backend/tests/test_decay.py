from datetime import UTC,datetime,timedelta
import numpy as np
import pytest
from app.physics.atmosphere import ConstantTestAtmosphere,MSISAtmosphere,state_geodetic
from app.physics.decay import (DecayUnsupported,DecayNumericalFailure,EarthOrientation,
    SolverSettings,propagate_orbital_decay)
from app.physics.drag import ObjectAerodynamicProperties
from app.physics.frames import earth_pole_gcrs
from app.physics.maneuvers import EARTH_RADIUS,MU_EARTH,NumericalTrajectory
from app.physics.propagation import StateVector
from test_atmosphere import weather

AT = datetime(2026,10,9,12,tzinfo=UTC)


def orbit(alt=400000):
    radius = EARTH_RADIUS+alt
    return StateVector(timestamp=AT,frame="GCRS",position_m=(radius,0,0),
        velocity_m_s=(0,np.sqrt(MU_EARTH/radius),0))


def props(ratio=.022):
    return ObjectAerodynamicProperties(input_category="HYPOTHETICAL_ASSUMPTION",cd_area_over_mass_m2_kg=ratio)


def controlled_weather(timestamp):
    """Explicit constant hypothetical solar history on the queried UTC day."""
    return weather().model_copy(update={"date":timestamp.astimezone(UTC).date()})


def run(rho=1e-11,ratio=.022,alt=400000,duration=10800,**settings):
    return propagate_orbital_decay(orbit(alt),AT,duration,props(ratio),ConstantTestAtmosphere(rho),SolverSettings(**settings))


def test_orientation_and_prepared_density_independently_checked():
    orientation = EarthOrientation(AT,AT+timedelta(days=1))
    atmosphere = MSISAtmosphere(controlled_weather).prepare(orientation)
    for offset in (0,157,599,1001,1199,2397,86399):
        s = orbit().model_copy(update={"timestamp":AT+timedelta(seconds=offset)})
        direct,fast = state_geodetic(s),orientation.geodetic(s)
        assert fast.latitude_deg == pytest.approx(direct.latitude_deg,abs=2e-6)
        assert fast.longitude_deg == pytest.approx(direct.longitude_deg,abs=2e-6)
        assert fast.altitude_m == pytest.approx(direct.altitude_m,abs=.02)
        expected = MSISAtmosphere(controlled_weather).density(s)
        assert atmosphere.density(s) == pytest.approx(expected,rel=1e-5)


def test_zero_drag_matches_existing_numerical_trajectory():
    result = run(rho=0)
    old = NumericalTrajectory(orbit(),AT+timedelta(seconds=10800),earth_pole_gcrs(AT))
    for sample in result.samples:
        reference = old(sample.state.timestamp)
        np.testing.assert_allclose(sample.state.position_m,reference.position_m,rtol=0,atol=1e-5)
        np.testing.assert_allclose(sample.state.velocity_m_s,reference.velocity_m_s,rtol=0,atol=1e-8)
    assert result.status == "PROPAGATED_WITHIN_HORIZON"
    assert abs(result.samples[-1].total_specific_energy_j_kg-result.samples[0].total_specific_energy_j_kg) < .1


def test_drag_trajectory_energy_and_scaling():
    zero,nominal,highratio,highdensity = run(rho=0),run(),run(ratio=.044),run(rho=2e-11)
    def loss(r): return r.samples[0].total_specific_energy_j_kg-r.samples[-1].total_specific_energy_j_kg
    assert loss(nominal) > 10
    assert loss(highratio) > loss(nominal)
    assert loss(highdensity) > loss(nominal)
    assert np.linalg.norm(np.array(nominal.samples[-1].state.position_m)-zero.samples[-1].state.position_m) > 1
    assert nominal.samples[-1].semimajor_axis_m < zero.samples[-1].semimajor_axis_m
    assert highratio.samples[-1].state == highdensity.samples[-1].state


def test_convergence_and_output_units():
    ordinary = run()
    tighter = run(rtol=1e-11,position_atol_m=1e-6,velocity_atol_m_s=1e-9,max_step_seconds=60)
    np.testing.assert_allclose(ordinary.samples[-1].state.position_m,tighter.samples[-1].state.position_m,rtol=0,atol=.05)
    assert ordinary.samples[-1].semimajor_axis_m == pytest.approx(tighter.samples[-1].semimajor_axis_m,abs=.01)
    sample = ordinary.samples[0]
    assert sample.state.position_units == "m" and sample.state.velocity_units == "m/s"
    assert sample.semimajor_axis_m == pytest.approx(EARTH_RADIUS+400000,abs=1e-6)
    assert sample.geodetic.altitude_m == pytest.approx(400000,abs=2)
    assert sample.density_kg_m3 == 1e-11
    assert ordinary.derivative_evaluations > 0
    print("ACTUAL_DECAY_CONVERGENCE",np.linalg.norm(np.array(ordinary.samples[-1].state.position_m)-tighter.samples[-1].state.position_m),"m",ordinary.elapsed_seconds,"s")


def test_real_msis_low_high_altitude_comparison():
    atmosphere = MSISAtmosphere(controlled_weather)
    low = propagate_orbital_decay(orbit(250000),AT,5400,props(),atmosphere)
    high = propagate_orbital_decay(orbit(800000),AT,5400,props(),atmosphere)
    def loss(r): return r.samples[0].total_specific_energy_j_kg-r.samples[-1].total_specific_energy_j_kg
    assert loss(low) > loss(high)
    assert abs(loss(high)) < 1
    assert high.samples[0].density_kg_m3 < low.samples[0].density_kg_m3
    assert low.environment["model"] == "NRLMSIS 2.1"
    assert low.environment["forcing_samples"]


@pytest.mark.parametrize("duration", [0,-1,91*86400,float("nan")])
def test_unsupported_horizons(duration):
    with pytest.raises(DecayUnsupported): run(duration=duration)


def test_missing_inputs_nonfinite_and_unsupported_state():
    for properties,atmosphere in ((None,ConstantTestAtmosphere(0)),(props(),None)):
        with pytest.raises(DecayUnsupported): propagate_orbital_decay(orbit(),AT,100,properties,atmosphere)
    with pytest.raises(DecayUnsupported): propagate_orbital_decay(orbit(),AT+timedelta(seconds=1),100,props(),ConstantTestAtmosphere(0))
    with pytest.raises(DecayUnsupported): run(alt=110000)
    with pytest.raises(DecayUnsupported): run(alt=1200000)
    class Bad(ConstantTestAtmosphere):
        def density(self,state): return float("nan")
    with pytest.raises(DecayNumericalFailure,match="nonfinite"):
        propagate_orbital_decay(orbit(),AT,100,props(),Bad(0))
