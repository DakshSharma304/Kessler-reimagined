from datetime import UTC,datetime
import json
from types import SimpleNamespace
from pathlib import Path
import httpx
import numpy as np
import pytest
from app.engine import Engine
from app.persistence import analyze_orbital_persistence,time_in_altitude_bands
from app.physics.persistence_scenarios import PersistenceSettings
from app.physics.propagation import propagate_object
from app.physics.frames import teme_to_gcrs
from test_decay import AT,props,run


def fixture_engine(tmp_path):
    payload = json.loads((Path(__file__).parent/"fixtures/gp_actual.json").read_text())
    def http(request):
        matches = [row for row in payload if str(row["NORAD_CAT_ID"]) == request.url.params.get("CATNR")]
        return httpx.Response(200,json=matches)
    return Engine(tmp_path,httpx.Client(transport=httpx.MockTransport(http)))


def assumed_settings(**changes):
    return PersistenceSettings(**({"horizon_days":.01,"scenario_mode":"COMPARE","weather_mode":"HYPOTHETICAL_CONSTANT",
        "nominal_f107_sfu":150,"nominal_ap":15}|changes))


def test_actual_fixture_gp_full_scenarios_and_provenance(tmp_path):
    engine = fixture_engine(tmp_path)
    start = datetime(2026,10,11,tzinfo=UTC)
    result = analyze_orbital_persistence("53495",props(),assumed_settings(),engine=engine,start_time=start)
    record = engine.celestrak.get_object("53495")
    assert result.initial_state == teme_to_gcrs(propagate_object(record,start))
    assert result.object_id == "53495" and result.object_name
    assert result.provenance["gp"]["content_sha256"] == record.content_sha256
    assert result.prediction_status == "COMPLETE"
    assert len(result.scenario_analysis.scenarios) == 3
    for scenario,metrics in zip(result.scenario_analysis.scenarios,result.persistence_metrics):
        assert scenario.boundary.propagation.samples
        assert metrics["status"] == "NOT_REACHED_WITHIN_HORIZON"
        assert metrics["modeled_time_in_orbit_seconds"] == pytest.approx(864)
        assert sum(metrics["time_in_bands_seconds"].values())+metrics["unclassified_seconds"] == pytest.approx(864)
        assert "instantaneous" in metrics["definition"]
        assert metrics["boundary_crossing_time"] is None


def test_missing_parameters_return_explicit_status(tmp_path):
    result = analyze_orbital_persistence("53495",None,assumed_settings(),engine=fixture_engine(tmp_path),
        start_time=datetime(2026,10,11,tzinfo=UTC))
    assert result.prediction_status == "INSUFFICIENT_OBJECT_PROPERTIES"
    assert result.scenario_analysis is None and result.persistence_metrics == []


def test_instantaneous_altitude_bands_conserve_modeled_time():
    propagation = run(rho=0,duration=1800)
    metrics = time_in_altitude_bands(propagation)
    assert metrics["time_in_bands_seconds"]["250–500 km"] == pytest.approx(1800)
    assert sum(metrics["time_in_bands_seconds"].values()) == pytest.approx(1800)
    with pytest.raises(ValueError): time_in_altitude_bands(propagation,[
        {"name":"A","lower_m":100000,"upper_m":400000},
        {"name":"B","lower_m":300000,"upper_m":600000}])


@pytest.mark.live
@pytest.mark.parametrize("identifier", ["25544","25338"])
def test_actual_catalog_object_msis_persistence(identifier):
    result = analyze_orbital_persistence(identifier,props(),PersistenceSettings(horizon_days=.001),engine=Engine())
    assert result.provenance["gp"]["source"] == "CelesTrak GP"
    assert result.object_id == identifier
    assert result.scenario_analysis.status == "COMPLETE"
    curve = result.scenario_analysis.scenarios[0].boundary.propagation
    assert curve.environment["model"] == "NRLMSIS 2.1"
    assert result.prediction_status == "NOT_REACHED_WITHIN_HORIZON"
    assert curve.samples[0].density_kg_m3 > 0
    print("ACTUAL_CATALOG_PERSISTENCE",identifier,result.object_name,result.gp_epoch.isoformat(),
        result.initial_orbit["geodetic_altitude_m"],curve.samples[0].density_kg_m3,result.prediction_status,curve.elapsed_seconds)
