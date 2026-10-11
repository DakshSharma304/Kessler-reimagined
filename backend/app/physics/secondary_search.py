"""One-vs-catalog segment search and continuous-time local refinement.

The filter minimizes each relative-position segment, then adds a curvature
allowance a_margin * dt**2/8 before discarding it. Default 40 m/s² is a generous
relative-acceleration allowance for supported Earth orbits, not a proven bound
on SGP4/differential interpolation errors. No mathematical completeness claim.
"""

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import time
import threading

from astropy.time import Time
import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from scipy.optimize import minimize_scalar
from sgp4.api import SatrecArray

from app.models.catalog import ScreeningCatalog
from app.models.orbital import OrbitalRecord
from app.models.screening import ScreeningSettings, ScreeningWindow
from app.physics.propagation import PropagationError, StateVector, propagate_object


@dataclass
class TrajectoryView:
    primary_object_id: str
    window: ScreeningWindow
    frame: str
    evaluate: Callable[[datetime], StateVector]
    sample_batch: Callable | None = None
    name: str = ""
    source: dict[str, str] = field(default_factory=lambda: {"dataset":"Constructed test trajectory"})

    def samples(self, timestamps):
        return self.sample_batch(timestamps) if self.sample_batch else [self.evaluate(at) for at in timestamps]


