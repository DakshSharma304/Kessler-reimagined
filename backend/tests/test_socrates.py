"""Checkpoint 2: actual fixture parsing, provenance, and cache behavior."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.data.cache import FileCache, make_record
from app.data.socrates import SOCRATES_URL, SocratesClient, SourceUnavailable, parse_dataset, parse_utc

FIXTURE = Path(__file__).parent / "fixtures" / "socrates_actual.csv"
NOW = datetime(2026, 10, 11, 2, 40, tzinfo=UTC)


def record(text=None):
    return make_record(
        FIXTURE.read_text() if text is None else text, SOCRATES_URL, NOW,
        datetime(2026, 10, 10, 15, 48, 20, tzinfo=UTC), "HTTP_LAST_MODIFIED",
    )


def test_actual_row_and_multirow_units_and_ids():
    dataset = parse_dataset(record())
    assert len(dataset.encounters) == 5
    first = dataset.encounters[0]
    assert first.object_1_id == "53495"
    assert first.object_2_id == "34452"
    assert first.source_miss_distance_m == 7
    assert first.source_relative_speed_m_s == 13952
    assert first.socrates_max_probability == 1
    assert first.source_dse_1_days == 3.961
    assert first.source_dse_2_days == 4.065
    assert first.time_of_closest_approach == datetime(2026, 10, 13, 5, 9, 3, 882000, tzinfo=UTC)
    assert dataset.encounters[3].object_2_id == "100033"
    assert dataset.encounters[1].source_dilution_m == 8
    assert "collision_probability" not in first.model_dump()
    assert first.dataset_timestamp == dataset.dataset_timestamp
    assert dataset.timestamp_basis == "HTTP_LAST_MODIFIED"


def test_utc_conversion():
    assert parse_utc("2026-10-13T07:09:03.882+02:00") == parse_utc("2026-10-13 05:09:03.882")


@pytest.mark.parametrize("replacement", ["nan", "inf", "-1", "not-a-number"])
def test_invalid_rows_do_not_corrupt_actual_data(replacement):
    text = FIXTURE.read_text()
    damaged = text.splitlines()[1].replace(
        "2026-10-13 05:09:03.882,0.007", f"2026-10-13 05:09:03.882,{replacement}"
    )
    dataset = parse_dataset(record(text + damaged + "\n"))
    assert len(dataset.encounters) == 5
    assert dataset.invalid_rows == 1
    assert dataset.warnings


def test_duplicates_and_repeated_pair_different_times():
    text = FIXTURE.read_text()
    row = text.splitlines()[1]
    dataset = parse_dataset(record(text + row + "\n" + row.replace("05:09:03.882", "05:09:04.882") + "\n"))
    assert dataset.duplicate_rows == 1
    assert len(dataset.encounters) == 6
    assert dataset.encounters[0].id != dataset.encounters[-1].id


def test_catalog_id_strings_preserve_leading_zeros():
    dataset = parse_dataset(record(FIXTURE.read_text().replace("53495", "053495")))
    assert dataset.encounters[0].object_1_id == "053495"


@pytest.mark.parametrize("text", ["", "<html>error</html>", "TCA,TCA\n1,2\n"])
def test_invalid_dataset_rejected(text):
    with pytest.raises(ValueError):
        parse_dataset(record(text))


def test_persistent_cache_avoids_repeated_downloads(tmp_path):
    calls = []
    def fetch(request):
        calls.append(request)
        return httpx.Response(200, text=FIXTURE.read_text(), headers={
            "Last-Modified": "Sat, 10 Oct 2026 15:48:20 GMT",
        })
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        client = SocratesClient(FileCache(tmp_path), http)
        first = client.get_dataset(NOW)
        assert client.get_dataset(NOW + timedelta(hours=1)) is first
        restored = SocratesClient(FileCache(tmp_path), http).get_dataset(NOW + timedelta(hours=1))
    assert len(calls) == 1
    assert restored.encounters == first.encounters


@pytest.mark.parametrize("status,body", [(503, "unavailable"), (200, "invalid csv")])
def test_bad_refresh_preserves_last_valid_dataset(tmp_path, status, body):
    cache = FileCache(tmp_path)
    previous = record()
    cache.write(SOCRATES_URL, previous)
    calls = []
    def fetch(request):
        calls.append(request)
        return httpx.Response(status, text=body)
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        client = SocratesClient(cache, http)
        failed = client.get_dataset(NOW + timedelta(hours=12))
        assert failed.data_status == "STALE_CACHE"
        assert len(failed.encounters) == 5
        assert all(item.data_status == "STALE_CACHE" for item in failed.encounters)
        assert client.get_dataset(NOW + timedelta(hours=13, minutes=5)) is failed
    assert len(calls) == 1
    assert cache.read(SOCRATES_URL) == previous


def test_missing_data_explicitly_unavailable(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as http:
        with pytest.raises(SourceUnavailable, match="SOCRATES unavailable"):
            SocratesClient(FileCache(tmp_path), http).get_dataset(NOW)


def test_corrupt_cache_rejected(tmp_path):
    cache = FileCache(tmp_path)
    valid = record()
    with pytest.raises(ValueError, match="checksum"):
        cache.write(SOCRATES_URL, valid.model_copy(update={"payload": "corrupt"}))


@pytest.mark.live
def test_full_actual_dataset_download_and_parse():
    from app.config import settings
    client = SocratesClient(FileCache(settings.cache_directory))
    dataset = client.get_dataset()
    print(f"Actual parsed SOCRATES encounters: {len(dataset.encounters)}; "
          f"invalid rows: {dataset.invalid_rows}; duplicates: {dataset.duplicate_rows}")
    assert dataset.encounters
    assert dataset.data_status == "VALID"
    assert client.get_dataset() is dataset
