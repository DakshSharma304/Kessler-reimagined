"""Bulk GP/local OMM catalogs using existing atomic, integrity-checked caches.

GP datasets are downloaded no more often than every two hours. A source error
halts further network queries in this client until operator action/restart.
Local and cached datasets remain available and retain explicit source metadata.
"""

import csv
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
import io
import json
from pathlib import Path
import threading

import httpx

from app.data.cache import CacheRecord, FileCache, make_record
from app.data.celestrak import GP_REFRESH_INTERVAL, GP_URL, validate_object_id
from app.models.catalog import CatalogMetadata, CatalogSelection, CatalogSource, ScreeningCatalog
from app.models.orbital import GPElements, OrbitalRecord


def parse_catalog(record: CacheRecord, mode="CACHE") -> tuple[dict[str, OrbitalRecord], CatalogSource, list[str]]:
    payload = record.payload.lstrip("\ufeff").strip()
    is_csv = not payload.startswith("[")
    if not is_csv:
        rows = json.loads(payload)
    else:
        reader = csv.DictReader(io.StringIO(payload))
        if not reader.fieldnames or "NORAD_CAT_ID" not in reader.fieldnames:
            raise ValueError("Catalog must be an OMM-compatible JSON array or CSV with NORAD_CAT_ID")
        rows = list(reader)
    if not isinstance(rows, list):
        raise ValueError("Catalog JSON must contain an array of records")
    records = {}
    rejected = duplicates = 0
    warnings = []
    for index, row in enumerate(rows, 1):
        try:
            if not isinstance(row, dict) or None in row:
                raise ValueError("Malformed OMM record")
            if is_csv and "EPHEMERIS_TYPE" in row:
                # DictReader returns text. Normalize the integer-valued OMM
                # field without relaxing GPElements' Literal[0] requirement.
                row = row | {"EPHEMERIS_TYPE": int(row["EPHEMERIS_TYPE"])}
            elements = GPElements.model_validate(row)
            identifier = validate_object_id(elements.object_id)
            elements = elements.model_copy(update={"object_id": identifier})
            elements.initialize_sgp4()
            orbit = OrbitalRecord(elements=elements,
                source="Local OMM" if mode == "LOCAL" else "CelesTrak GP",
                source_url=record.source_url, fetched_at=record.fetched_at,
                content_sha256=record.content_sha256,
                data_status="STALE_CACHE" if mode == "STALE_CACHE" else "VALID",
                warnings=["Dataset retrieval is stale; propagation suitability must be checked separately."] if mode == "STALE_CACHE" else [])
            if identifier in records:
                duplicates += 1
                if orbit.elements.epoch > records[identifier].elements.epoch:
                    records[identifier] = orbit
            else:
                records[identifier] = orbit
        except (ValueError, TypeError, OverflowError) as error:
            rejected += 1
            if len(warnings) < 20:
                warnings.append(f"Rejected OMM record {index}: {str(error).splitlines()[0]}")
    return records, CatalogSource(source_url=record.source_url,
        content_sha256=record.content_sha256, retrieved_at=record.fetched_at,
        dataset_timestamp=record.dataset_timestamp, timestamp_basis=record.timestamp_basis,
        retrieval_mode=mode, usable_records=len(records), rejected_records=rejected,
        duplicate_records=duplicates), warnings


