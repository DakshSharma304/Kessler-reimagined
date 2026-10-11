import pytest

from app.benchmark import benchmark_engine


@pytest.mark.live
def test_actual_machine_benchmark():
    report = benchmark_engine()
    assert report["source_encounters"] > 0
    assert report["propagations"]["100"]["states"] == 100
    assert report["propagations"]["1000"]["states"] == 1000
    assert report["optimizer_status"] == "COMPLETE"
    assert report["candidates_evaluated"] > 100
    assert report["best_solution"] is not None
    assert report["best_solution"]["delta_v_m_s"] <= .2 + 1e-12
    print("Actual-machine benchmark: " + str({key:value for key,value in report.items()
        if key.endswith("seconds") or key in ("source_encounters","candidates_evaluated","optimizer_status")}))
