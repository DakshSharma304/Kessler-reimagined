"""Checkpoint 2: actual downloaded OMM fixtures and isolated network tests."""

import csv
from datetime import timedelta
import io
import json

import httpx
import pytest

from app.data.cache import FileCache, make_record
from app.data.catalog import CatalogLoader, parse_catalog
from app.data.celestrak import GP_URL
from app.models.catalog import CatalogSelection
from test_celestrak import FIXTURE, NOW


def snapshot(rows):
    return make_record(json.dumps(rows), GP_URL+"?GROUP=stations&FORMAT=JSON", NOW, NOW, "FETCH_TIME")


def test_actual_multi_record_provenance_epochs_and_six_digits():
    records, source, warnings = parse_catalog(snapshot(FIXTURE))
    assert {"53495", "34452", "100033"} <= set(records)
    assert source.usable_records == len(FIXTURE)
    assert source.content_sha256 == snapshot(FIXTURE).content_sha256
    assert source.retrieved_at == NOW
    assert all(orbit.elements.epoch.tzinfo is not None for orbit in records.values())
    assert records["100033"].elements.initialize_sgp4().satnum == 100033
    assert not warnings


def test_canonical_dedup_newest_epoch_missing_and_invalid_records():
    newer = FIXTURE[0] | {"NORAD_CAT_ID":"053495", "EPOCH":"2026-10-11T01:00:00"}
    records, source, warnings = parse_catalog(snapshot([
        *FIXTURE, newer, FIXTURE[0] | {"ECCENTRICITY":2},
        {"NORAD_CAT_ID":123456}, "not a record", FIXTURE[0] | {"NORAD_CAT_ID":0},
    ]))
    assert len(records) == len(FIXTURE)
    assert records["53495"].elements.epoch > records["34452"].elements.epoch
    assert source.duplicate_records == 1
    assert source.rejected_records == 4
    assert len(warnings) == 4


def test_csv_uses_same_validation_and_real_sgp4():
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIXTURE[0].keys())
    writer.writeheader()
    writer.writerows(FIXTURE)
    original = snapshot([])
    record = make_record(out.getvalue(), original.source_url, NOW, NOW, "FETCH_TIME")
    records, source, _ = parse_catalog(record)
    assert len(records) == len(FIXTURE)
    assert source.rejected_records == 0
    assert records["53495"].elements.initialize_sgp4().satnum == 53495


@pytest.mark.parametrize("ephemeris_type", ["1", "0.5", "nan", "", "invalid"])
def test_csv_unsupported_or_malformed_ephemeris_type_still_rejected(ephemeris_type):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIXTURE[0].keys())
    writer.writeheader()
    writer.writerow(FIXTURE[0])
    writer.writerow(FIXTURE[1] | {"EPHEMERIS_TYPE": ephemeris_type})
    records, source, warnings = parse_catalog(make_record(
        output.getvalue(), "fixture", NOW, NOW, "FETCH_TIME"))
    assert set(records) == {"53495"}
    assert source.rejected_records == 1
    assert warnings


@pytest.mark.parametrize("payload", ["{}", "garbage", "<html>error</html>"])
def test_invalid_dataset_rejected(payload):
    with pytest.raises(ValueError):
        parse_catalog(make_record(payload, "fixture", NOW, NOW, "FETCH_TIME"))


def test_cache_reuse_multiple_sources_dedup_and_coverage(tmp_path):
    calls = []
    def fetch(request):
        calls.append(str(request.url))
        return httpx.Response(200, json=FIXTURE)
    cache = FileCache(tmp_path)
    selection = CatalogSelection(groups=("stations", "visual"))
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        loader = CatalogLoader(cache, http)
        one = loader.load_screening_catalog(selection, NOW)
        two = loader.load_screening_catalog(selection, NOW+timedelta(hours=1))
        restored = CatalogLoader(cache, http).load_screening_catalog(selection, NOW+timedelta(hours=1))
    assert len(calls) == 2
    assert one.records == two.records == restored.records
    assert one.metadata.snapshot_sha256 == restored.metadata.snapshot_sha256
    assert all(source.retrieval_mode == "HTTP" for source in one.metadata.sources)
    assert all(source.retrieval_mode == "CACHE" for source in two.metadata.sources)
    assert one.metadata.duplicate_count == len(FIXTURE)
    assert one.metadata.objects_available == len(FIXTURE)
    assert one.metadata.coverage == "PARTIAL"
    assert one.metadata.freshness_status == "FRESH"
    assert one.metadata.oldest_element_epoch < one.metadata.newest_element_epoch
    assert any("debris" in warning for warning in one.metadata.coverage_limitations)


