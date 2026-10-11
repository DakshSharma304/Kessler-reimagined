"""Checkpoint 5 analytic constructed trajectories, using the actual search."""

from datetime import timedelta

import numpy as np
import pytest

from app.models.screening import ScreeningSettings, ScreeningWindow
from app.physics.propagation import PropagationError, StateVector
from app.physics.secondary_search import CatalogPropagationCache, TrajectoryView, screen_trajectory_against_catalog
from test_encounters import START


def line(identifier, offset, velocity=(0,0,0), duration=100, name="Constructed object"):
    window = ScreeningWindow(start=START,end=START+timedelta(seconds=duration))
    def evaluate(at):
        seconds = (at-START).total_seconds()
        position = np.asarray(offset)+seconds*np.asarray(velocity)
        return StateVector(timestamp=at,position_m=tuple(position),velocity_m_s=velocity,frame="TEME")
    return TrajectoryView(identifier,window,"TEME",evaluate,name=name)


def screen(primary, others, **settings):
    return screen_trajectory_against_catalog(primary,others,ScreeningSettings(
        **(dict(alert_distance_km=.1,coarse_step_seconds=60,
                relative_acceleration_margin_m_s2=40,timeout_seconds=30)|settings)))


def test_between_sample_high_speed_crossing_not_detected_pointwise():
    primary = line("100001",(0,0,0))
    secondary = line("100002",(-250000,10,0),(10000,0,0),name="High speed crossing")
    assert min(np.linalg.norm(secondary.evaluate(START+timedelta(seconds=t)).position_m)
               for t in (0,50,100)) > 100000
    result = screen(primary,{"100002":secondary})
    assert result.complete
    assert len(result.approaches) == 1
    encounter = result.approaches[0]
    assert (encounter.tca-START).total_seconds() == pytest.approx(25,abs=1e-4)
    assert encounter.distance_m == pytest.approx(10,abs=.01)
    assert encounter.relative_speed_m_s == 10000
    assert encounter.object_id == "100002" and encounter.object_name == "High speed crossing"


def test_no_alert_closest_reported_and_self_excluded():
    primary = line("100001",(0,0,0))
    second = line("100002",(-250000,1000,0),(10000,0,0))
    result = screen(primary,{"100001":primary,"100002":second})
    assert not result.approaches
    assert result.complete
    assert result.objects_screened == {"100002"}
    assert result.closest.distance_m == pytest.approx(1000,abs=.001)


def test_shared_bounded_propagation_cache_is_thread_safe():
    from concurrent.futures import ThreadPoolExecutor
    cache = CatalogPropagationCache(max_bytes=2048)
    def exercise(worker):
        for index in range(100):
            key = (worker,index%16)
            value = (np.zeros((1,4),dtype=int),np.full((1,4,3),float(worker)))
            cache.put(key,value)
            retrieved = cache.get(key)
            if retrieved is not None:
                assert retrieved[1].shape == (1,4,3)
                assert (retrieved[1] == worker).all()
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(exercise,range(8)))
    assert 0 <= cache.bytes <= cache.max_bytes
    assert cache.bytes == sum(entry[1] for entry in cache.entries.values())


def test_crossing_at_sample_boundary_is_one_event_and_refines_distance():
    primary = line("1",(0,0,0))
    secondary = line("2",(-5000,10,0),(100,0,0))
    result = screen(primary,{"2":secondary})
    assert len(result.approaches) == 1
    assert result.approaches[0].distance_m == pytest.approx(10,abs=1e-5)
    assert (result.approaches[0].tca-START).total_seconds() == pytest.approx(50,abs=1e-4)


@pytest.mark.parametrize("shift_seconds", [-.00141,.00141,-.0002,.0002])
def test_near_boundary_minimum_not_duplicated_as_a_boundary_event(shift_seconds):
    primary=line("1",(0,0,0))
    tca=50+shift_seconds
    other=line("2",(-100*tca,10,0),(100,0,0))
    result=screen(primary,{"2":other})
    assert result.complete
    assert len(result.approaches)==1
    assert (result.approaches[0].tca-START).total_seconds()==pytest.approx(tca,abs=1e-5)
    assert result.approaches[0].distance_m==pytest.approx(10,abs=1e-6)


def test_multiple_minima_not_collapsed_by_object_id():
    primary = line("1",(0,0,0))
    def sinusoid(at):
        seconds=(at-START).total_seconds()
        omega=np.pi/25
        return StateVector(timestamp=at,position_m=(1000*np.cos(omega*seconds),10,0),
                           velocity_m_s=(-1000*omega*np.sin(omega*seconds),0,0),frame="TEME")
    other = TrajectoryView("2",primary.window,"TEME",sinusoid)
    result = screen(primary,{"2":other},coarse_step_seconds=5)
    assert len(result.approaches) == 4
    assert [(event.tca-START).total_seconds() for event in result.approaches] == pytest.approx([12.5,37.5,62.5,87.5],abs=1e-4)
    assert all(event.distance_m == pytest.approx(10,abs=.001) for event in result.approaches)


def test_identical_and_nearly_identical_trajectories_do_not_duplicate_events():
    primary = line("1",(7e6,0,0),(0,7500,0))
    for distance in (0,.001):
        other=line("2",(7e6,distance,0),(0,7500,0))
        result = screen(primary,{"2":other})
        assert len(result.approaches) == 1
        assert result.approaches[0].distance_m == pytest.approx(distance,abs=1e-6)


def test_invalid_propagation_and_budget_are_incomplete():
    primary = line("1",(0,0,0))
    def failed(at):
        raise PropagationError("Constructed propagation failure")
    other=TrajectoryView("2",primary.window,"TEME",failed)
    result=screen(primary,{"2":other})
    assert not result.complete and "2" in result.skipped_objects
    timed=screen(primary,{"3":line("3",(10000,0,0))},timeout_seconds=1e-6)
    assert not timed.complete
    assert not timed.approaches


def test_large_constructed_catalog_and_original_counterpart_are_included():
    primary=line("1",(0,0,0))
    others={str(i):line(str(i),(1000000+i*100,0,0),name=f"Catalog object {i}") for i in range(2,1002)}
    result=screen(primary,others,batch_size=128)
    assert result.complete
    assert len(result.objects_screened) == 1000
    assert len(result.objects_refined) < 200
    assert "2" in result.objects_screened
    assert not result.approaches
    assert result.closest.object_id == "2"


def test_mismatched_frames_cannot_be_silently_compared():
    primary=line("1",(0,0,0))
    other=line("2",(0,0,0))
    other.frame="GCRS"
    with pytest.raises(ValueError,match="window/frame"):
        screen(primary,{"2":other})
