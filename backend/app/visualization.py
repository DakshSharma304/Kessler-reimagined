"""Real batch SGP4 and actual Astropy Earth-fixed transforms; no JS physics."""
from datetime import UTC,datetime,timedelta
import astropy.units as u
from astropy.coordinates import CartesianRepresentation,GCRS,ITRS,TEME
from astropy.time import Time
import numpy as np
from sgp4.api import SatrecArray,SGP4_ERRORS,jday
from app.data.celestrak import validate_object_id
from app.data.metadata import MetadataUnavailable
from app.models.orbital import epoch_suitability
from app.models.visualization import (CatalogPage,ObjectInfo,ObjectSummary,ObjectPosition,
    PositionBatch,PositionSample,ObjectTrajectory,EncounterTrajectories,ManeuverTrajectories)
from app.physics.encounters import analyze_encounter
from app.physics.maneuvers import MatchedDynamics,NumericalTrajectory,simulate_maneuver
from app.physics.propagation import initialized_satellite
from app.probability.integration import with_maneuver_probability

FRAME_WARNINGS=['ITRS/ECEF Earth-fixed positions in km; not raw TEME/inertial coordinates.',
    'Installed offline IERS data; predictive/degraded Earth orientation may limit precision.',
    'Three.js right-handed Y-up mapping: (x,y,z)ITRS -> (x,z,-y); one world unit per km or a common display scale.',
    'Earth-fixed sampled paths rotate with Earth and are not closed inertial orbital ellipses.']


def metadata_for(engine):
    try: return engine.metadata.load(),[]
    except MetadataUnavailable as error: return None,[str(error),'Classification unavailable; UNKNOWN is not debris.']


def summary(record,metadata):
    elements=record.elements
    meta=None if metadata is None else metadata.records.get(elements.object_id)
    current=abs((datetime.now(UTC)-elements.epoch).total_seconds())<=7*86400
    return ObjectSummary(id=elements.object_id,name=elements.object_name,
        classification='UNKNOWN' if meta is None else meta.classification,element_epoch=elements.epoch,
        inclination_deg=elements.inclination_deg,operational_status_code=None if meta is None else meta.operational_status_code,
        cleanup_eligible=meta is not None and meta.eligibility_reason is None and current,
        apogee_km=None if meta is None else meta.apogee_km,perigee_km=None if meta is None else meta.perigee_km)


def list_objects(engine,search=None,classification=None,offset=0,limit=100):
    catalog=engine.public_catalog()
    metadata,warnings=metadata_for(engine)
    query=(search or '').strip().casefold()
    records=[r for i,r in catalog.records.items() if (not query or query in i or query in r.elements.object_name.casefold())
        and (classification is None or ('UNKNOWN' if metadata is None or i not in metadata.records else metadata.records[i].classification)==classification)]
    records.sort(key=lambda r:int(r.elements.object_id))
    return CatalogPage(items=[summary(r,metadata) for r in records[offset:offset+limit]],total=len(records),offset=offset,limit=limit,
        next_offset=offset+limit if offset+limit<len(records) else None,catalog=catalog.metadata,
        metadata_source=None if metadata is None else metadata.provenance,
        warnings=[*warnings,*catalog.metadata.warnings,*(() if metadata is None else metadata.warnings)])


def object_info(engine,identifier):
    identifier=validate_object_id(identifier)
    record=engine.public_catalog().records.get(identifier)
    if record is None: record=engine.celestrak.get_object(identifier)
    metadata,warnings=metadata_for(engine)
    return ObjectInfo(object=summary(record,metadata),orbit=record,
        metadata=None if metadata is None else metadata.records.get(identifier),warnings=[*warnings,*record.warnings])


def itrs_positions(positions_m,timestamps,frame):
    if frame not in {'TEME','GCRS'}: raise ValueError('ITRS transform requires known TEME or GCRS source frame')
    if not timestamps: return np.empty((0,3))
    if any(t.tzinfo is None for t in timestamps): raise ValueError('Transform timestamps must be timezone-aware')
    values=np.asarray(positions_m,dtype=float)
    if values.shape!=(len(timestamps),3) or not np.isfinite(values).all(): raise ValueError('Finite Nx3 positions required')
    at=Time([t.astimezone(UTC) for t in timestamps])
    source=TEME if frame=='TEME' else GCRS
    result=source(CartesianRepresentation(values.T*u.m),obstime=at).transform_to(ITRS(obstime=at))
    points=result.cartesian.xyz.to_value(u.km).T
    if not np.isfinite(points).all(): raise ValueError('ITRS transform produced nonfinite positions')
    return points


