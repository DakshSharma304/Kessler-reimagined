"""Final real-catalog pipelines, measured runtimes and explicit failure states."""

from datetime import timedelta
import io
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import httpx
import pytest

from app.api.routes import get_engine
from app.cli import main
from app.engine import Engine
from app.main import app
from app.models.catalog import CatalogSelection
from app.models.screening import ScreeningRequest, SecondaryOptimizationSettings
from app.secondary import screen_proposed_maneuver
from app.secondary_benchmark import benchmark_secondary
from test_cli import engine
from test_encounters import START, actual_case
from test_optimizer import SMALL
from test_secondary_api_cli import api, screen_input

FIXTURES = Path(__file__).parent / "fixtures"


def test_secondary_solver_failure_is_explicit_not_fabricated_success(api, monkeypatch):
    def failed(*args, **kwargs):
        return SimpleNamespace(success=False,message="Injected secondary solver failure")
    monkeypatch.setattr("app.physics.maneuvers.solve_ivp",failed)
    response = api.post(f"/api/encounters/{actual_case()[0].id}/screen",json=screen_input())
    assert response.status_code == 422
    assert "secondary solver failure" in response.json()["detail"]
    assert "screening_complete" not in response.json()


def test_stale_secondary_epoch_is_reported_as_incomplete(engine):
    encounter, first, second = actual_case()
    catalog = engine.catalog.load_screening_catalog(CatalogSelection(groups=(),local_files=(FIXTURES/"gp_actual.json",)),START)
    third = catalog.records["100033"]
    catalog.records["100033"] = third.model_copy(update={"elements":third.elements.model_copy(
        update={"epoch":third.elements.epoch-timedelta(days=30)})})
    request = ScreeningRequest(**screen_input(),encounter_id=encounter.id)
    result = screen_proposed_maneuver(encounter,first,second,request,catalog,now=START)
    assert result.screening_status == "INCOMPLETE"
    assert not result.screening_complete
    assert "epoch" in result.skipped_objects["100033"]


def test_stale_primary_source_is_not_silently_screened(engine):
    encounter, first, second = actual_case()
    catalog = engine.catalog.load_screening_catalog(CatalogSelection(groups=(),local_files=(FIXTURES/"gp_actual.json",)),START)
    request = ScreeningRequest(**screen_input(),encounter_id=encounter.id)
    stale = first.model_copy(update={"data_status":"STALE_CACHE"})
    with pytest.raises(ValueError,match="Primary orbital source refresh failed"):
        screen_proposed_maneuver(encounter,stale,second,request,catalog,now=START)


def test_selected_counterpart_snapshot_difference_is_disclosed(engine):
    encounter, first, second = actual_case()
    catalog = engine.catalog.load_screening_catalog(CatalogSelection(groups=(),local_files=(FIXTURES/"gp_actual.json",)),START)
    # Deliberately altered test input, not a claim about a live GP dataset.
    different = second.model_copy(update={"elements":second.elements.model_copy(
        update={"mean_anomaly_deg":(second.elements.mean_anomaly_deg+.01)%360}),
        "content_sha256":"constructed-test-record"})
    request = ScreeningRequest(**screen_input(),encounter_id=encounter.id)
    result = screen_proposed_maneuver(encounter,first,different,request,catalog,now=START)
    assert any("Original counterpart's catalog elements differ" in warning and
               "constructed-test-record" in warning for warning in result.warnings)
    assert result.alert_distance_km == request.alert_distance_km


def test_catalog_download_failure_remains_unavailable_and_halts_network(tmp_path):
    calls = []
    rows = json.loads((FIXTURES/"gp_actual.json").read_text())
    def fetch(request):
        if "/SOCRATES/" in request.url.path:
            return httpx.Response(200,text=(FIXTURES/"socrates_actual.csv").read_text())
        if "GROUP" in request.url.params:
            calls.append(str(request.url))
            return httpx.Response(503)
        return httpx.Response(200,json=[row for row in rows if str(row["NORAD_CAT_ID"])==request.url.params.get("CATNR")])
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        engine = Engine(tmp_path,http)
        case = engine.selected_case(actual_case()[0].id)
        catalog = engine.catalog.load_screening_catalog()
        request = ScreeningRequest(**screen_input(),encounter_id=case[0].id)
        result = screen_proposed_maneuver(*case,request,catalog)
        assert len(calls) == 1
        assert result.screening_status == "UNAVAILABLE"
        assert not result.screening_complete
        assert catalog.metadata.failed_sources
        assert not result.secondary_encounters


