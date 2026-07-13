import csv, os
from datetime import datetime, timezone
from .rep_detector import Rep

FIELDS = ["set_start_time", "rep_index_in_set", "logged_at",
          "time_up_s", "time_down_s", "max_speed_up_mps"]


class RepLogger:
    def __init__(self, path: str):
        self._path = path
        self._set_start_time = self._now()
        self._rep_index_in_set = 0
        if not os.path.exists(path):
            with open(path, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=FIELDS).writeheader()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def clear_set(self) -> None:
        self._set_start_time = self._now()
        self._rep_index_in_set = 0

    def log_rep(self, rep: Rep) -> None:
        with open(self._path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writerow({
                "set_start_time": self._set_start_time,
                "rep_index_in_set": self._rep_index_in_set,
                "logged_at": self._now(),
                "time_up_s": f"{rep.time_up_s:.3f}",
                "time_down_s": f"{rep.time_down_s:.3f}",
                "max_speed_up_mps": f"{rep.max_speed_up_mps:.3f}",
            })
        self._rep_index_in_set += 1

        