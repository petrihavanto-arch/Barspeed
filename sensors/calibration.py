"""Voltage -> distance calibration for the Sharp GP2Y0A02YK0F.

This module currently returns a NOMINAL curve fit derived from the
datasheet's typical output-voltage-vs-distance graph, not a fit to
your specific unit. Real sensors vary from the datasheet nominal
curve, and per earlier discussion, ADCDACPi's own reference voltage
and any wiring/divider differences also shift the mapping — treat
this as a placeholder to get the pipeline running end-to-end, then
replace load_calibration() with a fit against measured
(voltage, known_distance) points from your actual sensor.
"""

import json
import os

# Datasheet-typical fit: distance_cm ≈ A * V^B, valid over the sensor's
# ~20-150cm rated range. Coefficients from published curve-fits of the
# GP2Y0A02YK0F output graph (V in volts, distance in cm).
_NOMINAL_A = 60.374
_NOMINAL_B = -1.16

_MIN_DISTANCE_M = 0.20
_MAX_DISTANCE_M = 1.50
_MIN_VALID_VOLTAGE = 0.05  # avoid divide-by-zero / nonsense near 0V


def _nominal_curve(voltage: float) -> float:
    v = max(voltage, _MIN_VALID_VOLTAGE)
    distance_cm = _NOMINAL_A * (v ** _NOMINAL_B)
    distance_m = distance_cm / 100.0
    return min(max(distance_m, _MIN_DISTANCE_M), _MAX_DISTANCE_M)


def load_calibration(path: str):
    """Returns a callable: voltage (float) -> distance_m (float).

    If `path` exists, it's currently ignored (stub) - once you have
    real measured calibration points, this should load them (e.g. a
    JSON list of [voltage, distance_m] pairs) and fit/interpolate
    instead of falling back to the nominal curve below.
    """
    if not os.path.exists(path):
        # Expected for now - no real calibration file exists yet.
        return _nominal_curve

    with open(path) as f:
        data = json.load(f)  # noqa: F841 - not yet used, see docstring
    # TODO: fit or interpolate from data's (voltage, distance_m) points
    # instead of ignoring it. For now, still nominal:
    return _nominal_curve
