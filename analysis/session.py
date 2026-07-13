import threading
from collections import deque
from typing import List
from sensors.base import DistanceSensor
from .rep_detector import RepDetector, Rep
from .rep_logger import RepLogger
from .constants import DISPLAY_REP_COUNT


class Session:
    def __init__(self, sensor: DistanceSensor, log_path: str):
        self._sensor = sensor
        self._detector = RepDetector()
        self._logger = RepLogger(log_path)
        self._display: deque[Rep] = deque(maxlen=DISPLAY_REP_COUNT)
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
            try:
                rep = self._detector.update(self._sensor.read())
            except Exception:
                import logging
                logging.exception("sensor read failed, acquisition thread stopping")
                raise

            if rep is not None:
                self._logger.log_rep(rep)
                with self._lock:
                    self._display.append(rep)

    def clear(self) -> None:
        with self._lock:
            self._display.clear()
        self._logger.clear_set()

    def latest_reps(self) -> List[Rep]:
        with self._lock:
            return list(self._display)