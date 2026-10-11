"""Stage 12 real public-source pipelines and explicit scientific failure cases."""

from datetime import timedelta
import io
import json
from types import SimpleNamespace

import httpx
import pytest

from app.cli import main
from app.data.cache import FileCache
from app.data.celestrak import CelestrakClient, OrbitalUnavailable
from app.data.discovery import EncounterDiscovery
from app.data.socrates import SocratesClient, SourceUnavailable
from app.engine import Engine
from app.models.maneuver import ManeuverConstraints
from app.optimization.optimizer import SearchSettings, optimize_maneuver
from app.physics.encounters import CalculationUnavailable, analyze_encounter
from app.physics.maneuvers import ManeuverError, simulate_maneuver
from test_constraints import constraint_input
from test_encounters import START, actual_case


def test_source_failures_and_missing_object_never_substituted(tmp_path):
    for body in ([], "not JSON"):
        def fetch(request):
            return httpx.Response(200, json=body) if isinstance(body, list) else httpx.Response(200, text=body)
        with httpx.Client(transport=httpx.MockTransport(fetch)) as http:
            with pytest.raises(OrbitalUnavailable):
                CelestrakClient(FileCache(tmp_path / str(type(body).__name__)), http).get_object("53495")
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as http:
        with pytest.raises(SourceUnavailable):
            SocratesClient(FileCache(tmp_path/"socrates"), http).get_dataset()
        with pytest.raises(OrbitalUnavailable):
            CelestrakClient(FileCache(tmp_path/"gp"), http).get_object("53495")


def test_missing_constraint_object_and_stale_orbits_are_explicit():
    values = constraint_input()
    del values["maneuvering_object_id"]
    with pytest.raises(ValueError):
        ManeuverConstraints(**values)
    encounter, first, second = actual_case()
    stale = first.model_copy(update={"elements": first.elements.model_copy(update={"epoch": first.elements.epoch-timedelta(days=30)})})
    with pytest.raises(CalculationUnavailable, match="epoch"):
        analyze_encounter(encounter, stale, second)


def test_expired_window_and_infeasible_small_budget():
    encounter, first, second = actual_case()
    constraints = ManeuverConstraints(**constraint_input())
    with pytest.raises(ValueError, match="expired"):
        optimize_maneuver(encounter, first, second, constraints, now=encounter.time_of_closest_approach)
    impossible = ManeuverConstraints(**constraint_input(max_delta_v_m_s=0,
        target_miss_distance_km=1000, objective="MINIMUM_DELTA_V"))
    result = optimize_maneuver(encounter, first, second, impossible, now=START)
    assert result.status == "NO_FEASIBLE_SOLUTION"
    assert result.solutions == []
    assert result.candidates_evaluated == 1


def test_integration_solver_failure_returns_no_invented_result(monkeypatch):
    def failed(*args, **kwargs):
        return SimpleNamespace(success=False, message="Injected solver failure")
    monkeypatch.setattr("app.physics.maneuvers.solve_ivp", failed)
    encounter, first, second = actual_case()
    with pytest.raises(ManeuverError, match="Injected solver failure"):
        simulate_maneuver(encounter, first, second, encounter.object_1_id,
            encounter.time_of_closest_approach-timedelta(hours=1), (0,.1,0), True, now=START)


def test_optimization_timeout_is_partial_not_success():
    encounter, first, second = actual_case()
    result = optimize_maneuver(encounter, first, second, ManeuverConstraints(**constraint_input()),
        SearchSettings(timeout_seconds=1e-6), START)
    assert result.status == "PARTIAL"
    assert result.candidates_evaluated == 0
    assert result.solutions == []
    assert any("partial" in warning for warning in result.warnings)


@pytest.mark.live
def test_three_actual_upcoming_encounters_through_cli_with_changed_constraints():
    engine = Engine()
    # These IDs were observed in the actual downloaded dataset. Selection still
    # uses source rows and their IDs/timestamps, not fabricated conjunctions.
    observed_object_ids = ("53495", "53604", "27056")
    selected_ids = set()
    for object_id in observed_object_ids:
        encounters = engine.discovery.list_encounters(sort="minimum_separation", object_id=object_id, limit=5)
        assert encounters, f"No real upcoming source encounters for observed object {object_id}"
        encounter = next(item for item in encounters if item.id not in selected_ids)
        selected_ids.add(encounter.id)
        first, second = engine.celestrak.get_encounter_objects(encounter)
        baseline = analyze_encounter(encounter, first, second)
        assert baseline.calculated.status == "COMPLETE"
        assert first.elements.object_id == encounter.object_1_id
        assert second.elements.object_id == encounter.object_2_id
        outputs = []
        for budget in (.1, .3):
            args = ["--json", "optimize", "--encounter-id", encounter.id,
                "--object-id", object_id, "--max-delta-v", str(budget), "--max-lead-hours", "2",
                "--min-lead-minutes", "15", "--target-km", "10", "--objective", "MAXIMUM_CLEARANCE",
                "--assume-capability", "--time-samples", "2", "--magnitude-samples", "1",
                "--refinement-evaluations", "0"]
            output = io.StringIO()
            code = main(args, engine, output=output)
            assert code == 0, output.getvalue()
            result = json.loads(output.getvalue())
            assert result["status"] == "COMPLETE"
            assert result["solutions"]
            assert result["constraints"]["max_delta_v_m_s"] == budget
            assert result["candidates_evaluated"] == 13
            assert all(item["delta_v_m_s"] <= budget + 1e-12 for item in result["solutions"])
            assert any("Secondary" in text for text in result["model_assumptions"])
            outputs.append(result)
        assert outputs[0]["solutions"][0]["new_miss_distance_m"] != outputs[1]["solutions"][0]["new_miss_distance_m"]
        print("ACTUAL_E2E " + json.dumps({
            "encounter_id": encounter.id, "object_ids": [encounter.object_1_id, encounter.object_2_id],
            "names": [encounter.object_1_name, encounter.object_2_name],
            "published_miss_distance_m": baseline.published.miss_distance_m,
            "sgp4_miss_distance_m": baseline.calculated.miss_distance_m,
            "sgp4_tca": baseline.calculated.tca.isoformat(),
            "source_model_disagreement": baseline.source_model_disagreement,
            "matched_baseline_m": outputs[0]["baseline"]["miss_distance_m"],
            "evaluated_candidates_per_request": outputs[0]["candidates_evaluated"],
            "best_at_0_1_m_s": outputs[0]["solutions"][0]["new_miss_distance_m"],
            "best_at_0_3_m_s": outputs[1]["solutions"][0]["new_miss_distance_m"],
            "runtime_seconds": [output["elapsed_seconds"] for output in outputs],
        }))
    assert len(selected_ids) == 3
