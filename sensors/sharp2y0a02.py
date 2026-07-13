
from .base import DistanceSensor, Reading
import time, math 

class Sharp2Y0A02Sensor(DistanceSensor):
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


class DummySensor(DistanceSensor):
    def __init__(self, rate_hz: float = 25.0):
        self._rate_hz = rate_hz
        self._t0 = None

    def open(self) -> None:
        self._t0 = time.monotonic()

    @property
    def nominal_rate_hz(self) -> float:
        return self._rate_hz

    def read(self) -> Reading:
        time.sleep(1.0 / self._rate_hz)
        t = time.monotonic() - self._t0
        d = 0.85 + 0.15 * math.sin(t)
        return Reading(t=t, distance_m=d)

    def close(self) -> None:
        pass