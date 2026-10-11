"""Model-consistent differential trajectories for secondary screening.

delta_GCRS = numerical_maneuvered_GCRS - numerical_zero_burn_GCRS
modified_GCRS = nominal_SGP4_GCRS + delta_GCRS

Both position and velocity are transformed back into TEME for comparison with
the batched SGP4 catalog. This is an approximation, not precision orbit fitting.
"""

from datetime import datetime

from astropy.time import Time
import numpy as np
from sgp4.api import SGP4_ERRORS

from app.models.orbital import OrbitalRecord
from app.models.screening import ScreeningWindow
from app.physics.frames import earth_pole_gcrs, rtn_basis, teme_to_gcrs, transform_states
from app.physics.maneuvers import NumericalTrajectory
from app.physics.propagation import PropagationError, StateVector, initialized_satellite, propagate_object


def nominal_samples(orbit: OrbitalRecord, timestamps: list[datetime]) -> list[StateVector]:
    if not timestamps:
        return []
    if any(timestamp.tzinfo is None for timestamp in timestamps):
        raise ValueError("SGP4 samples require aware timestamps")
    times = Time(timestamps).utc
    errors, positions, velocities = initialized_satellite(orbit.elements).sgp4_array(times.jd1, times.jd2)
    if np.any(errors):
        first_error = int(errors[errors != 0][0])
        raise PropagationError(f"SGP4 batch error: {SGP4_ERRORS.get(first_error, first_error)}")
    if not np.isfinite(positions).all() or not np.isfinite(velocities).all():
        raise PropagationError("Nonfinite SGP4 batch states")
    return [StateVector(timestamp=at, frame="TEME", position_m=tuple(position*1000),
                        velocity_m_s=tuple(velocity*1000))
            for at, position, velocity in zip(timestamps, positions, velocities)]


class DifferentialTrajectory:
    frame = "TEME"
    model = "Nominal SGP4 + matched GCRS numerical impulse differential / TEME"

    def __init__(self, orbit: OrbitalRecord, window: ScreeningWindow,
                 delta_v_rtn_m_s: tuple[float, float, float],
                 reference_epoch: datetime | None = None, max_epoch_distance_days=7,
                 rtol=1e-9):
        self.orbit, self.window = orbit, window
        self.primary_object_id = orbit.elements.object_id
        self.burn_time = window.start
        self.reference_epoch = reference_epoch or self.burn_time
        if self.reference_epoch.tzinfo is None or self.reference_epoch > self.burn_time:
            raise ValueError("Numerical reference must be aware and no later than the burn")
        if (window.end-self.reference_epoch).total_seconds() > 48*3600:
            raise ValueError("Differential numerical propagation is limited to 48 hours")
        for endpoint in (self.reference_epoch, window.end):
            if abs((endpoint-orbit.elements.epoch).total_seconds()) > max_epoch_distance_days*86400:
                raise ValueError("Primary orbital epoch is outside the screening validity limit")
        delta = np.asarray(delta_v_rtn_m_s, dtype=float)
        if delta.shape != (3,) or not np.isfinite(delta).all():
            raise ValueError("Impulse requires three finite RTN components")
        self.delta_v_rtn_m_s = tuple(delta)
        self.pole = earth_pole_gcrs(self.reference_epoch)
        initial = teme_to_gcrs(propagate_object(orbit, self.reference_epoch))
        self.zero = NumericalTrajectory(initial, window.end, self.pole, rtol=rtol)
        self.before = self.zero(self.burn_time)
        impulse = rtn_basis(self.before) @ delta
        self.after = self.before.model_copy(update={
            "velocity_m_s":tuple(np.asarray(self.before.velocity_m_s)+impulse)})
        self.is_zero_burn = bool(np.all(delta == 0))
        self.burned = self.zero if self.is_zero_burn else NumericalTrajectory(
            self.after, window.end, self.pole, rtol=rtol)

    def _validate_times(self, timestamps):
        if any(timestamp.tzinfo is None or not self.window.start <= timestamp <= self.window.end
               for timestamp in timestamps):
            raise ValueError("Differential query outside the screening interval")

    def samples(self, timestamps: list[datetime], modified=True) -> list[StateVector]:
        self._validate_times(timestamps)
        nominal = nominal_samples(self.orbit, timestamps)
        if not modified or self.is_zero_burn or not timestamps:
            return nominal
        gcrs = transform_states(nominal, "GCRS")
        corrected = []
        for at, state in zip(timestamps, gcrs):
            zero, burned = self.zero(at), self.burned(at)
            corrected.append(state.model_copy(update={
                "position_m":tuple(np.asarray(state.position_m)+np.subtract(burned.position_m,zero.position_m)),
                "velocity_m_s":tuple(np.asarray(state.velocity_m_s)+np.subtract(burned.velocity_m_s,zero.velocity_m_s)),
            }))
        return transform_states(corrected, "TEME")

    def nominal(self, timestamp: datetime) -> StateVector:
        self._validate_times([timestamp])
        return propagate_object(self.orbit, timestamp)

    def modified(self, timestamp: datetime) -> StateVector:
        self._validate_times([timestamp])
        if self.is_zero_burn:
            return self.nominal(timestamp)
        # Match the scalar nominal time conversion exactly, rather than mixing
        # a rounded scalar Julian date with the batched two-part representation.
        nominal = teme_to_gcrs(self.nominal(timestamp))
        zero, burned = self.zero(timestamp), self.burned(timestamp)
        corrected = nominal.model_copy(update={
            "position_m":tuple(np.asarray(nominal.position_m)+np.subtract(burned.position_m,zero.position_m)),
            "velocity_m_s":tuple(np.asarray(nominal.velocity_m_s)+np.subtract(burned.velocity_m_s,zero.velocity_m_s)),
        })
        return transform_states([corrected], "TEME")[0]
