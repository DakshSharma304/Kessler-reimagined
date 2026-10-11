import csv
from datetime import UTC, datetime, timedelta
import io
import json
from pathlib import Path

import httpx
import pytest
from app.config import settings
from app.data.cache import FileCache, make_record
from app.data.space_weather import (SPACE_WEATHER_URL, SpaceWeatherClient,
    SpaceWeatherUnavailable, get_space_weather, parse_space_weather)

NOW = datetime(2026, 10, 11, tzinfo=UTC)
HEADER = "DATE,AP1,AP2,AP3,AP4,AP5,AP6,AP7,AP8,AP_AVG,F10.7_OBS,F10.7_ADJ,F10.7_DATA_TYPE,F10.7_OBS_CENTER81,F10.7_OBS_LAST81,F10.7_ADJ_CENTER81,F10.7_ADJ_LAST81\n"
ROWS = ("2000-01-01,56,39,27,18,32,15,32,22,30,129.9,125.6,OBS,166.2,179.0,161.1,175.0\n"
        "2026-10-12,4,4,4,4,4,4,4,4,4,150,148,PRD,145,144,143,142\n"
        "2026-12-01,,,,,,,,,,150,148,PRM,145,144,143,142\n")


def record(payload=HEADER+ROWS, fetched=NOW):
    return make_record(payload, SPACE_WEATHER_URL, fetched, fetched, "TEST_SNAPSHOT")


def test_documented_example_preserves_units_and_conventions():
    d = parse_space_weather(record())
    r = get_space_weather(datetime(2000, 1, 1, tzinfo=UTC), d).record
    assert r.f107_observed_sfu == 129.9
    assert r.f107_adjusted_sfu == 125.6
    assert r.f107_observed_center81_sfu == 166.2
    assert r.f107_observed_last81_sfu == 179
    assert r.ap_daily == 30
    assert r.ap_3hourly == (56,39,27,18,32,15,32,22)
    assert r.flux_type == "OBS"
    future = get_space_weather(datetime(2026,10,12,tzinfo=UTC), d)
    assert future.status == "AVAILABLE" and future.record.flux_type == "PRD"
    assert get_space_weather(datetime(2026,12,1,tzinfo=UTC),d).status == "UNSUPPORTED_MONTHLY_FORECAST"
    assert get_space_weather(datetime(2045,1,1,tzinfo=UTC),d).status == "OUTSIDE_COVERAGE"
    assert get_space_weather(NOW,d,as_of=NOW-timedelta(days=1)).status == "AS_OF_UNAVAILABLE"


def test_missing_and_interpolated_flux_are_not_fabricated():
    d = parse_space_weather(record((HEADER+ROWS).replace("129.9", "").replace(",OBS,", ",INT,")))
    result = get_space_weather(datetime(2000,1,1,tzinfo=UTC),d)
    assert result.status == "MISSING_DATA"
    assert result.record.f107_observed_sfu is None
    assert result.record.flux_type == "INT"


@pytest.mark.parametrize("change", [lambda s:s.replace("129.9","NaN"), lambda s:s.replace("129.9","-1"),
    lambda s:s.replace(",OBS,",",UNKNOWN,"), lambda s:s.replace("2000-01-01","2000-13-01"),
    lambda s:s.replace("56,39", "401,39"), lambda s:s+ROWS.splitlines()[0]+"\n"])
def test_invalid_csv_rejected(change):
    with pytest.raises(ValueError):
        parse_space_weather(record(change(HEADER+ROWS)))


def test_atomic_cache_and_provider_errors(tmp_path):
    calls = []
    def response(request):
        calls.append(request)
        return httpx.Response(200,text=HEADER+ROWS,headers={"Last-Modified":"Sun, 11 Oct 2026 00:00:00 GMT"})
    cache = FileCache(tmp_path)
    client = SpaceWeatherClient(cache,httpx.Client(transport=httpx.MockTransport(response)))
    first = client.load_space_weather(NOW)
    assert first.retrieval_mode == "DOWNLOAD"
    assert client.load_space_weather(NOW).retrieval_mode == "CACHE"
    assert len(calls) == 1
    before = cache.read(SPACE_WEATHER_URL)
    failing = SpaceWeatherClient(cache,httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503))))
    stale = failing.load_space_weather(NOW+timedelta(days=1))
    assert stale.retrieval_mode == "STALE_CACHE" and stale.warnings
    assert cache.read(SPACE_WEATHER_URL) == before
    assert failing.load_space_weather(NOW+timedelta(days=1)).retrieval_mode == "STALE_CACHE"
    malformed = SpaceWeatherClient(cache,httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,text="broken"))))
    assert malformed.load_space_weather(NOW+timedelta(days=1)).retrieval_mode == "STALE_CACHE"
    assert cache.read(SPACE_WEATHER_URL) == before


def test_unavailable_and_aware_times(tmp_path):
    client = SpaceWeatherClient(FileCache(tmp_path),httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(403))))
    with pytest.raises(SpaceWeatherUnavailable): client.load_space_weather(NOW)
    with pytest.raises(ValueError): client.load_space_weather(datetime(2026,10,11))
    with pytest.raises(ValueError): get_space_weather(datetime(2000,1,1),parse_space_weather(record()))


@pytest.mark.live
def test_actual_celestrak_csv_and_cache():
    # Actual live request on first execution; subsequent checkpoints reuse the
    # same checksum-verified source payload under the six-hour refresh policy.
    client = SpaceWeatherClient(FileCache(settings.cache_directory))
    data = client.load_space_weather()
    assert data.retrieval_mode != "STALE_CACHE"
    assert len(data.records) > 20000
    payload = client.cache.read(SPACE_WEATHER_URL)
    raw = list(csv.DictReader(io.StringIO(payload.payload)))
    selected = next(row for row in raw if row["DATE"] == "2000-01-01")
    sample = get_space_weather(datetime(2000,1,1,tzinfo=UTC),data)
    assert sample.status == "AVAILABLE"
    assert sample.record.f107_observed_sfu == float(selected["F10.7_OBS"])
    assert sample.record.ap_daily == float(selected["AP_AVG"])
    assert all(sample.record.ap_3hourly[i] == float(selected[f"AP{i+1}"]) for i in range(8))
    assert {r.flux_type for r in data.records.values()} == {"OBS","INT","PRD","PRM"}
    assert client.load_space_weather().content_sha256 == data.content_sha256
    print("ACTUAL_SPACE_WEATHER", json.dumps(data.coverage()))
