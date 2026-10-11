"""Actual impulsive maneuvers against a matched central-gravity/J2 baseline."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from scipy.integrate import solve_ivp

from app.models.encounter import Encounter
from app.models.orbital import OrbitalRecord
from app.physics.encounters import BaselineAnalysis, ClosestApproach, analyze_encounter, refine_closest_approach
from app.physics.frames import earth_pole_gcrs, rtn_basis, teme_to_gcrs
from app.physics.propagation import StateVector, propagate_object

MU_EARTH = 3.986004418e14  # m^3/s^2, WGS84
EARTH_RADIUS = 6378137.0  # m, WGS84 equatorial radius
J2 = 1.08262668e-3

MODEL_ASSUMPTIONS = [
    "Hypothetical instantaneous RTN velocity impulse; supplied capability is assumed, not verified.",
    "Central Earth gravity plus J2, WGS84 constants, in GCRS coordinates.",
    "Both zero-burn and post-burn trajectories use the same initial epoch and numerical force model.",
    "SGP4 TEME states are transformed into GCRS using Astropy and the installed offline IERS data.",
    "Earth pole is fixed at the burn epoch over this short local propagation; no drag, higher harmonics, third-body forces or ongoing maneuvers.",
    "RTN transverse direction is perpendicular to radial in the orbital plane; it need not equal the eccentric-orbit velocity direction.",
    "Nominal clearance is not a calibrated collision probability or an operational safety guarantee.",
    "Secondary encounters have not been assessed. Results are not spacecraft flight commands.",
]


class ManeuverError(RuntimeError):
    pass


class ManeuverSimulation(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    encounter_id: str
    maneuvering_object_id: str
    maneuver_time: AwareDatetime
    delta_v_rtn_m_s: tuple[float, float, float]
    delta_v_gcrs_m_s: tuple[float, float, float]
    delta_v_m_s: float = Field(ge=0)
    state_before_maneuver: StateVector
    state_after_maneuver: StateVector
    matched_baseline: ClosestApproach
    modified: ClosestApproach
    change_in_miss_distance_m: float
    change_in_tca_seconds: float
    baseline_trajectory: list[StateVector]
    modified_trajectory: list[StateVector]
    sgp4_reference: BaselineAnalysis
    model: Literal["Matched central gravity + J2 / GCRS / WGS84"] = "Matched central gravity + J2 / GCRS / WGS84"
    model_assumptions: list[str]
    warnings: list[str]


class NumericalTrajectory:
    def __init__(self, initial: StateVector, end: datetime, pole: np.ndarray,
                 start: datetime | None = None, rtol: float = 1e-9):
        if initial.frame != "GCRS" or end <= initial.timestamp:
            raise ValueError("Numerical propagation requires GCRS and a future endpoint")
        if not 1e-13 <= rtol <= 1e-6:
            raise ValueError("Unsupported numerical integration tolerance")
        self.initial = initial
        self.start = min(start or initial.timestamp, initial.timestamp)
        self.end = end
        self.pole = np.asarray(pole)
        self._forward = self._integrate(end, rtol)
        self._backward = self._integrate(self.start, rtol) if self.start < initial.timestamp else None

    def _integrate(self, end: datetime, rtol: float):
        y0 = np.array([*self.initial.position_m, *self.initial.velocity_m_s])
        if np.linalg.norm(y0[:3]) <= EARTH_RADIUS:
            raise ManeuverError("Initial numerical state intersects Earth")
        def derivatives(_time, values):
            position = values[:3]
            radius = np.linalg.norm(position)
            if radius <= 0:
                raise ManeuverError("Singular orbital state")
            z = np.dot(position, self.pole)
            central = -MU_EARTH * position / radius**3
            j2 = 1.5 * J2 * MU_EARTH * EARTH_RADIUS**2 / radius**5 * (
                (5 * (z / radius)**2 - 1) * position - 2 * z * self.pole)
            return np.concatenate([values[3:], central + j2])
        def earth_intersection(_time, values):
            return np.linalg.norm(values[:3]) - EARTH_RADIUS
        earth_intersection.terminal = True
        earth_intersection.direction = -1
        duration = (end - self.initial.timestamp).total_seconds()
        try:
            solution = solve_ivp(derivatives, (0, duration), y0, method="DOP853",
                                 rtol=rtol, atol=np.array([1e-4]*3 + [1e-7]*3),
                                 max_step=120, dense_output=True, events=earth_intersection)
        except (ValueError, FloatingPointError) as error:
            raise ManeuverError(f"Numerical integration failed: {error}") from error
        if not solution.success or abs(solution.t[-1] - duration) > 1e-6:
            raise ManeuverError(f"Numerical integration did not reach endpoint: {solution.message}")
        if not np.isfinite(solution.y).all():
            raise ManeuverError("Numerical integration returned nonfinite coordinates")
        return solution.sol

    def __call__(self, timestamp: datetime) -> StateVector:
        if not self.start <= timestamp <= self.end:
            raise ValueError("Trajectory query outside the integrated interval")
        offset = (timestamp - self.initial.timestamp).total_seconds()
        interpolator = self._backward if offset < 0 else self._forward
        if interpolator is None:
            raise ValueError("Backward trajectory not available")
        values = interpolator(offset)
        return StateVector(timestamp=timestamp, position_m=tuple(values[:3]),
                           velocity_m_s=tuple(values[3:]), frame="GCRS")


class MatchedDynamics:
    """One retained reference for comparable candidate burns at different times."""

    def __init__(self, encounter: Encounter, first: OrbitalRecord, second: OrbitalRecord,
                 anchor: datetime, reference: BaselineAnalysis, rtol: float = 1e-9):
        self.encounter_id = encounter.id
        self.object_ids = (first.elements.object_id, second.elements.object_id)
        self.anchor = anchor
        self.reference = reference
        self.pole = earth_pole_gcrs(anchor)
        self.nominal = [NumericalTrajectory(teme_to_gcrs(propagate_object(orbit, anchor)),
            reference.calculated.searched_end, self.pole,
            start=reference.calculated.searched_start, rtol=rtol) for orbit in (first, second)]
        self.baseline = refine_closest_approach(*self.nominal,
            reference.calculated.searched_start, reference.calculated.searched_end)


def simulate_maneuver(encounter: Encounter, first: OrbitalRecord, second: OrbitalRecord,
                       maneuvering_object_id: str, maneuver_time: datetime,
                       delta_v_vector: tuple[float, float, float],
                       hypothetical_capability_assumed: bool = False,
                       now: datetime | None = None, rtol: float = 1e-9,
                       trajectory_samples: int = 21,
                       analysis: BaselineAnalysis | None = None,
                       shared_dynamics: MatchedDynamics | None = None) -> ManeuverSimulation:
    if not hypothetical_capability_assumed:
        raise ValueError("Explicit hypothetical maneuver capability assumption is required")
    if maneuvering_object_id not in {encounter.object_1_id, encounter.object_2_id}:
        raise ValueError("Maneuvering object must participate in the selected encounter")
    now = now or datetime.now(UTC)
    if maneuver_time.tzinfo is None or now.tzinfo is None:
        raise ValueError("Maneuver/current timestamps must be timezone-aware")
    if maneuver_time < now:
        raise ValueError("Maneuver time cannot be in the past")
    if maneuver_time >= encounter.time_of_closest_approach:
        raise ValueError("Maneuver must occur before the selected encounter")
    if (encounter.time_of_closest_approach - maneuver_time).total_seconds() > 48 * 3600:
        raise ValueError("J2-only maneuver propagation is limited to 48-hour lead times")
    delta_v = np.asarray(delta_v_vector, dtype=float)
    if delta_v.shape != (3,) or not np.isfinite(delta_v).all():
        raise ValueError("Delta-v requires three finite RTN components")
    if not 0 <= trajectory_samples <= 1001:
        raise ValueError("Trajectory sample count must be 0–1001")
    reference = analysis or analyze_encounter(encounter, first, second)
    if reference.encounter_id != encounter.id or reference.calculated.status != "COMPLETE":
        raise ManeuverError("Supported interior SGP4 reference minimum required")
    if maneuver_time >= reference.calculated.tca:
        raise ValueError("Maneuver must also precede recalculated TCA")
    start, end = reference.calculated.searched_start, reference.calculated.searched_end
    if shared_dynamics is not None:
        if (shared_dynamics.encounter_id != encounter.id or
                shared_dynamics.object_ids != (first.elements.object_id, second.elements.object_id) or
                shared_dynamics.anchor > maneuver_time):
            raise ValueError("Shared numerical reference does not match the scenario")
        nominal = shared_dynamics.nominal
        pole = shared_dynamics.pole
        initial = [orbit(maneuver_time) for orbit in nominal]
    else:
        initial = [teme_to_gcrs(propagate_object(orbit, maneuver_time)) for orbit in (first, second)]
        pole = earth_pole_gcrs(maneuver_time)
        nominal = [NumericalTrajectory(state, end, pole, start=start, rtol=rtol) for state in initial]
    selected_index = 0 if maneuvering_object_id == encounter.object_1_id else 1
    before = initial[selected_index]
    impulse = rtn_basis(before) @ delta_v
    after = before.model_copy(update={"velocity_m_s": tuple(np.array(before.velocity_m_s) + impulse)})
    modified_orbit = NumericalTrajectory(after, end, pole, rtol=rtol)
    # If burn falls inside the search window, pre-burn states are nominal, not
    # a backwards propagation of an impulse that has not yet happened.
    def modified(at):
        return nominal[selected_index](at) if at < maneuver_time else modified_orbit(at)
    corrected = list(nominal)
    corrected[selected_index] = modified
    baseline = shared_dynamics.baseline if shared_dynamics is not None else refine_closest_approach(*nominal, start, end)
    changed = refine_closest_approach(*corrected, start, end)
    samples = [start + timedelta(seconds=float(value))
               for value in np.linspace(0, (end-start).total_seconds(), trajectory_samples)]
    warnings = list(reference.warnings)
    if baseline.status != "COMPLETE" or changed.status != "COMPLETE":
        warnings.append("Numerical minimum is at a search boundary; clearance is local-window-only and not an established interior TCA.")
    return ManeuverSimulation(
        encounter_id=encounter.id, maneuvering_object_id=maneuvering_object_id,
        maneuver_time=maneuver_time, delta_v_rtn_m_s=tuple(delta_v),
        delta_v_gcrs_m_s=tuple(impulse), delta_v_m_s=float(np.linalg.norm(delta_v)),
        state_before_maneuver=before, state_after_maneuver=after,
        matched_baseline=baseline, modified=changed,
        change_in_miss_distance_m=changed.miss_distance_m-baseline.miss_distance_m,
        change_in_tca_seconds=(changed.tca-baseline.tca).total_seconds(),
        baseline_trajectory=[nominal[selected_index](at) for at in samples],
        modified_trajectory=[modified(at) for at in samples], sgp4_reference=reference,
        model_assumptions=list(MODEL_ASSUMPTIONS), warnings=warnings,
    )
