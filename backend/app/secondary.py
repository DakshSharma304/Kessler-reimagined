"""Reusable proposed-maneuver screening service for optimizer, API and CLI."""

from datetime import datetime
from hashlib import sha256
import time

from app.models.catalog import CatalogSource, ScreeningCatalog
from app.models.screening import ScreeningRequest, ScreeningResult
from app.physics.propagation import propagate_object
from app.physics.screening_trajectories import DifferentialTrajectory
from app.physics.secondary_comparison import compare_secondary_conjunctions
from app.physics.secondary_search import CatalogPropagationCache, TrajectoryView


def with_counterpart(catalog, counterpart):
    """Add a missing actual selected record, with a new identifiable snapshot."""
    identifier=counterpart.elements.object_id
    if not catalog.records or identifier in catalog.records:
        return catalog
    records=catalog.records | {identifier:counterpart}
    source=CatalogSource(source_url=counterpart.source_url,content_sha256=counterpart.content_sha256,
        retrieved_at=counterpart.fetched_at,dataset_timestamp=counterpart.fetched_at,
        timestamp_basis="SELECTED_RECORD_FETCH_TIME",retrieval_mode="STALE_CACHE" if counterpart.data_status=="STALE_CACHE" else "CACHE",
        usable_records=1,rejected_records=0,duplicate_records=0)
    epochs=[item.elements.epoch for item in records.values()]
    metadata=catalog.metadata.model_copy(update={"objects_available":len(records),
        "sources":[*catalog.metadata.sources,source],"oldest_element_epoch":min(epochs),
        "newest_element_epoch":max(epochs),"snapshot_sha256":sha256(
            f"{catalog.metadata.snapshot_sha256}:{identifier}:{counterpart.content_sha256}".encode()).hexdigest(),
        "warnings":[*catalog.metadata.warnings,"Original counterpart added from its separately retrieved actual selected GP record; combined snapshot checksum identifies this addition."]})
    return ScreeningCatalog(records=records,metadata=metadata)


def screen_proposed_maneuver(encounter, first, second, request: ScreeningRequest,
        catalog: ScreeningCatalog, reference_epoch: datetime | None = None,
        now: datetime | None = None, cache: CatalogPropagationCache | None = None,
        deadline: float | None = None) -> ScreeningResult:
    started=time.perf_counter()
    deadline=min(deadline or float("inf"),started+request.timeout_seconds)
    window=request.screening_window(encounter,now)
    if (first.elements.object_id,second.elements.object_id)!=(encounter.object_1_id,encounter.object_2_id):
        raise ValueError("Selected orbital records do not match the encounter")
    orbit=first if request.maneuvering_object_id==first.elements.object_id else second
    counterpart=second if orbit is first else first
    if orbit.data_status == "STALE_CACHE":
        raise ValueError("Primary orbital source refresh failed; stale cache cannot constitute current screening")
    catalog=with_counterpart(catalog,counterpart)
    if not catalog.records:
        nominal=TrajectoryView(orbit.elements.object_id,window,"TEME",lambda at:propagate_object(orbit,at))
        return compare_secondary_conjunctions(nominal,nominal,catalog,request,
            encounter.id,counterpart.elements.object_id,cache,deadline=deadline)
    curve=DifferentialTrajectory(orbit,window,request.delta_v_rtn_m_s,reference_epoch,
                                 request.max_epoch_distance_days)
    nominal=TrajectoryView(orbit.elements.object_id,window,"TEME",curve.nominal,
                           lambda times:curve.samples(times,False))
    modified=TrajectoryView(orbit.elements.object_id,window,"TEME",curve.modified,curve.samples)
    result=compare_secondary_conjunctions(nominal,modified,catalog,request,encounter.id,
        counterpart.elements.object_id,cache,deadline=deadline)
    result.elapsed_seconds=time.perf_counter()-started
    result.timings_seconds["trajectory_generation"]=max(0,result.elapsed_seconds-sum(result.timings_seconds.values()))
    result.warnings.append(f"Primary trajectory uses selected GP record {orbit.elements.object_id}, epoch {orbit.elements.epoch.isoformat()}, SHA-256 {orbit.content_sha256}; it may differ from a same-ID bulk-catalog record, which is excluded from self-comparison.")
    screening_counterpart=catalog.records.get(counterpart.elements.object_id)
    if screening_counterpart is not None and screening_counterpart.elements != counterpart.elements:
        result.warnings.append(f"Original counterpart's catalog elements differ from the selected primary-analysis record: catalog SHA-256 {screening_counterpart.content_sha256}, epoch {screening_counterpart.elements.epoch.isoformat()}; selected SHA-256 {counterpart.content_sha256}, epoch {counterpart.elements.epoch.isoformat()}. Original-encounter screening distances must not be equated with primary-optimizer distances.")
    return result
