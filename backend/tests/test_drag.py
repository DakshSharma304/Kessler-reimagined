from datetime import UTC,datetime,timedelta
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from app.physics.atmosphere import ConstantTestAtmosphere
from app.physics.drag import ObjectAerodynamicProperties, acceleration_drag, EARTH_ANGULAR_SPEED_RAD_S
from app.physics.frames import earth_pole_gcrs
from app.physics.maneuvers import NumericalTrajectory,gravity_components,MU_EARTH,EARTH_RADIUS,J2
from app.physics.propagation import StateVector

AT = datetime(2026,10,11,tzinfo=UTC)


def state():
    return StateVector(timestamp=AT,frame="GCRS",position_m=(6778137,0,0),velocity_m_s=(0,7668,0))


def properties(**changes):
    return ObjectAerodynamicProperties(input_category="HYPOTHETICAL_ASSUMPTION",**({"mass_kg":100,"area_m2":1,"drag_coefficient":2.2}|changes))


def test_zero_density_and_zero_area():
    s,pole = state(),np.array([0,0,1])
    np.testing.assert_array_equal(acceleration_drag(s,0,properties(),pole),np.zeros(3))
    np.testing.assert_array_equal(acceleration_drag(s,1e-10,properties(area_m2=0),pole),np.zeros(3))


def test_analytical_dimensions_corotation_and_direction():
    s,pole,rho = state(),np.array([0,0,1]),1e-12
    relative = 7668-EARTH_ANGULAR_SPEED_RAD_S*6778137
    a = acceleration_drag(s,rho,properties(),pole)
    np.testing.assert_allclose(a,[0,-.5*rho*.022*relative**2,0],rtol=1e-15)
    assert np.dot(a,[0,relative,0]) < 0
    assert abs(a[1]) < .5*rho*.022*7668**2
    corotating = s.model_copy(update={"velocity_m_s":(0,EARTH_ANGULAR_SPEED_RAD_S*6778137,0)})
    np.testing.assert_array_equal(acceleration_drag(corotating,rho,properties(),pole),np.zeros(3))
    np.testing.assert_array_equal(a,acceleration_drag(s,rho,properties(),pole))


def test_density_area_and_mass_scaling():
    s,pole,rho = state(),np.array([0,0,1]),1e-12
    a = acceleration_drag(s,rho,properties(),pole)
    np.testing.assert_allclose(acceleration_drag(s,2*rho,properties(),pole),2*a)
    np.testing.assert_allclose(acceleration_drag(s,rho,properties(area_m2=2),pole),2*a)
    np.testing.assert_allclose(acceleration_drag(s,rho,properties(mass_kg=200),pole),a/2)
    ratio = ObjectAerodynamicProperties(input_category="USER_SUPPLIED",cd_area_over_mass_m2_kg=.022)
    np.testing.assert_allclose(acceleration_drag(s,rho,ratio,pole),a)


@pytest.mark.parametrize("changes", [{"mass_kg":0},{"mass_kg":-1},{"area_m2":-1},
    {"drag_coefficient":0},{"drag_coefficient":-1},{"drag_coefficient":float("nan")},
    {"mass_kg":None},{"cd_area_over_mass_m2_kg":.022}])
def test_invalid_properties(changes):
    with pytest.raises(ValueError): properties(**changes)


def test_invalid_density_frame_and_pole():
    with pytest.raises(ValueError): acceleration_drag(state(),-1,properties(),[0,0,1])
    with pytest.raises(ValueError): acceleration_drag(state(),float("nan"),properties(),[0,0,1])
    with pytest.raises(ValueError): acceleration_drag(state(),0,properties(),[0,0,2])
    with pytest.raises(ValueError): acceleration_drag(state().model_copy(update={"frame":"TEME"}),0,properties(),[0,0,1])


def test_shared_gravity_components_and_no_drag_match_existing_integrator():
    initial = state()
    pole = earth_pole_gcrs(AT)
    zero = ConstantTestAtmosphere(0)
    reference = NumericalTrajectory(initial,AT+timedelta(hours=1),pole)
    def rhs(t,y):
        s = StateVector(timestamp=AT+timedelta(seconds=t),frame="GCRS",position_m=tuple(y[:3]),velocity_m_s=tuple(y[3:]))
        central,j2 = gravity_components(y[:3],pole)
        return np.concatenate([y[3:],central+j2+acceleration_drag(s,zero.density(s),properties(),pole)])
    result = solve_ivp(rhs,(0,3600),[*initial.position_m,*initial.velocity_m_s],method="DOP853",rtol=1e-9,
        atol=[1e-4]*3+[1e-7]*3,max_step=120,dense_output=True)
    assert result.success
    for t in (0,1000,3600):
        expected = reference(AT+timedelta(seconds=t))
        np.testing.assert_allclose(result.sol(t),[*expected.position_m,*expected.velocity_m_s],rtol=0,atol=1e-7)
