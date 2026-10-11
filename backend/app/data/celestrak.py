"""On-demand OMM-compatible GP retrieval; no more than once per two hours."""

from datetime import UTC, datetime, timedelta
import json
import threading

import httpx

from app.data.cache import CacheRecord, FileCache, make_record
from app.models.encounter import Encounter
from app.models.orbital import GPElements, OrbitalRecord, epoch_suitability

GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
GP_REFRESH_INTERVAL = timedelta(hours=2)


class OrbitalUnavailable(RuntimeError):
    """A requested orbit is missing, invalid, or unsupported; never substitute."""


def validate_object_id(value: str) -> str:
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or not 0 < int(value) <= 999999999:
        raise ValueError("Catalog ID must be a positive numeric string of at most nine digits")
    return str(int(value))


def parse_gp(record: CacheRecord, requested_id: str) -> OrbitalRecord:
    requested_id = validate_object_id(requested_id)
    records = json.loads(record.payload)
    if not isinstance(records, list) or not records:
        raise ValueError("No GP orbital records available")
    if len(records) != 1:
        raise ValueError("Ambiguous GP response: expected exactly one requested object")
    elements = GPElements.model_validate(records[0])
    if elements.object_id != requested_id:
        raise ValueError(f"Requested catalog ID {requested_id} does not match returned {elements.object_id}")
    elements.initialize_sgp4()
    return OrbitalRecord(elements=elements, source_url=record.source_url,
                         fetched_at=record.fetched_at, content_sha256=record.content_sha256)


class CelestrakClient:
    def __init__(self, cache: FileCache, http: httpx.Client | None = None):
        self.cache = cache
        self.http = http
        self._records: dict[str, OrbitalRecord] = {}
        self._blocked_error: str | None = None
        self._lock = threading.Lock()

    def get_object(self, object_id: str, now: datetime | None = None) -> OrbitalRecord:
        identifier = validate_object_id(object_id)
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Current time must be timezone-aware")
        url = f"{GP_URL}?CATNR={identifier}&FORMAT=JSON"
        with self._lock:
            record = self._records.get(identifier)
            if record is None:
                cached = self.cache.read(url)
                if cached is not None:
                    try:
                        record = parse_gp(cached, identifier)
                    except ValueError:
                        pass
            if record is not None and now - record.fetched_at < GP_REFRESH_INTERVAL:
                self._records[identifier] = record
                return record
            if self._blocked_error is not None:
                if record is not None:
                    return record.model_copy(update={"data_status": "STALE_CACHE", "warnings": [self._blocked_error]})
                raise OrbitalUnavailable(self._blocked_error)
            try:
                if self.http is None:
                    with httpx.Client(timeout=30) as client:
                        response = client.get(url)
                else:
                    response = self.http.get(url)
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError(f"Unexpected GP HTTP status {response.status_code}")
                fetched = make_record(response.text, url, now, now, "FETCH_TIME")
                record_new = parse_gp(fetched, identifier)
                self.cache.write(url, fetched)
                self._records[identifier] = record_new
                return record_new
            except (httpx.HTTPError, ValueError, OSError) as error:
                self._blocked_error = f"GP queries halted after error; operator action required: {error}"
                if record is not None:
                    stale = record.model_copy(update={"data_status": "STALE_CACHE", "warnings": [self._blocked_error]})
                    self._records[identifier] = stale
                    return stale
                raise OrbitalUnavailable(f"Object {identifier} orbit unavailable: {error}") from error

    def get_encounter_objects(self, encounter: Encounter) -> tuple[OrbitalRecord, OrbitalRecord]:
        objects = (self.get_object(encounter.object_1_id), self.get_object(encounter.object_2_id))
        for record in objects:
            supported, warnings = epoch_suitability(record, encounter.time_of_closest_approach)
            if not supported:
                raise OrbitalUnavailable("Unsuitable orbital epoch: " + "; ".join(warnings))
        return objects
