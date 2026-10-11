"""Bounded atmospheric cutoff detection; never ground impact or certainty."""
from datetime import timedelta
from typing import Literal
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field
from app.data.space_weather import SpaceWeatherUnavailable
from app.physics.decay import (DecayPropagation,DecayUnsupported,DecayModelOutOfValidity,
    DecayNumericalFailure,propagate_orbital_decay)


class BoundaryAnalysis(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    prediction_status: Literal["BOUNDARY_REACHED","NOT_REACHED_WITHIN_HORIZON",
        "INSUFFICIENT_OBJECT_PROPERTIES","INSUFFICIENT_ENVIRONMENT_DATA",
        "INITIAL_STATE_UNSUPPORTED","NUMERICAL_FAILURE","MODEL_OUT_OF_VALIDITY"]
    boundary_altitude_m: float
    crossing_occurred: bool = False
    crossing_time: AwareDatetime | None = None
    modeled_time_until_crossing_seconds: float | None = Field(default=None,ge=0)
    prediction_horizon_days: float = Field(gt=0,le=90)
    propagation: DecayPropagation | None = None
    assumptions: list[str]
    warnings: list[str]


def estimate_boundary_crossing(orbit,physical_properties,environment,prediction_horizon,
        *,boundary_altitude_m=120000,solver_settings=None):
    seconds = prediction_horizon.total_seconds() if isinstance(prediction_horizon,timedelta) else float(prediction_horizon)
    common = {"boundary_altitude_m":boundary_altitude_m,"prediction_horizon_days":seconds/86400,
        "assumptions":["Finite prediction horizon and explicit aerodynamic/environment inputs.",
            "Boundary is a WGS84 geodetic orbital-model cutoff, not breakup or ground impact."],
        "warnings":["Modeled crossing dates are scenario calculations, not precise operational reentry predictions.",
            "Not reaching the boundary within the horizon does not imply perpetual orbital persistence."]}
    if physical_properties is None:
        return BoundaryAnalysis(prediction_status="INSUFFICIENT_OBJECT_PROPERTIES",**common)
    if environment is None:
        return BoundaryAnalysis(prediction_status="INSUFFICIENT_ENVIRONMENT_DATA",**common)
    try:
        propagation = propagate_orbital_decay(orbit,orbit.timestamp,seconds,physical_properties,
            environment,solver_settings,boundary_altitude_m=boundary_altitude_m)
    except SpaceWeatherUnavailable as error:
        common["warnings"].append(str(error))
        return BoundaryAnalysis(prediction_status="INSUFFICIENT_ENVIRONMENT_DATA",**common)
    except DecayModelOutOfValidity as error:
        common["warnings"].append(str(error))
        return BoundaryAnalysis(prediction_status="MODEL_OUT_OF_VALIDITY",**common)
    except DecayUnsupported as error:
        common["warnings"].append(str(error))
        return BoundaryAnalysis(prediction_status="INITIAL_STATE_UNSUPPORTED",**common)
    except (DecayNumericalFailure,FloatingPointError) as error:
        common["warnings"].append(str(error))
        return BoundaryAnalysis(prediction_status="NUMERICAL_FAILURE",**common)
    except ValueError as error:
        common["warnings"].append(str(error))
        return BoundaryAnalysis(prediction_status="MODEL_OUT_OF_VALIDITY",**common)
    reached = propagation.boundary_crossing_time is not None
    return BoundaryAnalysis(prediction_status="BOUNDARY_REACHED" if reached else "NOT_REACHED_WITHIN_HORIZON",
        crossing_occurred=reached,crossing_time=propagation.boundary_crossing_time,
        modeled_time_until_crossing_seconds=(propagation.integrated_end_time-orbit.timestamp).total_seconds() if reached else None,
        propagation=propagation,**common)
