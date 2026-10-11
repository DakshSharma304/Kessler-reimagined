from fastapi import APIRouter,Depends
from app.api.routes import get_engine
from app.api.limits import calculation_slot
from app.engine import Engine
from app.cleanup import analyze_cleanup
from app.models.cleanup import CleanupRequest,CleanupPortfolio

router=APIRouter(prefix='/api')

@router.post('/cleanup/optimize',response_model=CleanupPortfolio,dependencies=[Depends(calculation_slot)])
def cleanup_optimize(request: CleanupRequest,engine: Engine=Depends(get_engine)):
    return analyze_cleanup(engine,request.constraints,request.policy,request.candidate_ids)
