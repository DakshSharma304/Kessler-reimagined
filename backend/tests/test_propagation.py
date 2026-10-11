from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time

import numpy as np
import pytest
from sgp4.api import Satrec

from app.models.orbital import GPElements
from app.physics.propagation import propagate_object, propagate_trajectory


def actual_elements():
    return GPElements.model_validate(json.loads(
        (Path(__file__).parent / "fixtures" / "gp_actual.json").read_text())[0])


def test_actual_propagation_finite_explicit_frame_and_units():
    elements = actual_elements()
    state = propagate_object(elements, elements.epoch)
    assert len(state.position_m) == len(state.velocity_m_s) == 3
    assert np.isfinite([*state.position_m, *state.velocity_m_s]).all()
    assert 6e6 < np.linalg.norm(state.position_m) < 8e6
    assert 6000 < np.linalg.norm(state.velocity_m_s) < 9000
    assert state.frame == "TEME"
    assert (state.position_units, state.velocity_units, state.propagation_status) == ("m", "m/s", "OK")


def test_time_changes_and_repeat_determinism():
    elements = actual_elements()
    first = propagate_object(elements, elements.epoch)
    later = propagate_object(elements, elements.epoch + timedelta(seconds=60))
    assert np.linalg.norm(np.subtract(first.position_m, later.position_m)) > 100000
    assert propagate_object(elements, elements.epoch) == first


def test_trajectory_times_and_endpoints():
    elements = actual_elements()
    end = elements.epoch + timedelta(minutes=10)
    states = propagate_trajectory(elements, elements.epoch, end, 11)
    assert len(states) == 11
    assert states[0].timestamp == elements.epoch
    assert states[-1].timestamp == end


def test_invalid_elements_or_times_rejected():
    with pytest.raises(ValueError):
        GPElements.model_validate({"NORAD_CAT_ID": "53495", "ECCENTRICITY": 2})
    with pytest.raises(ValueError, match="timezone-aware"):
        propagate_object(actual_elements(), datetime(2026, 10, 11))
    elements = actual_elements()
    with pytest.raises(ValueError):
        propagate_trajectory(elements, elements.epoch, elements.epoch, 10)


def test_vallado_trusted_sgp4_reference():
    # Vallado/CSSI verification case 00005, t=0, WGS72 improved mode.
    # Published verification output is shipped as tcppver.out by python-sgp4.
    satellite = Satrec.twoline2rv(
        "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753",
        "2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667",
    )
    state = propagate_object(satellite, datetime(2000, 6, 27, 18, 50, 19, 733568, tzinfo=UTC))
    # Tolerance: 1 mm position, 1 micrometre/s velocity, compared with rounded
    # reference text. This checks unit conversion and UTC->Julian-date handling.
    np.testing.assert_allclose(state.position_m,
        np.array([7022.46529266, -1400.08296755, 0.03995155]) * 1000, atol=.001, rtol=0)
    np.testing.assert_allclose(state.velocity_m_s,
        np.array([1.893841015, 6.405893759, 4.534807250]) * 1000, atol=.000001, rtol=0)


@pytest.mark.parametrize("count", [100, 1000])
def test_actual_propagation_benchmark(count):
    elements = actual_elements()
    started = time.perf_counter()
    states = propagate_trajectory(elements, elements.epoch,
                                  elements.epoch + timedelta(hours=1), count)
    elapsed = time.perf_counter() - started
    print(f"Actual GP SGP4 benchmark: {count} states in {elapsed:.6f}s")
    assert len(states) == count
    assert all(np.isfinite(item.position_m).all() for item in states)