def test_local_file_and_existing_individual_cache_are_supported(tmp_path):
    # Reuse a supplied actual downloaded OMM fixture; do not manufacture orbits.
    from test_encounters import FIXTURES
    cache = FileCache(tmp_path)
    cached = make_record(json.dumps([FIXTURE[0]]), GP_URL+"?CATNR=53495&FORMAT=JSON",
                        NOW, NOW, "FETCH_TIME")
    cache.write(cached.source_url, cached)
    loader = CatalogLoader(cache)
    result = loader.load_screening_catalog(CatalogSelection(groups=(),
        local_files=(FIXTURES/"gp_actual.json",), include_cached_records=True), NOW)
    assert result.metadata.objects_available == len(FIXTURE)
    assert result.metadata.duplicate_count == 1
    assert {source.retrieval_mode for source in result.metadata.sources} == {"LOCAL", "CACHE"}
    assert any(orbit.source == "Local OMM" for orbit in result.records.values())


def test_source_failure_stops_queries_and_retains_valid_stale_snapshot(tmp_path):
    cache = FileCache(tmp_path)
    stored = snapshot(FIXTURE)
    cache.write(stored.source_url, stored)
    calls = []
    def fetch(request):
        calls.append(request)
        return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        loader = CatalogLoader(cache, http)
        result = loader.load_screening_catalog(CatalogSelection(groups=("stations", "visual")), NOW+timedelta(hours=3))
        again = loader.load_screening_catalog(CatalogSelection(groups=("stations",)), NOW+timedelta(hours=4))
    assert len(calls) == 1
    assert result.metadata.freshness_status == "STALE"
    assert result.metadata.failed_sources
    assert result.metadata.objects_available == len(FIXTURE)
    assert all(orbit.data_status == "STALE_CACHE" for orbit in result.records.values())
    assert again.records == result.records
    assert cache.read(stored.source_url) == stored


def test_empty_stale_and_unavailable_are_not_complete_catalogs(tmp_path):
    cache = FileCache(tmp_path)
    empty = CatalogLoader(cache).load_screening_catalog(CatalogSelection(groups=()), NOW)
    assert empty.records == {}
    assert empty.metadata.freshness_status == "UNAVAILABLE"
    cache.write(snapshot(FIXTURE).source_url, snapshot(FIXTURE))
    stale = CatalogLoader(cache).load_screening_catalog(CatalogSelection(groups=(), include_cached_records=True), NOW+timedelta(days=30))
    assert stale.metadata.objects_available == len(FIXTURE)
    assert stale.metadata.freshness_status == "STALE"
    assert any("seven days" in warning for warning in stale.metadata.warnings)


def test_unknown_and_invented_all_group_rejected():
    for group in ("ALL", "invented"):
        with pytest.raises(ValueError):
            CatalogSelection(groups=(group,))


@pytest.mark.live
def test_real_broader_catalog_ingestion_and_preserved_cache():
    from app.config import settings
    catalog = CatalogLoader(FileCache(settings.cache_directory)).load_screening_catalog()
    assert not catalog.metadata.failed_sources, catalog.metadata.model_dump_json(indent=2)
    assert len(catalog.records) > 100, catalog.metadata.model_dump_json(indent=2)
    assert len(set(catalog.records)-{"53495", "34452"}) > 100
    assert any(len(identifier) >= 6 for identifier in catalog.records)
    assert any("DEB" in orbit.elements.object_name for orbit in catalog.records.values())
    assert any("R/B" in orbit.elements.object_name for orbit in catalog.records.values())
    assert catalog.metadata.coverage == "PARTIAL"
    assert all(orbit.elements.initialize_sgp4() for orbit in catalog.records.values())
    print("ACTUAL_SCREENING_CATALOG " + catalog.metadata.model_dump_json())
    # A second loader must not download the same datasets again this update.
    restored = CatalogLoader(FileCache(settings.cache_directory)).load_screening_catalog()
    assert restored.metadata.snapshot_sha256 == catalog.metadata.snapshot_sha256
    assert all(source.retrieval_mode == "CACHE" for source in restored.metadata.sources)
