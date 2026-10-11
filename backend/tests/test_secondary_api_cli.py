"""Transport-only HTTP fixtures; every scientific result uses actual GP/solvers."""

from datetime import timedelta
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.api.routes import get_engine
from app.cli import main
from app.main import app
from test_cli import engine, optimize_args
from test_constraints import constraint_input
from test_encounters import actual_case
from test_optimizer import SMALL

GP = Path(__file__).parent / "fixtures" / "gp_actual.json"


@pytest.fixture
def api(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def screen_input(**updates):
    encounter = actual_case()[0]
    return dict(maneuvering_object_id="53495",
        maneuver_time=(encounter.time_of_closest_approach-timedelta(minutes=15)).isoformat(),
        delta_v_rtn_m_s=[0,.1,0], hypothetical_capability_assumed=True,
        post_tca_horizon_hours=.01, coarse_step_seconds=120,
        catalog_selection={"groups":[],"local_files":[str(GP)]}) | updates


def screen_args(request):
    return ["--json","screen","--encounter-id",actual_case()[0].id,
        "--object-id",request["maneuvering_object_id"],"--maneuver-time",request["maneuver_time"],
        "--delta-v-rtn",*[str(value) for value in request["delta_v_rtn_m_s"]],
        "--assume-capability","--catalog-file",str(GP),"--post-tca-horizon-hours",".01",
        "--coarse-step-seconds","120"]


def science(result):
    fields = ["encounter_id","maneuvering_object_id","alert_distance_km","screening_status","screening_complete",
        "screening_window","objects_screened","candidate_objects_refined",
        "additional_close_approaches","newly_introduced","worsened","improved","skipped_objects"]
    payload = {key:result[key] for key in fields}
    # Local retrieval timestamps and elapsed timings differ between requests;
    # compare all calculated event fields, identities, frames and warnings.
    payload["secondary_encounters"] = [{key:value for key,value in event.items() if key != "source"}
                                        for event in result["secondary_encounters"]]
    closest = result["closest_additional_encounter"]
    payload["closest_additional_encounter"] = None if closest is None else {
        key:value for key,value in closest.items() if key != "source"}
    return payload


def test_catalog_status_has_no_download_and_openapi_is_typed(api, engine):
    assert engine.catalog.last_catalog is None
    before = api.get("/api/catalog/status")
    assert before.status_code == 200
    assert before.json()["status"] == "NOT_LOADED"
    assert engine.catalog.last_catalog is None
    schema = api.get("/openapi.json").json()
    path = schema["paths"]["/api/encounters/{encounter_id}/screen"]["post"]
    assert path["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("ScreeningResult")
    assert "secondary_screening" in schema["components"]["schemas"]["OptimizeRequest"]["properties"]
    assert "policy_passed" in schema["components"]["schemas"]["CandidateScreeningAssessment"]["properties"]


def test_actual_gp_screen_api_cli_agree_and_catalog_status_updates(api, engine):
    request = screen_input()
    response = api.post(f"/api/encounters/{actual_case()[0].id}/screen", json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["screening_status"] == "SCREENED_WITHIN_COVERAGE"
    assert result["catalog"]["coverage"] == "PARTIAL"
    assert result["objects_screened"] == 2
    assert result["secondary_encounters"][0]["baseline_miss_distance_m"] > 0
    assert result["secondary_encounters"][0]["change_in_miss_distance_m"] != 0
    assert api.get("/api/catalog/status").json()["catalog"]["objects_available"] == 3
    output = io.StringIO()
    assert main(screen_args(request), engine, output=output) == 0
    assert science(json.loads(output.getvalue())) == science(result)


@pytest.mark.parametrize("updates", [
    {"maneuvering_object_id":"abc"}, {"maneuvering_object_id":"100033"},
    {"delta_v_rtn_m_s":[0,1]}, {"hypothetical_capability_assumed":False},
    {"alert_distance_km":0}, {"post_tca_horizon_hours":25},
    {"catalog_selection":{"groups":["ALL"]}}, {"encounter_id":"different"},
])
def test_invalid_screening_input_rejected_before_catalog_loading(api, engine, updates):
    response = api.post(f"/api/encounters/{actual_case()[0].id}/screen", json=screen_input(**updates))
    assert response.status_code == 422, response.text
    assert engine.catalog.last_catalog is None


def test_unavailable_and_bounded_partial_api_results_do_not_pass(api):
    path = f"/api/encounters/{actual_case()[0].id}/screen"
    empty = api.post(path,json=screen_input(catalog_selection={"groups":[],"local_files":[]}))
    assert empty.status_code == 200, empty.text
    assert empty.json()["screening_status"] == "UNAVAILABLE"
    assert not empty.json()["screening_complete"]
    assert empty.json()["closest_additional_encounter"] is None
    partial = api.post(path,json=screen_input(max_objects=1))
    assert partial.status_code == 200, partial.text
    assert partial.json()["screening_status"] == "INCOMPLETE"
    assert not partial.json()["screening_complete"]
    assert partial.json()["skipped_objects"]


def test_optional_screened_optimizer_api_cli_agree(api, engine):
    encounter = actual_case()[0]
    settings = dict(policy="REPORT_ONLY",max_finalists=2,post_tca_horizon_hours=.01,
        coarse_step_seconds=120,catalog_selection={"groups":[],"local_files":[str(GP)]})
    body = constraint_input(max_lead_time_hours=.5) | {"search":SMALL.model_dump(),"secondary_screening":settings}
    response = api.post(f"/api/encounters/{encounter.id}/optimize",json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["secondary_screening"]["candidates_screened"] == 1
    assert result["secondary_screening"]["candidate_results"][0]["policy_passed"] is True
    args = optimize_args(encounter.id) + ["--max-lead-hours",".5","--secondary-screening","REPORT_ONLY",
        "--catalog-file",str(GP),"--post-tca-horizon-hours",".01","--coarse-step-seconds","120",
        "--screen-max-finalists","2"]
    output = io.StringIO()
    assert main(args,engine,output=output) == 0
    cli = json.loads(output.getvalue())
    assert cli["solutions"] == result["solutions"]
    assert science(cli["secondary_screening"]["candidate_results"][0]["screening"]) == science(
        result["secondary_screening"]["candidate_results"][0]["screening"])


def test_interactive_optional_screening_uses_actual_calculation(engine):
    answers = iter(["1","1","yes",".2",".5","15","10","2",
                    "yes","REPORT_ONLY","5",".01","2",str(GP)])
    output = io.StringIO()
    assert main([],engine,input_fn=lambda prompt:next(answers),output=output) == 0
    text = output.getvalue()
    assert "Secondary policy: REPORT_ONLY; status: COMPLETE" in text
    assert "Catalog objects screened: 2/3" in text
    assert "coverage: PARTIAL" in text
    assert "Screening horizon (UTC)" in text
    assert "original counterpart" in text
    assert "no flight-safety guarantee" in text


def test_catalog_cli_local_only_and_bad_cli_settings(engine):
    output = io.StringIO()
    assert main(["--json","catalog","--catalog-file",str(GP)],engine,output=output) == 0
    assert json.loads(output.getvalue())["objects_available"] == 3
    assert all(source.retrieval_mode == "LOCAL" for source in engine.catalog.last_catalog.metadata.sources)
    output = io.StringIO()
    assert main(screen_args(screen_input())+["--alert-distance-km","-1"],engine,output=output) == 2
    assert json.loads(output.getvalue())["status"] == "ERROR"
