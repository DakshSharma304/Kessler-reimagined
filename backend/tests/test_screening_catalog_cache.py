"""Scope-safe reuse of genuine GP snapshots, without replacing calculations."""
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import Settings
from app.models.catalog import CatalogSelection
from test_visualization import visual_api


def test_default_screening_reuses_same_verified_snapshot_and_refreshes(visual_api):
    _, engine = visual_api
    original = engine.public_catalog()
    assert engine.screening_catalog(CatalogSelection()) is original
    assert engine.catalog.last_catalog is original
    fingerprint = original.metadata.snapshot_sha256
    original.metadata.assembled_at = datetime.now(UTC) - timedelta(minutes=6)
    refreshed = engine.screening_catalog(CatalogSelection())
    assert refreshed is not original
    assert refreshed.metadata.snapshot_sha256 == fingerprint
    assert refreshed.metadata.assembled_at > original.metadata.assembled_at
    assert refreshed.records.keys() == original.records.keys()


def test_custom_scope_never_reuses_default_or_changes_public_scope(visual_api):
    _, engine = visual_api
    original = engine.public_catalog()
    empty = engine.screening_catalog(CatalogSelection(groups=()))
    assert not empty.records
    assert empty is not original
    assert engine.catalog.last_catalog is empty
    assert engine.public_catalog() is original
    assert engine.screening_catalog(CatalogSelection()) is original
    assert engine.catalog.last_catalog is original


def test_local_browser_scope_never_substitutes_for_public_screening(visual_api):
    _, engine = visual_api
    fixture = Path(__file__).parent / 'fixtures' / 'gp_actual.json'
    engine.config = Settings(catalog_files=(fixture,))
    local = engine.public_catalog()
    assert all(source.retrieval_mode == 'LOCAL' for source in local.metadata.sources)
    public = engine.screening_catalog(CatalogSelection())
    assert public is not local
    assert all(source.retrieval_mode != 'LOCAL' for source in public.metadata.sources)
    assert engine.public_catalog() is local
