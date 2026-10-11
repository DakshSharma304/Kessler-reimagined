from datetime import UTC, datetime
from pathlib import Path
import time

import pytest

from app.data.cache import FileCache, make_record
from app.data.discovery import EncounterDiscovery, EncounterNotFound, quality_warnings
from app.data.socrates import SOCRATES_URL, SocratesClient, SourceUnavailable, parse_dataset

NOW = datetime(2026, 10, 11, tzinfo=UTC)


class FixtureClient:
    def __init__(self):
        text = (Path(__file__).parent / "fixtures" / "socrates_actual.csv").read_text()
        self.dataset = parse_dataset(make_record(text, SOCRATES_URL, NOW, NOW, "FETCH_TIME"))

    def get_dataset(self):
        return self.dataset


@pytest.fixture
def discovery():
    return EncounterDiscovery(FixtureClient())


def test_max_probability_sort(discovery):
    items = discovery.list_encounters("max_probability", now=NOW)
    assert [item.socrates_max_probability for item in items] == [1, .3523, .1397, .01057, .004208]


def test_minimum_separation_sort(discovery):
    items = discovery.list_encounters("minimum_separation", now=NOW)
    assert [item.source_miss_distance_m for item in items] == [7, 12, 21, 25, 27]


def test_chronological_sort(discovery):
    items = discovery.list_encounters("time", now=NOW)
    assert [item.time_of_closest_approach for item in items] == sorted(item.time_of_closest_approach for item in items)


def test_name_and_either_catalog_filter(discovery):
    assert len(discovery.list_encounters(name="starlink", now=NOW)) == 3
    assert len(discovery.list_encounters(object_id="34452", now=NOW)) == 1
    item = discovery.list_encounters(object_id="53495", now=NOW)[0]
    selected = discovery.get_encounter(item.id)
    assert (selected.object_1_id, selected.object_2_id) == ("53495", "34452")
    assert discovery.list_encounters(object_id="100033", now=NOW)[0].object_2_id == "100033"


def test_unknown_id_and_unavailable_source(discovery):
    with pytest.raises(EncounterNotFound, match="Unknown encounter"):
        discovery.get_encounter("not-an-encounter")
    class MissingClient:
        def get_dataset(self):
            raise SourceUnavailable("Missing SOCRATES data")
    with pytest.raises(SourceUnavailable, match="Missing"):
        EncounterDiscovery(MissingClient()).list_encounters(now=NOW)


def test_expired_predictions_excluded(discovery):
    assert discovery.list_encounters(now=datetime(2026, 10, 17, tzinfo=UTC)) == []


def test_default_age_screening_is_transparent(discovery):
    items = discovery.list_encounters(now=NOW)
    # Source element age > 7 days is a caution, not an operational validity limit.
    assert [item.object_1_id for item in items] == ["53495", "53604", "27056", "62320", "28370"]
    assert any("seven-day" in warning for warning in quality_warnings(items[-1]))
    assert any("not calibrated" in warning for warning in quality_warnings(items[0]))


@pytest.mark.parametrize("kwargs", [{"sort": "danger"}, {"limit": 0}, {"offset": -1}, {"object_id": "abc"}])
def test_invalid_filter_rejected(discovery, kwargs):
    with pytest.raises(ValueError):
        discovery.list_encounters(now=NOW, **kwargs)


def test_large_limit_is_allowed(discovery):
    assert len(discovery.list_encounters(now=NOW, limit=1001)) == 5


@pytest.mark.live
def test_select_actual_upcoming_encounter():
    from app.config import settings
    discovery = EncounterDiscovery(SocratesClient(FileCache(settings.cache_directory)))
    items = discovery.list_encounters(limit=10)
    assert items
    selected = discovery.get_encounter(items[0].id)
    assert selected.time_of_closest_approach >= datetime.now(UTC)
    started = time.perf_counter()
    assert discovery.get_encounter(selected.id) == selected
    elapsed = time.perf_counter() - started
    print(f"Selected real encounter {selected.object_1_id}/{selected.object_2_id}; indexed lookup {elapsed:.6f}s")
    assert elapsed < 1
