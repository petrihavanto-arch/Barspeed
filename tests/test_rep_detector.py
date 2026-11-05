import pytest
from sensors.base import Reading
from analysis.rep_detector import RepDetector
from analysis.constants import MIN_ROM_M, MIN_TURNAROUND_INTERVAL_S


def test_no_debounce():
    # debounce_samples = 1 means turnarounds are confirmed immediately on the first sample past MIN_ROM_M
    detector = RepDetector(up_is_decreasing=True, debounce_samples=1)
    
    # Establish a baseline trend: moving up (distance decreasing, starting from 1.0m to 0.80m)
    assert detector.update(Reading(t=0.0, distance_m=1.00)) is None
    assert detector.update(Reading(t=0.1, distance_m=0.90)) is None
    
    # Establish the trend: 0.1m change is >= MIN_ROM_M (0.05m)
    # The current trend is now "up". The extremum is at 0.90m.
    
    # Let's move down past MIN_ROM_M (to 0.96m, a delta of 0.06m)
    # Since debounce_samples = 1, it should confirm the turnaround immediately and return None
    # because it is an "up" segment completing (returns None as we need down-segment to complete a full Rep)
    rep = detector.update(Reading(t=0.2, distance_m=0.96))
    assert rep is None
    assert detector._trend == "down"


def test_segment_includes_start_and_end_times():
    segments = []
    detector = RepDetector(up_is_decreasing=True, debounce_samples=1, on_segment=segments.append)

    detector.update(Reading(t=2.0, distance_m=1.00))
    detector.update(Reading(t=2.1, distance_m=0.90))
    detector.update(Reading(t=2.2, distance_m=0.96))

    assert len(segments) == 1
    assert segments[0].start_t == 2.0
    assert segments[0].end_t == 2.1


@pytest.mark.parametrize(
    ("top_distance", "expected_rep"),
    [(0.901, False), (0.9, True)],
)
def test_rep_requires_at_least_100mm_excursion(top_distance, expected_rep):
    detector = RepDetector(up_is_decreasing=True, debounce_samples=1)
    reps = []
    readings = [
        Reading(t=0.0, distance_m=1.0),
        Reading(t=0.1, distance_m=0.95),
        Reading(t=0.2, distance_m=top_distance),
        Reading(t=0.3, distance_m=top_distance + 0.06),
        Reading(t=0.4, distance_m=1.0),
        Reading(t=0.5, distance_m=0.94),
    ]

    for reading in readings:
        rep = detector.update(reading)
        if rep is not None:
            reps.append(rep)

    assert bool(reps) is expected_rep


def test_counts_first_rep_when_motion_begins_down():
    detector = RepDetector(up_is_decreasing=True, debounce_samples=1)
    reps = []
    distances = [
        0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
        0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, 0.1,
    ]

    for index, distance in enumerate(distances):
        rep = detector.update(Reading(t=index * 0.3, distance_m=distance))
        if rep is not None:
            reps.append(rep)

    assert len(reps) == 1
    assert reps[0].index == 0


def test_counts_first_full_rep_after_startup_partial_segment():
    detector = RepDetector(up_is_decreasing=True, debounce_samples=1)
    reps = []
    distances = [
        0.95, 1.00, 0.94, 0.40, 0.34, 0.40, 0.95, 1.00, 0.94,
        0.88,
    ]

    for index, distance in enumerate(distances):
        rep = detector.update(Reading(t=index * 0.3, distance_m=distance))
        if rep is not None:
            reps.append(rep)

    assert len(reps) == 1
    assert reps[0].index == 0


