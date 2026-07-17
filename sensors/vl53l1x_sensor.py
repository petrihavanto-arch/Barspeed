import time

from .base import DistanceSensor, Reading

# Distance modes per the pimoroni VL53L1X library: 1=Short, 2=Medium, 3=Long.
# Short favors speed and immunity to ambient IR over max range - a good fit
# for tracking a barbell at typically <1.5m, versus Sharp's much slower response.
_DISTANCE_MODE_SHORT = 1

_TIMING_BUDGET_US = 20000       # measurement time budget, microseconds
_INTER_MEASUREMENT_MS = 50       # must be >= timing budget (in ms); ~28Hz


class VL53L1XSensor(DistanceSensor):
    """ToF laser distance sensor via I2C (pimoroni VL53L1X python package).
    Distance comes back directly in mm from the sensor itself - no
    voltage->distance calibration curve needed, unlike the Sharp 2Y0A02."""

    def __init__(self, i2c_bus: int = 1, i2c_address: int = 0x29):
        # lazy import - keeps this module (and sensors/__init__.py, via
        # factory.py) importable on a PC with no I2C/VL53L1X hardware
        import VL53L1X
        self._tof = VL53L1X.VL53L1X(i2c_bus=i2c_bus, i2c_address=i2c_address)
        self._t0 = None

    def open(self) -> None:
        self._tof.open()
#        self._tof.set_distance_mode(_DISTANCE_MODE_SHORT)
        self._tof.set_timing(_TIMING_BUDGET_US, _INTER_MEASUREMENT_MS)
        self._tof.start_ranging(1)  # 0 = use mode/timing already configured above
        self._t0 = time.monotonic()

    @property
    def nominal_rate_hz(self) -> float:
        return 1000.0 / _INTER_MEASUREMENT_MS

    def read(self) -> Reading:
        distance_mm = self._tof.get_distance()  # blocks until a reading is ready
        t = time.monotonic() - self._t0
        valid = distance_mm > 0  # library returns 0 on an invalid/no-target read
        return Reading(t=t, distance_m=distance_mm / 1000.0, valid=valid)

    def close(self) -> None:
        self._tof.stop_ranging()
        self._tof.close()