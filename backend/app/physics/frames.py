"""Astropy TEME/GCRS transformations with a retained, offline IERS table."""

from datetime import datetime

import astropy.units as u
from astropy.coordinates import CartesianDifferential, CartesianRepresentation, GCRS, ITRS, TEME
from astropy.time import Time
from astropy.utils import iers
import numpy as np

from app.physics.propagation import StateVector

# Never silently download time-varying tables while computing or optimizing.
# astropy-iers-data is an installed dependency; predictive/degraded accuracy is
# an explicitly documented model limitation, not an operational precision claim.
iers.conf.auto_download = False
iers.conf.iers_degraded_accuracy = "warn"


def teme_to_gcrs(state: StateVector) -> StateVector:
    if state.frame != "TEME":
        raise ValueError("TEME input required for this transformation")
    at = Time(state.timestamp)
    representation = CartesianRepresentation(
        np.asarray(state.position_m) * u.m,
        differentials=CartesianDifferential(np.asarray(state.velocity_m_s) * u.m / u.s),
    )
    transformed = TEME(representation, obstime=at).transform_to(GCRS(obstime=at))
    return StateVector(timestamp=state.timestamp, frame="GCRS",
                       position_m=tuple(transformed.cartesian.xyz.to_value(u.m)),
                       velocity_m_s=tuple(transformed.velocity.d_xyz.to_value(u.m / u.s)))


def earth_pole_gcrs(timestamp: datetime) -> np.ndarray:
    at = Time(timestamp)
    pole = ITRS(CartesianRepresentation([0, 0, 1] * u.m), obstime=at).transform_to(GCRS(obstime=at))
    vector = pole.cartesian.xyz.to_value(u.m)
    return vector / np.linalg.norm(vector)


def rtn_basis(state: StateVector) -> np.ndarray:
    if state.frame != "GCRS":
        raise ValueError("RTN basis for numerical dynamics requires GCRS input")
    position, velocity = np.array(state.position_m), np.array(state.velocity_m_s)
    normal = np.cross(position, velocity)
    if np.linalg.norm(position) <= 0 or np.linalg.norm(normal) <= 0:
        raise ValueError("Degenerate state cannot define the RTN maneuver basis")
    radial = position / np.linalg.norm(position)
    normal = normal / np.linalg.norm(normal)
    transverse = np.cross(normal, radial)
    return np.column_stack([radial, transverse, normal])
