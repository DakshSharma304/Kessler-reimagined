"""Library SGP4 propagation in TEME, normalized to SI without frame relabeling."""

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Literal

import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict
from sgp4.api import Satrec, SGP4_ERRORS, jday

from app.models.orbital import GPElements, OrbitalRecord


class PropagationError(RuntimeError):
    pass


class StateVector(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    timestamp: AwareDatetime
    position_m: tuple[float, float, float]
    velocity_m_s: tuple[float, float, float]
    frame: Literal["TEME", "GCRS"]
    position_units: Literal["m"] = "m"
    velocity_units: Literal["m/s"] = "m/s"
    propagation_status: Literal["OK"] = "OK"


@lru_cache(maxsize=256)
def initialized_satellite(elements: GPElements) -> Satrec:
    return elements.initialize_sgp4()


def propagate_object(orbit: OrbitalRecord | GPElements | Satrec,
                     timestamp: datetime) -> StateVector:
    if timestamp.tzinfo is None:
        raise ValueError("Propagation timestamp must be timezone-aware")
    timestamp = timestamp.astimezone(UTC)
    if isinstance(orbit, OrbitalRecord):
        satellite = initialized_satellite(orbit.elements)
    elif isinstance(orbit, GPElements):
        satellite = initialized_satellite(orbit)
    elif isinstance(orbit, Satrec):
        satellite = orbit
    else:
        raise TypeError("Propagation requires validated GP elements or an initialized Satrec")
    jd, fraction = jday(timestamp.year, timestamp.month, timestamp.day, timestamp.hour,
                        timestamp.minute, timestamp.second + timestamp.microsecond / 1e6)
    error, position, velocity = satellite.sgp4(jd, fraction)
    if error:
        raise PropagationError(f"SGP4 error {error}: {SGP4_ERRORS.get(error, 'unknown error')}")
    values = np.array([*position, *velocity]) * 1000
    if not np.isfinite(values).all():
        raise PropagationError("SGP4 returned nonfinite state coordinates")
    return StateVector(timestamp=timestamp, position_m=tuple(values[:3]),
                       velocity_m_s=tuple(values[3:]), frame="TEME")


def propagate_trajectory(orbit: OrbitalRecord | GPElements | Satrec,
                         start_time: datetime, end_time: datetime,
                         sample_count: int) -> list[StateVector]:
    if start_time.tzinfo is None or end_time.tzinfo is None:
        raise ValueError("Trajectory times must be timezone-aware")
    if end_time <= start_time or not 2 <= sample_count <= 100000:
        raise ValueError("Trajectory requires increasing times and 2–100000 samples")
    seconds = (end_time - start_time).total_seconds()
    return [propagate_object(orbit, start_time + timedelta(seconds=float(offset)))
            for offset in np.linspace(0, seconds, sample_count)]
