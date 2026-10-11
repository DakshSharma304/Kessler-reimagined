"""Reject excess scientific work rather than building an unbounded work queue."""
from fastapi import Request

class CalculationBusy(RuntimeError):
    pass

def calculation_slot(request: Request):
    from app.api.routes import get_engine
    override=request.app.dependency_overrides.get(get_engine)
    engine=override() if override else request.app.state.engine
    if not engine.calculation_slots.acquire(blocking=False):
        raise CalculationBusy('Concurrent calculation limit reached; retry after the current calculation completes')
    try: yield
    finally: engine.calculation_slots.release()