def test_default_debounce_rejection_and_confirmation():
    # debounce_samples = 2 (default)
    detector = RepDetector(up_is_decreasing=True, debounce_samples=2)
    
    # Establish trend: moving up (1.00m -> 0.80m)
    assert detector.update(Reading(t=0.0, distance_m=1.00)) is None
    assert detector.update(Reading(t=0.1, distance_m=0.80)) is None
    
    # Reversal sample 1: goes to 0.86m (reversed by 0.06m >= MIN_ROM_M).
    # Debounce counter becomes 1. Not confirmed yet.
    assert detector.update(Reading(t=0.2, distance_m=0.86)) is None
    assert detector._trend == "up"  # Still up
    assert detector._non_extending_count == 1
    
    # Reversal sample 2: goes to 0.87m (reversed by 0.07m >= MIN_ROM_M).
    # Debounce counter becomes 2. Confirmed!
    assert detector.update(Reading(t=0.3, distance_m=0.87)) is None
    assert detector._trend == "down"  # Flipped to down
    assert detector._non_extending_count == 0


def test_extending_resets_debounce():
    detector = RepDetector(up_is_decreasing=True, debounce_samples=2)
    
    # Establish trend: moving up (1.00m -> 0.80m)
    assert detector.update(Reading(t=0.0, distance_m=1.00)) is None
    assert detector.update(Reading(t=0.1, distance_m=0.80)) is None
    
    # Reversal sample 1: goes to 0.86m (reversed by 0.06m >= MIN_ROM_M).
    # Debounce counter becomes 1.
    assert detector.update(Reading(t=0.2, distance_m=0.86)) is None
    assert detector._non_extending_count == 1
    
    # Next sample resumes extending the original trend (distance decreases to 0.75m).
    # Debounce counter should reset to 0, and extremum updates to 0.75m.
    assert detector.update(Reading(t=0.3, distance_m=0.75)) is None
    assert detector._non_extending_count == 0
    assert detector._extremum.distance_m == 0.75
    assert detector._trend == "up"


def test_refractory_window_reset():
    detector = RepDetector(up_is_decreasing=True, debounce_samples=1)
    
    # Establish trend: moving up (1.00m -> 0.80m)
    assert detector.update(Reading(t=0.0, distance_m=1.00)) is None
    assert detector.update(Reading(t=0.1, distance_m=0.80)) is None
    
    # Turnaround 1 (confirmed immediately since debounce=1):
    assert detector.update(Reading(t=0.2, distance_m=0.86)) is None
    assert detector._trend == "down"
    assert detector._last_turnaround_t == 0.1  # time of the extremum (t=0.1)
    
    # Try to turnaround again to "up" within refractory window (MIN_TURNAROUND_INTERVAL_S = 0.20s).
    # Last turnaround was at t=0.1. Current time is t=0.25 (delta = 0.15s < 0.20s).
    # We move back to 0.80m (reversed by 0.06m >= MIN_ROM_M).
    # It should be rejected due to refractory window, and debounce count reset.
    assert detector.update(Reading(t=0.25, distance_m=0.80)) is None
    assert detector._trend == "down"  # Trend remains down
    assert detector._non_extending_count == 0


def test_debounce_with_temporary_dip():
    detector = RepDetector(up_is_decreasing=True, debounce_samples=2)
    
    # Establish trend: moving up (1.00m -> 0.80m)
    assert detector.update(Reading(t=0.0, distance_m=1.00)) is None
    assert detector.update(Reading(t=0.1, distance_m=0.80)) is None
    
    # Reversal sample 1: goes to 0.86m (reversed by 0.06m >= MIN_ROM_M).
    # Debounce counter becomes 1. Not confirmed yet.
    assert detector.update(Reading(t=0.2, distance_m=0.86)) is None
    assert detector._non_extending_count == 1
    
    # Reversal sample 2: goes to 0.83m (reversed by 0.03m < MIN_ROM_M).
    # It is still non-extending (0.83m > 0.80m), so it should NOT reset the counter.
    # It increments the counter to 2 and confirms!
    assert detector.update(Reading(t=0.3, distance_m=0.83)) is None
    assert detector._trend == "down"
    assert detector._non_extending_count == 0


