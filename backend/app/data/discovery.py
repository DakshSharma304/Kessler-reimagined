"""Transparent filtering and screening of predicted close approaches."""

from datetime import UTC, datetime
from typing import Literal

from app.data.socrates import SocratesClient
from app.models.encounter import Encounter, EncounterDataset

SortOrder = Literal["screening", "max_probability", "minimum_separation", "time"]


class EncounterNotFound(LookupError):
    pass


def quality_warnings(encounter: Encounter) -> list[str]:
    warnings = [
        "Predicted close approach, not a confirmed collision.",
        "SOCRATES MAX_PROB is an external screening metric, not calibrated collision probability.",
        "Current orbital record availability has not yet been verified.",
    ]
    if encounter.data_status == "STALE_CACHE":
        warnings.append("Source refresh failed; this prediction is from the last valid cache.")
    for index, age in enumerate([encounter.source_dse_1_days, encounter.source_dse_2_days], 1):
        if age is None:
            warnings.append(f"Object {index} source element age is unavailable.")
        elif abs(age) > 7:
            warnings.append(f"Object {index} source element age exceeds the seven-day screening caution threshold.")
    return warnings


def has_age_caution(encounter: Encounter) -> bool:
    return any(age is None or abs(age) > 7 for age in (
        encounter.source_dse_1_days, encounter.source_dse_2_days,
    ))


def probability_key(encounter: Encounter):
    value = encounter.socrates_max_probability
    return (value is None, -value if value is not None else 0,
            encounter.source_miss_distance_m, encounter.time_of_closest_approach, encounter.id)


class EncounterDiscovery:
    def __init__(self, client: SocratesClient):
        self.client = client
        self._dataset: EncounterDataset | None = None
        self._by_id: dict[str, Encounter] = {}

    def _load(self) -> list[Encounter]:
        # SourceUnavailable propagates explicitly; absence is never an empty fake dataset.
        dataset = self.client.get_dataset()
        if dataset is not self._dataset:
            self._dataset = dataset
            self._by_id = {item.id: item for item in dataset.encounters}
        return dataset.encounters

    def get_encounter(self, identifier: str) -> Encounter:
        self._load()
        try:
            return self._by_id[identifier]
        except KeyError as error:
            raise EncounterNotFound(f"Unknown encounter ID: {identifier}") from error

    def list_encounters(self, sort: SortOrder = "screening", limit: int = 50,
                        object_id: str | None = None, name: str | None = None,
                        now: datetime | None = None) -> list[Encounter]:
        if sort not in {"screening", "max_probability", "minimum_separation", "time"}:
            raise ValueError("Unknown encounter sort")
        if not 1 <= limit <= 1000:
            raise ValueError("Encounter limit must be between 1 and 1000")
        if object_id is not None and (not object_id.isascii() or not object_id.isdecimal()):
            raise ValueError("Catalog ID must be a numeric string")
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Current time must be timezone-aware")
        encounters = self._load()
        matches = [item for item in encounters
                   if item.time_of_closest_approach >= now
                   and (object_id is None or object_id in {item.object_1_id, item.object_2_id})
                   and (name is None or name.casefold() in item.object_1_name.casefold()
                        or name.casefold() in item.object_2_name.casefold())]
        if sort == "max_probability":
            key = probability_key
        elif sort == "minimum_separation":
            key = lambda item: (item.source_miss_distance_m, item.time_of_closest_approach, item.id)
        elif sort == "time":
            key = lambda item: (item.time_of_closest_approach, item.id)
        else:
            # Lexicographic criteria, never a combined calibrated danger score.
            key = lambda item: (item.data_status != "VALID", has_age_caution(item), *probability_key(item))
        return sorted(matches, key=key)[:limit]
