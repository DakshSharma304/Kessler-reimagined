"""Shared cached sources for API/CLI; no network requests during initialization."""

from pathlib import Path

import httpx

from app.config import settings
from app.data.cache import FileCache
from app.data.celestrak import CelestrakClient
from app.data.discovery import EncounterDiscovery
from app.data.socrates import SocratesClient


class Engine:
    def __init__(self, cache_directory: Path | None = None, http: httpx.Client | None = None):
        self.cache = FileCache(cache_directory or settings.cache_directory)
        self.socrates = SocratesClient(self.cache, http)
        self.discovery = EncounterDiscovery(self.socrates)
        self.celestrak = CelestrakClient(self.cache, http)

    def selected_case(self, identifier: str):
        encounter = self.discovery.get_encounter(identifier)
        first, second = self.celestrak.get_encounter_objects(encounter)
        return encounter, first, second
