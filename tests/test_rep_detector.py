"""Unit tests for RepDetector.

These feed hand-built Reading sequences directly into update() rather
than relying on DummySensor's continuous sine wave, so each test can
assert exact expected outputs -- known ROM, known noise spikes, known
invalid reads -- rather than just "it didn't crash".
"""
import pytest

from analysis.rep_detector import RepDetector
from sensors.base import Reading


def feed(detector, points):
    """Feed a list of (t, distance_m, valid) tuples through update();
    return the list of non-None results (completed Reps), in order."""
    reps = []
    for t, d, valid in points:
        rep = detector.update(Reading(t=t, distance_m=d, valid=valid))
        if rep is not None:
            reps.append(rep)
    return reps


# A clean up-then-down cycle: 1.00m -> 0.60m -> 1.00m, in 0.1s steps,
# constant 1.0 m/s slope on both legs. Distances chosen so every
# reversal comfortably clears MIN_ROM_M (0.05m) once confirmed.
CLEAN_CYCLE = [
    (0.0, 1.00, True),
    (0.1, 0.90, True),
    (0.2, 0.80, True),
    (0.3, 0.70, True),
    (0.4, 0.60, True),   # turnaround (top of the rep)
    (0.5, 0.62, True),   # reversed_by=0.02, below MIN_ROM_M -- not yet a candidate
    (0.6, 0.68, True),   # reversed_by=0.08 -- candidate #1
    (0.7, 0.75, True),   # candidate #2 -- confirms the "up" segment
    (0.8, 0.85, True),
    (0.9, 0.95, True),
    (1.0, 1.00, True),   # turnaround (bottom of the rep)
    (1.1, 0.98, True),   # reversed_by=0.02 -- not yet a candidate
    (1.2, 0.90, True),   # candidate #1
    (1.3, 0.85, True),   # candidate #2 -- confirms the "down" segment -> Rep
]


def test_full_rep_cycle_timing_and_speed():
    detector = RepDetector()
    reps = feed(detector, CLEAN_CYCLE)

    assert len(reps) == 1
    rep = reps[0]
    assert rep.index == 0
    # 10%/90%-of-ROM crossing times worked out by hand for this sequence
    # (see test module docstring / PR description for the derivation).
    assert rep.time_up_s == pytest.approx(0.32, abs=1e-6)
    assert rep.time_down_s == pytest.approx(0.44, abs=1e-6)
    assert rep.max_speed_up_mps == pytest.approx(1.0, abs=1e-6)


def test_invalid_readings_do_not_affect_detection():
    """An invalid (e.g. VL53L1X out-of-range) reading dropped into the
    middle of a segment must not change the resulting Rep at all --
    it should be as if it was never sent."""
    with_noise = list(CLEAN_CYCLE)
    # Insert a wildly-out-of-range invalid reading mid-segment. If this
    # weren't filtered, its distance_m=0.0 would look like a huge,
    # fast reversal and corrupt extremum/segment tracking.
    with_noise.insert(3, (0.25, 0.0, False))

    clean_reps = feed(RepDetector(), CLEAN_CYCLE)
    noisy_reps = feed(RepDetector(), with_noise)

    assert len(clean_reps) == len(noisy_reps) == 1
    assert noisy_reps[0].time_up_s == pytest.approx(clean_reps[0].time_up_s)
    assert noisy_reps[0].time_down_s == pytest.approx(clean_reps[0].time_down_s)
    assert noisy_reps[0].max_speed_up_mps == pytest.approx(clean_reps[0].max_speed_up_mps)


def test_debounce_prevents_single_sample_false_trigger():
    """A single noisy sample that reverses past MIN_ROM_M and then
    immediately resumes the original trend must not be confirmed as a
    real turnaround when debounce_samples > 1."""
    noisy_climb = [
        (0.0, 1.00, True),
        (0.1, 0.90, True),   # establishes "up" trend
        (0.2, 0.80, True),
        (0.25, 0.90, True),  # single-sample noise blip (reversed_by=0.10)
        (0.3, 0.70, True),   # trend resumes -- the blip should be forgotten
        (0.4, 0.60, True),
    ]

    # With debounce, the blip alone (1 non-extending sample) can't
    # confirm a turnaround -- no Rep should appear from this partial
    # sequence at all yet (still mid-"up"-segment).
    debounced = feed(RepDetector(debounce_samples=2), noisy_climb)
    assert debounced == []

    # Without debounce (debounce_samples=1), the exact same single
    # noisy sample is enough to confirm a (spurious) turnaround right
    # away -- this is the failure mode the debounce logic exists to
    # prevent. We can observe it here as a completed "up" Segment
    # being consumed into pending_up immediately after the blip,
    # which flips the trend to "down" one step early.
    no_debounce = RepDetector(debounce_samples=1)
    no_debounce.update(Reading(t=0.0, distance_m=1.00))
    no_debounce.update(Reading(t=0.1, distance_m=0.90))
    no_debounce.update(Reading(t=0.2, distance_m=0.80))
    no_debounce.update(Reading(t=0.25, distance_m=0.90))
    # Trend has already flipped to "down" after just the single blip --
    # confirm by checking that a small further decrease is now read as
    # a *new* reversal candidate for the (wrongly) resumed "down" trend,
    # rather than simply continuing the original "up" trend.
    assert no_debounce._trend == "down"


def test_up_is_decreasing_false_mirrors_convention():
    """With up_is_decreasing=False, distance INCREASING represents the
    bar moving up -- the mirror image of the default convention."""
    mirrored_cycle = [(t, 2.0 - d, valid) for (t, d, valid) in CLEAN_CYCLE]

    default_reps = feed(RepDetector(), CLEAN_CYCLE)
    mirrored_reps = feed(RepDetector(up_is_decreasing=False), mirrored_cycle)

    assert len(default_reps) == len(mirrored_reps) == 1
    assert mirrored_reps[0].time_up_s == pytest.approx(default_reps[0].time_up_s)
    assert mirrored_reps[0].time_down_s == pytest.approx(default_reps[0].time_down_s)
    assert mirrored_reps[0].max_speed_up_mps == pytest.approx(default_reps[0].max_speed_up_mps)


def test_leading_partial_down_segment_is_discarded():
    """If the reading stream starts mid-rep (first completed segment
    is a 'down' with no preceding 'up'), it must be silently discarded
    rather than emitted or crashing -- and detection must recover
    normally for the next full cycle."""
    # Starts already descending (mid-rep), completes that partial
    # "down" segment, then does one full clean up+down cycle.
    mid_rep_start = [
        (0.0, 0.60, True),
        (0.1, 0.70, True),
        (0.2, 0.80, True),
        (0.3, 0.90, True),
        (0.4, 1.00, True),   # turnaround -- completes a leading "down" (discarded)
        (0.5, 0.98, True),
        (0.6, 0.90, True),   # confirms discard, trend flips to "up"
    ] + [(t + 0.6, d, valid) for (t, d, valid) in CLEAN_CYCLE[1:]]

    reps = feed(RepDetector(), mid_rep_start)

    # Exactly one Rep should come out -- the full cycle appended after
    # the discarded leading partial segment, not two.
    assert len(reps) == 1
    assert reps[0].index == 0
