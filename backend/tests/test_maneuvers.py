from datetime import timedelta
import time

import numpy as np
import pytest

from app.physics.maneuvers import simulate_maneuver
from test_encounters import START, actual_case


def simulate(delta=(0, .1, 0), lead_hours=1, **kwargs):
    encounter, first, second = actual_case()
    return simulate_maneuver(encounter, first, second, encounter.object_1_id,
        encounter.time_of_closest_approach-timedelta(hours=lead_hours), delta,
        hypothetical_capability_assumed=True, now=START, **kwargs)


def test_zero_burn_reproduces_matched_baseline():
    result = simulate((0, 0, 0))
    assert result.modified.miss_distance_m == pytest.approx(result.matched_baseline.miss_distance_m, abs=1e-8)
    assert result.modified.tca == result.matched_baseline.tca
    assert result.state_before_maneuver == result.state_after_maneuver
    assert result.baseline_trajectory == result.modified_trajectory


def test_impulse_changes_velocity_not_position_and_real_trajectory():
    result = simulate()
    assert result.state_before_maneuver.position_m == result.state_after_maneuver.position_m
    assert np.linalg.norm(np.subtract(result.state_after_maneuver.velocity_m_s,
                                     result.state_before_maneuver.velocity_m_s)) == pytest.approx(.1, abs=1e-10)
    assert np.linalg.norm(np.subtract(result.modified_trajectory[-1].position_m,
                                     result.baseline_trajectory[-1].position_m)) > 1
    assert abs(result.change_in_miss_distance_m) > .01
    assert result.modified.miss_distance_m <= result.modified.sampled_minimum_m
    assert result.modified.frame == "GCRS"
    assert result.sgp4_reference.calculated.frame == "TEME"


def test_positive_negative_direction_and_timing_change_outcomes():
    positive = simulate((0, .1, 0))
    negative = simulate((0, -.1, 0))
    radial = simulate((.1, 0, 0))
    earlier = simulate((0, .1, 0), lead_hours=2)
    values = [result.modified.miss_distance_m for result in (positive, negative, radial, earlier)]
    assert len({round(value, 3) for value in values}) == 4


def test_maneuver_timing_and_capability_enforced():
    encounter, first, second = actual_case()
    for at in [encounter.time_of_closest_approach, encounter.time_of_closest_approach + timedelta(seconds=1), START-timedelta(seconds=1)]:
        with pytest.raises(ValueError):
            simulate_maneuver(encounter, first, second, encounter.object_1_id, at, (0, .1, 0), True, now=START)
    with pytest.raises(ValueError, match="assumption"):
        simulate_maneuver(encounter, first, second, encounter.object_1_id,
                          encounter.time_of_closest_approach-timedelta(hours=1), (0, .1, 0), now=START)


def test_numerical_convergence_and_repeatability():
    started = time.perf_counter()
    first = simulate()
    elapsed = time.perf_counter()-started
    tighter = simulate(rtol=1e-11)
    repeated = simulate()
    assert abs(first.modified.miss_distance_m-tighter.modified.miss_distance_m) < .2
    assert abs(first.matched_baseline.miss_distance_m-tighter.matched_baseline.miss_distance_m) < .2
    assert abs((first.modified.tca-tighter.modified.tca).total_seconds()) < .001
    assert first.modified == repeated.modified
    print(f"Actual fixture maneuver: matched zero-burn {first.matched_baseline.miss_distance_m:.3f}m; "
          f"post-burn {first.modified.miss_distance_m:.3f}m; "
          f"delta {first.change_in_miss_distance_m:.3f}m; runtime {elapsed:.6f}s; "
          f"tight-tolerance difference {abs(first.modified.miss_distance_m-tighter.modified.miss_distance_m):.6f}m")


def test_burn_within_search_window_uses_nominal_preburn_states():
    result = simulate(lead_hours=1/60)
    assert result.baseline_trajectory[0] == result.modified_trajectory[0]
    assert result.maneuver_time > result.baseline_trajectory[0].timestamp
    assert result.baseline_trajectory[-1] != result.modified_trajectory[-1]


@pytest.mark.live
def test_selected_real_encounter_maneuver():
    from app.config import settings
    from app.data.cache import FileCache
    from app.data.celestrak import CelestrakClient
    from app.data.discovery import EncounterDiscovery
    from app.data.socrates import SocratesClient
    cache = FileCache(settings.cache_directory)
    encounter = EncounterDiscovery(SocratesClient(cache)).list_encounters(limit=1)[0]
    first, second = CelestrakClient(cache).get_encounter_objects(encounter)
    result = simulate_maneuver(encounter, first, second, encounter.object_1_id,
        encounter.time_of_closest_approach-timedelta(hours=1), (0, .1, 0), True)
    assert abs(result.change_in_miss_distance_m) > .01
    print(f"Selected real maneuver: {result.delta_v_m_s:.3f}m/s, clearance change "
          f"{result.change_in_miss_distance_m:.3f}m, status {result.modified.status}")
