from fastapi import APIRouter,Depends
from app.api.routes import get_engine
from app.engine import Engine
from app.cleanup import analyze_cleanup
from app.models.cleanup import CleanupRequest,CleanupPortfolio

from app.api.error_schemas import ERROR_RESPONSES
router=APIRouter(prefix='/api',responses=ERROR_RESPONSES)

@router.post('/cleanup/optimize',response_model=CleanupPortfolio)
def cleanup_optimize(request: CleanupRequest,engine: Engine=Depends(get_engine)):
    return analyze_cleanup(engine,request.constraints,request.policy,request.candidate_ids)
