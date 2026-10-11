from datetime import timedelta
import json
from pathlib import Path

from fastapi.testclient import TestClient
import httpx
import pytest

from app.engine import Engine
from app.main import app
from app.api.routes import get_engine
from app.physics.propagation import PropagationError
from test_constraints import constraint_input
from test_encounters import actual_case
from test_optimizer import SMALL

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path):
    records = json.loads((FIXTURES/"gp_actual.json").read_text())
    def fetch(request):
        if "/SOCRATES/" in request.url.path:
            return httpx.Response(200, text=(FIXTURES/"socrates_actual.csv").read_text())
        identifier = request.url.params.get("CATNR")
        return httpx.Response(200, json=[row for row in records if str(row["NORAD_CAT_ID"]) == identifier])
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        engine = Engine(tmp_path, http)
        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with TestClient(app) as client:
                yield client
        finally:
            app.dependency_overrides.clear()


def test_every_endpoint_runs_real_engine(client, monkeypatch):
    import app.api.routes as routes
    calls = {"analyze_encounter": 0, "simulate_maneuver": 0, "optimize_maneuver": 0}
    for function in calls:
        real = getattr(routes, function)
        def observe(*args, _function=function, _real=real, **kwargs):
            calls[_function] += 1
            return _real(*args, **kwargs)
        monkeypatch.setattr(routes, function, observe)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/status").json()["source_status"] == "NOT_LOADED"
    items = client.get("/api/encounters", params={"sort":"max_probability","name":"STARLINK"}).json()["items"]
    assert items
    identifier = items[0]["id"]
    encounter, *_ = actual_case()
    assert identifier == encounter.id
    assert client.get(f"/api/encounters/{identifier}").status_code == 200
    assert client.get("/api/objects/53495").json()["elements"]["object_id"] == "53495"
    baseline = client.post(f"/api/encounters/{identifier}/analyze")
    assert baseline.status_code == 200, baseline.text
    assert baseline.json()["published"]["miss_distance_m"] == 7
    simulated = client.post(f"/api/encounters/{identifier}/simulate", json={
        "maneuvering_object_id":"53495", "maneuver_time":(encounter.time_of_closest_approach-timedelta(hours=1)).isoformat(),
        "delta_v_rtn_m_s":[0,.1,0], "hypothetical_capability_assumed":True})
    assert simulated.status_code == 200, simulated.text
    assert simulated.json()["change_in_miss_distance_m"] != 0
    optimized = client.post(f"/api/encounters/{identifier}/optimize",
        json=constraint_input() | {"search":SMALL.model_dump()})
    assert optimized.status_code == 200, optimized.text
    assert optimized.json()["candidates_evaluated"] == 13
    assert optimized.json()["solutions"]
    assert calls == {name:1 for name in calls}
    schema = client.get("/openapi.json").json()
    # Preserve every old path and verify exactly the five Phase 5 visualization additions.
    assert {path for path in schema["paths"] if path.startswith("/api/")} == {
        "/api/health", "/api/status", "/api/encounters", "/api/encounters/{encounter_id}",
        "/api/encounters/{encounter_id}/analyze", "/api/encounters/{encounter_id}/simulate",
        "/api/encounters/{encounter_id}/optimize", "/api/objects/{object_id}",
        "/api/catalog/status", "/api/encounters/{encounter_id}/screen", "/api/probability/calculate",
        "/api/space-weather/status", "/api/atmosphere/density", "/api/objects/{object_id}/decay",
        "/api/objects/{object_id}/persistence", "/api/objects", "/api/positions",
        "/api/objects/{object_id}/metadata", "/api/objects/{object_id}/trajectory",
        "/api/encounters/{encounter_id}/trajectories"}
    object_ref = schema["paths"]["/api/objects/{object_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    object_schema = schema["components"]["schemas"][object_ref.rsplit("/", 1)[-1]]
    elements_ref = object_schema["properties"]["elements"]["$ref"]
    elements_schema = schema["components"]["schemas"][elements_ref.rsplit("/", 1)[-1]]
    assert "object_id" in elements_schema["properties"]
    assert "NORAD_CAT_ID" not in elements_schema["properties"]


def test_invalid_inputs_unknown_encounters_and_scientific_errors(client, monkeypatch):
    encounter, *_ = actual_case()
    assert client.get("/api/encounters/unknown").status_code == 404
    assert client.get("/api/encounters", params={"limit":0}).status_code == 422
    assert client.get("/api/objects/abc").status_code == 422
    assert client.post(f"/api/encounters/{encounter.id}/optimize", json=constraint_input(max_delta_v_m_s=-1)).status_code == 422
    assert client.post(f"/api/encounters/{encounter.id}/simulate", json={}).status_code == 422
    def failed(*args, **kwargs):
        raise PropagationError("Injected scientific propagation failure")
    monkeypatch.setattr("app.api.routes.analyze_encounter", failed)
    error = client.post(f"/api/encounters/{encounter.id}/analyze")
    assert error.status_code == 422
    assert error.json()["status"] == "UNSUPPORTED"
    assert "propagation failure" in error.json()["detail"]


def test_changed_valid_api_inputs_change_calculation(client):
    encounter, *_ = actual_case()
    url = f"/api/encounters/{encounter.id}/optimize"
    one = client.post(url, json=constraint_input(max_delta_v_m_s=.05) | {"search":SMALL.model_dump()})
    two = client.post(url, json=constraint_input(max_delta_v_m_s=.3) | {"search":SMALL.model_dump()})
    assert one.status_code == two.status_code == 200
    assert one.json()["solutions"][0]["new_miss_distance_m"] != two.json()["solutions"][0]["new_miss_distance_m"]


@pytest.mark.live
def test_actual_public_source_api_smoke():
    # No dependency override: sources come from the production persistent cache
    # or actual CelesTrak, and all HTTP actions call the production calculations.
    assert not app.dependency_overrides
    with TestClient(app) as client:
        listed = client.get("/api/encounters", params={"object_id":"27056", "sort":"minimum_separation", "limit":1})
        assert listed.status_code == 200, listed.text
        encounter = listed.json()["items"][0]
        identifier = encounter["id"]
        assert client.get(f"/api/objects/{encounter['object_1_id']}").status_code == 200
        baseline = client.post(f"/api/encounters/{identifier}/analyze")
        assert baseline.status_code == 200, baseline.text
        tca = datetime_from_iso(encounter["time_of_closest_approach"])
        simulated = client.post(f"/api/encounters/{identifier}/simulate", json={
            "maneuvering_object_id":encounter["object_1_id"], "maneuver_time":(tca-timedelta(hours=1)).isoformat(),
            "delta_v_rtn_m_s":[0,.1,0], "hypothetical_capability_assumed":True})
        assert simulated.status_code == 200, simulated.text
        constraints = constraint_input(encounter_id=identifier, maneuvering_object_id=encounter["object_1_id"])
        optimized = client.post(f"/api/encounters/{identifier}/optimize", json=constraints | {"search":SMALL.model_dump()})
        assert optimized.status_code == 200, optimized.text
        assert optimized.json()["solutions"]
        assert optimized.json()["candidates_evaluated"] == 13
        print(f"Actual API smoke: {identifier}, baseline/analyze/simulate/optimize HTTP 200")


def datetime_from_iso(value):
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