def julian(timestamp):
    t=timestamp.astimezone(UTC)
    return jday(t.year,t.month,t.day,t.hour,t.minute,t.second+t.microsecond/1e6)


def bulk_positions(engine,request):
    at=(request.epoch or datetime.now(UTC)).astimezone(UTC)
    catalog=engine.public_catalog()
    metadata,warnings=metadata_for(engine)
    items=[]; satellites=[]; indices=[]
    for identifier in request.object_ids:
        record=catalog.records.get(identifier)
        meta=None if metadata is None else metadata.records.get(identifier)
        item=ObjectPosition(id=identifier,name=None if record is None else record.elements.object_name,
            classification='UNKNOWN' if meta is None else meta.classification,epoch=at,position_km=None,
            propagation_status='NOT_IN_CATALOG',error='Object not present in selected public snapshot')
        if record is not None:
            suitable,notes=epoch_suitability(record,at)
            if not suitable: item.propagation_status='UNSUPPORTED_EPOCH';item.error=notes[-1]
            else:
                try:
                    satellites.append(initialized_satellite(record.elements));indices.append(len(items))
                except ValueError as error: item.propagation_status='SGP4_ERROR';item.error=str(error)
        items.append(item)
    if satellites:
        jd,fr=julian(at)
        errors,positions,_=SatrecArray(satellites).sgp4(np.array([jd]),np.array([fr]))
        good=[];coordinates=[]
        for row,index in enumerate(indices):
            code=int(errors[row,0]);point=positions[row,0]
            if code or not np.isfinite(point).all():
                items[index].propagation_status='SGP4_ERROR';items[index].error=f'SGP4 {code}: {SGP4_ERRORS.get(code,"nonfinite state")}'
            else: good.append(index);coordinates.append(point*1000)
        transformed=itrs_positions(coordinates,[at]*len(good),'TEME')
        for index,point in zip(good,transformed):
            items[index].position_km=tuple(point);items[index].propagation_status='OK';items[index].error=None
    return PositionBatch(items=items,epoch=at,catalog=catalog.metadata,
        metadata_source=None if metadata is None else metadata.provenance,warnings=[*warnings,*FRAME_WARNINGS])


def times_between(start,end,count):
    if start.tzinfo is None or end.tzinfo is None or not 0<(end-start).total_seconds()<=86400 or not 2<=count<=1001:
        raise ValueError('Aware increasing UTC times, interval <=24 hours and 2..1001 samples required')
    return [start.astimezone(UTC)+timedelta(seconds=float(t)) for t in np.linspace(0,(end-start).total_seconds(),count)]


def sgp4_trajectory(record,start,end,count):
    times=times_between(start,end,count)
    suitable,notes=epoch_suitability(record,start)
    suitable_end,end_notes=epoch_suitability(record,end)
    if not suitable or not suitable_end: raise ValueError('Trajectory endpoints exceed seven-day GP epoch limit')
    satellite=initialized_satellite(record.elements)
    jd,fr=np.array([julian(at) for at in times]).T
    errors,positions,_=satellite.sgp4_array(np.ascontiguousarray(jd),np.ascontiguousarray(fr))
    good=(errors==0)&np.isfinite(positions).all(axis=1)
    points=itrs_positions(positions[good]*1000,[at for at,ok in zip(times,good) if ok],'TEME')
    iterator=iter(points)
    samples=[PositionSample(epoch=at,position_km=tuple(next(iterator)) if ok else None,
        propagation_status='OK' if ok else 'SGP4_ERROR',error=None if ok else f'SGP4 {int(code)}: {SGP4_ERRORS.get(int(code),"nonfinite state")}')
        for at,ok,code in zip(times,good,errors)]
    return ObjectTrajectory(id=record.elements.object_id,name=record.elements.object_name,samples=samples,
        provenance={'source_url':record.source_url,'content_sha256':record.content_sha256,'fetched_at':record.fetched_at.isoformat(),
            'element_epoch':record.elements.epoch.isoformat(),'data_status':record.data_status},model='SGP4 WGS72 TEME -> Astropy ITRS',warnings=[*notes,*FRAME_WARNINGS])


