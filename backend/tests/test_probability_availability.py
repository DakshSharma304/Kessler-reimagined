from datetime import timedelta
import numpy as np
import pytest
from app.engine import Engine
from app.physics.encounters import analyze_encounter
from app.physics.propagation import propagate_object
from app.probability.availability import ILLUSTRATIVE_LABEL, ProbabilityInputs, analyze_live_probability
from app.probability.cdm import load_reference, reference_cases
from test_encounters import actual_case


def probability_case():
    e, a, b = actual_case()
    analysis = analyze_encounter(e, a, b)
    return e, propagate_object(a, analysis.calculated.tca), propagate_object(b, analysis.calculated.tca)


def covariance_inputs(e, epoch, kind="ASSUMED"):
    return dict(kind=kind, primary_object_id=e.object_1_id, secondary_object_id=e.object_2_id,
        primary=dict(matrix_m2=(1e8*np.eye(3)).tolist(), frame="RTN", epoch=epoch.isoformat()),
        secondary=dict(matrix_m2=(1e8*np.eye(3)).tolist(), frame="RTN", epoch=epoch.isoformat()),
        combined_hard_body_radius_m=15)


def test_no_covariance_preserves_real_source_metric_separately():
    e, a, b = probability_case()
    result = analyze_live_probability(e, a, b)
    assert result.probability_status == "UNAVAILABLE_NO_COVARIANCE"
    assert result.calculated_pc is None
    assert result.calculation is None
    assert result.assumptions == []
    assert result.socrates_max_probability == e.socrates_max_probability


@pytest.mark.parametrize("kind,status", [("SUPPLIED", "CALCULATED_FROM_SUPPLIED_COVARIANCE"),
                                         ("ASSUMED", "SCENARIO_WITH_ASSUMED_COVARIANCE")])
def test_supplied_vs_hypothetical(kind, status):
    e, a, b = probability_case()
    result = analyze_live_probability(e, a, b, covariance_inputs(e, a.timestamp, kind))
    assert result.probability_status == status
    assert 0 < result.calculated_pc < 1
    assert result.socrates_max_probability == e.socrates_max_probability
    assert (result.label == ILLUSTRATIVE_LABEL) == (kind == "ASSUMED")
    assert any("independent" in a for a in result.assumptions)


@pytest.mark.parametrize("invalid", ["negative", "missing_covariance", "missing_radius", "wrong_id", "bad_units", "missing_frame"])
def test_invalid_cannot_produce_pc(invalid):
    e, a, b = probability_case()
    values = covariance_inputs(e, a.timestamp)
    if invalid == "negative": values["primary"]["matrix_m2"][0][0] = -1
    if invalid == "missing_covariance": del values["secondary"]
    if invalid == "missing_radius": del values["combined_hard_body_radius_m"]
    if invalid == "wrong_id": values["primary_object_id"] = "999"
    if invalid == "bad_units": values["primary"]["units"] = "km2"
    if invalid == "missing_frame": del values["primary"]["frame"]
    result = analyze_live_probability(e, a, b, values)
    assert result.probability_status == "UNAVAILABLE_INVALID_COVARIANCE"
    assert result.calculated_pc is None
    assert result.warnings


def test_epoch_mismatch_and_known_correlation_are_unsupported():
    e, a, b = probability_case()
    values = covariance_inputs(e, a.timestamp)
    values["primary"]["epoch"] = (a.timestamp + timedelta(seconds=1)).isoformat()
    result = analyze_live_probability(e, a, b, values)
    assert result.probability_status == "UNSUPPORTED_MODEL"
    assert result.calculated_pc is None
    values = covariance_inputs(e, a.timestamp)
    values["correlation"] = "CORRELATED"
    result = analyze_live_probability(e, a, b, values)
    assert result.probability_status == "UNSUPPORTED_MODEL"
    assert result.calculated_pc is None


def test_historical_reference_cannot_be_live():
    _, a, b = probability_case()
    with pytest.raises(ValueError, match="Historical NASA"):
        analyze_live_probability(load_reference(reference_cases()[0]), a, b)


@pytest.mark.live
def test_actual_live_socrates_geometry_reports_unavailable():
    engine = Engine()
    e = engine.discovery.list_encounters(sort="minimum_separation", object_id="53495", limit=1)[0]
    e, a, b = engine.selected_case(e.id)
    analysis = analyze_encounter(e, a, b)
    result = analyze_live_probability(e, propagate_object(a, analysis.calculated.tca), propagate_object(b, analysis.calculated.tca))
    assert result.source == "SOCRATES"
    assert result.probability_status == "UNAVAILABLE_NO_COVARIANCE"
    assert result.calculated_pc is None
    assert result.socrates_max_probability == e.socrates_max_probability
    print("ACTUAL_LIVE_PC_AVAILABILITY", e.id, result.model_dump(mode="json"))
