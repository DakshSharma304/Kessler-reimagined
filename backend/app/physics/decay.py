"""Bounded GCRS gravity/J2/drag propagation, never a ground-impact model.

Shared WGS84 force constants and adaptive DOP853, as in existing maneuvers.
Osculating elements use central-gravity energy; total energy also includes
the conservative J2 potential. Perigee/apogee are radii minus WGS84 equatorial
radius, NOT instantaneous WGS84 geodetic altitude. No monotonic sample claim.
"""
from datetime import UTC, datetime, timedelta
import math
import time

import astropy.units as u
from astropy.coordinates import CartesianRepresentation, GCRS, ITRS
from astropy.time import Time
import erfa
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation, Slerp

from app.physics.atmosphere import GeodeticPosition
from app.physics.drag import ObjectAerodynamicProperties, _drag_from_validated_components
from app.physics.frames import earth_pole_gcrs, teme_to_gcrs
from app.physics.maneuvers import EARTH_RADIUS, J2, MU_EARTH, gravity_components
from app.physics.propagation import StateVector


class DecayUnsupported(ValueError):
    pass


class DecayNumericalFailure(RuntimeError):
    pass


class DecayModelOutOfValidity(DecayUnsupported):
    pass


class SolverSettings(BaseModel):
    model_config = ConfigDict(frozen=True,extra="forbid",allow_inf_nan=False)
    rtol: float = Field(default=1e-9,ge=1e-12,le=1e-6)
    position_atol_m: float = Field(default=1e-4,gt=0,le=.1)
    velocity_atol_m_s: float = Field(default=1e-7,gt=0,le=1e-3)
    max_step_seconds: float = Field(default=120,gt=0,le=120)
    sample_step_seconds: float = Field(default=600,ge=10,le=3600)
    timeout_seconds: float = Field(default=180,gt=0,le=600)


class DecaySample(BaseModel):
    model_config = ConfigDict(frozen=True,allow_inf_nan=False)
    state: StateVector
    geodetic: GeodeticPosition
    central_specific_energy_j_kg: float
    total_specific_energy_j_kg: float
    semimajor_axis_m: float
    eccentricity: float = Field(ge=0,lt=1)
    perigee_altitude_m: float
    apogee_altitude_m: float
    density_kg_m3: float = Field(ge=0)
    model_status: str = "MODEL_CALCULATED"


