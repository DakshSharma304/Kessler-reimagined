import pytest
from app.probability.cdm import load_reference, reference_cases, reference_table
from app.probability.reference import evaluate_reference


@pytest.mark.parametrize("case", reference_cases())
def test_precise_genuine_nasa_reference_and_convergence(case):
    normal = evaluate_reference(case, independent_benchmark=True)
    tight = evaluate_reference(case, independent_benchmark=True, relative_tolerance=1e-11)
    expected = reference_table()[case]["Pc2D"]
    # 2e-9 relative: aligned with independently requested numerical accuracy;
    # much stricter than rounded CDM precision; no blanket absolute tolerance.
    assert normal.calculation.status == tight.calculation.status == "CALCULATED"
    assert normal.calculated_pc == pytest.approx(expected, rel=2e-9, abs=0)
    assert tight.calculated_pc == pytest.approx(expected, rel=2e-9, abs=0)
    assert normal.calculated_pc == pytest.approx(tight.calculated_pc, rel=2e-10, abs=0)
    assert normal.calculation.estimated_absolute_error <= normal.calculated_pc * 1e-9
    assert abs(normal.linear_tca_offset_seconds) < .0005
    assert normal.source == "NASA_CARA_HISTORICAL_REFERENCE"
    assert normal.reference_only
    assert normal.state_frame == "EME2000"
    assert any("correlation" in w for w in normal.warnings)
    print("NASA_VALIDATION", case, normal.calculated_pc, expected, normal.relative_difference)


def test_reference_metadata_never_used_as_calculation_answer(monkeypatch):
    from app.probability import reference
    case = reference_cases()[0]
    original = evaluate_reference(case, independent_benchmark=True)
    table = reference_table()
    table[case]["Pc2D"] = .5
    encounter = load_reference(case).model_copy(update={"published_reference_pc": .9})
    monkeypatch.setattr(reference, "reference_table", lambda: table)
    monkeypatch.setattr(reference, "load_reference", lambda _: encounter)
    changed = evaluate_reference(case, independent_benchmark=True)
    assert changed.calculated_pc == original.calculated_pc
    assert changed.published_reference_pc == .5
    assert changed.cdm_rounded_reference_pc == .9
    assert changed.numerical_difference == original.calculated_pc - .5


def test_known_correlations_not_silently_assumed_independent():
    with pytest.raises(ValueError, match="Explicit independent_benchmark"):
        evaluate_reference(reference_cases()[0])
