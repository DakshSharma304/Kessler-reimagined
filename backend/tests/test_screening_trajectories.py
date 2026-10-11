"""Checkpoint 4 scientific invariants using actual SGP4 and J2 integration."""

from datetime import timedelta

import numpy as np
import pytest

from app.models.screening import ScreeningWindow
from app.physics.frames import rtn_basis, teme_to_gcrs, transform_states
from app.physics.propagation import propagate_object
from app.physics.screening_trajectories import DifferentialTrajectory, nominal_samples
from test_encounters import actual_case


def trajectory(delta=(0,.2,0), **kwargs):
    encounter, orbit, _ = actual_case()
    return DifferentialTrajectory(orbit, ScreeningWindow(
        start=encounter.time_of_closest_approach-timedelta(hours=2),
        end=encounter.time_of_closest_approach+timedelta(hours=6)), delta, **kwargs)


def test_zero_burn_is_nominal_even_when_numerical_model_drifts():
    curve = trajectory((0,0,0))
    at = curve.window.end
    assert curve.nominal(at) == curve.modified(at)
    assert curve.samples([curve.window.start,at], False) == curve.samples([curve.window.start,at], True)
    numeric = curve.zero(at)
    sgp4 = teme_to_gcrs(curve.nominal(at))
    assert np.linalg.norm(np.subtract(numeric.position_m,sgp4.position_m)) > 1


def test_nonzero_signs_timestamp_frames_units_and_reproducibility():
    positive, negative = trajectory(), trajectory((0,-.2,0))
    at = positive.window.end
    nominal = positive.nominal(at)
    modified = positive.modified(at)
    assert nominal.timestamp == modified.timestamp == at
    assert nominal.frame == modified.frame == "TEME"
    assert modified.position_units == "m" and modified.velocity_units == "m/s"
    assert np.linalg.norm(np.subtract(modified.position_m,nominal.position_m)) > 1
    assert np.linalg.norm(np.subtract(modified.position_m,negative.modified(at).position_m)) > 1
    assert trajectory().modified(at) == modified


def test_position_continuity_velocity_impulse_and_frame_roundtrip():
    curve = trajectory()
    before = teme_to_gcrs(curve.nominal(curve.burn_time))
    after = teme_to_gcrs(curve.modified(curve.burn_time))
    np.testing.assert_allclose(after.position_m, before.position_m, atol=1e-6, rtol=0)
    expected = rtn_basis(curve.before) @ np.asarray(curve.delta_v_rtn_m_s)
    np.testing.assert_allclose(np.subtract(after.velocity_m_s,before.velocity_m_s),expected,atol=2e-7,rtol=0)
    roundtrip = transform_states([before], "TEME")[0]
    nominal = curve.nominal(curve.burn_time)
    np.testing.assert_allclose(roundtrip.position_m, nominal.position_m, atol=1e-6, rtol=0)
    np.testing.assert_allclose(roundtrip.velocity_m_s, nominal.velocity_m_s, atol=2e-7, rtol=0)


def test_batch_matches_scalar_sgp4_and_modified_dense_queries():
    curve = trajectory()
    times = [curve.window.start+timedelta(minutes=minute) for minute in (0,5,90,180)]
    for state, at in zip(nominal_samples(curve.orbit,times),times):
        reference = propagate_object(curve.orbit,at)
        np.testing.assert_allclose(state.position_m,reference.position_m,atol=.002,rtol=0)
        np.testing.assert_allclose(state.velocity_m_s,reference.velocity_m_s,atol=2e-6,rtol=0)
    for state, at in zip(curve.samples(times),times):
        scalar = curve.modified(at)
        np.testing.assert_allclose(state.position_m,scalar.position_m,atol=.002,rtol=0)
        np.testing.assert_allclose(state.velocity_m_s,scalar.velocity_m_s,atol=2e-6,rtol=0)


def test_shared_reference_and_tolerance_convergence():
    curve = trajectory()
    earlier = trajectory(reference_epoch=curve.burn_time-timedelta(minutes=30))
    tighter = trajectory(rtol=1e-11)
    at = curve.window.end
    assert earlier.reference_epoch < earlier.burn_time
    assert earlier.before.position_m == earlier.after.position_m
    assert not np.array_equal(curve.modified(at).position_m,earlier.modified(at).position_m)
    np.testing.assert_allclose(curve.modified(at).position_m,tighter.modified(at).position_m,atol=.2,rtol=0)


def test_invalid_queries_frames_and_epoch_limits_rejected():
    curve = trajectory()
    with pytest.raises(ValueError):
        curve.modified(curve.window.start-timedelta(seconds=1))
    with pytest.raises(ValueError):
        trajectory(reference_epoch=curve.burn_time+timedelta(seconds=1))
    assert trajectory(max_epoch_distance_days=.01).nominal(curve.burn_time).frame=='TEME'
    with pytest.raises(ValueError):
        transform_states([curve.nominal(curve.burn_time)],"ITRS")
