"""Strict reader for the genuine CARA CCSDS 1.0 KVN CDMs shipped here.

States are at the historical CDM TCA, never replaced by current GP elements.
CCSDS CDM CR/CT/CN records are object-local RTN position covariances even
when REF_FRAME (the Cartesian state frame) is EME2000.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import math
import re
from typing import Literal
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

DATA = Path(__file__).with_name("reference_data")
NASA_COMMIT = "ce0f00722c56808755ee0adbe47a4e3d56439484"
NASA_URL = f"https://github.com/nasa/CARA_Analysis_Tools/tree/{NASA_COMMIT}/DataFiles/PcTestCaseCDMs"
Vector3 = tuple[float, float, float]
Matrix3 = tuple[Vector3, Vector3, Vector3]


class ReferenceState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    timestamp: datetime
    position_m: Vector3
    velocity_m_s: Vector3
    frame: Literal["EME2000", "GCRF"]


class CDMObject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    object_id: str
    object_name: str | None
    state: ReferenceState
    covariance_m2: Matrix3
    covariance_frame: Literal["RTN"] = "RTN"
    metadata: dict[str, str]


class ReferenceEncounter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    source: Literal["NASA_CARA_HISTORICAL_REFERENCE"] = "NASA_CARA_HISTORICAL_REFERENCE"
    encounter_id: str
    tca: datetime
    primary: CDMObject
    secondary: CDMObject
    combined_hard_body_radius_m: float | None = Field(default=None, gt=0)
    published_reference_pc: float | None = Field(default=None, ge=0, le=1)
    published_reference_method: str | None
    metadata: dict[str, str]
    source_sha256: str
    warnings: list[str]


def _required(fields: dict[str, str], key: str) -> str:
    if key not in fields or not fields[key].strip():
        raise ValueError(f"CDM missing critical field {key}")
    return fields[key]


def _quantity(value: str, factors: dict[str, float], name: str) -> float:
    match = re.fullmatch(r"\s*([^\s\[]+)\s*\[([^\]]+)\]\s*", value)
    if not match or match[2] not in factors:
        raise ValueError(f"CDM {name}: explicit supported units required")
    number = float(match[1]) * factors[match[2]]
    if not math.isfinite(number):
        raise ValueError(f"CDM {name}: finite value required")
    return number


def _utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # CCSDS CDM time system is UTC (including fixtures with no suffix).
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def parse_cdm(text: str) -> ReferenceEncounter:
    """Read KVN, preserve unknown metadata, reject duplicate scientific fields."""
    header: dict[str, str] = {}
    objects: list[dict[str, str]] = []
    current = header
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        comment = line.startswith("COMMENT ")
        if comment:
            line = line[8:]
        if "=" not in line:
            if comment:
                continue
            raise ValueError(f"CDM malformed KVN record at line {number}")
        key, value = (part.strip() for part in line.split("=", 1))
        if key == "OBJECT":
            if value != f"OBJECT{len(objects) + 1}" or len(objects) >= 2:
                raise ValueError("CDM requires ordered OBJECT1 and OBJECT2 records")
            current = {key: value}
            objects.append(current)
            continue
        if key in current:
            raise ValueError(f"CDM duplicate field {key}")
        current[key] = value
    if _required(header, "CCSDS_CDM_VERS") != "1.0":
        raise ValueError("Unsupported CDM version; expected CCSDS KVN 1.0")
    if len(objects) != 2:
        raise ValueError("CDM requires both object states and covariances")
    if header.get("TIME_SYSTEM", "UTC") != "UTC":
        raise ValueError("Unsupported CDM time system")
    tca = _utc(_required(header, "TCA"))
    parsed = []
    for fields in objects:
        # Optional velocity covariance records remain metadata (the engine is
        # position-only), but malformed supplied covariance records are errors.
        for key, value in fields.items():
            if re.fullmatch(r"C[RTN](?:DOT)?_[RTN](?:DOT)?", key):
                power = key.count("DOT")
                suffix = "" if power == 0 else "/s" if power == 1 else "/s**2"
                _quantity(value, {f"m**2{suffix}": 1, f"km**2{suffix}": 1e6}, key)
        frame = _required(fields, "REF_FRAME")
        if frame not in {"EME2000", "GCRF"}:
            raise ValueError(f"Unsupported CDM state frame {frame}")
        if fields.get("COV_REF_FRAME", "RTN") not in {"RTN", "RIC"}:
            raise ValueError("CR/CT/CN records require object-local RTN/RIC covariance")
        position = tuple(_quantity(_required(fields, k), {"km": 1000, "m": 1}, k) for k in ("X", "Y", "Z"))
        velocity = tuple(_quantity(_required(fields, k), {"km/s": 1000, "m/s": 1}, k) for k in ("X_DOT", "Y_DOT", "Z_DOT"))
        covariance = np.zeros((3, 3))
        for key, i, j in (("CR_R", 0, 0), ("CT_R", 1, 0), ("CT_T", 1, 1),
                          ("CN_R", 2, 0), ("CN_T", 2, 1), ("CN_N", 2, 2)):
            covariance[i, j] = covariance[j, i] = _quantity(_required(fields, key), {"m**2": 1, "km**2": 1e6}, key)
        if np.linalg.eigvalsh(covariance)[0] < 0:
            raise ValueError("CDM position covariance is not positive semidefinite")
        if fields.get("TIME_SYSTEM", "UTC") != "UTC":
            raise ValueError("Unsupported object time system")
        if not re.fullmatch(r"\d{1,9}", _required(fields, "OBJECT_DESIGNATOR")):
            raise ValueError("CDM invalid object identifier")
        parsed.append(CDMObject(object_id=fields["OBJECT_DESIGNATOR"], object_name=fields.get("OBJECT_NAME"),
            state=ReferenceState(timestamp=tca, position_m=position, velocity_m_s=velocity, frame=frame),
            covariance_m2=tuple(map(tuple, covariance)), metadata=fields))
    if parsed[0].state.frame != parsed[1].state.frame:
        raise ValueError("CDM objects require a common supported inertial frame")
    pc = float(header["COLLISION_PROBABILITY"]) if "COLLISION_PROBABILITY" in header else None
    hbr = _quantity(header["HBR"], {"m": 1, "km": 1000}, "HBR") if "HBR" in header else None
    warnings = ["Historical validation data, not a current operational conjunction."]
    if any("DCP Density Forecast Uncertainty" in obj.metadata for obj in parsed):
        warnings.append("DCP common-density correlation metadata present: independence must be explicitly selected only for the NASA independent-model benchmark, not assumed for encounter risk.")
    return ReferenceEncounter(encounter_id=_required(header, "MESSAGE_ID"), tca=tca,
        primary=parsed[0], secondary=parsed[1], combined_hard_body_radius_m=hbr,
        published_reference_pc=pc, published_reference_method=header.get("COLLISION_PROBABILITY_METHOD"),
        metadata=header, source_sha256=sha256(text.encode()).hexdigest(), warnings=warnings)


def reference_cases() -> list[str]:
    return sorted(path.stem for path in DATA.glob("*.cdm"))


def load_reference(case: str) -> ReferenceEncounter:
    if case not in reference_cases():
        raise ValueError(f"Unknown NASA reference case; available: {', '.join(reference_cases())}")
    return parse_cdm((DATA / f"{case}.cdm").read_text())


def reference_table() -> dict[str, dict[str, str | float]]:
    """Read precise published reference metadata, not scientific computation.

    This deliberately targets the shipped one-sheet NASA workbook only, using
    Python's standard library; no spreadsheet dependency or fabricated values.
    """
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(DATA / "CARA_PcMethod_Test_Conjunctions.xlsx") as archive:
        strings = ["".join(si.itertext()) for si in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        rows = ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall("s:sheetData/s:row", ns)
    columns = {}
    result = {}
    for row in rows:
        values = {}
        for cell in row:
            value = cell.find("s:v", ns)
            if value is None:
                continue
            column = re.sub(r"\d", "", cell.attrib["r"])
            values[column] = strings[int(value.text)] if cell.attrib.get("t") == "s" else float(value.text)
        if not columns:
            columns = values
        else:
            record = {columns[k]: v for k, v in values.items() if k in columns}
            result[record["Conjunction_ID"]] = record
    return result
