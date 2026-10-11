"""Checkpoint 3 contract and interval gates; no fabricated screening results."""

from datetime import timedelta

import pytest

from app.data.cache import FileCache
from app.data.catalog import CatalogLoader
from app.models.catalog import CatalogSelection
from app.models.screening import ScreeningRequest, ScreeningResult, ScreeningStatus, ScreeningWindow
from test_encounters import START, actual_case


def request(**updates):
    encounter, *_ = actual_case()
    return ScreeningRequest(**(dict(encounter_id=encounter.id, maneuvering_object_id="53495",
        maneuver_time=encounter.time_of_closest_approach-timedelta(hours=2),
        delta_v_rtn_m_s=(0,.2,0), hypothetical_capability_assumed=True) | updates))


def test_request_defaults_identity_window_and_serialization():
    encounter, *_ = actual_case()
    value = request()
    window = value.screening_window(encounter, START)
    assert window.start == value.maneuver_time
    assert window.end == encounter.time_of_closest_approach+timedelta(hours=6)
    assert value.alert_distance_km == 5
    assert request(maneuvering_object_id="053495").maneuvering_object_id == "53495"
    assert ScreeningRequest.model_validate_json(value.model_dump_json()) == value
    assert ScreeningWindow.model_validate_json(window.model_dump_json()) == window


@pytest.mark.parametrize("updates", [
    {"delta_v_rtn_m_s":(0,float("nan"),0)}, {"delta_v_rtn_m_s":(0,0)},
    {"alert_distance_km":0}, {"alert_distance_km":-1},
    {"post_tca_horizon_hours":0}, {"post_tca_horizon_hours":25},
    {"hypothetical_capability_assumed":False}, {"maneuvering_object_id":"bad"},
    {"coarse_step_seconds":121}, {"max_epoch_distance_days":8},
    {"maneuver_time":"2026-10-13T03:09:03"},
])
def test_invalid_request_rejected(updates):
    with pytest.raises(ValueError):
        request(**updates)


def test_membership_encounter_past_and_long_intervals_rejected():
    encounter, *_ = actual_case()
    for updates in ({"maneuvering_object_id":"100033"}, {"encounter_id":"other"},
                    {"maneuver_time":START-timedelta(seconds=1)},
                    {"maneuver_time":encounter.time_of_closest_approach},
                    {"maneuver_time":encounter.time_of_closest_approach-timedelta(hours=47)}):
        with pytest.raises(ValueError):
            request(**updates).screening_window(encounter, START)
    for start, end in ((START,START), (START,START-timedelta(seconds=1)),
                       (START,START+timedelta(hours=49))):
        with pytest.raises(ValueError):
            ScreeningWindow(start=start,end=end)
    assert request(post_tca_horizon_hours=12).screening_window(encounter, START).end == encounter.time_of_closest_approach+timedelta(hours=12)


def empty_result(tmp_path, **updates):
    empty = CatalogLoader(FileCache(tmp_path)).load_screening_catalog(CatalogSelection(groups=()), START)
    value = request()
    encounter, *_ = actual_case()
    return ScreeningResult(**(dict(encounter_id=encounter.id, maneuvering_object_id="53495",
        screening_status="UNAVAILABLE", screening_complete=False, catalog=empty.metadata,
        screening_window=value.screening_window(encounter,START), objects_screened=0,
        candidate_objects_refined=0, additional_close_approaches=0, newly_introduced=0,
        worsened=0, improved=0, closest_additional_encounter=None,
        secondary_encounters=[], elapsed_seconds=0) | updates))


def test_unavailable_empty_results_cannot_be_claimed_complete(tmp_path):
    result = empty_result(tmp_path)
    assert result.screening_status == ScreeningStatus.UNAVAILABLE
    assert not result.screening_complete
    assert result.closest_additional_encounter is None
    assert ScreeningResult.model_validate_json(result.model_dump_json()) == result
    assert any("partial" in text for text in result.model_limitations)
    assert "SAFE" not in {status.value for status in ScreeningStatus}
    with pytest.raises(ValueError):
        empty_result(tmp_path, screening_complete=True, screening_status="SCREENED_WITHIN_COVERAGE")


def test_incomplete_failed_coverage_must_not_be_a_pass(tmp_path):
    from test_encounters import FIXTURES
    catalog = CatalogLoader(FileCache(tmp_path)).load_screening_catalog(
        CatalogSelection(groups=(),local_files=(FIXTURES/"gp_actual.json",)), START)
    metadata = catalog.metadata.model_copy(update={"failed_sources":["Missing requested debris group"]})
    result = empty_result(tmp_path, catalog=metadata, screening_status="INCOMPLETE")
    assert not result.screening_complete
    with pytest.raises(ValueError):
        empty_result(tmp_path, catalog=metadata, screening_status="SCREENED_WITHIN_COVERAGE", screening_complete=True)
    with pytest.raises(ValueError):
        empty_result(tmp_path, catalog=catalog.metadata, screening_status="ALERTS_FOUND", screening_complete=False)
