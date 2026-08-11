import threading
from typing import List
from sensors.base import DistanceSensor
from .rep_detector import RepDetector, Rep
from .rep_logger import RepLogger
from .constants import DISPLAY_REP_COUNT


class Session:
    def __init__(self, sensor: DistanceSensor, log_path: str, print_sensor: bool = False, print_rep: bool = False):
        self._sensor = sensor
        self._detector = RepDetector()
        self._logger = RepLogger(log_path)
        self._print_sensor = print_sensor
        self._print_rep = print_rep
        self._display: List[Rep] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._sensor.open()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self._sensor.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            reading = self._sensor.read()
            if self._print_sensor:
                print(f"Sensor Reading: t={reading.t:.3f}s, distance={reading.distance_m:.3f}m, valid={reading.valid}")
            rep = self._detector.update(reading)
            if rep is not None:
                if self._print_rep:
                    print(f"Detected Rep: index={rep.index}, time_up_s={rep.time_up_s:.3f}, time_down_s={rep.time_down_s:.3f}, max_speed_up_mps={rep.max_speed_up_mps:.3f}")
                self._logger.log_rep(rep)  # every rep is still logged to CSV regardless of display state
                with self._lock:
                    if len(self._display) < DISPLAY_REP_COUNT:
                        self._display.append(rep)

    def clear(self) -> None:
        with self._lock:
            self._display = []
        self._logger.clear_set()

    def latest_reps(self) -> List[Rep]:
        with self._lock:
            return list(self._display)

    def is_full(self) -> bool:
        with self._lock:
            return len(self._display) >= DISPLAY_REP_COUNT