def test_measured_secondary_benchmark_uses_actual_fixture_and_phase1_search(engine):
    settings = SecondaryOptimizationSettings(post_tca_horizon_hours=.01,coarse_step_seconds=30,
        catalog_selection=CatalogSelection(groups=(),local_files=(FIXTURES/"gp_actual.json",)))
    report = benchmark_secondary(engine,actual_case()[0].id,"53495",settings,SMALL)
    assert report["secondary_status"] == "COMPLETE"
    assert report["primary_candidates_evaluated"] == 13
    assert report["maneuvers_screened"] == 1
    assert report["candidates"][0]["objects_considered"] == 2
    assert report["candidates"][0]["objects_refined"] == 2
    assert all(report["candidates"][0]["timings_seconds"][key] >= 0 for key in
        ("catalog_propagation","coarse_screening","refinement","comparison","trajectory_generation"))
    assert report["optimizer_and_screening_seconds"] >= report["candidates"][0]["screening_seconds"]
    assert report["catalog_load_seconds"] > 0


@pytest.mark.live
def test_three_real_encounters_broader_catalog_and_actual_runtime_measurements():
    engine = Engine()
    identifiers = set()
    for object_id in ("53495","53604","27056"):
        report = benchmark_secondary(engine,object_id=object_id)
        identifiers.add(report["encounter_id"])
        assert report["source_encounters"] > 0
        assert report["catalog"]["objects_available"] > 1000
        assert report["catalog"]["coverage"] == "PARTIAL"
        assert report["solutions"]  # REPORT_ONLY, not a screening-policy pass.
        assert report["maneuvers_screened"] == 1
        screen = report["candidates"][0]
        assert screen["status"] in {"SCREENED_WITHIN_COVERAGE","ALERTS_FOUND","INCOMPLETE"}
        assert screen["screening_seconds"] > 0
        assert screen["timings_seconds"]["catalog_propagation"] > 0
        assert screen["timings_seconds"]["refinement"] > 0
        if screen["status"] == "INCOMPLETE":
            assert screen["policy_passed"] is None
            assert screen["skipped_reasons"]
        else:
            assert screen["policy_passed"] is True
        assert 0 <= screen["objects_refined"] <= screen["objects_considered"] <= report["catalog"]["objects_available"]
        assert "SAFE" not in screen["status"]
        print("ACTUAL_PHASE2_E2E " + json.dumps(report,allow_nan=False))
    assert len(identifiers) == 3


@pytest.mark.live
def test_actual_broader_catalog_api_and_cli_demonstrations():
    # Dependency injection uses a real production Engine, without HTTP mocks.
    engine = Engine()
    encounter = engine.discovery.list_encounters(sort="minimum_separation",object_id="53495",limit=1)[0]
    output = io.StringIO()
    code = main(["--json","optimize","--encounter-id",encounter.id,"--object-id","53495",
        "--max-delta-v",".2","--target-km","10","--min-lead-minutes","10","--max-lead-hours",".25",
        "--assume-capability","--time-samples","2","--magnitude-samples","1","--refinement-evaluations","0",
        "--secondary-screening","REPORT_ONLY","--post-tca-horizon-hours",".01",
        "--screen-timeout-seconds","15"],engine,output=output)
    assert code == 0, output.getvalue()
    result = json.loads(output.getvalue())
    assert result["solutions"]
    candidate = result["secondary_screening"]["candidate_results"][0]
    assert candidate["screening"]["catalog"]["objects_available"] > 1000
    app.dependency_overrides[get_engine] = lambda:engine
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/encounters/{encounter.id}/screen",json={
                "maneuvering_object_id":"53495","maneuver_time":candidate["maneuver_time"],
                "delta_v_rtn_m_s":candidate["delta_v_rtn_m_s"],"hypothetical_capability_assumed":True,
                "post_tca_horizon_hours":.01,"timeout_seconds":15})
            assert response.status_code == 200, response.text
            screen = response.json()
            assert screen["catalog"]["objects_available"] > 1000
            assert screen["catalog"]["coverage"] == "PARTIAL"
            assert not screen["screening_complete"] if screen["screening_status"] == "INCOMPLETE" else screen["screening_complete"]
            status = client.get("/api/catalog/status")
            assert status.status_code == 200 and status.json()["status"] == "LOADED"
            print("ACTUAL_PHASE2_TRANSPORT " + json.dumps({"encounter_id":encounter.id,
                "catalog_objects":screen["catalog"]["objects_available"],"api_status":screen["screening_status"],
                "api_objects_screened":screen["objects_screened"],"api_seconds":screen["elapsed_seconds"],
                "cli_status":candidate["screening"]["screening_status"],
                "cli_objects_screened":candidate["screening"]["objects_screened"],
                "cli_seconds":candidate["screening"]["elapsed_seconds"]}))
    finally:
        app.dependency_overrides.clear()