class CatalogLoader:
    def __init__(self, cache: FileCache, http: httpx.Client | None = None):
        self.cache, self.http = cache, http
        self._blocked_error: str | None = None
        self._lock = threading.Lock()
        self.last_catalog: ScreeningCatalog | None = None

    def _group(self, group: str, now: datetime):
        url = f"{GP_URL}?GROUP={group}&FORMAT=JSON"
        cached = self.cache.read(url)
        if cached is not None:
            try:
                parsed = parse_catalog(cached)
                if not parsed[0]:
                    cached = None
            except ValueError:
                cached = None
        if cached is not None and now-cached.fetched_at < GP_REFRESH_INTERVAL:
            return parsed
        if self._blocked_error is None:
            try:
                if self.http is None:
                    with httpx.Client(timeout=60) as client:
                        response = client.get(url)
                else:
                    response = self.http.get(url)
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError(f"Unexpected GP HTTP status {response.status_code}")
                modified = response.headers.get("Last-Modified")
                timestamp = parsedate_to_datetime(modified).astimezone(UTC) if modified else now
                downloaded = make_record(response.text, url, now, timestamp,
                    "HTTP_LAST_MODIFIED" if modified else "FETCH_TIME", response.headers.get("ETag"))
                result = parse_catalog(downloaded, "HTTP")
                if not result[0]:
                    raise ValueError("No usable GP records in downloaded group")
                self.cache.write(url, downloaded)
                return result
            except (httpx.HTTPError, ValueError, OSError) as error:
                self._blocked_error = f"Catalog network queries halted; operator action required: {error}"
        if cached is not None:
            records, source, warnings = parse_catalog(cached, "STALE_CACHE")
            return records, source, [*warnings, self._blocked_error]
        raise ValueError(self._blocked_error)

    def load_screening_catalog(self, selection: CatalogSelection | None = None,
                               now: datetime | None = None) -> ScreeningCatalog:
        selection = selection or CatalogSelection()
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Catalog assembly time must be timezone-aware")
        with self._lock:
            all_records = {}
            sources, warnings, failed = [], [], []
            duplicates = rejected = 0

            def merge(parsed):
                nonlocal duplicates, rejected
                records, source, notes = parsed
                sources.append(source)
                warnings.extend(notes)
                duplicates += source.duplicate_records
                rejected += source.rejected_records
                for identifier, orbit in records.items():
                    if identifier in all_records:
                        duplicates += 1
                        prior = all_records[identifier]
                        # Newest element epoch wins; ties use latest actual retrieval.
                        if (orbit.elements.epoch, orbit.fetched_at) > (prior.elements.epoch, prior.fetched_at):
                            all_records[identifier] = orbit
                    else:
                        all_records[identifier] = orbit

            for group in selection.groups:
                try:
                    merge(self._group(group, now))
                except (ValueError, OSError) as error:
                    failed.append(f"GROUP={group}: {error}")
            for filename in selection.local_files:
                try:
                    path = Path(filename).resolve()
                    modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
                    local = make_record(path.read_text(encoding="utf-8"), path.as_uri(), now,
                        modified, "LOCAL_FILE_MTIME")
                    parsed = parse_catalog(local, "LOCAL")
                    merge(parsed)
                    self.cache.write(path.as_uri(), local)
                    if not parsed[0]:
                        failed.append(f"{path}: no usable OMM records")
                except (OSError, ValueError) as error:
                    failed.append(f"{filename}: {error}")
            if selection.include_cached_records:
                seen = {source.source_url for source in sources}
                for path in sorted(self.cache.directory.glob("*.json")):
                    try:
                        stored = CacheRecord.model_validate_json(path.read_text())
                        if not stored.source_url.startswith(GP_URL + "?") or stored.source_url in seen:
                            continue
                        verified = self.cache.read(stored.source_url)
                        if verified is None:
                            rejected += 1
                            warnings.append(f"Rejected corrupt GP cache: {path.name}")
                            continue
                        mode = "CACHE" if now-verified.fetched_at < GP_REFRESH_INTERVAL else "STALE_CACHE"
                        merge(parse_catalog(verified, mode))
                        seen.add(stored.source_url)
                    except (OSError, ValueError) as error:
                        rejected += 1
                        warnings.append(f"Unreadable cache entry {path.name}: {str(error).splitlines()[0]}")
            epochs = [orbit.elements.epoch for orbit in all_records.values()]
            stale_elements = sum(abs((now-epoch).total_seconds()) > 7*86400 for epoch in epochs)
            if stale_elements:
                warnings.append(f"{stale_elements} records have epochs more than seven days from assembly time; retained but must not be silently screened as current.")
            freshness = "UNAVAILABLE" if not all_records else "STALE" if (
                failed or stale_elements or any(source.retrieval_mode == "STALE_CACHE" for source in sources)) else "FRESH"
            fingerprint = json.dumps([(identifier, orbit.elements.model_dump(mode="json"),
                orbit.source_url, orbit.content_sha256) for identifier, orbit in sorted(all_records.items())],
                sort_keys=True, separators=(",", ":"))
            catalog = ScreeningCatalog(records=all_records, metadata=CatalogMetadata(
                objects_available=len(all_records), freshness_status=freshness,
                sources=sources, snapshot_sha256=sha256(fingerprint.encode()).hexdigest(),
                assembled_at=now, oldest_element_epoch=min(epochs) if epochs else None,
                newest_element_epoch=max(epochs) if epochs else None,
                rejected_record_count=rejected, duplicate_count=duplicates,
                failed_sources=failed, coverage_limitations=[
                    "PARTIAL catalog: only the selected available public GP groups, local OMM datasets and explicitly selected caches.",
                    "GROUP=active does not contain all debris; debris groups cover only their named populations.",
                    "Not all tracked objects have public GP data; untracked and restricted objects are absent.",
                    "No completeness against the full orbiting population has been established.",
                    "Newest element epoch retained per canonical NORAD ID; source datasets may have different retrieval times.",
                ], warnings=list(dict.fromkeys(warnings))))
            self.last_catalog = catalog
            return catalog


def load_screening_catalog(cache: FileCache, selection: CatalogSelection | None = None,
                           http: httpx.Client | None = None, now: datetime | None = None):
    """One-shot loader; retain CatalogLoader for shared error throttling/status."""
    return CatalogLoader(cache, http).load_screening_catalog(selection, now)
