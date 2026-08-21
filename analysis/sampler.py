from dataclasses import dataclass
from typing import List, Optional
from sensors.base import Reading


@dataclass
class SamplingResult:
    lowest_distance_m: float
    highest_distance_m: float
    limit_10_m: float
    limit_90_m: float
    travel_distance_m: float
    travel_time_s: float
    lift_speed_mps: float
    sample_count: int


def _interp_time(p0: Reading, p1: Reading, target_d: float) -> float:
    if p1.distance_m == p0.distance_m:
        return p1.t
    frac = (target_d - p0.distance_m) / (p1.distance_m - p0.distance_m)
    frac = max(0.0, min(1.0, frac))
    return p0.t + frac * (p1.t - p0.t)


def calculate_sampling_result(readings: List[Reading], up_is_decreasing: bool = True) -> Optional[SamplingResult]:
    valid = [r for r in readings if r.valid]
    if len(valid) < 2:
        return None

    lowest_d = min(r.distance_m for r in valid)
    highest_d = max(r.distance_m for r in valid)
    total_range = highest_d - lowest_d

    if total_range <= 1e-6:
        return SamplingResult(
            lowest_distance_m=lowest_d,
            highest_distance_m=highest_d,
            limit_10_m=lowest_d,
            limit_90_m=highest_d,
            travel_distance_m=0.0,
            travel_time_s=0.0,
            lift_speed_mps=0.0,
            sample_count=len(valid),
        )

    if up_is_decreasing:
        # Distance DECREASES during upward lift (bottom is highest_d, top is lowest_d)
        d_10 = highest_d - 0.10 * total_range
        d_90 = highest_d - 0.90 * total_range
    else:
        # Distance INCREASES during upward lift (bottom is lowest_d, top is highest_d)
        d_10 = lowest_d + 0.10 * total_range
        d_90 = lowest_d + 0.90 * total_range

    travel_distance = abs(d_90 - d_10)

    travel_times = []
    t_10_current = None

    for p0, p1 in zip(valid, valid[1:]):
        if up_is_decreasing:
            if p0.distance_m >= d_10 >= p1.distance_m and t_10_current is None:
                t_10_current = _interp_time(p0, p1, d_10)
            if p0.distance_m >= d_90 >= p1.distance_m and t_10_current is not None:
                t_90 = _interp_time(p0, p1, d_90)
                if t_90 > t_10_current:
                    travel_times.append(t_90 - t_10_current)
                t_10_current = None
        else:
            if p0.distance_m <= d_10 <= p1.distance_m and t_10_current is None:
                t_10_current = _interp_time(p0, p1, d_10)
            if p0.distance_m <= d_90 <= p1.distance_m and t_10_current is not None:
                t_90 = _interp_time(p0, p1, d_90)
                if t_90 > t_10_current:
                    travel_times.append(t_90 - t_10_current)
                t_10_current = None

    if travel_times:
        avg_travel_time = sum(travel_times) / len(travel_times)
    else:
        t_min = min(valid, key=lambda r: r.distance_m).t
        t_max = max(valid, key=lambda r: r.distance_m).t
        avg_travel_time = abs(t_min - t_max) * 0.8

    lift_speed = travel_distance / avg_travel_time if avg_travel_time > 0 else 0.0

    return SamplingResult(
        lowest_distance_m=lowest_d,
        highest_distance_m=highest_d,
        limit_10_m=d_10,
        limit_90_m=d_90,
        travel_distance_m=travel_distance,
        travel_time_s=avg_travel_time,
        lift_speed_mps=lift_speed,
        sample_count=len(valid),
    )
