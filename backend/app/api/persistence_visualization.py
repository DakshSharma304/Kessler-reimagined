"""Opt-in compact Earth-fixed view, with original scientific results unmodified."""
from pydantic import BaseModel
import numpy as np
from app.models.visualization import ObjectTrajectory,PositionSample
from app.persistence import PersistenceAnalysis
from app.visualization import itrs_positions,FRAME_WARNINGS

class PersistenceVisualization(BaseModel):
    object_id: str
    prediction_status: str
    analysis: dict
    trajectories: dict[str,ObjectTrajectory]
    warnings: list[str]

def visualization_view(result: PersistenceAnalysis):
    analysis=result.model_dump(mode='json')
    trajectories={}
    if result.scenario_analysis is not None:
        for index,scenario in enumerate(result.scenario_analysis.scenarios):
            curve=scenario.boundary.propagation
            if curve is None: continue
            samples=curve.samples
            selected=sorted(set(np.linspace(0,len(samples)-1,min(1001,len(samples)),dtype=int)))
            states=[samples[int(i)].state for i in selected]
            points=itrs_positions([s.position_m for s in states],[s.timestamp for s in states],'GCRS')
            output=analysis['scenario_analysis']['scenarios'][index]['boundary']['propagation']
            output['samples']=None
            output['sample_status']='OMITTED_FROM_COMPACT_VIEW'
            output['original_sample_count']=len(samples)
            trajectories[scenario.scenario]=ObjectTrajectory(id=result.object_id,name=result.object_name,
                samples=[PositionSample(epoch=s.timestamp,position_km=tuple(p),propagation_status='OK') for s,p in zip(states,points)],
                provenance={'gp':result.provenance['gp'],'weather':scenario.environment_assumptions,
                    'sample_treatment':'Actual computed samples; evenly indexed subsampling if original count exceeds1001'},
                model=curve.model+' -> Astropy ITRS',warnings=[*curve.warnings,*FRAME_WARNINGS])
    return PersistenceVisualization(object_id=result.object_id,prediction_status=result.prediction_status,
        analysis=analysis,trajectories=trajectories,warnings=['Opt-in compact visualization response; raw scientific samples omitted, not zero-filled.',
            'Metrics/physical assumptions computed from the original full scientific propagation.'])
