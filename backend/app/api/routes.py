"""API endpoints implemented and verified at each project checkpoint."""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.config import settings
from app.api.schemas import (AnalyzeRequest, EncounterListResponse, OptimizeRequest,
                             ScreenedEncounter, SimulateRequest, StatusResponse,
                             CatalogStatusResponse, ScreenRequest)
from app.data.discovery import SortOrder, quality_warnings
from app.engine import Engine
from app.models.maneuver import ManeuverConstraints
from app.models.orbital import OrbitalRecord
from app.models.screening import ScreeningRequest, ScreeningResult
from app.optimization.optimizer import OptimizationResult, optimize_maneuver
from app.optimization.screened_optimizer import optimize_with_secondary_screening
from app.physics.encounters import BaselineAnalysis, analyze_encounter
from app.physics.maneuvers import ManeuverSimulation, simulate_maneuver
from app.secondary import screen_proposed_maneuver

router = APIRouter(prefix="/api")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["Kessler"]
    version: Literal["0.1.0"]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service, version=settings.version)


def get_engine(request: Request) -> Engine:
    return request.app.state.engine


def view(encounter):
    return ScreenedEncounter(**encounter.model_dump(), warnings=quality_warnings(encounter))


@router.get("/status", response_model=StatusResponse)
def status(engine: Engine = Depends(get_engine)):
    dataset = engine.socrates._dataset
    return StatusResponse(source_status="NOT_LOADED" if dataset is None else dataset.data_status,
        encounters_loaded=0 if dataset is None else len(dataset.encounters),
        cache_directory=str(engine.cache.directory),
        warnings=["Live sources are not checked by the health/status endpoints.",
                  "Secondary encounters have not been assessed."])


@router.get("/catalog/status", response_model=CatalogStatusResponse)
def catalog_status(engine: Engine = Depends(get_engine)):
    catalog = engine.catalog.last_catalog
    return CatalogStatusResponse(status="NOT_LOADED" if catalog is None else "LOADED",
        catalog=None if catalog is None else catalog.metadata,
        warnings=["Reports only the last explicitly loaded catalog; no network request is made.",
                  "Catalog coverage is partial; metadata does not certify any maneuver."])


@router.get("/encounters", response_model=EncounterListResponse)
def list_encounters(sort: SortOrder = "screening", limit: int = Query(50, ge=1, le=1000),
                    object_id: str | None = None, name: str | None = None,
                    engine: Engine = Depends(get_engine)):
    items = engine.discovery.list_encounters(sort, limit, object_id, name)
    dataset = engine.socrates.get_dataset()
    return EncounterListResponse(items=[view(item) for item in items], sort=sort,
        dataset_timestamp=dataset.dataset_timestamp, data_status=dataset.data_status,
        source_url=dataset.source_url, content_sha256=dataset.content_sha256)


@router.get("/encounters/{encounter_id}", response_model=ScreenedEncounter)
def encounter_detail(encounter_id: str, engine: Engine = Depends(get_engine)):
    return view(engine.discovery.get_encounter(encounter_id))


@router.post("/encounters/{encounter_id}/analyze", response_model=BaselineAnalysis)
def analyze(encounter_id: str, request: AnalyzeRequest | None = None,
            engine: Engine = Depends(get_engine)):
    return analyze_encounter(*engine.selected_case(encounter_id),
                             half_window_seconds=(request or AnalyzeRequest()).half_window_seconds)


@router.post("/encounters/{encounter_id}/simulate", response_model=ManeuverSimulation)
def simulate(encounter_id: str, request: SimulateRequest, engine: Engine = Depends(get_engine)):
    return simulate_maneuver(*engine.selected_case(encounter_id), request.maneuvering_object_id,
        request.maneuver_time, request.delta_v_rtn_m_s, request.hypothetical_capability_assumed)


@router.post("/encounters/{encounter_id}/optimize", response_model=OptimizationResult)
def optimize(encounter_id: str, request: OptimizeRequest, engine: Engine = Depends(get_engine)):
    if request.encounter_id != encounter_id:
        raise ValueError("Body encounter_id must match the URL encounter_id")
    constraints = ManeuverConstraints.model_validate(request.model_dump(exclude={"search", "secondary_screening"}))
    case = engine.selected_case(encounter_id)
    if request.secondary_screening is None:
        return optimize_maneuver(*case, constraints, request.search)
    catalog = engine.catalog.load_screening_catalog(request.secondary_screening.catalog_selection)
    return optimize_with_secondary_screening(*case, constraints, request.search,
        secondary_settings=request.secondary_screening, catalog=catalog,
        cache=engine.catalog_propagation_cache)


@router.post("/encounters/{encounter_id}/screen", response_model=ScreeningResult)
def screen(encounter_id: str, request: ScreenRequest, engine: Engine = Depends(get_engine)):
    if request.encounter_id is not None and request.encounter_id != encounter_id:
        raise ValueError("Body encounter_id must match the URL encounter_id")
    settings = ScreeningRequest.model_validate(request.model_dump() | {"encounter_id":encounter_id})
    case = engine.selected_case(encounter_id)
    settings.screening_window(case[0])  # Validate before any bulk download.
    catalog = engine.catalog.load_screening_catalog(settings.catalog_selection)
    return screen_proposed_maneuver(*case, settings, catalog, cache=engine.catalog_propagation_cache)


@router.get("/objects/{object_id}", response_model=OrbitalRecord, response_model_by_alias=False)
def object_detail(object_id: str, engine: Engine = Depends(get_engine)):
    return engine.celestrak.get_object(object_id)
