"""Owns the sensor, detector, and logger for one running session, and
the background thread that ties them together. This is the seam
between the acquisition/analysis layers and the web layer -- webapp/
only ever calls start(), clear(), and latest_reps()."""
import logging
import threading
from collections import deque
from typing import List

from sensors.base import DistanceSensor

from .constants import DISPLAY_REP_COUNT
from .rep_detector import Rep, RepDetector
from .rep_logger import RepLogger


class Session:
    """Runs sensor acquisition on a background daemon thread and makes
    completed reps available to callers (e.g. Flask request handlers)
    without either side touching the other's internals directly."""

    def __init__(self, sensor: DistanceSensor, log_path: str):
        self._sensor = sensor
        self._detector = RepDetector()
        self._logger = RepLogger(log_path)
        self._display: deque[Rep] = deque(maxlen=DISPLAY_REP_COUNT)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Open the sensor and start the background acquisition thread."""
        self._sensor.open()
        self._thread.start()

    def stop(self) -> None:
        """Signal the acquisition thread to stop, wait briefly for it,
        then close the sensor. If the thread is blocked inside a
        hardware read longer than the join timeout, this returns
        without the thread having actually exited."""
        self._stop.set()
        self._thread.join(timeout=2)
        self._sensor.close()

    def _run(self) -> None:
        """Background loop: read the sensor, feed the detector, and
        publish any completed rep. Logs and re-raises on failure --
        the thread will die, and callers keep seeing the last
        published reps until the process is restarted."""
        while not self._stop.is_set():
            try:
                rep = self._detector.update(self._sensor.read())
            except Exception:
                logging.exception("sensor read failed, acquisition thread stopping")
                raise

            if rep is not None:
                self._logger.log_rep(rep)
                with self._lock:
                    self._display.append(rep)

    def clear(self) -> None:
        """Clear the display buffer and start a new logged set."""
        with self._lock:
            self._display.clear()
        self._logger.clear_set()

    def latest_reps(self) -> List[Rep]:
        """Return a snapshot of the most recent reps for display."""
        with self._lock:
            return list(self._display)
