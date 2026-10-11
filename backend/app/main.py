"""Start with `python -m uvicorn app.main:app` from backend/."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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

from app.api.cleanup_routes import router as cleanup_router


async def scientific_error(_request, error):
    if isinstance(error, EncounterNotFound):
        code, status = 404, "NOT_FOUND"
    elif isinstance(error, (SourceUnavailable, OrbitalUnavailable,SpaceWeatherUnavailable)):
        code, status = 503, "UNAVAILABLE"
    else:
        code, status = 422, "UNSUPPORTED"
    return JSONResponse(status_code=code, content={"status": status, "detail": str(error)})


def create_app(config=None):
    config=config or settings
    application=FastAPI(title=config.service,version=config.version)
    application.state.engine=Engine(config=config)
    application.add_middleware(CORSMiddleware,allow_origins=list(config.allowed_origins),
        allow_credentials=False,allow_methods=['GET','POST','OPTIONS'],allow_headers=['Content-Type'])
    application.include_router(router)
    application.include_router(visualization_router)
    application.include_router(cleanup_router)
    for error_type in (EncounterNotFound, SourceUnavailable, OrbitalUnavailable,
        CalculationUnavailable,ManeuverError,PropagationError,ValueError,SpaceWeatherUnavailable):
        application.add_exception_handler(error_type,scientific_error)
    return application

app=create_app()
