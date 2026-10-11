from datetime import datetime, timezone, timedelta
import numpy as np
import pytest
from app.physics.propagation import StateVector
from app.probability.cdm import load_reference, reference_cases
from app.probability.covariance import (validate_covariance, rotate_covariance, object_rtn_basis,
    position_rotation, covariance_in_frame, relative_covariance, encounter_plane_basis, project_encounter)

EPOCH = datetime(2026, 10, 11, tzinfo=timezone.utc)
ROTATION = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
COV = np.array([[2., .2, .1], [.2, 3, .3], [.1, .3, 4]])


def test_identity_orthogonal_roundtrip_symmetry_analytical():
    np.testing.assert_array_equal(rotate_covariance(COV, np.eye(3)), COV)
    transformed = rotate_covariance(COV, ROTATION)
    np.testing.assert_allclose(transformed, [[3, -.2, -.3], [-.2, 2, .1], [-.3, .1, 4]])
    np.testing.assert_allclose(rotate_covariance(transformed, ROTATION.T), COV)
    np.testing.assert_array_equal(transformed, transformed.T)
    np.testing.assert_allclose(np.linalg.eigvalsh(transformed), np.linalg.eigvalsh(COV))


@pytest.mark.parametrize("matrix", [None, [[1, 0], [0, 1]], np.diag([1, 1, -1e-8]),
    [[1, .1, 0], [0, 1, 0], [0, 0, 1]], np.full((3, 3), np.nan), np.full((3, 3), np.inf)])
def test_invalid_covariance_rejected(matrix):
    with pytest.raises(ValueError):
        validate_covariance(matrix)


def test_psd_and_invalid_rotation():
    np.testing.assert_array_equal(validate_covariance(np.diag([0, 1, 2])), np.diag([0, 1, 2]))
    np.testing.assert_array_equal(validate_covariance(np.zeros((3, 3))), np.zeros((3, 3)))
    with pytest.raises(ValueError, match="orthogonal"):
        rotate_covariance(COV, 2 * np.eye(3))


def test_relative_independent_and_correlated_examples():
    np.testing.assert_allclose(relative_covariance(COV, COV), 2 * COV)
    np.testing.assert_allclose(relative_covariance(np.eye(3), np.eye(3), cross_covariance=.5 * np.eye(3), correlation="CORRELATED"), np.eye(3))
    with pytest.raises(ValueError, match="cross-covariance"):
        relative_covariance(COV, COV, correlation="CORRELATED")
    with pytest.raises(ValueError, match="semidefinite"):
        relative_covariance(np.eye(3), np.eye(3), cross_covariance=2 * np.eye(3))
    with pytest.raises(ValueError, match="contradicts"):
        relative_covariance(COV, COV, cross_covariance=np.eye(3), correlation="INDEPENDENT")


@pytest.mark.parametrize("velocity", [(0, 0, 10), (5, 7, -3), (10, 0, 0)])
def test_plane_basis_and_projection(velocity):
    b = encounter_plane_basis(velocity)
    np.testing.assert_allclose(b.T @ b, np.eye(2), atol=1e-15)
    np.testing.assert_allclose(b.T @ velocity, np.zeros(2), atol=1e-14)
    _, miss, cov = project_encounter([2, 4, 6], velocity, 3 * np.eye(3))
    np.testing.assert_allclose(cov, 3 * np.eye(2), atol=1e-14)
    np.testing.assert_allclose(b @ miss, np.array([2, 4, 6]) - np.dot([2, 4, 6], velocity) * np.array(velocity) / np.dot(velocity, velocity))


def test_known_projection_and_degeneracy():
    b, miss, cov = project_encounter([2, 4, 6], [0, 0, 10], np.diag([2, 3, 4]))
    np.testing.assert_allclose(miss, [4, -2])
    np.testing.assert_allclose(cov, np.diag([3, 2]))
    with pytest.raises(ValueError, match="relative velocity"):
        encounter_plane_basis([0, 0, 0])


def test_each_object_uses_own_rtn_basis_and_common_epoch():
    first = StateVector(timestamp=EPOCH, frame="GCRS", position_m=(7e6, 0, 0), velocity_m_s=(0, 7500, 0))
    second = StateVector(timestamp=EPOCH, frame="GCRS", position_m=(0, 7e6, 0), velocity_m_s=(-7500, 0, 0))
    c = np.diag([1, 2, 3])
    c1 = covariance_in_frame(c, "RTN", first, "GCRS", epoch=EPOCH)
    c2 = covariance_in_frame(c, "RIC", second, "GCRS", epoch=EPOCH)
    np.testing.assert_allclose(c1, np.diag([1, 2, 3]))
    np.testing.assert_allclose(c2, np.diag([2, 1, 3]))
    np.testing.assert_allclose(relative_covariance(c1, c2), np.diag([3, 3, 6]))
    with pytest.raises(ValueError, match="epoch"):
        covariance_in_frame(c, "RTN", second, "GCRS", epoch=EPOCH + timedelta(seconds=1))


def test_actual_teme_gcrs_covariance_roundtrip_without_relabel():
    r = position_rotation("TEME", "GCRS", EPOCH)
    assert np.linalg.norm(r - np.eye(3)) > .001
    np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-14)
    back = position_rotation("GCRS", "TEME", EPOCH)
    np.testing.assert_allclose(rotate_covariance(rotate_covariance(COV, r), back), COV, atol=2e-13)
    with pytest.raises(ValueError, match="not relabeled"):
        position_rotation("EME2000", "GCRS", EPOCH)


@pytest.mark.parametrize("case", reference_cases())
def test_actual_nasa_individual_rtn_transform(case):
    e = load_reference(case)
    for obj in (e.primary, e.secondary):
        basis = object_rtn_basis(obj.state)
        np.testing.assert_allclose(basis.T @ basis, np.eye(3), atol=1e-14)
        inertial = covariance_in_frame(obj.covariance_m2, "RTN", obj.state, "EME2000", epoch=e.tca)
        np.testing.assert_allclose(rotate_covariance(inertial, basis.T), obj.covariance_m2, rtol=1e-10, atol=1e-9)
