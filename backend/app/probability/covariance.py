"""Position-only covariance mathematics in SI, without eigenvalue clipping."""
from datetime import datetime
import numpy as np

from app.physics.frames import rtn_basis, transform_states
from app.physics.propagation import StateVector


class UnsupportedCovariance(ValueError):
    """Information insufficient for a supported uncertainty model."""


def validate_covariance(matrix, size: int = 3) -> np.ndarray:
    if matrix is None:
        raise ValueError("Position covariance is required")
    value = np.asarray(matrix, dtype=float)
    if value.shape != (size, size) or not np.isfinite(value).all():
        raise ValueError(f"Covariance must be a finite {size}x{size} matrix in m²")
    scale = max(float(np.linalg.norm(value, ord=2)), np.finfo(float).tiny)
    if not np.isfinite(scale):
        raise ValueError("Covariance scales exceed numerical representation limits")
    tolerance = 64 * np.finfo(float).eps * scale
    if np.max(np.abs(value - value.T)) > tolerance:
        raise ValueError("Covariance must be symmetric")
    # Only symmetrize floating-point roundoff, never repair negative eigenvalues.
    value = (value + value.T) / 2
    if np.linalg.eigvalsh(value)[0] < -tolerance:
        raise ValueError("Covariance must be positive semidefinite; no remediation applied")
    return value


def rotate_covariance(covariance, rotation) -> np.ndarray:
    value = validate_covariance(covariance)
    rotation = np.asarray(rotation, dtype=float)
    if rotation.shape != (3, 3) or not np.isfinite(rotation).all() or not np.allclose(
            rotation.T @ rotation, np.eye(3), rtol=0, atol=1e-12):
        raise ValueError("Covariance transformation requires an orthogonal 3x3 rotation")
    return validate_covariance(rotation @ value @ rotation.T)


def object_rtn_basis(state) -> np.ndarray:
    """Each object's own R, T, N columns, in its actual Cartesian frame."""
    if state.frame not in {"GCRS", "TEME", "EME2000", "GCRF"}:
        raise UnsupportedCovariance(f"Unsupported state frame {state.frame}")
    r = np.asarray(state.position_m, dtype=float)
    v = np.asarray(state.velocity_m_s, dtype=float)
    h = np.cross(r, v)
    if not np.isfinite([r, v]).all() or np.linalg.norm(r) == 0 or np.linalg.norm(h) <= 1e-12 * np.linalg.norm(r) * np.linalg.norm(v):
        raise UnsupportedCovariance("Degenerate object state cannot define RTN")
    if state.frame == "GCRS":
        return rtn_basis(state)
    radial, normal = r / np.linalg.norm(r), h / np.linalg.norm(h)
    return np.column_stack((radial, np.cross(normal, radial), normal))


def position_rotation(source: str, target: str, epoch: datetime) -> np.ndarray:
    if epoch.tzinfo is None:
        raise ValueError("Covariance transformations require an aware UTC epoch")
    if source == target and source in {"TEME", "GCRS", "EME2000", "GCRF"}:
        return np.eye(3)
    if {source, target} != {"TEME", "GCRS"}:
        raise UnsupportedCovariance(f"Unsupported covariance conversion {source} to {target}; frames are not relabeled")
    axes = [StateVector(timestamp=epoch, frame=source, position_m=tuple(axis), velocity_m_s=(0, 0, 0)) for axis in np.eye(3)]
    converted = transform_states(axes, target)
    return np.column_stack([s.position_m for s in converted])


def covariance_in_frame(covariance, covariance_frame: str, state, target: str, *, epoch: datetime | None = None) -> np.ndarray:
    if epoch is not None and epoch != state.timestamp:
        raise UnsupportedCovariance("Covariance epoch does not match object state; propagation is unavailable")
    value = validate_covariance(covariance)
    source = covariance_frame
    if source in {"RTN", "RIC"}:
        value = rotate_covariance(value, object_rtn_basis(state))
        source = state.frame
    return rotate_covariance(value, position_rotation(source, target, state.timestamp))


def relative_covariance(primary, secondary, *, cross_covariance=None, correlation: str = "UNSPECIFIED") -> np.ndarray:
    """Inputs must already be expressed in one common inertial frame and epoch.

    Unspecified correlation requires the disclosed independence assumption.
    Known correlations cannot be silently discarded. C12 = Cov(primary,secondary).
    """
    p1, p2 = validate_covariance(primary), validate_covariance(secondary)
    if correlation not in {"UNSPECIFIED", "INDEPENDENT", "CORRELATED"}:
        raise ValueError("Unknown correlation metadata")
    if correlation == "CORRELATED" and cross_covariance is None:
        raise UnsupportedCovariance("Known correlation requires common-frame cross-covariance")
    if cross_covariance is None:
        return validate_covariance(p1 + p2)
    cross = np.asarray(cross_covariance, dtype=float)
    if cross.shape != (3, 3) or not np.isfinite(cross).all():
        raise ValueError("Cross-covariance must be a finite common-frame 3x3 matrix")
    if correlation == "INDEPENDENT" and np.any(cross != 0):
        raise ValueError("Nonzero cross-covariance contradicts independence metadata")
    validate_covariance(np.block([[p1, cross], [cross.T, p2]]), size=6)
    return validate_covariance(p1 + p2 - cross - cross.T)


def encounter_plane_basis(relative_velocity) -> np.ndarray:
    velocity = np.asarray(relative_velocity, dtype=float)
    if velocity.shape != (3,) or not np.isfinite(velocity).all():
        raise ValueError("Relative velocity must be a finite three-vector in m/s")
    speed = np.linalg.norm(velocity)
    if speed <= 1e-12:
        raise UnsupportedCovariance("Zero/near-zero relative velocity cannot define the 2D encounter plane")
    normal = velocity / speed
    axis = np.eye(3)[np.argmin(np.abs(normal))]
    first = np.cross(normal, axis)
    first /= np.linalg.norm(first)
    return np.column_stack((first, np.cross(normal, first)))


def project_encounter(relative_position, relative_velocity, covariance):
    position = np.asarray(relative_position, dtype=float)
    if position.shape != (3,) or not np.isfinite(position).all():
        raise ValueError("Relative position must be a finite three-vector in m")
    basis = encounter_plane_basis(relative_velocity)
    projected = basis.T @ validate_covariance(covariance) @ basis
    return basis, basis.T @ position, validate_covariance(projected, size=2)
