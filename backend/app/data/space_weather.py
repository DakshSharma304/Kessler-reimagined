"""CelesTrak's documented CSV, retaining flux conventions and missing data.

OBS/INT/PRD/PRM qualify solar flux, NOT independent geomagnetic provenance.
Monthly records are not daily forecasts and are never extrapolated. An as-of
backtest needs a snapshot fetched by that date, not today's revised history.
"""
import csv
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
import io
import threading
from typing import Literal

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from app.data.cache import FileCache, make_record

SPACE_WEATHER_URL = "https://celestrak.org/SpaceData/SW-All.csv"
REFRESH_INTERVAL = timedelta(hours=6)
FLUX_FIELDS = ("F10.7_OBS", "F10.7_ADJ", "F10.7_OBS_CENTER81",
               "F10.7_OBS_LAST81", "F10.7_ADJ_CENTER81", "F10.7_ADJ_LAST81")


class SpaceWeatherUnavailable(RuntimeError):
    pass


class SpaceWeatherRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    date: date
    flux_type: Literal["OBS", "INT", "PRD", "PRM"]
    f107_observed_sfu: float | None = Field(default=None, gt=0)
    f107_adjusted_sfu: float | None = Field(default=None, gt=0)
    f107_observed_center81_sfu: float | None = Field(default=None, gt=0)
    f107_observed_last81_sfu: float | None = Field(default=None, gt=0)
    f107_adjusted_center81_sfu: float | None = Field(default=None, gt=0)
    f107_adjusted_last81_sfu: float | None = Field(default=None, gt=0)
    ap_daily: float | None = Field(default=None, ge=0, le=400)
    ap_3hourly: tuple[float | None, ...]


