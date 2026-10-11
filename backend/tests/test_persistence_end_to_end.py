"""Final actual-source propagation benchmarks and real HTTP demonstration."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest

from app.persistence_benchmark import benchmark_persistence


@pytest.mark.live
def test_real_data_cases_a_b_c_d_and_horizon_benchmarks():
    report = benchmark_persistence(progress=lambda s:print(s,flush=True))
    # Full evidence available on failure as well as on success; no answer fixtures.
    print("ACTUAL_PERSISTENCE_BENCHMARK",json.dumps(report,allow_nan=False),flush=True)
    assert report["benchmark_status"] == "COMPLETE",report
    runs = report["propagations"]
    assert [r["horizon_days"] for r in runs[:3]] == [1,7,30]
    assert all(r["status"] == "NOT_REACHED_WITHIN_HORIZON" for r in runs[:4])
    assert all(s["environment"]["model"] == "NRLMSIS 2.1" for r in runs for s in r["scenarios"])
    low,high = runs[0]["scenarios"][0],runs[3]["scenarios"][0]
    assert report["objects"]["25544"]["initial_geodetic_altitude_m"] < report["objects"]["25338"]["initial_geodetic_altitude_m"]
    assert low["first_density_kg_m3"] > high["first_density_kg_m3"]
    assert low["energy_change_j_kg"] < high["energy_change_j_kg"] < 0
    assert abs(high["energy_change_j_kg"]) < 10 # Negligible versus ~24 MJ/kg binding energy.
    solar = runs[4]["scenarios"]
    assert solar[2]["first_density_kg_m3"] > solar[0]["first_density_kg_m3"]
    assert solar[2]["energy_change_j_kg"] < solar[0]["energy_change_j_kg"]
    assert runs[5]["scenarios"][0]["energy_change_j_kg"] < low["energy_change_j_kg"]
    # One-day two-tolerance convergence: <1 m numerical discrepancy, not
    # a physical prediction-accuracy guarantee or an uncertainty bound.
    assert report["one_day_convergence_position_m"] < 1
    assert report["space_weather"]["content_sha256"]
    assert all(r["elapsed_seconds"] > 0 for r in runs)


@pytest.mark.live
def test_actual_http_persistence_endpoints(tmp_path):
    with socket.socket() as address:
        address.bind(("127.0.0.1",0))
        port = address.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with (tmp_path/"uvicorn.log").open("w+") as log:
        process = subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app",
            "--host","127.0.0.1","--port",str(port)],cwd=Path(__file__).resolve().parents[1],stdout=log,stderr=log)
        try:
            with httpx.Client(timeout=60,trust_env=False) as client:
                deadline = time.monotonic()+15
                while True:
                    try:
                        response = client.get(base+"/api/health")
                        break
                    except httpx.TransportError:
                        if time.monotonic() >= deadline or process.poll() is not None:
                            log.seek(0)
                            pytest.fail(f"uvicorn did not start: {log.read()}")
                        time.sleep(.05)
                assert response.status_code == 200
                weather = client.get(base+"/api/space-weather/status",params={"load":"true"})
                assert weather.status_code == 200,weather.text
                assert weather.json()["coverage"]
                from datetime import UTC,datetime
                density = client.post(base+"/api/atmosphere/density",json={"timestamp":datetime.now(UTC).isoformat(),
                    "latitude_deg":0,"longitude_deg":0,"altitude_m":400000})
                assert density.status_code == 200,density.text
                assert density.json()["density_kg_m3"] > 0
                body = {"horizon_days":.01,"aerodynamic_properties":{"input_category":"HYPOTHETICAL_ASSUMPTION",
                    "mass_kg":100,"area_m2":1,"drag_coefficient":2.2}}
                for endpoint in ("decay","persistence"):
                    tick = time.perf_counter()
                    result = client.post(base+f"/api/objects/25544/{endpoint}",json=body)
                    elapsed = time.perf_counter()-tick
                    assert result.status_code == 200,result.text
                    data = result.json()
                    assert data["prediction_status"] == "NOT_REACHED_WITHIN_HORIZON"
                    assert data["provenance"]["gp"]["source"] == "CelesTrak GP"
                    assert data["scenario_analysis"]["scenarios"][0]["boundary"]["propagation"]["environment"]["model"] == "NRLMSIS 2.1"
                    print("ACTUAL_HTTP_PERSISTENCE",endpoint,"seconds",elapsed,"status",data["prediction_status"],flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
