"""Shared cached sources for API/CLI; no network requests during initialization."""

from pathlib import Path

import httpx

from app.config import settings,Settings
from app.models.catalog import CatalogSelection
from app.data.cache import FileCache
from app.data.catalog import CatalogLoader
from app.data.celestrak import CelestrakClient
from app.data.discovery import EncounterDiscovery
from app.data.socrates import SocratesClient
from app.data.space_weather import SpaceWeatherClient
from app.data.metadata import MetadataClient
from datetime import UTC,datetime,timedelta
from collections import OrderedDict
import threading
from app.physics.secondary_search import CatalogPropagationCache


class Engine:
    def __init__(self, cache_directory: Path | None = None, http: httpx.Client | None = None,*,config: Settings | None=None):
        self.config=config or settings
        self.cache = FileCache(cache_directory or self.config.cache_directory)
        self.socrates = SocratesClient(self.cache, http)
        self.discovery = EncounterDiscovery(self.socrates)
        self.celestrak = CelestrakClient(self.cache, http)
        self.catalog = CatalogLoader(self.cache, http)
        self.space_weather = SpaceWeatherClient(self.cache, http)
        self.catalog_propagation_cache = CatalogPropagationCache()
        self.metadata = MetadataClient(self.cache,http,self.config.metadata_file)
        self.persistence_evidence = OrderedDict()
        self._evidence_lock=threading.Lock()
        self.calculation_slots=threading.BoundedSemaphore(self.config.max_calculations)
        self._public_catalog = None
        self._public_lock = threading.Lock()

    def public_catalog(self):
        """Five-minute in-memory browsing snapshot; existing source limits apply.

        Separate from the arbitrary local/group scope of a screening request.
        No atmosphere/encounter calculations or per-object HTTP requests.
        """
        with self._public_lock:
            now = datetime.now(UTC)
            if self._public_catalog is None or now-self._public_catalog.metadata.assembled_at >= timedelta(minutes=5):
                selection=CatalogSelection(groups=(),local_files=self.config.catalog_files) if self.config.catalog_files else None
                self._public_catalog = self.catalog.load_screening_catalog(selection)
            return self._public_catalog

    def selected_case(self, identifier: str):
        encounter = self.discovery.get_encounter(identifier)
        first, second = self.celestrak.get_encounter_objects(encounter)
        return encounter, first, second
