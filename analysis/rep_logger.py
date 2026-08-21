"""CSV logging for completed reps. Every rep ever detected is appended
permanently -- clearing a set never deletes rows, it only starts a new
`set_start_time` and resets the per-set index (see `clear_set`).
"""
import csv
import os
from datetime import datetime, timezone

from .rep_detector import Rep

FIELDS = ["set_start_time", "rep_index_in_set", "logged_at",
          "time_up_s", "time_down_s", "avg_speed_up_mps", "max_speed_up_mps"]


class RepLogger:
    """Appends completed `Rep`s to a CSV file at `path`.

    The header row is written once, only if `path` doesn't already
    exist, so re-running against an existing log file appends rather
    than truncating it.
    """

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
        """Start a new set: resets the per-set rep index and start
        time for subsequent rows. Does not delete or modify any
        already-logged rows."""
        self._set_start_time = self._now()
        self._rep_index_in_set = 0

    def log_rep(self, rep: Rep) -> None:
        """Append one completed rep as a new CSV row."""
        with open(self._path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writerow({
                "set_start_time": self._set_start_time,
                "rep_index_in_set": self._rep_index_in_set,
                "logged_at": self._now(),
                "time_up_s": f"{rep.time_up_s:.3f}",
                "time_down_s": f"{rep.time_down_s:.3f}",
                "avg_speed_up_mps": f"{rep.avg_speed_up_mps:.3f}",
                "max_speed_up_mps": f"{rep.max_speed_up_mps:.3f}",
            })
        self._rep_index_in_set += 1

