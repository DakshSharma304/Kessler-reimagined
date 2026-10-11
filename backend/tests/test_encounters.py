from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time

import numpy as np
import pytest

from app.data.cache import FileCache, make_record
from app.data.celestrak import CelestrakClient, parse_gp
from app.data.discovery import EncounterDiscovery
from app.data.socrates import SOCRATES_URL, SocratesClient, parse_dataset
from app.physics.encounters import CalculationUnavailable, analyze_encounter, refine_closest_approach
from app.physics.propagation import StateVector

START = datetime(2026, 10, 11, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures"


def actual_case():
    data = parse_dataset(make_record((FIXTURES / "socrates_actual.csv").read_text(),
        SOCRATES_URL, START, START, "FETCH_TIME"))
    raw = json.loads((FIXTURES / "gp_actual.json").read_text())
    objects = [parse_gp(make_record(json.dumps([row]), "fixture", START, START, "FETCH_TIME"),
                        str(row["NORAD_CAT_ID"])) for row in raw[:2]]
    return data.encounters[0], *objects


def stationary(at):
    return StateVector(timestamp=at, position_m=(0, 0, 0), velocity_m_s=(0, 0, 0), frame="TEME")


def crossing(at):
    seconds = (at - START).total_seconds()
    return StateVector(timestamp=at, position_m=(100 - 2 * seconds, 10, 0),
                       velocity_m_s=(-2, 0, 0), frame="TEME")


def test_identical_synthetic_trajectories_zero():
    result = refine_closest_approach(stationary, stationary, START, START + timedelta(seconds=100))
    assert result.miss_distance_m == 0
    assert result.relative_position_m == result.relative_velocity_m_s == (0, 0, 0)


def test_known_crossing_relative_geometry_and_refinement():
    result = refine_closest_approach(stationary, crossing, START, START + timedelta(seconds=100), 10)
    assert result.miss_distance_m == pytest.approx(10, abs=1e-8)
    assert (result.tca - START).total_seconds() == pytest.approx(50, abs=1e-5)
    np.testing.assert_allclose(result.relative_position_m, [0, -10, 0], atol=2e-5)
    assert result.relative_velocity_m_s == (2, 0, 0)
    assert result.relative_speed_m_s == 2
    assert result.miss_distance_m <= result.sampled_minimum_m
    assert START <= result.tca <= START + timedelta(seconds=100)


def test_incompatible_frames_rejected():
    def wrong_frame(at):
        return stationary(at).model_copy(update={"frame": "GCRS"})
    with pytest.raises(CalculationUnavailable, match="frames"):
        refine_closest_approach(stationary, wrong_frame, START, START + timedelta(seconds=100))


def test_actual_fixture_baseline_preserves_published_prediction():
    encounter, first, second = actual_case()
    result = analyze_encounter(encounter, first, second)
    assert result.published.miss_distance_m == 7
    assert result.published.max_probability_screening_metric == 1
    assert np.isfinite(result.calculated.miss_distance_m)
    assert result.calculated.miss_distance_m <= result.calculated.sampled_minimum_m
    assert result.calculated.searched_start <= result.calculated.tca <= result.calculated.searched_end
    assert result.element_epochs == (first.elements.epoch, second.elements.epoch)


def test_source_model_disagreement_reported():
    encounter, first, second = actual_case()
    # Deliberately mutate a historical fixture to test discrepancy reporting.
    altered = encounter.model_copy(update={"source_miss_distance_m": 1e9})
    result = analyze_encounter(altered, first, second)
    assert result.source_model_disagreement
    assert any("Source/model disagreement" in warning for warning in result.warnings)
    assert result.published.miss_distance_m == 1e9


def test_wrong_object_or_stale_epoch_rejected():
    encounter, first, second = actual_case()
    with pytest.raises(CalculationUnavailable, match="match"):
        analyze_encounter(encounter, second, first)
    stale = encounter.model_copy(update={"time_of_closest_approach": START + timedelta(days=30)})
    with pytest.raises(CalculationUnavailable, match="epoch"):
        analyze_encounter(stale, first, second)


@pytest.mark.live
def test_actual_upcoming_encounter_baseline():
    from app.config import settings
    cache = FileCache(settings.cache_directory)
    encounter = EncounterDiscovery(SocratesClient(cache)).list_encounters(limit=1)[0]
    objects = CelestrakClient(cache).get_encounter_objects(encounter)
    started = time.perf_counter()
    result = analyze_encounter(encounter, *objects)
    elapsed = time.perf_counter() - started
    print(f"Actual baseline: published {result.published.miss_distance_m:.3f}m; "
          f"recalculated {result.calculated.miss_distance_m:.3f}m at {result.calculated.tca}; "
          f"status {result.calculated.status}; disagreement {result.source_model_disagreement}; "
          f"runtime {elapsed:.6f}s")
    assert result.encounter_id == encounter.id
    assert result.calculated.status == "COMPLETE"
