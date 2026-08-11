import time
from dataclasses import dataclass
from typing import List, Optional
from sensors.base import Reading
from .constants import REP_START_FRACTION, REP_END_FRACTION, MIN_ROM_M, MIN_TURNAROUND_INTERVAL_S


@dataclass
class Segment:
    direction: str        # "up" or "down"
    duration_s: float     # time between the 10% and 90% crossings
    max_speed_mps: float  # peak speed within that 10%-90% window


@dataclass
class Rep:
    index: int
    time_up_s: float
    time_down_s: float
    max_speed_up_mps: float
    completed_at: float


def _interp_time(p0: Reading, p1: Reading, target_d: float) -> float:
    if p1.distance_m == p0.distance_m:
        return p1.t
    frac = (target_d - p0.distance_m) / (p1.distance_m - p0.distance_m)
    frac = max(0.0, min(1.0, frac))
    return p0.t + frac * (p1.t - p0.t)


def _crossing_time(points: List[Reading], target_d: float, falling: bool) -> float:
    for p0, p1 in zip(points, points[1:]):
        bracketed = (p0.distance_m >= target_d >= p1.distance_m) if falling \
            else (p0.distance_m <= target_d <= p1.distance_m)
        if bracketed:
            return _interp_time(p0, p1, target_d)
    return points[-1].t


def _max_speed_in_window(points: List[Reading], t_lo: float, t_hi: float) -> float:
    max_v = 0.0
    for p0, p1 in zip(points, points[1:]):
        if not (t_lo <= (p0.t + p1.t) / 2 <= t_hi):
            continue
        dt = p1.t - p0.t
        if dt > 0:
            max_v = max(max_v, abs(p1.distance_m - p0.distance_m) / dt)
    return max_v


def _build_segment(points: List[Reading], direction: str, falling: bool) -> Segment:
    d_start, d_end = points[0].distance_m, points[-1].distance_m
    rom = abs(d_end - d_start)
    sign = -1 if falling else 1
    d_10 = d_start + sign * REP_START_FRACTION * rom
    d_90 = d_start + sign * REP_END_FRACTION * rom
    t_10 = _crossing_time(points, d_10, falling)
    t_90 = _crossing_time(points, d_90, falling)
    return Segment(direction, t_90 - t_10, _max_speed_in_window(points, t_10, t_90))


class RepDetector:
    """Feed readings one at a time via update(). Convention: distance_m
    DECREASES as the bar moves up - set up_is_decreasing=False if your
    sensor mounting gives the opposite relationship."""

    def __init__(self, up_is_decreasing: bool = True, debounce_samples: int = 2, on_segment=None):
        self._up_is_decreasing = up_is_decreasing
        self._debounce_samples = debounce_samples
        self._non_extending_count = 0
        self._seg_points: List[Reading] = []
        self._trend: Optional[str] = None
        self._extremum: Optional[Reading] = None
        self._pending_up: Optional[Segment] = None
        self._rep_index = 0
        self._last_turnaround_t: Optional[float] = None
        self.on_segment = on_segment

    def _falling_means(self, trend: str) -> bool:
        return (trend == "up") == self._up_is_decreasing

    def update(self, reading: Reading) -> Optional[Rep]:
        if not reading.valid:
            return None  # don't let invalid/no-target readings move the extremum or trigger a turnaround

        if not self._seg_points:
            self._seg_points = [reading]
            self._extremum = reading
            return None
        self._seg_points.append(reading)

        if self._trend is None:
            delta = reading.distance_m - self._seg_points[0].distance_m
            if abs(delta) < MIN_ROM_M:
                return None
            falling = delta < 0
            self._trend = "up" if (falling == self._up_is_decreasing) else "down"
            self._extremum = reading
            return None

        falling = self._falling_means(self._trend)
        extending = reading.distance_m < self._extremum.distance_m if falling \
            else reading.distance_m > self._extremum.distance_m
        if extending:
            self._extremum = reading
            self._non_extending_count = 0
            return None

        if (self._last_turnaround_t is not None
                and reading.t - self._last_turnaround_t < MIN_TURNAROUND_INTERVAL_S):
            self._non_extending_count = 0
            return None  # inside refractory window - treat as jitter/settling, not a real turnaround

        reversed_by = abs(reading.distance_m - self._extremum.distance_m)
        if reversed_by >= MIN_ROM_M or self._non_extending_count > 0:
            self._non_extending_count += 1
            if self._non_extending_count < self._debounce_samples:
                return None
        else:
            return None

        closing = [p for p in self._seg_points if p.t <= self._extremum.t] + [self._extremum]
        segment = _build_segment(closing, self._trend, falling)
        if self.on_segment:
            self.on_segment(segment)
        rep = self._consume(segment)

        self._last_turnaround_t = self._extremum.t
        self._trend = "down" if self._trend == "up" else "up"
        self._seg_points = [p for p in self._seg_points if p.t >= self._extremum.t]
        self._extremum = reading
        self._non_extending_count = 0
        return rep

    def _consume(self, segment: Segment) -> Optional[Rep]:
        if segment.direction == "up":
            self._pending_up = segment
            return None
        if self._pending_up is None:
            return None
        rep = Rep(self._rep_index, self._pending_up.duration_s, segment.duration_s,
                  self._pending_up.max_speed_mps, time.time())
        self._rep_index += 1
        self._pending_up = None
        return rep
