from fastapi import APIRouter,Depends,Query
from pydantic import AwareDatetime
from app.api.routes import get_engine
from app.api.limits import calculation_slot
from app.engine import Engine
from app.data.metadata import ObjectClassification
from app.models.visualization import (CatalogPage,ObjectInfo,PositionRequest,PositionBatch,ObjectTrajectory,
    EncounterTrajectories,ManeuverTrajectoryRequest,ManeuverTrajectories)
from app.visualization import (list_objects,object_info,bulk_positions,object_trajectory,
    encounter_trajectories,maneuver_trajectories)

from app.api.error_schemas import ERROR_RESPONSES
router=APIRouter(prefix='/api',responses=ERROR_RESPONSES)

@router.get('/objects',response_model=CatalogPage)
def objects(search: str | None=Query(None,max_length=100),classification: ObjectClassification | None=None,
    offset: int=Query(0,ge=0,le=1000000),limit: int=Query(100,ge=1,le=500),engine: Engine=Depends(get_engine)):
    return list_objects(engine,search,classification,offset,limit)

@router.post('/positions',response_model=PositionBatch)
def positions(request: PositionRequest,engine: Engine=Depends(get_engine)):
    return bulk_positions(engine,request)

@router.get('/objects/{object_id}/metadata',response_model=ObjectInfo,response_model_by_alias=False)
def metadata(object_id: str,engine: Engine=Depends(get_engine)):
    return object_info(engine,object_id)

@router.get('/objects/{object_id}/trajectory',response_model=ObjectTrajectory)
def trajectory(object_id: str,start_time: AwareDatetime | None=None,end_time: AwareDatetime | None=None,
    sample_count: int=Query(121,ge=2,le=1001),engine: Engine=Depends(get_engine)):
    return object_trajectory(engine,object_id,start_time,end_time,sample_count)

@router.get('/encounters/{encounter_id}/trajectories',response_model=EncounterTrajectories)
def encounter_paths(encounter_id: str,half_window_seconds: float=Query(300,gt=0,le=1800),
    sample_count: int=Query(121,ge=2,le=1001),engine: Engine=Depends(get_engine)):
    return encounter_trajectories(engine,encounter_id,half_window_seconds,sample_count)

@router.post('/encounters/{encounter_id}/trajectories',response_model=ManeuverTrajectories,dependencies=[Depends(calculation_slot)])
def maneuver_paths(encounter_id: str,request: ManeuverTrajectoryRequest,engine: Engine=Depends(get_engine)):
    return maneuver_trajectories(engine,encounter_id,request)
