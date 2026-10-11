"""Deterministic 2D Gaussian disk Pc, conditional on the rectilinear model.

Diagonalize the projected covariance, integrate one normal analytically and
the other by adaptive QUADPACK quadrature. Log-CDF differences protect rare
tail probabilities. No Monte Carlo, reference answers or covariance repair.
"""
import math
from typing import Literal
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.integrate import quad
from scipy.special import log_ndtr, ndtr

from app.probability.covariance import UnsupportedCovariance, project_encounter, relative_covariance


class ProbabilityResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    status: Literal["CALCULATED", "UNSUPPORTED_MODEL", "NUMERICAL_FAILURE"]
    calculated_pc: float | None = Field(default=None, ge=0, le=1)
    encounter_plane_miss_m: tuple[float, float] | None = None
    projected_covariance_m2: tuple[tuple[float, float], tuple[float, float]] | None = None
    combined_hard_body_radius_m: float
    numerical_method: str = "2D Gaussian disk: eigenbasis, stable normal-CDF difference, adaptive QUADPACK"
    numerical_status: Literal["CONVERGED", "UNDERFLOW", "UNSUPPORTED", "FAILED"]
    estimated_absolute_error: float | None = None
    requested_relative_tolerance: float
    projected_condition_number: float | None = None
    integrand_evaluations: int = 0
    assumptions: list[str]
    warnings: list[str]


def _normal_interval(lo: float, hi: float) -> float:
    if lo >= hi:
        return 0.0
    if hi <= 0:
        high, low = float(log_ndtr(hi)), float(log_ndtr(lo))
        return math.exp(high) * -math.expm1(min(0.0, low - high))
    if lo >= 0:
        return _normal_interval(-hi, -lo)
    return float(ndtr(hi) - ndtr(lo))


def calculate_collision_probability(relative_position, relative_velocity,
        covariance_primary, covariance_secondary, hard_body_radius, *,
        cross_covariance=None, correlation: str = "UNSPECIFIED",
        relative_tolerance: float = 1e-9, model_applicable: bool = True) -> ProbabilityResult:
    """All input geometry/covariances share one inertial frame and epoch.

    SI only: m, m/s, m², combined radius m. Position uncertainties are Gaussian
    and stationary during a short, rectilinear encounter. Instantaneous states
    alone cannot certify these physical assumptions; callers must set
    model_applicable=False for known long-duration/curved encounters. No
    velocity uncertainty or operational covariance realism is inferred.
    """
    if hard_body_radius is None or not math.isfinite(hard_body_radius) or hard_body_radius <= 0:
        raise ValueError("A finite positive combined hard-body radius in m is required")
    if not math.isfinite(relative_tolerance) or not 1e-12 <= relative_tolerance <= 1e-4:
        raise ValueError("Relative integration tolerance must be between 1e-12 and 1e-4")
    assumptions = ["Short rectilinear relative motion; stationary Gaussian position uncertainties.",
        "Collision disk radius is the explicitly supplied combined hard-body radius.",
        "Covariances and relative states share one inertial frame, epoch and SI units.",
        "Velocity uncertainty, covariance evolution, shape/orientation and non-Gaussian errors are not modeled."]
    warnings = ["Numerical error estimates are not physical uncertainty bounds or an operational safety guarantee.",
        "Estimated absolute error covers quadrature only, not covariance/frame roundoff or input uncertainty.",
        "Instantaneous states cannot establish rectilinear-model applicability or covariance realism."]
    if cross_covariance is None and correlation != "CORRELATED":
        assumptions.append("Object position errors assumed independent; cross-covariance unavailable or explicitly zero.")
    else:
        assumptions.append("Supplied common-frame position cross-covariance used; no independence assumption.")
    values = dict(combined_hard_body_radius_m=hard_body_radius,
                  requested_relative_tolerance=relative_tolerance, assumptions=assumptions, warnings=warnings)
    try:
        covariance = relative_covariance(covariance_primary, covariance_secondary,
            cross_covariance=cross_covariance, correlation=correlation)
        _, miss, projected = project_encounter(relative_position, relative_velocity, covariance)
        values.update(encounter_plane_miss_m=tuple(miss), projected_covariance_m2=tuple(map(tuple, projected)))
        if not model_applicable:
            raise UnsupportedCovariance("Known long-duration/curved encounter: 2D rectilinear model is inapplicable")
        eigenvalues, eigenvectors = np.linalg.eigh(projected)
        if eigenvalues[0] <= 0:
            raise UnsupportedCovariance("Singular encounter-plane covariance: 2D density is undefined; no regularization")
        condition = float(eigenvalues[-1] / eigenvalues[0])
        values["projected_condition_number"] = condition
        if condition > 1e12:
            raise UnsupportedCovariance("Near-degenerate projected covariance condition number exceeds 1e12; no eigenvalue clipping")
    except UnsupportedCovariance as error:
        warnings.append(str(error))
        return ProbabilityResult(status="UNSUPPORTED_MODEL", numerical_status="UNSUPPORTED", **values)
    # Integrate along the larger-variance axis; disk is rotation invariant.
    means = eigenvectors.T @ miss
    mx, my = float(means[1]), float(means[0])
    sx, sy = float(math.sqrt(eigenvalues[1])), float(math.sqrt(eigenvalues[0]))
    radius = float(hard_body_radius)
    lo, hi = (-radius - mx) / sx, (radius - mx) / sx
    if not np.isfinite([lo, hi, mx, my, sx, sy]).all() or lo >= hi:
        warnings.append("Input scales exceed floating-point integration resolution")
        return ProbabilityResult(status="UNSUPPORTED_MODEL", numerical_status="UNSUPPORTED", **values)

    def integrand(t):
        x = mx + sx * t
        # Product form avoids cancellation in radius²−x² near the disk edge.
        height = math.sqrt(max(0.0, (radius - x) * (radius + x)))
        mass = _normal_interval((-height - my) / sy, (height - my) / sy)
        return math.exp(-.5 * t * t) / math.sqrt(2 * math.pi) * mass

    # Split around normal mass so a very wide interval cannot miss a narrow peak.
    points = [t for t in (-16, -8, -4, -1, 0, 1, 4, 8, 16) if lo < t < hi]
    output = quad(integrand, lo, hi, points=points, epsabs=1e-300,
                  epsrel=relative_tolerance, limit=500, full_output=1)
    pc, error, info = output[:3]
    values.update(estimated_absolute_error=error, integrand_evaluations=info["neval"])
    if len(output) > 3 or not np.isfinite([pc, error]).all() or pc < -error or pc > 1 + error:
        warnings.append(str(output[3]) if len(output) > 3 else "Integration failed probability bounds/finite checks")
        return ProbabilityResult(status="NUMERICAL_FAILURE", numerical_status="FAILED", **values)
    if pc == 0:
        warnings.append("Probability below representable numerical range; reported zero is numerical underflow, not established impossibility.")
        return ProbabilityResult(status="CALCULATED", calculated_pc=0, numerical_status="UNDERFLOW", **values)
    if error > pc * relative_tolerance:
        warnings.append("Requested relative numerical accuracy was not achieved")
        return ProbabilityResult(status="NUMERICAL_FAILURE", numerical_status="FAILED", **values)
    if not 0 <= pc <= 1:
        warnings.append("Roundoff at a probability bound rounded within the reported quadrature error")
    return ProbabilityResult(status="CALCULATED", calculated_pc=min(1., max(0., pc)), numerical_status="CONVERGED", **values)
