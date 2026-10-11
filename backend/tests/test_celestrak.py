from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time

import httpx
import pytest

from app.data.cache import FileCache, make_record
from app.data.celestrak import GP_URL, CelestrakClient, OrbitalUnavailable, parse_gp
from app.models.orbital import epoch_suitability

NOW = datetime(2026, 10, 11, 2, 45, tzinfo=UTC)
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "gp_actual.json").read_text())


def cache_record(raw):
    return make_record(json.dumps(raw), GP_URL, NOW, NOW, "FETCH_TIME")


def test_two_actual_objects_and_epoch():
    first = parse_gp(cache_record([FIXTURE[0]]), "53495")
    second = parse_gp(cache_record([FIXTURE[1]]), "34452")
    assert first.elements.object_id == "53495"
    assert second.elements.object_id == "34452"
    assert first.elements.epoch == datetime(2026, 10, 10, 13, 23, 52, 331712, tzinfo=UTC)
    assert first.elements.frame == "TEME"
    assert first.elements.initialize_sgp4().satnum == 53495


def test_actual_six_digit_catalog_sgp4():
    orbit = parse_gp(cache_record([FIXTURE[2]]), "100033")
    assert orbit.elements.object_id == "100033"
    assert orbit.elements.initialize_sgp4().satnum == 100033


@pytest.mark.parametrize("field,value", [
    ("ECCENTRICITY", 1), ("MEAN_MOTION", 0), ("INCLINATION", 181),
    ("BSTAR", float("nan")), ("EPOCH", "invalid"), ("REF_FRAME", "ITRF"),
    ("MEAN_ELEMENT_THEORY", "OTHER"),
])
def test_invalid_elements_rejected(field, value):
    raw = dict(FIXTURE[0])
    raw[field] = value
    with pytest.raises(ValueError):
        parse_gp(cache_record([raw]), "53495")


@pytest.mark.parametrize("raw,requested", [([], "53495"), ([FIXTURE[0]], "34452"), ({}, "53495")])
def test_missing_or_mismatched_object_not_substituted(raw, requested):
    with pytest.raises(ValueError):
        parse_gp(cache_record(raw), requested)


def test_cached_record_avoids_repeated_queries(tmp_path):
    calls = []
    def fetch(request):
        calls.append(request)
        return httpx.Response(200, json=[FIXTURE[0]])
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        cache = FileCache(tmp_path)
        client = CelestrakClient(cache, http)
        first = client.get_object("53495", NOW)
        assert client.get_object("53495", NOW + timedelta(hours=1)) is first
        restored = CelestrakClient(cache, http).get_object("53495", NOW + timedelta(hours=1))
    assert len(calls) == 1
    assert restored == first


def test_http_failure_halts_queries_and_returns_unavailable(tmp_path):
    calls = []
    def fetch(request):
        calls.append(request)
        return httpx.Response(404)
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        client = CelestrakClient(FileCache(tmp_path), http)
        with pytest.raises(OrbitalUnavailable):
            client.get_object("53495", NOW)
        with pytest.raises(OrbitalUnavailable, match="halted"):
            client.get_object("34452", NOW)
    assert len(calls) == 1


def test_stale_epoch_flagged():
    orbit = parse_gp(cache_record([FIXTURE[0]]), "53495")
    supported, warnings = epoch_suitability(orbit, datetime(2026, 10, 25, tzinfo=UTC))
    assert not supported
    assert any("exceeds" in item for item in warnings)
    assert any("may differ" in item for item in warnings)


@pytest.mark.live
def test_real_selected_encounter_has_two_usable_orbits():
    from app.config import settings
    from app.data.discovery import EncounterDiscovery
    from app.data.socrates import SocratesClient
    cache = FileCache(settings.cache_directory)
    encounter = EncounterDiscovery(SocratesClient(cache)).list_encounters(limit=1)[0]
    client = CelestrakClient(cache)
    first, second = client.get_encounter_objects(encounter)
    assert first.elements.object_id == encounter.object_1_id
    assert second.elements.object_id == encounter.object_2_id
    assert first.data_status == second.data_status == "VALID"
    six_digit = client.get_object("100033")
    assert six_digit.elements.initialize_sgp4().satnum == 100033
    started = time.perf_counter()
    assert client.get_object(encounter.object_1_id) is first
    print(f"Actual pair {first.elements.object_id}/{second.elements.object_id}; "
          f"epochs {first.elements.epoch}/{second.elements.epoch}; "
          f"cached orbit lookup {time.perf_counter()-started:.6f}s")
