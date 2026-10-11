from datetime import datetime, timedelta, timezone
import io
import json
import numpy as np
import pytest
from app.api.routes import get_engine
from app.cli import main
from app.main import app
from app.probability.availability import ILLUSTRATIVE_LABEL
from app.probability.cdm import reference_cases, reference_table
from test_api_engine import client
from test_encounters import actual_case
from test_probability_availability import covariance_inputs


def direct_request(kind="SUPPLIED"):
    return dict(kind=kind, tca="2026-10-11T00:00:00Z", frame="GCRS",
        relative_position_m=[0, 0, 0], relative_velocity_m_s=[0, 0, 1000],
        covariance_primary_m2=(.5*np.eye(3)).tolist(), covariance_secondary_m2=(.5*np.eye(3)).tolist(),
        combined_hard_body_radius_m=1)


@pytest.mark.parametrize("case", reference_cases())
def test_reference_through_api(client, case):
    response = client.post("/api/probability/calculate", json={"reference_case":case, "independent_benchmark":True})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["source"] == "NASA_CARA_HISTORICAL_REFERENCE"
    assert result["reference_only"]
    assert result["calculated_pc"] == pytest.approx(reference_table()[case]["Pc2D"], rel=2e-9, abs=0)
    assert result["published_reference_pc"] == reference_table()[case]["Pc2D"]


@pytest.mark.parametrize("kind,status", [("SUPPLIED", "CALCULATED_FROM_SUPPLIED_COVARIANCE"), ("ASSUMED", "SCENARIO_WITH_ASSUMED_COVARIANCE")])
def test_direct_probability_endpoint(client, kind, status):
    response = client.post("/api/probability/calculate", json=direct_request(kind))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["probability_status"] == status
    assert result["calculated_pc"] == pytest.approx(-np.expm1(-.5), rel=1e-9)
    assert result["socrates_max_probability"] is None
    assert (result["label"] == ILLUSTRATIVE_LABEL) == (kind == "ASSUMED")


@pytest.mark.parametrize("invalid", ["radius", "covariance", "negative", "frame", "nan", "epoch"])
def test_invalid_request_422_without_pc(client, invalid):
    values = direct_request()
    if invalid == "radius": del values["combined_hard_body_radius_m"]
    if invalid == "covariance": del values["covariance_primary_m2"]
    if invalid == "negative": values["covariance_primary_m2"][0][0] = -1
    if invalid == "frame": values["frame"] = "RTN"
    if invalid == "nan": values["relative_position_m"][0] = "NaN"
    if invalid == "epoch": values["tca"] = "2026-10-11T00:00:00"
    response = client.post("/api/probability/calculate", json=values)
    assert response.status_code == 422, response.text
    assert "calculated_pc" not in response.json()


def test_reference_requires_ack_and_unknown_case_422(client):
    assert client.post("/api/probability/calculate", json={"reference_case":reference_cases()[0]}).status_code == 422
    assert client.post("/api/probability/calculate", json={"reference_case":"../../README", "independent_benchmark":True}).status_code == 422


def test_opt_in_live_analysis_preserves_default_contract(client):
    e, *_ = actual_case()
    url = f"/api/encounters/{e.id}/analyze"
    original = client.post(url).json()
    assert "probability_analysis" not in original
    enabled = client.post(url, json={"probability_analysis":True})
    assert enabled.status_code == 200, enabled.text
    data = enabled.json()
    probability = data.pop("probability_analysis")
    assert data == original
    assert probability["probability_status"] == "UNAVAILABLE_NO_COVARIANCE"
    assert probability["calculated_pc"] is None
    assert probability["socrates_max_probability"] == e.socrates_max_probability
    epoch = datetime.fromisoformat(original["calculated"]["tca"].replace("Z", "+00:00"))
    scenario = covariance_inputs(e, epoch)
    result = client.post(url, json={"probability_inputs":scenario}).json()["probability_analysis"]
    assert result["probability_status"] == "SCENARIO_WITH_ASSUMED_COVARIANCE"
    assert result["label"] == ILLUSTRATIVE_LABEL


def test_maneuver_response_optional_scenario_preserves_geometry(client):
    e, *_ = actual_case()
    baseline = client.post(f"/api/encounters/{e.id}/analyze").json()
    epoch = datetime.fromisoformat(baseline["calculated"]["tca"].replace("Z", "+00:00"))
    scenario = covariance_inputs(e, epoch) | {"fixed_covariance":True}
    request = dict(maneuvering_object_id=e.object_1_id,
        maneuver_time=(e.time_of_closest_approach-timedelta(hours=2)).isoformat(),
        delta_v_rtn_m_s=[0,.1,0], hypothetical_capability_assumed=True)
    url = f"/api/encounters/{e.id}/simulate"
    original = client.post(url, json=request).json()
    assert "probability_comparison" not in original
    response = client.post(url, json=request | {"probability_scenario":scenario})
    assert response.status_code == 200, response.text
    data = response.json()
    comparison = data.pop("probability_comparison")
    assert data == original
    assert comparison["label"] == ILLUSTRATIVE_LABEL
    assert comparison["delta_pc"] != 0


