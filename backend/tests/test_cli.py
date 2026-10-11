from datetime import timedelta
import io
import json
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from app.cli import main
from app.data.socrates import SourceUnavailable
from app.engine import Engine
from test_encounters import actual_case

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def engine(tmp_path):
    records = json.loads((FIXTURES/"gp_actual.json").read_text())
    def fetch(request):
        if "/SOCRATES/" in request.url.path:
            return httpx.Response(200, text=(FIXTURES/"socrates_actual.csv").read_text())
        return httpx.Response(200, json=[row for row in records if str(row["NORAD_CAT_ID"]) == request.url.params.get("CATNR")])
    with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
        yield Engine(tmp_path, http)


def optimize_args(identifier, budget=".2"):
    return ["--json", "optimize", "--encounter-id", identifier, "--object-id", "53495",
            "--max-delta-v", budget, "--target-km", "10", "--assume-capability",
            "--time-samples", "2", "--magnitude-samples", "1", "--refinement-evaluations", "0"]


def test_cli_help_real_process():
    response = subprocess.run([sys.executable, "-m", "app.cli", "--help"], capture_output=True, text=True, timeout=20)
    assert response.returncode == 0
    assert "optimize" in response.stdout


def test_noninteractive_complete_engine_flow(engine):
    output = io.StringIO()
    assert main(["--json", "list", "--name", "STARLINK"], engine, output=output) == 0
    identifier = json.loads(output.getvalue())["items"][0]["id"]
    output = io.StringIO()
    assert main(["--json", "analyze", "--encounter-id", identifier], engine, output=output) == 0
    assert json.loads(output.getvalue())["published"]["miss_distance_m"] == 7
    output = io.StringIO()
    assert main(optimize_args(identifier), engine, output=output) == 0
    result = json.loads(output.getvalue())
    assert result["encounter_id"] == identifier
    assert result["solutions"] and result["candidates_evaluated"] == 13
    assert result["constraints"]["max_delta_v_m_s"] == .2
    assert any("Secondary" in line for line in result["model_assumptions"])


def test_interactive_workflow_and_invalid_inputs_recover(engine):
    answers = iter(["abc", "1", "invalid", "1", "yes", "bad", ".2", "2", "15", "10", "2"])
    output = io.StringIO()
    assert main([], engine, input_fn=lambda prompt: next(answers), output=output) == 0
    text = output.getvalue()
    assert "Invalid choice" in text and "Invalid number" in text
    assert "SGP4 calculated closest approach" in text
    assert "Best evaluated maneuver" in text
    assert "Model assumptions" in text


def test_invalid_constraints_and_missing_encounter_are_json_errors(engine):
    identifier = actual_case()[0].id
    for args in (optimize_args(identifier, "-1"), ["--json", "analyze", "--encounter-id", "unknown"]):
        output = io.StringIO()
        assert main(args, engine, output=output) == 2
        assert json.loads(output.getvalue())["status"] == "ERROR"


def test_empty_or_unavailable_source_handled(engine, monkeypatch):
    output, errors = io.StringIO(), io.StringIO()
    monkeypatch.setattr(engine.discovery, "list_encounters", lambda **kwargs: [])
    assert main([], engine, output=output, error_output=errors) == 2
    assert "No upcoming" in errors.getvalue()
    def unavailable(*args, **kwargs):
        raise SourceUnavailable("SOCRATES unavailable")
    monkeypatch.setattr(engine.discovery, "list_encounters", unavailable)
    output = io.StringIO()
    assert main(["--json", "list"], engine, output=output) == 2
    assert json.loads(output.getvalue())["status"] == "UNAVAILABLE"


@pytest.mark.live
def test_real_noninteractive_cli_process():
    listing = subprocess.run([sys.executable, "-m", "app.cli", "--json", "list", "--limit", "1"],
                             capture_output=True, text=True, timeout=40)
    assert listing.returncode == 0, listing.stderr + listing.stdout
    data = json.loads(listing.stdout)
    assert data["total_source_encounters"] > 0
    encounter = data["items"][0]
    assert encounter["object_1_id"] == "53495"
    optimized = subprocess.run([sys.executable, "-m", "app.cli", *optimize_args(encounter["id"])],
                              capture_output=True, text=True, timeout=40)
    assert optimized.returncode == 0, optimized.stderr + optimized.stdout
    result = json.loads(optimized.stdout)
    assert result["solutions"]
    print(f"Real CLI: {data['total_source_encounters']} encounters; "
          f"{result['candidates_evaluated']} calculated candidates; "
          f"best clearance {result['solutions'][0]['new_miss_distance_m']:.3f} m")