def test_rep_avg_speed_up():
    detector = RepDetector(up_is_decreasing=True, debounce_samples=1)
    # Up segment: distance 1.0 -> 0.0 over t=0 to t=10
    # ROM = 1.0m, 10% = 0.9m (t=1), 90% = 0.1m (t=9)
    # duration_s = 8.0s, dist_10_90 = 0.8m -> avg_speed_up_mps = 0.1 m/s
    detector.update(Reading(t=0.0, distance_m=1.00))
    detector.update(Reading(t=1.0, distance_m=0.90))
    detector.update(Reading(t=5.0, distance_m=0.50))
    detector.update(Reading(t=9.0, distance_m=0.10))
    detector.update(Reading(t=10.0, distance_m=0.00))
    # Turnaround at top (d=0.0) -> start down segment (d increases to 0.10)
    detector.update(Reading(t=10.1, distance_m=0.10))
    # Down segment completes turnaround at bottom
    rep = detector.update(Reading(t=20.0, distance_m=1.00))

    if rep is None:
        rep = detector.update(Reading(t=20.1, distance_m=0.90))

    assert rep is not None
    assert pytest.approx(rep.time_up_s) == 8.0
    assert pytest.approx(rep.avg_speed_up_mps) == 0.1


def test_flush_recognizes_single_rep_without_trailing_reversal():
    # Sensor on floor: up_is_decreasing=False (distance increases as bar moves up)
    detector = RepDetector(up_is_decreasing=False, debounce_samples=1, eccentric_first=True)
    
    # 1. Start at top lockout (1.00m)
    assert detector.update(Reading(t=0.0, distance_m=1.00)) is None
    # 2. Descend to hole (0.40m)
    assert detector.update(Reading(t=1.0, distance_m=0.40)) is None
    # 3. Ascend to 0.46m (confirms hole turnaround)
    assert detector.update(Reading(t=1.1, distance_m=0.46)) is None
    # 4. Ascend all the way back to lockout (1.00m)
    assert detector.update(Reading(t=2.0, distance_m=1.00)) is None

    # Stream ends at lockout with no downward reversal.
    # Without flush, rep is None because lockout turnaround was never confirmed by a reversal.
    rep = detector.flush()
    assert rep is not None
    assert rep.index == 0
    assert rep.time_down_s > 0
    assert rep.time_up_s > 0


def test_eccentric_first_ignores_unrack_upward_segment():
    detector = RepDetector(up_is_decreasing=False, debounce_samples=1, eccentric_first=True)
    
    # Unrack: bar starts in hooks (0.85m), lifted up to 1.00m (ROM = 0.15m >= 0.10m)
    detector.update(Reading(t=0.0, distance_m=0.85))
    detector.update(Reading(t=0.5, distance_m=1.00))
    # Settle dip (1.00 -> 0.94) confirms the unrack "up" segment
    detector.update(Reading(t=0.8, distance_m=0.94))

    # Rep 1 descent (0.94 -> 0.40)
    detector.update(Reading(t=1.8, distance_m=0.40))
    # Turnaround confirmation in hole
    detector.update(Reading(t=1.9, distance_m=0.46))
    # Rep 1 ascent (0.46 -> 1.00)
    detector.update(Reading(t=2.8, distance_m=1.00))

    # Finish set
    rep = detector.flush()
    assert rep is not None
    assert rep.index == 0
    # The downward duration must reflect the descent (0.94 -> 0.40), not 0.0
    assert rep.time_down_s > 0
    assert rep.time_up_s > 0


def test_set_limits_fallback_for_shallower_rep():
    # Global set limits from a set spanning 0.40m to 1.00m
    # d_10 = 0.46m, d_90 = 0.94m
    detector = RepDetector(
        up_is_decreasing=False,
        debounce_samples=1,
        set_d_10=0.46,
        set_d_90=0.94,
        eccentric_first=True,
    )
    # A shallower rep that only reaches 0.50m (does not reach 0.46m)
    detector.update(Reading(t=0.0, distance_m=1.00))
    detector.update(Reading(t=1.0, distance_m=0.50))
    detector.update(Reading(t=1.1, distance_m=0.56))  # turnaround in hole
    detector.update(Reading(t=2.0, distance_m=1.00))  # lockout

    rep = detector.flush()
    assert rep is not None
    assert rep.time_down_s > 0.0
    assert rep.time_up_s > 0.0