def test_cli_reference_independent_comparison_and_selection():
    out = io.StringIO()
    case = reference_cases()[0]
    assert main(["--json", "probability", "--reference-case", case, "--independent-benchmark"], output=out) == 0
    result = json.loads(out.getvalue())
    assert result["calculated_pc"] == pytest.approx(reference_table()[case]["Pc2D"], rel=2e-9)
    assert result["numerical_difference"] == result["calculated_pc"] - result["published_reference_pc"]
    human = io.StringIO()
    assert main(["probability", "--reference-case", case, "--independent-benchmark"], output=human) == 0
    assert "Published precise Pc2D" in human.getvalue()
    assert "Independent Kessler Pc" in human.getvalue()
    assert "Historical" in human.getvalue()
    assert main(["probability", "--reference-case", case], output=io.StringIO(), error_output=io.StringIO()) == 2
    cases = io.StringIO()
    assert main(["--json", "probability", "--list-reference-cases"], output=cases) == 0
    assert json.loads(cases.getvalue())["reference_cases"] == reference_cases()


def test_cli_live_availability_and_covariance_file(client, tmp_path):
    engine = app.dependency_overrides[get_engine]()
    e, *_ = actual_case()
    out = io.StringIO()
    assert main(["--json", "probability", "--encounter-id", e.id], engine=engine, output=out) == 0
    original = json.loads(out.getvalue())
    assert original["probability_status"] == "UNAVAILABLE_NO_COVARIANCE"
    epoch = datetime.fromisoformat(original["tca"].replace("Z", "+00:00"))
    values = covariance_inputs(e, epoch)
    path = tmp_path / "assumptions.json"
    path.write_text(json.dumps(values))
    out = io.StringIO()
    assert main(["--json", "probability", "--encounter-id", e.id, "--covariance-file", str(path)], engine=engine, output=out) == 0
    result = json.loads(out.getvalue())
    assert result["label"] == ILLUSTRATIVE_LABEL
    assert result["calculated_pc"] > 0
    out = io.StringIO()
    assert main(["--json", "analyze", "--encounter-id", e.id, "--probability"], engine=engine, output=out) == 0
    assert json.loads(out.getvalue())["probability_analysis"]["probability_status"] == "UNAVAILABLE_NO_COVARIANCE"


def test_cli_maneuver_scenario_and_bad_file(client, tmp_path):
    engine = app.dependency_overrides[get_engine]()
    e, *_ = actual_case()
    baseline = client.post(f"/api/encounters/{e.id}/analyze").json()
    epoch = datetime.fromisoformat(baseline["calculated"]["tca"].replace("Z", "+00:00"))
    path = tmp_path / "fixed.json"
    path.write_text(json.dumps(covariance_inputs(e, epoch) | {"fixed_covariance":True}))
    out = io.StringIO()
    assert main(["--json", "simulate", "--encounter-id", e.id, "--object-id", e.object_1_id,
        "--maneuver-time", (e.time_of_closest_approach-timedelta(hours=2)).isoformat(),
        "--delta-v-rtn", "0", ".1", "0", "--assume-capability", "--probability-scenario-file", str(path)], engine=engine, output=out) == 0
    assert json.loads(out.getvalue())["probability_comparison"]["label"] == ILLUSTRATIVE_LABEL
    assert main(["--json", "probability", "--input-file", str(tmp_path/"missing.json")], output=io.StringIO()) == 2


def test_openapi_schema_references_and_new_models_valid(client):
    schema = client.get("/openapi.json").json()
    json.dumps(schema, allow_nan=False)
    assert "/api/probability/calculate" in schema["paths"]
    assert schema["components"]["schemas"]["DirectProbabilityRequest"]["properties"]["tca"]["format"] == "date-time"
    assert "probability_analysis" in schema["components"]["schemas"]["ProbabilityBaselineAnalysis"]["required"]
    def verify(value):
        if isinstance(value, dict):
            if "$ref" in value:
                target = schema
                for key in value["$ref"].removeprefix("#/").split("/"):
                    target = target[key]
            for child in value.values(): verify(child)
        elif isinstance(value, list):
            for child in value: verify(child)
    verify(schema)


@pytest.mark.live
def test_actual_live_probability_cli():
    from app.engine import Engine
    engine = Engine()
    e = engine.discovery.list_encounters(sort="minimum_separation", object_id="53495", limit=1)[0]
    out = io.StringIO()
    assert main(["--json", "probability", "--encounter-id", e.id], engine=engine, output=out) == 0
    result = json.loads(out.getvalue())
    assert result["probability_status"] == "UNAVAILABLE_NO_COVARIANCE"
    assert result["calculated_pc"] is None
    assert result["socrates_max_probability"] == e.socrates_max_probability
