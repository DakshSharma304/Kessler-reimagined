from datetime import UTC,datetime
import io
import json
import subprocess
import sys
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.api.routes import get_engine
from app.cli import main
from app.physics.atmosphere import calculate_density
from app.persistence import analyze_orbital_persistence
from app.physics.persistence_scenarios import PersistenceSettings
from test_persistence import fixture_engine,assumed_settings
from test_decay import props
from test_atmosphere import AT,weather


@pytest.fixture
def api(tmp_path):
    engine = fixture_engine(tmp_path)
    app.dependency_overrides[get_engine] = lambda:engine
    try:
        with TestClient(app) as client: yield client,engine
    finally: app.dependency_overrides.clear()


def body():
    return assumed_settings().model_dump(mode="json") | {"aerodynamic_properties":props().model_dump(),
        "start_time":"2026-10-11T00:00:00Z"}


@pytest.mark.parametrize("endpoint", ["decay","persistence"])
def test_real_api_trajectory_matches_service(api,endpoint):
    client,engine = api
    response = client.post(f"/api/objects/53495/{endpoint}",json=body())
    assert response.status_code == 200,response.text
    data = response.json()
    expected = analyze_orbital_persistence("53495",props(),assumed_settings(),engine=engine,start_time=datetime(2026,10,11,tzinfo=UTC))
    assert data["initial_state"] == expected.initial_state.model_dump(mode="json")
    assert data["prediction_status"] == "COMPLETE"
    for result,reference in zip(data["scenario_analysis"]["scenarios"],expected.scenario_analysis.scenarios):
        assert result["boundary"]["propagation"]["samples"] == [s.model_dump(mode="json") for s in reference.boundary.propagation.samples]
        assert result["boundary"]["crossing_time"] is None


def test_api_actual_msis_and_status_no_startup_download(api):
    client,engine = api
    assert client.get("/api/space-weather/status").json()["status"] == "NOT_LOADED"
    response = client.post("/api/atmosphere/density",json={"timestamp":AT.isoformat(),"latitude_deg":40,
        "longitude_deg":-105,"altitude_m":400000,"space_weather":weather().model_dump(mode="json")})
    assert response.status_code == 200,response.text
    assert response.json()["density_kg_m3"] == calculate_density(AT,40,-105,400000,weather()).density_kg_m3


@pytest.mark.parametrize("change", [{"horizon_days":91},{"boundary_altitude_m":70000},
    {"aerodynamic_properties":{"mass_kg":0,"area_m2":1,"drag_coefficient":2.2,"input_category":"HYPOTHETICAL_ASSUMPTION"}},
    {"nominal_ap":-1},{"weather_mode":"HYPOTHETICAL_CONSTANT","nominal_f107_sfu":None},
    {"start_time":"2026-10-11T00:00:00"}])
def test_invalid_api_inputs_422(api,change):
    response = api[0].post("/api/objects/53495/persistence",json=body()|change)
    assert response.status_code == 422


def test_missing_properties_and_density_invalid_inputs(api):
    client,_ = api
    response = client.post("/api/objects/53495/decay",json=body()|{"aerodynamic_properties":None})
    assert response.status_code == 200
    assert response.json()["prediction_status"] == "INSUFFICIENT_OBJECT_PROPERTIES"
    assert response.json()["scenario_analysis"] is None
    assert client.post("/api/atmosphere/density",json={"timestamp":AT.isoformat(),"latitude_deg":91,
        "longitude_deg":0,"altitude_m":400000}).status_code == 422


def test_openapi_all_local_references_resolve(api):
    schema = api[0].get("/openapi.json").json()
    assert len(schema["paths"]) == 20
    def walk(node):
        if isinstance(node,dict):
            if "$ref" in node:
                target = schema
                for part in node["$ref"][2:].split("/"): target = target[part]
            for value in node.values(): walk(value)
        elif isinstance(node,list):
            for value in node: walk(value)
    walk(schema)


def test_cli_noninteractive_and_missing_property_status(api):
    _,engine = api
    output = io.StringIO()
    code = main(["--json","persistence","--object-id","53495","--cd-area-over-mass",".022","--assume-properties",
        "--horizon-days",".01","--scenario-mode","COMPARE","--weather-mode","HYPOTHETICAL_CONSTANT",
        "--nominal-f107","150","--nominal-ap","15","--start-time","2026-10-11T00:00:00Z"],engine=engine,output=output)
    assert code == 0
    assert json.loads(output.getvalue())["prediction_status"] == "COMPLETE"
    output = io.StringIO()
    assert main(["--json","decay","--object-id","53495","--start-time","2026-10-11T00:00:00Z"],engine=engine,output=output) == 0
    assert json.loads(output.getvalue())["prediction_status"] == "INSUFFICIENT_OBJECT_PROPERTIES"


def test_cli_interactive_and_explicit_assumption_required(api):
    _,engine = api
    answers = iter(["53495","100","1","2.2",".001","2"])
    output = io.StringIO()
    assert main(["persistence","--weather-mode","HYPOTHETICAL_CONSTANT","--nominal-f107","150","--nominal-ap","15"],
        engine=engine,input_fn=lambda _:next(answers),output=output) == 0
    assert "Analyze orbital decay / persistence" in output.getvalue()
    assert "NOT_REACHED_WITHIN_HORIZON" in output.getvalue()
    output = io.StringIO()
    assert main(["--json","decay","--object-id","53495","--mass-kg","100","--area-m2","1","--drag-coefficient","2.2"],engine=engine,output=output) == 2
    assert "--assume-properties" in json.loads(output.getvalue())["detail"]


@pytest.mark.live
def test_actual_cli_process_live_object():
    result = subprocess.run([sys.executable,"-m","app.cli","--json","persistence","--object-id","25544",
        "--cd-area-over-mass",".022","--assume-properties","--horizon-days",".001"],capture_output=True,text=True,timeout=60)
    assert result.returncode == 0,result.stderr
    data = json.loads(result.stdout)
    assert data["object_id"] == "25544"
    assert data["prediction_status"] == "NOT_REACHED_WITHIN_HORIZON"
    assert data["scenario_analysis"]["scenarios"][0]["boundary"]["propagation"]["environment"]["model"] == "NRLMSIS 2.1"
