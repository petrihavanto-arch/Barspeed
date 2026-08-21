import threading
import time
from typing import List, Optional, Dict, Any
from sensors.base import DistanceSensor, Reading
from .rep_detector import RepDetector, Rep
from .rep_logger import RepLogger
from .constants import DISPLAY_REP_COUNT
from .sampler import calculate_sampling_result, SamplingResult

SAMPLING_TIMEOUT_S = 300.0  # 5 minutes


class Session:
    def __init__(self, sensor: DistanceSensor, log_path: str, print_sensor: bool = False, print_rep: bool = False):
        self._sensor = sensor
        
        def handle_segment(segment):
            if self._print_rep:
                name = "Time up" if segment.direction == "up" else "Time down"
                print(f"{name}: {segment.duration_s:.3f}s (max speed: {segment.max_speed_mps:.3f} m/s)")
                
        self._detector = RepDetector(on_segment=handle_segment)
        self._logger = RepLogger(log_path)
        self._print_sensor = print_sensor
        self._print_rep = print_rep
        self._display: List[Rep] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()

        # Sampling session state
        self._is_sampling: bool = False
        self._sampling_start_t: Optional[float] = None
        self._sampling_buffer: List[Reading] = []
        self._sampling_result: Optional[SamplingResult] = None

        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._sensor.open()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self._sensor.close()

    def _run(self) -> None:
        if self._print_sensor:
            print("t,distance_m,valid")
        while not self._stop.is_set():
            reading = self._sensor.read()
            if self._print_sensor:
                print(f"{reading.t:.3f},{reading.distance_m:.3f},{reading.valid}")

            with self._lock:
                if self._is_sampling:
                    if self._sampling_start_t is None:
                        self._sampling_start_t = reading.t

                    # Check 5-minute timeout
                    elapsed = reading.t - self._sampling_start_t
                    if elapsed >= SAMPLING_TIMEOUT_S:
                        self._stop_sampling_locked()
                    else:
                        if reading.valid:
                            self._sampling_buffer.append(reading)

            rep = self._detector.update(reading)
            if rep is not None:
                self._logger.log_rep(rep)
                with self._lock:
                    if len(self._display) < DISPLAY_REP_COUNT:
                        self._display.append(rep)

    def _stop_sampling_locked(self) -> None:
        self._is_sampling = False
        self._sampling_result = calculate_sampling_result(self._sampling_buffer)

    def toggle_sampling(self) -> Dict[str, Any]:
        with self._lock:
            if not self._is_sampling:
                # Start sampling
                self._is_sampling = True
                self._sampling_start_t = None
                self._sampling_buffer = []
                self._sampling_result = None
                self._display = []
                self._logger.clear_set()
                return {"status": "sampling_started"}
            else:
                # Stop sampling
                self._stop_sampling_locked()
                return {"status": "sampling_stopped"}

    def clear(self) -> None:
        self.toggle_sampling()

    def get_sampling_status(self) -> Dict[str, Any]:
        with self._lock:
            elapsed = 0.0
            if self._is_sampling and self._sampling_buffer and self._sampling_start_t is not None:
                elapsed = max(0.0, self._sampling_buffer[-1].t - self._sampling_start_t)

            res_dict = None
            if self._sampling_result is not None:
                res = self._sampling_result
                res_dict = {
                    "lowest_distance_m": round(res.lowest_distance_m, 3),
                    "highest_distance_m": round(res.highest_distance_m, 3),
                    "limit_10_m": round(res.limit_10_m, 3),
                    "limit_90_m": round(res.limit_90_m, 3),
                    "travel_distance_m": round(res.travel_distance_m, 3),
                    "travel_time_s": round(res.travel_time_s, 3),
                    "lift_speed_mps": round(res.lift_speed_mps, 3),
                    "sample_count": res.sample_count,
                }

            return {
                "is_sampling": self._is_sampling,
                "elapsed_s": round(elapsed, 1),
                "result": res_dict,
            }

    def latest_reps(self) -> List[Rep]:
        with self._lock:
            return list(self._display)

    def is_full(self) -> bool:
        with self._lock:
            return len(self._display) >= DISPLAY_REP_COUNT