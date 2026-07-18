"""Smoke tests for DummySensor -- confirms it honestly satisfies the
DistanceSensor contract (Reading shape, monotonically increasing t,
always-valid readings), since every layer above sensors/ trusts that
contract without re-checking it."""
from sensors.base import Reading
from sensors.dummy import DummySensor


def test_read_returns_valid_reading_with_increasing_time():
    sensor = DummySensor(rate_hz=100.0)  # fast rate to keep the test quick
    sensor.open()

    readings = [sensor.read() for _ in range(5)]
    sensor.close()

    for r in readings:
        assert isinstance(r, Reading)
        assert r.valid is True
        assert isinstance(r.distance_m, float)

    times = [r.t for r in readings]
    assert times == sorted(times)
    assert times[0] >= 0.0


def test_nominal_rate_hz_matches_constructor_argument():
    sensor = DummySensor(rate_hz=42.0)
    assert sensor.nominal_rate_hz == 42.0
