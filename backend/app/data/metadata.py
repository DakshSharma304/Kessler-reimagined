"""Documented CelesTrak SATCAT types/status/RCS, not GP security markings.

Schema: https://celestrak.org/satcat/satcat-format.php (2026-09-23).
RCS is radar cross section, NOT mass, dimensions or aerodynamic drag area.
"""
import csv
from datetime import UTC,datetime,timedelta
from email.utils import parsedate_to_datetime
import io
import math
import threading
from typing import Literal

import httpx
from pydantic import BaseModel,ConfigDict,Field

from app.data.cache import make_record
from app.data.celestrak import validate_object_id

SATCAT_URL = "https://celestrak.org/pub/satcat.csv"
TYPE_MAP = {"PAY":"PAYLOAD","R/B":"ROCKET_BODY","DEB":"DEBRIS","UNK":"UNKNOWN"}
ObjectClassification = Literal["PAYLOAD","ROCKET_BODY","DEBRIS","UNKNOWN"]
ACTIVE_CODES = frozenset({"+","P","B","S","X"})


class MetadataUnavailable(RuntimeError):
    pass


class ObjectMetadata(BaseModel):
    model_config = ConfigDict(frozen=True,allow_inf_nan=False)
    id: str
    name: str
    classification: ObjectClassification
    source_object_type: str
    operational_status_code: str | None
    decay_date: str | None
    orbit_center: str | None
    orbit_type: str | None
    radar_cross_section_m2: float | None = Field(default=None,ge=0)
    apogee_km: float | None = None
    perigee_km: float | None = None
    mass_kg: float | None = None
    dimensions_m: list[float] | None = None
    aerodynamic_area_m2: float | None = None
    provenance: dict

    @property
    def eligibility_reason(self):
        if self.classification not in {"DEBRIS","ROCKET_BODY"}:
            return "Payloads and uncertain object types are excluded from this removal-assessment MVP"
        if self.operational_status_code in ACTIVE_CODES:
            return "Source indicates an active object; excluded even if object-type metadata conflicts"
        if self.decay_date or self.operational_status_code == "D":
            return "Source marks object decayed"
        if self.orbit_center != "EA" or self.orbit_type != "ORB":
            return "An independently orbiting Earth object is not established (docked/other status excluded)"
        return None


class MetadataDataset(BaseModel):
    records: dict[str,ObjectMetadata]
    provenance: dict
    warnings: list[str]


def parse_metadata(record,mode="CACHE"):
    reader = csv.DictReader(io.StringIO(record.payload.lstrip("\ufeff")))
    required = {"NORAD_CAT_ID","OBJECT_NAME","OBJECT_TYPE","OPS_STATUS_CODE","DECAY_DATE","ORBIT_CENTER","ORBIT_TYPE","RCS"}
    if not reader.fieldnames or not required <= set(reader.fieldnames):
        raise ValueError("SATCAT CSV missing documented critical columns")
    provenance = {"source":"CelesTrak SATCAT","source_url":record.source_url,
        "fetched_at":record.fetched_at.isoformat(),"dataset_timestamp":record.dataset_timestamp.isoformat(),
        "content_sha256":record.content_sha256,"retrieval_mode":mode}
    records = {}
    rejected = duplicates = 0
    for row in reader:
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed SATCAT row")
            identifier = validate_object_id(row["NORAD_CAT_ID"].strip())
            rcs = float(row["RCS"]) if row["RCS"].strip() else None
            if rcs is not None and (not math.isfinite(rcs) or rcs < 0):
                raise ValueError("Invalid radar cross section")
            altitude = {name.lower()+"_km":float(row[name]) if row.get(name,"").strip() else None
                for name in ("APOGEE","PERIGEE")}
            item = ObjectMetadata(id=identifier,name=row["OBJECT_NAME"],
                classification=TYPE_MAP.get(row["OBJECT_TYPE"],"UNKNOWN"),source_object_type=row["OBJECT_TYPE"],
                operational_status_code=row["OPS_STATUS_CODE"].strip() or None,
                decay_date=row["DECAY_DATE"].strip() or None,orbit_center=row["ORBIT_CENTER"].strip() or None,
                orbit_type=row["ORBIT_TYPE"].strip() or None,radar_cross_section_m2=rcs,**altitude,provenance=provenance)
            if identifier in records:
                duplicates += 1
                if records[identifier] != item:
                    # Conflicting classifications must not authorize removal.
                    records[identifier] = item.model_copy(update={"classification":"UNKNOWN"})
            else:
                records[identifier] = item
        except (ValueError,TypeError):
            rejected += 1
    if not records:
        raise ValueError("No usable SATCAT records")
    return MetadataDataset(records=records,provenance=provenance | {"records":len(records),
        "rejected_records":rejected,"duplicate_records":duplicates},warnings=[
        "SATCAT type/status are catalog metadata, not verified removal feasibility.",
        "Radar cross section is not aerodynamic area, dimensions or mass; these remain unknown.",
        "Catalog metadata can lag actual physical/operational status; unknown/conflicting types are not eligible."])


class MetadataClient:
    def __init__(self,cache,http=None):
        self.cache,self.http = cache,http
        self.dataset = None
        self._blocked_error = None
        self._lock = threading.Lock()

    def load(self,now=None):
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Metadata retrieval time must be aware")
        with self._lock:
            if self.dataset is not None and now-datetime.fromisoformat(self.dataset.provenance["fetched_at"]) < timedelta(days=1):
                return self.dataset
            stored = self.cache.read(SATCAT_URL)
            if stored is not None:
                try:
                    cached = parse_metadata(stored)
                    if now-stored.fetched_at < timedelta(days=1):
                        self.dataset = cached
                        return cached
                except ValueError:
                    stored = None
            if self._blocked_error is None:
                try:
                    if self.http is None:
                        with httpx.Client(timeout=45,follow_redirects=True) as http:
                            response = http.get(SATCAT_URL)
                    else:
                        response = self.http.get(SATCAT_URL)
                    response.raise_for_status()
                    modified = response.headers.get("Last-Modified")
                    at = parsedate_to_datetime(modified).astimezone(UTC) if modified else now
                    downloaded = make_record(response.text,SATCAT_URL,now,at,
                        "HTTP_LAST_MODIFIED" if modified else "FETCH_TIME",response.headers.get("ETag"))
                    result = parse_metadata(downloaded,"HTTP")
                    self.cache.write(SATCAT_URL,downloaded)
                    self.dataset = result
                    return result
                except (httpx.HTTPError,ValueError,OSError) as error:
                    self._blocked_error = f"SATCAT queries halted after source failure: {error}"
            if stored is not None:
                result = parse_metadata(stored,"STALE_CACHE")
                result.warnings.append(self._blocked_error)
                self.dataset = result
                return result
            raise MetadataUnavailable(self._blocked_error)
