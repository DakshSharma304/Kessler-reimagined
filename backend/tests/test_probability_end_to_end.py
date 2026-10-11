from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import numpy as np
import pytest
from app.cli import main
from app.engine import Engine
from app.models.maneuver import ManeuverConstraints
from app.models.screening import SecondaryOptimizationSettings
from app.optimization.screened_optimizer import optimize_with_secondary_screening
from app.physics.encounters import analyze_encounter
from app.physics.frames import teme_to_gcrs
from app.physics.maneuvers import simulate_maneuver
from app.physics.propagation import StateVector, propagate_object
from app.probability.cdm import DATA, load_reference, parse_cdm, reference_cases, reference_table
from app.probability.covariance import covariance_in_frame, object_rtn_basis, validate_covariance
from app.probability.engine import calculate_collision_probability
from app.probability.integration import with_live_probability, with_maneuver_probability
from test_optimizer import SMALL
from test_probability_api_cli import client, direct_request
from test_probability_availability import covariance_inputs


@pytest.mark.parametrize("case", reference_cases())
def test_real_cli_process_nasa_pipeline(case):
    completed = subprocess.run([sys.executable, "-m", "app.cli", "--json", "probability",
        "--reference-case", case, "--independent-benchmark"], capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["source"] == "NASA_CARA_HISTORICAL_REFERENCE"
    assert result["calculated_pc"] == pytest.approx(reference_table()[case]["Pc2D"], rel=2e-9, abs=0)


def test_actual_uvicorn_http_probability_pipeline(tmp_path):
    with socket.socket() as address:
        address.bind(("127.0.0.1", 0))
        port = address.getsockname()[1]
    with (tmp_path/"server.log").open("w+") as log:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=Path(__file__).resolve().parents[1], stdout=log, stderr=log)
        try:
            base = f"http://127.0.0.1:{port}"
            ready = False
            deadline = time.monotonic()+15
            with httpx.Client(timeout=10, trust_env=False) as http:
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        ready = http.get(base+"/api/health").status_code == 200
                        if ready: break
                    except httpx.TransportError:
                        time.sleep(.05)
                assert ready, "Actual uvicorn failed to start"
                for case in reference_cases():
                    response = http.post(base+"/api/probability/calculate", json={"reference_case":case, "independent_benchmark":True})
                    assert response.status_code == 200, response.text
                    assert response.json()["calculated_pc"] == pytest.approx(reference_table()[case]["Pc2D"], rel=2e-9, abs=0)
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


@pytest.mark.live
def test_actual_live_geometry_scenario_maneuver_optimizer_and_screening():
    engine = Engine()
    e = engine.discovery.list_encounters(sort="minimum_separation", object_id="53495", limit=1)[0]
    case = engine.selected_case(e.id)
    e, first, second = case
    baseline = analyze_encounter(*case)
    unavailable = with_live_probability(case, baseline).probability_analysis
    assert unavailable.probability_status == "UNAVAILABLE_NO_COVARIANCE"
    assert unavailable.calculated_pc is None
    values = covariance_inputs(e, baseline.calculated.tca)
    # Explicit, hypothetical anisotropic assumptions, not estimates from GP.
    values["primary"]["matrix_m2"] = np.diag([1e7, 1e8, 4e7]).tolist()
    values["secondary"]["matrix_m2"] = np.diag([9e7, 4e8, 2e7]).tolist()
    scenario = with_live_probability(case, baseline, values).probability_analysis
    assert scenario.probability_status == "SCENARIO_WITH_ASSUMED_COVARIANCE"
    simulation = simulate_maneuver(*case, e.object_1_id,
        e.time_of_closest_approach-timedelta(hours=2), (0,.1,0), True)
    comparison = with_maneuver_probability(case, simulation, values | {"fixed_covariance":True}).probability_comparison
    assert comparison.probability_status == "SCENARIO_WITH_ASSUMED_COVARIANCE"
    assert comparison.delta_pc != 0
    assert comparison.original_tca != comparison.modified_tca
    # Independently reconstruct each ORIGINAL object's frozen inertial matrix.
    states = [teme_to_gcrs(propagate_object(record, comparison.original_tca)) for record in (first, second)]
    covariances = [covariance_in_frame(values[name]["matrix_m2"], "RTN", state, "GCRS") for name,state in zip(("primary", "secondary"),states)]
    expected = calculate_collision_probability(simulation.modified.relative_position_m,
        simulation.modified.relative_velocity_m_s, *covariances, 15)
    assert comparison.modified_scenario_pc == pytest.approx(expected.calculated_pc, rel=1e-11, abs=0)
    catalog = engine.catalog.load_screening_catalog()
    settings = SecondaryOptimizationSettings(policy="REPORT_ONLY", max_finalists=1, total_timeout_seconds=10,
        timeout_seconds=5, max_objects=256, post_tca_horizon_hours=.01)
    constraints = ManeuverConstraints(encounter_id=e.id, maneuvering_object_id=e.object_1_id,
        max_delta_v_m_s=.2, min_lead_time_minutes=15, max_lead_time_hours=2,
        target_miss_distance_km=10, objective="MAXIMUM_CLEARANCE", hypothetical_capability_assumed=True)
    result = optimize_with_secondary_screening(*case, constraints, SMALL,
        secondary_settings=settings, catalog=catalog, cache=engine.catalog_propagation_cache)
    assert result.solutions
    assert result.secondary_screening.candidates_screened == 1
    assessed = result.secondary_screening.candidate_results[0]
    assert assessed.screening is not None
    if not assessed.screening.screening_complete:
        assert assessed.policy_passed is None
    print("ACTUAL_PHASE3_E2E", json.dumps({"encounter":e.id,
        "socrates_max_probability":unavailable.socrates_max_probability,
        "live_pc_status":unavailable.probability_status, "assumed_sgp4_pc":scenario.calculated_pc,
        "baseline_scenario_pc":comparison.baseline_pc, "modified_scenario_pc":comparison.modified_scenario_pc,
        "delta_pc":comparison.delta_pc, "original_tca":comparison.original_tca.isoformat(),
        "baseline_tca":comparison.baseline_tca.isoformat(), "modified_tca":comparison.modified_tca.isoformat(),
        "optimization_status":result.status, "candidates_evaluated":result.candidates_evaluated,
        "screening_status":assessed.screening.screening_status, "objects_screened":assessed.screening.objects_screened,
        "catalog_objects":catalog.metadata.objects_available}, allow_nan=False))


