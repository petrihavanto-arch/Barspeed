import pytest
from sensors.base import Reading
from analysis.sampler import calculate_sampling_result


def test_calculate_sampling_result_empty():
    assert calculate_sampling_result([]) is None
    assert calculate_sampling_result([Reading(t=0.0, distance_m=1.0, valid=False)]) is None


def test_calculate_sampling_result_flat():
    readings = [
        Reading(t=0.0, distance_m=1.0),
        Reading(t=1.0, distance_m=1.0),
    ]
    res = calculate_sampling_result(readings)
    assert res is not None
    assert res.highest_distance_m == 1.0
    assert res.lowest_distance_m == 1.0
    assert res.lift_speed_mps == 0.0


def test_calculate_sampling_result_single_lift():
    # Distance DECREASES during lift (up_is_decreasing=True)
    # Range: 1.0m to 0.0m -> total range 1.0m
    # 10% limit = 0.9m, 90% limit = 0.1m
    # 10-90 travel distance = 0.8m
    # Travel from d=1.0 (t=0) to d=0.0 (t=10)
    # Crossing 0.9 occurs at t=1.0
    # Crossing 0.1 occurs at t=9.0
    # Travel time = 8.0s -> Lift speed = 0.8m / 8.0s = 0.1 m/s
    readings = [Reading(t=float(i), distance_m=1.0 - 0.1 * i) for i in range(11)]
    res = calculate_sampling_result(readings, up_is_decreasing=True)

    assert res is not None
    assert pytest.approx(res.highest_distance_m) == 1.0
    assert pytest.approx(res.lowest_distance_m) == 0.0
    assert pytest.approx(res.limit_10_m) == 0.9
    assert pytest.approx(res.limit_90_m) == 0.1
    assert pytest.approx(res.travel_distance_m) == 0.8
    assert pytest.approx(res.travel_time_s) == 8.0
    assert pytest.approx(res.lift_speed_mps) == 0.1