class RefinedSecondaryApproach(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    object_id: str
    object_name: str
    tca: AwareDatetime
    distance_m: float = Field(ge=0)
    relative_speed_m_s: float = Field(ge=0)
    frame: str
    source: dict[str, str]
    warnings: list[str] = Field(default_factory=list)


@dataclass
class SearchReport:
    approaches: list[RefinedSecondaryApproach]
    closest: RefinedSecondaryApproach | None
    objects_screened: set[str]
    objects_refined: set[str]
    skipped_objects: dict[str, str]
    complete: bool
    refinements: int
    timings_seconds: dict[str, float]


class CatalogPropagationCache:
    """Bounded LRU of coarse nominal positions; snapshot and times are in key."""
    def __init__(self, max_bytes=64*1024*1024):
        self.max_bytes, self.bytes = max_bytes, 0
        self.entries = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self.entries:
                self.entries.move_to_end(key)
                return self.entries[key][0]
            return None

    def put(self, key, value):
        size = value[0].nbytes+value[1].nbytes
        if size > self.max_bytes:
            return
        with self._lock:
            if key in self.entries:
                self.bytes -= self.entries.pop(key)[1]
            while self.entries and self.bytes+size > self.max_bytes:
                _, (_, removed) = self.entries.popitem(last=False)
                self.bytes -= removed
            self.entries[key] = (value,size)
            self.bytes += size


def _positions(states, timestamps, frame):
    if len(states) != len(timestamps) or any(state.timestamp != at or state.frame != frame
                                            for state,at in zip(states,timestamps)):
        raise ValueError("Screening trajectories must have matching frames and timestamps")
    return np.asarray([state.position_m for state in states])


def _source(orbit):
    return {"url":orbit.source_url, "sha256":orbit.content_sha256,
            "element_epoch":orbit.elements.epoch.isoformat(), "retrieved_at":orbit.fetched_at.isoformat()}


def _segment_distances(relative):
    begin = relative[:,:-1]
    movement = relative[:,1:]-begin
    denominator = np.einsum("bti,bti->bt",movement,movement)
    fraction = np.divide(-np.einsum("bti,bti->bt",begin,movement),denominator,
                         out=np.zeros_like(denominator),where=denominator>0)
    fraction = np.clip(fraction,0,1)
    closest = begin+fraction[...,None]*movement
    return np.linalg.norm(closest,axis=-1),fraction


def screen_trajectory_against_catalog(trajectory: TrajectoryView,
        catalog: ScreeningCatalog | dict[str, OrbitalRecord | TrajectoryView],
        screening_settings: ScreeningSettings, cache: CatalogPropagationCache | None = None,
        deadline: float | None = None, original_counterpart_id: str | None = None) -> SearchReport:
    started = time.perf_counter()
    deadline = min(deadline or float("inf"),started+screening_settings.timeout_seconds)
    window = trajectory.window
    duration = (window.end-window.start).total_seconds()
    count = int(np.ceil(duration/screening_settings.coarse_step_seconds))+1
    records = catalog.records if isinstance(catalog,ScreeningCatalog) else catalog
    records = {identifier:orbit for identifier,orbit in records.items()
               if identifier != trajectory.primary_object_id}
    timings = {"catalog_propagation":0.,"coarse_screening":0.,"refinement":0.,"primary_samples":0.}
    screened, refined, skipped = set(),set(),{}
    approaches = []
    closest = None
    refinement_count = 0
    if not records:
        return SearchReport([],None,screened,refined,skipped,True,0,timings)
    if count > 10001:
        return SearchReport([],None,screened,refined,{key:"Time-grid workload exceeds 10,001 samples" for key in records},False,0,timings)
    offsets = np.linspace(0,duration,count)
    timestamps = [window.start+timedelta(seconds=float(offset)) for offset in offsets]
    tick = time.perf_counter()
    primary = _positions(trajectory.samples(timestamps),timestamps,trajectory.frame)
    timings["primary_samples"] += time.perf_counter()-tick
    times = Time(timestamps).utc
    usable = []
    for identifier, orbit in records.items():
        if len(usable) >= screening_settings.max_objects:
            skipped[identifier] = "Object workload limit reached"
            continue
        if isinstance(orbit,OrbitalRecord):
            age = max(abs((endpoint-orbit.elements.epoch).total_seconds()) for endpoint in (window.start,window.end))
            if age > screening_settings.max_epoch_distance_days*86400:
                skipped[identifier] = "Element epoch outside validity at a screening endpoint"
                continue
            if orbit.data_status == "STALE_CACHE":
                skipped[identifier] = "Source refresh failed; stale cache not silently accepted as current"
                continue
            if trajectory.frame != "TEME":
                raise ValueError("Bulk SGP4 catalog comparison requires a TEME primary trajectory")
            if orbit.elements.object_id != identifier:
                raise ValueError("Catalog record identity differs from its key")
        elif orbit.frame != trajectory.frame or orbit.window != window or orbit.primary_object_id != identifier:
            raise ValueError("Constructed catalog trajectories must share window/frame and retain their identity")
        usable.append((identifier,orbit))
    stop = False
    for batch_start in range(0,len(usable),screening_settings.batch_size):
        batch = usable[batch_start:batch_start+screening_settings.batch_size]
        if time.perf_counter() >= deadline or stop:
            skipped.update({identifier:"Screening compute/refinement budget exhausted" for identifier,_ in usable[batch_start:]})
            break
        tick = time.perf_counter()
        try:
            if all(isinstance(orbit,OrbitalRecord) for _,orbit in batch):
                # Retain orbit identity, epochs and exact timestamp grid in cache key.
                key = (window.start,window.end,count,
                       tuple((identifier,orbit.content_sha256,orbit.elements) for identifier,orbit in batch))
                cached = cache.get(key) if cache else None
                if cached is None:
                    satellites = SatrecArray([orbit.elements.initialize_sgp4() for _,orbit in batch])
                    errors, positions, _ = satellites.sgp4(times.jd1,times.jd2)
                    positions *= 1000
                    cached = (errors,positions)
                    if cache:
                        cache.put(key,cached)
                errors, positions = cached
            else:
                errors = np.zeros((len(batch),count),dtype=int)
                positions = np.zeros((len(batch),count,3))
                for row, (identifier,orbit) in enumerate(batch):
                    try:
                        states = orbit.samples(timestamps) if isinstance(orbit,TrajectoryView) else [propagate_object(orbit,at) for at in timestamps]
                        positions[row] = _positions(states,timestamps,trajectory.frame)
                    except (ValueError,PropagationError) as error:
                        errors[row] = 1
                        skipped[identifier] = str(error)
        except (ValueError,PropagationError) as error:
            skipped.update({identifier:f"Batch propagation failed: {error}" for identifier,_ in batch})
            timings["catalog_propagation"] += time.perf_counter()-tick
            continue
        timings["catalog_propagation"] += time.perf_counter()-tick
        tick = time.perf_counter()
        distances, fractions = _segment_distances(positions-primary[None,:,:])
        margin = screening_settings.relative_acceleration_margin_m_s2*np.diff(offsets)**2/8
        near = distances <= screening_settings.alert_distance_km*1000+margin[None,:]
        timings["coarse_screening"] += time.perf_counter()-tick
        for row,(identifier,orbit) in enumerate(batch):
            if np.any(errors[row]) or not np.isfinite(positions[row]).all():
                skipped.setdefault(identifier,"Invalid or failed SGP4 propagation")
                continue
            if stop or time.perf_counter() >= deadline:
                skipped[identifier] = "Screening compute/refinement budget exhausted"
                stop = True
                continue
            screened.add(identifier)
            evaluate = orbit.evaluate if isinstance(orbit,TrajectoryView) else lambda at,_orbit=orbit:propagate_object(_orbit,at)
            name = orbit.name if isinstance(orbit,TrajectoryView) else orbit.elements.object_name
            source = orbit.source if isinstance(orbit,TrajectoryView) else _source(orbit)
            # Refine alert candidates and objects that could beat the retained
            # nearest encounter under the same curvature allowance. Distant
            # objects are still counted as screened, not needlessly minimized.
            candidate_indices = set(np.flatnonzero(near[row]).tolist())
            nearest_index = int(np.argmin(distances[row]))
            if identifier == original_counterpart_id or closest is None or distances[row,nearest_index] <= closest.distance_m+margin[nearest_index]:
                candidate_indices.add(nearest_index)
            if not candidate_indices:
                continue
            relative_samples = positions[row]-primary
            flat = np.max(np.linalg.norm(relative_samples-relative_samples[0],axis=1)) < 1e-6
            if flat:
                candidate_indices = {0}
            tick = time.perf_counter()
            found = []
            def relative(at_offset):
                at = window.start+timedelta(seconds=float(at_offset))
                first, second = trajectory.evaluate(at),evaluate(at)
                if first.timestamp != at or second.timestamp != at or first.frame != second.frame or first.frame != trajectory.frame:
                    raise ValueError("Incompatible refinement frames or timestamps")
                position = np.subtract(first.position_m,second.position_m)
                velocity = np.subtract(first.velocity_m_s,second.velocity_m_s)
                return (float(position@position),float(np.linalg.norm(velocity)),
                        2*float(position@velocity))
            try:
                for index in sorted(candidate_indices):
                    if refinement_count >= screening_settings.max_refinements or time.perf_counter() >= deadline:
                        skipped[identifier] = "Refinement/time budget exhausted during object search"
                        stop = True
                        break
                    refinement_count += 1
                    refined.add(identifier)
                    lo,hi = float(offsets[index]),float(offsets[index+1])
                    def objective(offset):
                        if time.perf_counter() >= deadline:
                            raise TimeoutError("Continuous refinement time budget exhausted")
                        return relative(offset)[0]
                    solution = minimize_scalar(objective,method="bounded",bounds=(lo,hi),
                        options={"xatol":1e-5,"maxiter":80})
                    if not solution.success or not np.isfinite(solution.fun):
                        raise ValueError("Secondary closest-approach refinement failed")
                    choices = [(float(solution.x),float(solution.fun)),(lo,objective(lo)),(hi,objective(hi))]
                    best_at,value = min(choices,key=lambda item:item[1])
                    probe = min(.01,(hi-lo)/10)
                    is_local = (best_at<=1e-5 or best_at>=duration-1e-5 or flat or
                        (value <= objective(max(0,best_at-probe))+1e-8 and
                         value <= objective(min(duration,best_at+probe))+1e-8))
                    internal_endpoint = (0 < best_at < duration and
                        (abs(best_at-lo)<=1e-6 or abs(best_at-hi)<=1e-6))
                    if internal_endpoint and not flat:
                        # An endpoint can minimize one segment while the objects
                        # are still approaching/receding across its boundary.
                        # Require stationarity of distance² using the relative
                        # state, not only probes that can jump over a nearby TCA.
                        _,speed,slope=relative(best_at)
                        numerical_slope_tolerance=1e-8+1e-6*max(1.,np.sqrt(value)*speed)
                        is_local = is_local and abs(slope)<=numerical_slope_tolerance
                    event = RefinedSecondaryApproach(object_id=identifier,object_name=name,
                        tca=window.start+timedelta(seconds=best_at),distance_m=float(np.sqrt(value)),
                        relative_speed_m_s=relative(best_at)[1],frame=trajectory.frame,source=source,
                        warnings=["Minimum is at the screening-window boundary; TCA is constrained to this interval."] if best_at<=1e-5 or best_at>=duration-1e-5 else [])
                    if identifier != original_counterpart_id and (closest is None or event.distance_m < closest.distance_m):
                        closest = event
                    if is_local and (identifier == original_counterpart_id or event.distance_m < screening_settings.alert_distance_km*1000):
                        if not any(abs((event.tca-prior.tca).total_seconds()) <= .001 for prior in found):
                            found.append(event)
                approaches.extend(found)
            except (ValueError,PropagationError,TimeoutError) as error:
                skipped[identifier] = f"Continuous refinement failed or incomplete: {error}"
                if isinstance(error,TimeoutError):
                    stop = True
            timings["refinement"] += time.perf_counter()-tick
    approaches.sort(key=lambda item:(item.tca,item.object_id))
    complete = not skipped and len(screened) == len(records)
    return SearchReport(approaches,closest,screened,refined,skipped,complete,refinement_count,timings)
