"""Atomic JSON file cache with integrity and fetch-time provenance."""

from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from pydantic import AwareDatetime, BaseModel


class CacheRecord(BaseModel):
    payload: str
    source_url: str
    fetched_at: AwareDatetime
    dataset_timestamp: AwareDatetime
    timestamp_basis: str
    content_sha256: str
    etag: str | None = None


class FileCache:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / f"{sha256(key.encode()).hexdigest()}.json"

    def read(self, key: str) -> CacheRecord | None:
        try:
            record = CacheRecord.model_validate_json(self._path(key).read_text())
            if sha256(record.payload.encode()).hexdigest() != record.content_sha256:
                return None
            return record
        except (OSError, ValueError):
            return None

    def write(self, key: str, record: CacheRecord) -> None:
        if sha256(record.payload.encode()).hexdigest() != record.content_sha256:
            raise ValueError("Cache payload checksum mismatch")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.directory, delete=False,
            ) as output:
                temporary = Path(output.name)
                output.write(record.model_dump_json())
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def make_record(payload: str, source_url: str, fetched_at: datetime,
                dataset_timestamp: datetime, timestamp_basis: str,
                etag: str | None = None) -> CacheRecord:
    return CacheRecord(
        payload=payload, source_url=source_url, fetched_at=fetched_at,
        dataset_timestamp=dataset_timestamp, timestamp_basis=timestamp_basis,
        content_sha256=sha256(payload.encode()).hexdigest(), etag=etag,
    )
