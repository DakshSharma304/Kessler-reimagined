import math
import numpy as np
import pytest
from scipy.stats import ncx2
from scipy.special import gammainc, gammaln, logsumexp
from app.probability.engine import calculate_collision_probability as calculate


def isotropic_series(miss, radius, sigma, terms=256):
    """Independent noncentral chi-square Poisson/gamma analytical expansion.

    SciPy 1.15.3 ncx2.cdf loses ~2.8e-7 relative accuracy at the tested 1e-73
    tail; the positive-term expansion avoids that inaccurate test oracle.
    """
    if miss == 0:
        return -math.expm1(-radius**2 / (2*sigma**2))
    poisson_mean = miss**2 / (2*sigma**2)
    disk = radius**2 / (2*sigma**2)
    logs = [-poisson_mean + k*math.log(poisson_mean) - gammaln(k+1) + math.log(gammainc(k+1, disk))
            for k in range(terms) if gammainc(k+1, disk) > 0]
    return math.exp(float(logsumexp(logs)))


@pytest.mark.parametrize("miss,radius,sigma", [(0, 1, 10), (1e-10, 2, 3), (5, 1, 10), (20, 2, 1), (40, 1, 2), (0, 100, 1)])
def test_isotropic_analytical_zero_large_miss_and_rare_probabilities(miss, radius, sigma):
    c = .5 * sigma**2 * np.eye(3)
    result = calculate([miss, 0, 0], [0, 0, 1000], c, c, radius)
    assert result.status == "CALCULATED", result
    assert result.numerical_status == "CONVERGED"
    expected = isotropic_series(miss, radius, sigma)
    assert expected == pytest.approx(isotropic_series(miss, radius, sigma, terms=128), rel=1e-13, abs=0)
    if expected > 1e-20:
        assert expected == pytest.approx(ncx2.cdf(radius**2/sigma**2, 2, miss**2/sigma**2), rel=2e-9)
    assert result.calculated_pc == pytest.approx(expected, rel=2e-9, abs=0)
    assert 0 <= result.calculated_pc <= 1
    assert result.estimated_absolute_error <= result.calculated_pc * 1e-9


def test_tiny_probability_not_rounded_to_zero():
    c = .5 * np.eye(3)
    r = calculate([20, 0, 0], [0, 0, 1000], c, c, 1)
    assert 0 < r.calculated_pc < 1e-75
    assert r.calculated_pc == pytest.approx(isotropic_series(20, 1, 1), rel=2e-9, abs=0)


def test_rotation_consistency_convergence_and_determinism():
    c1 = np.array([[4, .8, 0], [.8, 1, .1], [0, .1, 3]])
    c2 = 2 * np.eye(3)
    r = np.array([4, 8, 2.])
    v = np.array([5, 2, 10.])
    rotation, _ = np.linalg.qr(np.array([[1., 2, 3], [4, 2, -1], [5, 1, 1]]))
    a = calculate(r, v, c1, c2, 1, relative_tolerance=1e-8)
    b = calculate(rotation@r, rotation@v, rotation@c1@rotation.T, rotation@c2@rotation.T, 1, relative_tolerance=1e-11)
    assert a.status == b.status == "CALCULATED"
    assert a.calculated_pc == pytest.approx(b.calculated_pc, rel=2e-10)
    assert a == calculate(r, v, c1, c2, 1, relative_tolerance=1e-8)


@pytest.mark.parametrize("radius", [None, 0, -1, np.nan, np.inf])
def test_missing_or_invalid_radius_rejected(radius):
    with pytest.raises(ValueError, match="radius"):
        calculate([0, 0, 0], [0, 0, 1], np.eye(3), np.eye(3), radius)


@pytest.mark.parametrize("c", [None, np.diag([1, 1, -1]), np.ones((2, 2)), np.full((3, 3), np.nan)])
def test_missing_or_invalid_covariance_rejected(c):
    with pytest.raises(ValueError, match="[Cc]ovariance"):
        calculate([0, 0, 0], [0, 0, 1], c, np.eye(3), 1)


def test_degenerate_model_explicitly_unsupported_without_remediation():
    for c, v in [(np.diag([0, 1, 1]), [0, 0, 1]), (np.diag([1e-15, 1, 1]), [0, 0, 1]), (np.eye(3), [0, 0, 0])]:
        result = calculate([1, 0, 0], v, c, c, 1)
        assert result.status == "UNSUPPORTED_MODEL"
        assert result.calculated_pc is None
    result = calculate([1, 0, 0], [0, 0, 1], np.eye(3), np.eye(3), 1, model_applicable=False)
    assert result.status == "UNSUPPORTED_MODEL"
    assert any("inapplicable" in w for w in result.warnings)


def test_known_correlation_requires_cross_covariance():
    unsupported = calculate([0, 0, 0], [0, 0, 1], np.eye(3), np.eye(3), 1, correlation="CORRELATED")
    assert unsupported.status == "UNSUPPORTED_MODEL"
    supplied = calculate([0, 0, 0], [0, 0, 1], np.eye(3), np.eye(3), 1, correlation="CORRELATED", cross_covariance=.5 * np.eye(3))
    assert supplied.calculated_pc == pytest.approx(-math.expm1(-.5), rel=1e-9)
    assert any("no independence" in a for a in supplied.assumptions)


def test_numerical_underflow_disclosed():
    r = calculate([1000, 0, 0], [0, 0, 1], np.eye(3), np.eye(3), 1)
    assert r.calculated_pc == 0
    assert r.numerical_status == "UNDERFLOW"
    assert any("underflow" in w for w in r.warnings)
