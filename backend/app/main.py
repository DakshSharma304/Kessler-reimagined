"""Start with `python -m uvicorn app.main:app` from backend/."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.visualization_routes import router as visualization_router
from app.config import settings
from app.engine import Engine
from app.data.discovery import EncounterNotFound
from app.data.socrates import SourceUnavailable
from app.data.celestrak import OrbitalUnavailable
from app.data.space_weather import SpaceWeatherUnavailable
from app.physics.encounters import CalculationUnavailable
from app.physics.maneuvers import ManeuverError
from app.physics.propagation import PropagationError

app = FastAPI(title=settings.service, version=settings.version)
app.state.engine = Engine()
app.include_router(router)
app.include_router(visualization_router)


async def scientific_error(_request, error):
    if isinstance(error, EncounterNotFound):
        code, status = 404, "NOT_FOUND"
    elif isinstance(error, (SourceUnavailable, OrbitalUnavailable,SpaceWeatherUnavailable)):
        code, status = 503, "UNAVAILABLE"
    else:
        code, status = 422, "UNSUPPORTED"
    return JSONResponse(status_code=code, content={"status": status, "detail": str(error)})


for error_type in (EncounterNotFound, SourceUnavailable, OrbitalUnavailable,
                   CalculationUnavailable, ManeuverError, PropagationError, ValueError,SpaceWeatherUnavailable):
    app.add_exception_handler(error_type, scientific_error)
