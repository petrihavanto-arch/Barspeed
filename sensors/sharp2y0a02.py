"""Legacy/fallback distance sensor: Sharp GP2Y0A02YK0F (analog IR) via
an MCP3202 ADC, read through the ABElectronics ADCDACPi library.

Superseded by the VL53L1X (see vl53l1x_sensor.py) for accuracy and
sample rate, but kept available as a `--sensor sharp2y0a02` fallback.
"""
import time

from .base import DistanceSensor, Reading


class Sharp2Y0A02Sensor(DistanceSensor):
    """Sharp 2Y0A02 analog IR distance sensor.

    Requires a fitted `calib` callable (voltage -> distance_m) --
    see `calibration.py`. `nominal_rate_hz` reflects the sensor's own
    ~26Hz response-time ceiling, not anything configurable here.
    """

    def __init__(self, channel: int, calib):
        from ADCDACPi import ADCDACPi  # lazy import, only touched on rpi
        self._adc = ADCDACPi()
        self._adc.set_adc_refvoltage(3.3)
        self._channel = channel
        self._calib = calib
        self._t0 = None

    def open(self) -> None:
        self._t0 = time.monotonic()

    @property
    def nominal_rate_hz(self) -> float:
        return 26.0  # Sharp 2Y0A02 spec, 38ms±10ms response time

    def read(self) -> Reading:
        v = self._adc.read_adc_voltage(self._channel)
        return Reading(t=time.monotonic() - self._t0, distance_m=self._calib(v))

    def close(self) -> None:
        pass  # ADCDACPi has no explicit close