class DecayPropagation(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    status: str
    start_time: datetime
    requested_end_time: datetime
    integrated_end_time: datetime
    horizon_days: float
    samples: list[DecaySample]
    elapsed_seconds: float
    derivative_evaluations: int
    solver_settings: SolverSettings
    environment: dict
    aerodynamic_properties: dict
    boundary_altitude_m: float = 120000
    boundary_crossing_time: datetime | None = None
    model: str = "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag"
    assumptions: list[str]
    warnings: list[str]


class EarthOrientation:
    """Batch true Astropy GCRS→ITRS at ≤20-minute spacing, SO(3) SLERP.

    No density interpolation. Grid orientation is independently checked
    against scalar Astropy transforms; the stored offline IERS limitations
    still apply. ERFA gc2gd supplies exact WGS84 geodetic conversion.
    """
    def __init__(self,start,end,step_seconds=1200):
        self.start,self.end = start,end
        duration = (end-start).total_seconds()
        offsets = np.linspace(0,duration,max(2,int(math.ceil(duration/step_seconds))+1))
        stamps = [start+timedelta(seconds=float(x)) for x in offsets]
        dates = Time([stamp for stamp in stamps for _ in range(3)])
        axes = CartesianRepresentation(np.tile(np.eye(3),(1,len(stamps)))*u.m)
        transformed = GCRS(axes,obstime=dates).transform_to(ITRS(obstime=dates))
        matrices = transformed.cartesian.xyz.to_value(u.m).T.reshape(-1,3,3).transpose(0,2,1)
        self.interpolator = Slerp(offsets,Rotation.from_matrix(matrices))
        self._last_timestamp = None
        self._last_rotation = None

    def rotation(self,timestamp):
        if not self.start <= timestamp <= self.end:
            raise DecayUnsupported("Earth-orientation query outside prepared interval")
        if timestamp != self._last_timestamp:
            matrix = self.interpolator((timestamp-self.start).total_seconds()).as_matrix()
            matrix.setflags(write=False)
            self._last_timestamp,self._last_rotation = timestamp,matrix
        return self._last_rotation

    def geodetic(self,state):
        return self.position_geodetic(state.timestamp,np.asarray(state.position_m))

    def position_geodetic(self,timestamp,position):
        return self._geodetic_with_rotation(self.rotation(timestamp),position)

    @staticmethod
    def _geodetic_with_rotation(rotation,position):
        lon,lat,height = erfa.gc2gd(1,rotation@position)
        return GeodeticPosition(latitude_deg=math.degrees(lat),longitude_deg=math.degrees(lon),altitude_m=float(height))

    def geodetic_and_pole(self,timestamp,position):
        rotation = self.rotation(timestamp)
        return self._geodetic_with_rotation(rotation,position),rotation[2,:]

    def pole(self,timestamp):
        return self.rotation(timestamp)[2,:]


def orbital_quantities(state,pole):
    r,v = np.asarray(state.position_m),np.asarray(state.velocity_m_s)
    radius = np.linalg.norm(r)
    if radius <= EARTH_RADIUS or not np.isfinite([*r,*v]).all():
        raise DecayUnsupported("Unsupported singular/intersecting/nonfinite numerical state")
    energy = .5*np.dot(v,v)-MU_EARTH/radius
    h = np.cross(r,v)
    if energy >= 0 or np.linalg.norm(h) <= 0:
        raise DecayUnsupported("Only bound nondegenerate Earth orbits are supported")
    a = -MU_EARTH/(2*energy)
    eccentricity = np.linalg.norm(np.cross(v,h)/MU_EARTH-r/radius)
    if eccentricity >= 1 or not np.isfinite([a,eccentricity]).all():
        raise DecayUnsupported("Invalid/unbound osculating elements")
    potential_j2 = MU_EARTH*J2*EARTH_RADIUS**2/(2*radius**3)*(3*(np.dot(r,pole)/radius)**2-1)
    return {"central_specific_energy_j_kg":float(energy),
            "total_specific_energy_j_kg":float(energy+potential_j2),
            "semimajor_axis_m":float(a),"eccentricity":float(eccentricity),
            "perigee_altitude_m":float(a*(1-eccentricity)-EARTH_RADIUS),
            "apogee_altitude_m":float(a*(1+eccentricity)-EARTH_RADIUS)}


def propagate_orbital_decay(initial_state,start_time,duration,aerodynamic_properties,
        atmosphere,solver_settings=None,*,boundary_altitude_m=120000) -> DecayPropagation:
    settings = solver_settings or SolverSettings()
    if not isinstance(settings,SolverSettings): settings = SolverSettings.model_validate(settings)
    if start_time.tzinfo is None or initial_state.timestamp != start_time:
        raise DecayUnsupported("Initial state must be at the supplied aware start time")
    seconds = duration.total_seconds() if isinstance(duration,timedelta) else float(duration)
    if not math.isfinite(seconds) or not 0 < seconds <= 90*86400:
        raise DecayUnsupported("Decay duration must be finite, positive and bounded to 90 days")
    if aerodynamic_properties is None:
        raise DecayUnsupported("Explicit aerodynamic properties required; no BSTAR substitution")
    aerodynamic_properties = ObjectAerodynamicProperties.model_validate(aerodynamic_properties)
    drag_ratio = aerodynamic_properties.effective_ratio
    if atmosphere is None:
        raise DecayUnsupported("Explicit atmospheric density provider required")
    if not math.isfinite(boundary_altitude_m) or not 80000 <= boundary_altitude_m <= 500000:
        raise ValueError("Boundary must be finite WGS84 geodetic altitude between 80 and 500 km")
    initial = teme_to_gcrs(initial_state) if initial_state.frame == "TEME" else initial_state
    end = start_time+timedelta(seconds=seconds)
    started = time.perf_counter()
    orientation = EarthOrientation(start_time,end)
    gravity_pole = earth_pole_gcrs(start_time)
    orbital_quantities(initial,gravity_pole)
    initial_alt = orientation.geodetic(initial).altitude_m
    if not boundary_altitude_m < initial_alt <= 1000000:
        raise DecayUnsupported("Initial geodetic altitude must be above configured boundary and at most 1000 km")
    if hasattr(atmosphere,"prepare"):
        atmosphere = atmosphere.prepare(orientation)
    density_at = getattr(atmosphere,"density_at",None)
    deadline = started+settings.timeout_seconds

    def state_at(t,y):
        return StateVector(timestamp=start_time+timedelta(seconds=float(t)),frame="GCRS",
            position_m=tuple(y[:3]),velocity_m_s=tuple(y[3:]))

    def derivatives(t,y):
        if time.perf_counter() > deadline:
            raise DecayNumericalFailure("Propagation computation budget exhausted; no complete lifetime prediction")
        if not np.isfinite(y).all():
            raise DecayNumericalFailure("Nonfinite numerical force state")
        timestamp = start_time+timedelta(seconds=float(t))
        geo,pole = orientation.geodetic_and_pole(timestamp,y[:3])
        if not 80000 <= geo.altitude_m <= 1000000:
            raise DecayModelOutOfValidity("Trial state outside 80–1000-km orbital model validity; stop, no ground-impact propagation")
        rho = density_at(timestamp,geo) if density_at is not None else atmosphere.density(state_at(t,y))
        if not math.isfinite(rho) or rho < 0:
            raise DecayNumericalFailure("Atmosphere returned nonfinite/negative density")
        central,j2 = gravity_components(y[:3],gravity_pole)
        drag = _drag_from_validated_components(y[:3],y[3:],rho,drag_ratio,pole)
        derivative = np.concatenate([y[3:],central+j2+drag])
        if not np.isfinite(derivative).all():
            raise DecayNumericalFailure("Nonfinite numerical acceleration")
        return derivative

    def boundary_event(t,y):
        return orientation.position_geodetic(start_time+timedelta(seconds=float(t)),y[:3]).altitude_m-boundary_altitude_m
    boundary_event.terminal = True
    boundary_event.direction = -1
    solution = solve_ivp(derivatives,(0,seconds),[*initial.position_m,*initial.velocity_m_s],
        method="DOP853",rtol=settings.rtol,atol=[settings.position_atol_m]*3+[settings.velocity_atol_m_s]*3,
        max_step=settings.max_step_seconds,dense_output=True,events=boundary_event)
    if not solution.success or not np.isfinite(solution.y).all():
        raise DecayNumericalFailure(f"Numerical integration failed: {solution.message}")
    crossing = bool(len(solution.t_events[0]))
    integrated_seconds = float(solution.t[-1])
    integrated_end = start_time+timedelta(seconds=integrated_seconds)
    offsets = np.linspace(0,integrated_seconds,max(2,min(20000,int(math.ceil(integrated_seconds/settings.sample_step_seconds))+1)))
    samples = []
    for offset in offsets:
        state = state_at(offset,solution.sol(offset))
        geo = orientation.geodetic(state)
        rho = density_at(state.timestamp,geo) if density_at is not None else atmosphere.density(state)
        samples.append(DecaySample(state=state,geodetic=geo,
            density_kg_m3=rho,**orbital_quantities(state,gravity_pole)))
    return DecayPropagation(status="BOUNDARY_REACHED" if crossing else "PROPAGATED_WITHIN_HORIZON",start_time=start_time,requested_end_time=end,
        integrated_end_time=integrated_end,horizon_days=seconds/86400,samples=samples,
        elapsed_seconds=time.perf_counter()-started,derivative_evaluations=solution.nfev,
        solver_settings=settings,environment=atmosphere.provenance(),
        aerodynamic_properties=aerodynamic_properties.model_dump(),
        boundary_altitude_m=boundary_altitude_m,boundary_crossing_time=integrated_end if crossing else None,
        assumptions=["GCRS SI initial state; SGP4 TEME inputs are transformed, never relabeled.",
            "Shared WGS84 central/J2 dynamics; gravity pole fixed at initial epoch as in existing numerical model.",
            "Co-rotation axis and geographic density positions use time-varying GCRS/ITRS orientation.",
            "SO(3) Earth-orientation interpolation at at most 20-minute spacing; density itself is not interpolated.",
            "Constant supplied effective Cd*A/m; no attitude dynamics, winds or active orbit control.",
            "Terminal descending WGS84 geodetic boundary event; no output beyond the cutoff.",
            "Osculating central-gravity elements; perigee/apogee are radii minus equatorial Earth radius, not geodetic heights."],
        warnings=["Bounded research model, not observationally verified decay or operational reentry prediction.",
            "J2 produces short-period osculating-element oscillations; individual semimajor-axis samples need not monotonically decrease.",
            "Fixed gravity pole, offline predictive Earth orientation, no higher harmonics/third bodies and increasing initial-GP uncertainty limit long-horizon accuracy.",
            "No breakup, ablation, fragmentation or ground-impact calculation."])