class SpaceWeatherDataset(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    records: dict[date, SpaceWeatherRecord]
    source_url: str
    fetched_at: AwareDatetime
    dataset_timestamp: AwareDatetime
    timestamp_basis: str
    content_sha256: str
    retrieval_mode: Literal["DOWNLOAD", "CACHE", "STALE_CACHE"]
    warnings: list[str] = Field(default_factory=list)

    def coverage(self):
        observed = [d for d, r in self.records.items() if r.flux_type == "OBS"]
        daily = [d for d, r in self.records.items() if r.flux_type == "PRD"]
        monthly = [d for d, r in self.records.items() if r.flux_type == "PRM"]
        def span(days):
            return None if not days else [min(days).isoformat(), max(days).isoformat()]
        return {"records": len(self.records), "supported_date_range": span(list(self.records)),
                "last_observed_flux_date": None if not observed else max(observed).isoformat(),
                "daily_flux_forecast_coverage": span(daily),
                "monthly_flux_forecast_coverage": span(monthly),
                "cache_timestamp": self.fetched_at.isoformat(),
                "dataset_timestamp": self.dataset_timestamp.isoformat(),
                "source_url": self.source_url, "content_sha256": self.content_sha256,
                "retrieval_mode": self.retrieval_mode, "warnings": self.warnings}


class WeatherLookup(BaseModel):
    status: Literal["AVAILABLE", "MISSING_DATA", "OUTSIDE_COVERAGE", "AS_OF_UNAVAILABLE", "UNSUPPORTED_MONTHLY_FORECAST"]
    record: SpaceWeatherRecord | None = None
    warnings: list[str] = Field(default_factory=list)


def parse_space_weather(record, *, retrieval_mode="CACHE") -> SpaceWeatherDataset:
    reader = csv.DictReader(io.StringIO(record.payload.lstrip("\ufeff")))
    required = {"DATE", "F10.7_DATA_TYPE", "AP_AVG", *FLUX_FIELDS, *[f"AP{i}" for i in range(1, 9)]}
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError("Unsupported space-weather CSV header")
    rows = {}
    for number, row in enumerate(reader, 2):
        try:
            if None in row or any(row[k] is None for k in required):
                raise ValueError("Malformed CSV field count")
            def value(key):
                raw = row[key].strip()
                return None if not raw else float(raw)
            day = date.fromisoformat(row["DATE"])
            if day in rows:
                raise ValueError("Duplicate date")
            rows[day] = SpaceWeatherRecord(date=day, flux_type=row["F10.7_DATA_TYPE"],
                **dict(zip(("f107_observed_sfu", "f107_adjusted_sfu",
                    "f107_observed_center81_sfu", "f107_observed_last81_sfu",
                    "f107_adjusted_center81_sfu", "f107_adjusted_last81_sfu"),
                    [value(k) for k in FLUX_FIELDS])), ap_daily=value("AP_AVG"),
                ap_3hourly=tuple(value(f"AP{i}") for i in range(1, 9)))
            if any(a is not None and not 0 <= a <= 400 for a in rows[day].ap_3hourly):
                raise ValueError("Invalid three-hourly Ap")
        except (ValueError, TypeError) as error:
            raise ValueError(f"Invalid space-weather row {number}: {error}") from error
    if not rows:
        raise ValueError("Empty space-weather dataset")
    return SpaceWeatherDataset(records=rows, source_url=record.source_url,
        fetched_at=record.fetched_at, dataset_timestamp=record.dataset_timestamp,
        timestamp_basis=record.timestamp_basis, content_sha256=record.content_sha256,
        retrieval_mode=retrieval_mode,
        warnings=["Flux qualifier describes solar flux; per-field geomagnetic observation/forecast issue times are not supplied by this CSV.",
                  "Centered 81-day averages can contain forecast/interpolated values; they are not wholly observed inputs."])


class SpaceWeatherClient:
    def __init__(self, cache: FileCache, http: httpx.Client | None = None):
        self.cache, self.http = cache, http
        self.dataset = None
        self._blocked_error = None
        self._lock = threading.Lock()

    def load_space_weather(self, now: datetime | None = None) -> SpaceWeatherDataset:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Aware current timestamp required")
        with self._lock:
            cached = self.cache.read(SPACE_WEATHER_URL)
            old = None
            if cached is not None:
                try:
                    old = parse_space_weather(cached)
                except ValueError:
                    pass
            if old is not None and timedelta(0) <= now - old.fetched_at < REFRESH_INTERVAL:
                self.dataset = old
                return old
            if self._blocked_error is None:
                try:
                    if self.http is None:
                        with httpx.Client(timeout=30) as client:
                            response = client.get(SPACE_WEATHER_URL)
                    else:
                        response = self.http.get(SPACE_WEATHER_URL)
                    response.raise_for_status()
                    if response.status_code != 200:
                        raise ValueError(f"Unexpected weather HTTP status {response.status_code}")
                    modified = response.headers.get("Last-Modified")
                    stamp = parsedate_to_datetime(modified) if modified else now
                    fresh = make_record(response.text, SPACE_WEATHER_URL, now, stamp,
                        "HTTP_LAST_MODIFIED" if modified else "FETCH_TIME", response.headers.get("ETag"))
                    result = parse_space_weather(fresh, retrieval_mode="DOWNLOAD")
                    self.cache.write(SPACE_WEATHER_URL, fresh)
                    self.dataset = result
                    return result
                except (httpx.HTTPError, ValueError, OSError) as error:
                    self._blocked_error = f"Space-weather refresh halted: {error}"
            if old is None:
                raise SpaceWeatherUnavailable(self._blocked_error)
            self.dataset = old.model_copy(update={"retrieval_mode": "STALE_CACHE",
                "warnings": [*old.warnings, self._blocked_error]})
            return self.dataset

    def get_space_weather(self, timestamp: datetime, *, as_of: datetime | None = None) -> WeatherLookup:
        return get_space_weather(timestamp, self.load_space_weather(), as_of=as_of)


def get_space_weather(timestamp: datetime, dataset: SpaceWeatherDataset, *, as_of: datetime | None = None) -> WeatherLookup:
    if timestamp.tzinfo is None or (as_of is not None and as_of.tzinfo is None):
        raise ValueError("Aware timestamps required")
    if as_of is not None and dataset.fetched_at > as_of:
        return WeatherLookup(status="AS_OF_UNAVAILABLE", warnings=["An archived snapshot fetched by the requested as-of time is required; today's revised observations/forecasts cannot be used."])
    day = timestamp.astimezone(UTC).date()
    row = dataset.records.get(day)
    if row is None:
        return WeatherLookup(status="OUTSIDE_COVERAGE", warnings=["No record on requested date; no interpolation or forecast extrapolation."])
    if row.flux_type == "PRM":
        return WeatherLookup(status="UNSUPPORTED_MONTHLY_FORECAST", record=row,
            warnings=["Monthly solar prediction is not a complete daily space-weather forecast."])
    if row.flux_type == "OBS" and day >= dataset.fetched_at.astimezone(UTC).date():
        return WeatherLookup(status="MISSING_DATA", record=row,
            warnings=["Current/future-day observations are not complete; no known future solar activity is assumed."])
    missing = any(x is None for x in (row.f107_observed_sfu, row.f107_observed_center81_sfu, row.ap_daily, *row.ap_3hourly))
    return WeatherLookup(status="MISSING_DATA" if missing else "AVAILABLE", record=row,
        warnings=[*dataset.warnings, "F10.7_OBS is Earth-distance flux in sfu; adjusted and centered/trailing fields remain distinct.",
                  f"Solar flux input category: {row.flux_type}; missing values remain null."])
