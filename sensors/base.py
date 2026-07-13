# sensors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Reading:
    t: float          # seconds, monotonic clock, relative to sensor open()
    distance_m: float
    valid: bool = True


class DistanceSensor(ABC):
    """Interface every sensor implementation (real or dummy) must satisfy.
    Layers above this (calibration, kinematics, rep analysis, UI) depend
    only on this interface, never on a concrete sensor class."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> Reading: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def nominal_rate_hz(self) -> float: ...