def test_benchmark_actual_pc_calculations():
    results = []
    table = reference_table()
    for case in reference_cases():
        encounter = load_reference(case)
        a,b = encounter.primary, encounter.secondary
        c1 = covariance_in_frame(a.covariance_m2, "RTN", a.state, "EME2000")
        c2 = covariance_in_frame(b.covariance_m2, "RTN", b.state, "EME2000")
        r = np.array(a.state.position_m)-b.state.position_m
        v = np.array(a.state.velocity_m_s)-b.state.velocity_m_s
        timings = []
        for _ in range(30):
            start = time.perf_counter()
            pc = calculate_collision_probability(r, v, c1, c2, encounter.combined_hard_body_radius_m)
            timings.append((time.perf_counter()-start)*1000)
            assert pc.calculated_pc == pytest.approx(table[case]["Pc2D"], rel=2e-9, abs=0)
        results.append(dict(case=case, samples=len(timings), median_ms=float(np.median(timings)),
            p95_ms=float(np.percentile(timings,95)), max_relative_reference_error=abs(pc.calculated_pc/table[case]["Pc2D"]-1),
            quadrature_absolute_error=pc.estimated_absolute_error, integrand_evaluations=pc.integrand_evaluations))
    print("ACTUAL_PC_BENCHMARK", json.dumps(results, allow_nan=False))


def test_malformed_optional_cdm_covariance_not_ignored():
    text = (DATA/f"{reference_cases()[0]}.cdm").read_text()
    for line in text.splitlines():
        if line.startswith("CRDOT_R "):
            text = text.replace(line, "CRDOT_R = NaN [m**2/s]", 1)
            break
    with pytest.raises(ValueError, match="finite"):
        parse_cdm(text)


def test_covariance_numeric_range_and_degenerate_gcrs_basis():
    with np.errstate(over="ignore"):
        with pytest.raises(ValueError, match="representation"):
            validate_covariance(np.full((3,3),1e308))
    state = StateVector(timestamp=datetime(2026,10,11,tzinfo=timezone.utc), frame="GCRS",
        position_m=(7e6,0,0), velocity_m_s=(7500,1e-10,0))
    with pytest.raises(ValueError, match="Degenerate"):
        object_rtn_basis(state)


@pytest.mark.parametrize("kind", ["ASSUMED", "SUPPLIED"])
def test_cli_direct_input_file_and_known_inapplicable_api_model(client, tmp_path, kind):
    values = direct_request(kind)
    path = tmp_path/"direct.json"
    path.write_text(json.dumps(values))
    out = io.StringIO()
    assert main(["--json", "probability", "--input-file", str(path)], output=out) == 0
    assert json.loads(out.getvalue())["calculated_pc"] == pytest.approx(-np.expm1(-.5), rel=1e-9)
    response = client.post("/api/probability/calculate", json=values | {"model_applicable":False})
    assert response.status_code == 200
    assert response.json()["probability_status"] == "UNSUPPORTED_MODEL"
    assert response.json()["calculated_pc"] is None
