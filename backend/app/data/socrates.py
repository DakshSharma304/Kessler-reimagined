"""SOCRATES CSV ingestion with explicit SI units and conservative refreshes.

CelesTrak's current usage policy specifies SOCRATES Plus updates every 10–11
hours. Never force-refresh on individual API requests; retain cached predictions
and halt further source queries after errors until an operator restarts the client.
"""

import csv
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
import io
import threading

import httpx
from pydantic import ValidationError

from app.data.cache import CacheRecord, FileCache, make_record
from app.models.encounter import Encounter, EncounterDataset

SOCRATES_URL = "https://celestrak.org/SOCRATES/sort-minRange.csv"
REFRESH_INTERVAL = timedelta(hours=11)
RETRY_INTERVAL = timedelta(hours=1)
REQUIRED_FIELDS = {
    "NORAD_CAT_ID_1", "OBJECT_NAME_1", "DSE_1", "NORAD_CAT_ID_2", "OBJECT_NAME_2",
    "DSE_2", "TCA", "TCA_RANGE", "TCA_RELATIVE_SPEED", "MAX_PROB", "DILUTION",
}


class SourceUnavailable(RuntimeError):
    """No valid real source dataset is available."""


def parse_utc(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    # The published SOCRATES format explicitly defines its naive TCA as UTC.
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def encounter_id(first: str, second: str, tca: datetime) -> str:
    # Canonical pair plus full UTC instant distinguishes repeated conjunctions.
    key = ":".join([*sorted([first, second]), tca.isoformat()])
    return "socrates-" + sha256(key.encode()).hexdigest()[:24]


def optional_number(value: str | None) -> float | None:
    return float(value) if value is not None and value.strip() else None


def parse_dataset(record: CacheRecord) -> EncounterDataset:
    reader = csv.DictReader(io.StringIO(record.payload.lstrip("\ufeff")))
    if reader.fieldnames is None:
        raise ValueError("Missing SOCRATES CSV header")
    reader.fieldnames = [name.strip() for name in reader.fieldnames]
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Duplicate CSV header fields")
    if not REQUIRED_FIELDS <= set(reader.fieldnames):
        raise ValueError("SOCRATES CSV is missing required fields")
    encounters = {}
    invalid_rows = duplicate_rows = 0
    warnings = []
    for number, row in enumerate(reader, start=2):
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Wrong column count")
            first, second = row["NORAD_CAT_ID_1"].strip(), row["NORAD_CAT_ID_2"].strip()
            if not first.isascii() or not second.isascii() or not first.isdecimal() or not second.isdecimal():
                raise ValueError("Invalid catalog ID")
            if int(first) <= 0 or int(second) <= 0 or first == second:
                raise ValueError("Catalog IDs must be positive and distinct")
            tca = parse_utc(row["TCA"])
            dilution = optional_number(row["DILUTION"])
            encounter = Encounter(
                id=encounter_id(first, second, tca),
                object_1_id=first, object_1_name=row["OBJECT_NAME_1"].strip(),
                object_2_id=second, object_2_name=row["OBJECT_NAME_2"].strip(),
                time_of_closest_approach=tca,
                source_miss_distance_m=float(row["TCA_RANGE"]) * 1000,
                source_relative_speed_m_s=float(row["TCA_RELATIVE_SPEED"]) * 1000,
                socrates_max_probability=optional_number(row["MAX_PROB"]),
                source_dse_1_days=optional_number(row["DSE_1"]),
                source_dse_2_days=optional_number(row["DSE_2"]),
                source_dilution_m=None if dilution is None else dilution * 1000,
                dataset_timestamp=record.dataset_timestamp,
            )
            if encounter.id in encounters:
                duplicate_rows += 1
                if encounter != encounters[encounter.id] and len(warnings) < 100:
                    warnings.append(f"Conflicting duplicate at CSV row {number}; first record retained")
            else:
                encounters[encounter.id] = encounter
        except (ValueError, TypeError, ValidationError) as error:
            invalid_rows += 1
            if len(warnings) < 100:
                warnings.append(f"Invalid CSV row {number}: {error}")
    if not encounters:
        raise ValueError("No valid SOCRATES encounters in dataset")
    return EncounterDataset(
        encounters=list(encounters.values()), dataset_timestamp=record.dataset_timestamp,
        fetched_at=record.fetched_at, source_url=record.source_url,
        content_sha256=record.content_sha256, timestamp_basis=record.timestamp_basis,
        invalid_rows=invalid_rows, duplicate_rows=duplicate_rows, warnings=warnings,
    )


class SocratesClient:
    def __init__(self, cache: FileCache, http: httpx.Client | None = None):
        self.cache = cache
        self.http = http
        self._dataset: EncounterDataset | None = None
        self._last_attempt: datetime | None = None
        self._blocked_error: str | None = None
        self._lock = threading.Lock()

    def get_dataset(self, now: datetime | None = None) -> EncounterDataset:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Current time must be timezone-aware")
        with self._lock:
            record = self.cache.read(SOCRATES_URL) if self._dataset is None else None
            if record is not None:
                try:
                    self._dataset = parse_dataset(record)
                except ValueError:
                    record = None
            if self._dataset is not None and now - self._dataset.fetched_at < REFRESH_INTERVAL:
                return self._dataset
            if self._blocked_error is not None:
                if self._dataset is not None:
                    return self._dataset
                raise SourceUnavailable(self._blocked_error)
            if self._last_attempt is not None and now - self._last_attempt < RETRY_INTERVAL:
                if self._dataset is not None:
                    return self._dataset
                raise SourceUnavailable("SOCRATES unavailable; retry is rate-limited")
            self._last_attempt = now
            try:
                if self.http is None:
                    with httpx.Client(timeout=30, follow_redirects=True) as client:
                        response = client.get(SOCRATES_URL)
                else:
                    response = self.http.get(SOCRATES_URL)
                response.raise_for_status()
                modified = response.headers.get("Last-Modified")
                timestamp = parsedate_to_datetime(modified).astimezone(UTC) if modified else now
                record = make_record(
                    response.text, SOCRATES_URL, now, timestamp,
                    "HTTP_LAST_MODIFIED" if modified else "FETCH_TIME",
                    response.headers.get("ETag"),
                )
                dataset = parse_dataset(record)
                self.cache.write(SOCRATES_URL, record)
                self._dataset = dataset
                return dataset
            except (httpx.HTTPError, ValueError, OSError) as error:
                self._blocked_error = f"SOCRATES queries halted after error; operator action required: {error}"
                if self._dataset is None:
                    raise SourceUnavailable(f"SOCRATES unavailable: {error}") from error
                self._dataset = self._dataset.model_copy(update={
                    "data_status": "STALE_CACHE",
                    "encounters": [item.model_copy(update={"data_status": "STALE_CACHE"})
                                   for item in self._dataset.encounters],
                    "warnings": [*self._dataset.warnings, f"Refresh failed; cached data retained: {error}"],
                })
                return self._dataset
