from datetime import timezone
import numpy as np
import pytest
from app.probability.cdm import DATA, load_reference, parse_cdm, reference_cases, reference_table

TERRA = "000025994_conj_000037558_20210324_151047_20210323_154356"


@pytest.mark.parametrize("case", reference_cases())
def test_genuine_nasa_fixture(case):
    encounter = load_reference(case)
    assert encounter.source == "NASA_CARA_HISTORICAL_REFERENCE"
    assert encounter.tca.tzinfo == timezone.utc
    assert encounter.tca.year < 2024
    for obj in (encounter.primary, encounter.secondary):
        assert obj.state.timestamp == encounter.tca
        assert obj.state.frame == "EME2000"
        assert obj.covariance_frame == "RTN"
        assert 6e6 < np.linalg.norm(obj.state.position_m) < 9e6
        assert 5000 < np.linalg.norm(obj.state.velocity_m_s) < 9000
        assert np.linalg.eigvalsh(obj.covariance_m2)[0] > 0
    assert encounter.combined_hard_body_radius_m == pytest.approx(reference_table()[case]["HBR_m"])
    # Four significant digits in the actual CDM, unlike the precise workbook.
    assert encounter.published_reference_pc == pytest.approx(reference_table()[case]["Pc2D"], rel=5e-4)


def test_exact_values_units_and_correlation_metadata_preserved():
    e = load_reference(TERRA)
    assert e.primary.object_id == "000025994"
    assert e.secondary.object_id == "000037558"
    assert e.primary.state.position_m[0] == pytest.approx(31469.755321311194)
    assert e.primary.state.velocity_m_s[0] == pytest.approx(7032.447307172805)
    assert e.primary.covariance_m2[0][0] == pytest.approx(12.65652366685803)
    assert e.published_reference_pc == 0.02117
    assert e.combined_hard_body_radius_m == 15
    assert "DCP Density Forecast Uncertainty" in e.primary.metadata
    assert any("correlation" in w for w in e.warnings)


@pytest.mark.parametrize("old,new,error", [
    ("CR_R                                        = 1.265652366685803010e+01 [m**2]", "CR_R = -1 [m**2]", "semidefinite"),
    ("REF_FRAME                                   = EME2000", "REF_FRAME = ITRF", "frame"),
    ("[m**2]", "[km/s]", "units"),
    ("[km]", "", "units"),
    ("X_DOT", "MISSING_VELOCITY", "critical"),
    ("CT_R", "MISSING_COVARIANCE", "critical"),
    ("CCSDS_CDM_VERS                              = 1.0", "CCSDS_CDM_VERS = 9.0", "version"),
])
def test_invalid_cdm_rejected(old, new, error):
    text = (DATA / f"{TERRA}.cdm").read_text()
    assert old in text
    with pytest.raises(ValueError, match=error):
        parse_cdm(text.replace(old, new))


def test_missing_optional_data_not_invented_and_duplicate_rejected():
    text = (DATA / f"{TERRA}.cdm").read_text()
    stripped = "\n".join(line for line in text.splitlines() if not line.startswith(("COMMENT HBR", "COLLISION_PROBABILITY ")))
    e = parse_cdm(stripped)
    assert e.combined_hard_body_radius_m is None
    assert e.published_reference_pc is None
    with pytest.raises(ValueError, match="duplicate"):
        parse_cdm(text + "\nCN_N = 1 [m**2]\n")
    with pytest.raises(ValueError, match="Unknown NASA"):
        load_reference("../README")