def object_trajectory(engine,identifier,start=None,end=None,count=121):
    identifier=validate_object_id(identifier)
    record=engine.public_catalog().records.get(identifier)
    if record is None: record=engine.celestrak.get_object(identifier)
    start=start or datetime.now(UTC)
    end=end or start+timedelta(seconds=min(86400,86400/record.elements.mean_motion_rev_day))
    return sgp4_trajectory(record,start,end,count)


def encounter_trajectories(engine,identifier,half_window_seconds=300,sample_count=121):
    encounter,first,second=engine.selected_case(identifier)
    start=encounter.time_of_closest_approach-timedelta(seconds=half_window_seconds)
    end=encounter.time_of_closest_approach+timedelta(seconds=half_window_seconds)
    return EncounterTrajectories(encounter_id=identifier,participant_ids=(first.elements.object_id,second.elements.object_id),
        trajectories=[sgp4_trajectory(r,start,end,sample_count) for r in (first,second)],
        warnings=['Published TCA-centered sample window; call analyze for recalculated local closest approach.'])


def numerical_path(record,states,anchor,assumptions):
    points=itrs_positions([s.position_m for s in states],[s.timestamp for s in states],'GCRS')
    return ObjectTrajectory(id=record.elements.object_id,name=record.elements.object_name,
        samples=[PositionSample(epoch=s.timestamp,position_km=tuple(p),propagation_status='OK') for s,p in zip(states,points)],
        provenance={'source_url':record.source_url,'content_sha256':record.content_sha256,'numerical_reference_epoch':anchor.isoformat()},
        model='Matched central gravity + J2 GCRS -> Astropy ITRS',warnings=[*assumptions,*FRAME_WARNINGS])


def maneuver_trajectories(engine,identifier,request):
    case=engine.selected_case(identifier)
    encounter,first,second=case
    reference=analyze_encounter(*case)
    anchor=request.numerical_reference_epoch or request.maneuver_time
    if not encounter.time_of_closest_approach-timedelta(hours=48)<=anchor<=request.maneuver_time:
        raise ValueError('Reference epoch must precede/equal burn and be within the 48-hour encounter model')
    if any(not epoch_suitability(r,anchor)[0] for r in (first,second)): raise ValueError('Reference GP epoch unsupported')
    dynamics=MatchedDynamics(*case,anchor,reference)
    simulation=simulate_maneuver(*case,request.maneuvering_object_id,request.maneuver_time,
        request.delta_v_rtn_m_s,request.hypothetical_capability_assumed,analysis=reference,shared_dynamics=dynamics,trajectory_samples=0)
    if request.probability_scenario is not None: simulation=with_maneuver_probability(case,simulation,request.probability_scenario)
    # Retain the SAME simulator initial state, pole and validated integrator.
    modified=NumericalTrajectory(simulation.state_after_maneuver,reference.calculated.searched_end,dynamics.pole)
    span=(reference.calculated.searched_end-anchor).total_seconds()
    if span<=0 or span>48*3600+1800: raise ValueError('Unsupported maneuver visualization interval')
    times=[anchor+timedelta(seconds=float(t)) for t in np.linspace(0,span,request.sample_count)]
    selected=0 if request.maneuvering_object_id==first.elements.object_id else 1
    records=(first,second)
    baseline_states=[dynamics.nominal[selected](t) for t in times]
    modified_states=[dynamics.nominal[selected](t) if t<request.maneuver_time else modified(t) for t in times]
    other_states=[dynamics.nominal[1-selected](t) for t in times]
    return ManeuverTrajectories(encounter_id=identifier,participant_ids=(first.elements.object_id,second.elements.object_id),
        numerical_reference_epoch=anchor,baseline=numerical_path(records[selected],baseline_states,anchor,simulation.model_assumptions),
        modified=numerical_path(records[selected],modified_states,anchor,simulation.model_assumptions),
        counterpart=numerical_path(records[1-selected],other_states,anchor,simulation.model_assumptions),simulation=simulation,
        warnings=['Use optimize.numerical_reference_epoch to reproduce an optimized option, not a different nominal anchor.',
            'Hypothetical trajectories, not spacecraft flight commands; matched numerical model differs from nominal SGP4 paths.'])
