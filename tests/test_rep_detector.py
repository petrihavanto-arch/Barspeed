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
