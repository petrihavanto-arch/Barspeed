"""Unit tests for RepLogger.

Focused on the two documented invariants that matter most in
practice: the header is written exactly once, and clear_set() never
deletes previously-logged rows.
"""
import csv

from analysis.rep_detector import Rep
from analysis.rep_logger import FIELDS, RepLogger


def make_rep(index=0, time_up=0.3, time_down=0.4, max_speed=1.2):
    return Rep(index=index, time_up_s=time_up, time_down_s=time_down,
               max_speed_up_mps=max_speed, completed_at=0.0)


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_header_written_once_on_first_creation(tmp_path):
    log_path = tmp_path / "reps_log.csv"
    RepLogger(str(log_path))

    with open(log_path, newline="") as f:
        header = next(csv.reader(f))
    assert header == FIELDS

    # Constructing a second RepLogger against the same (now-existing)
    # path must not rewrite/truncate the file.
    RepLogger(str(log_path))
    rows = read_rows(log_path)
    assert rows == []  # still just the header, no duplicate header row


def test_log_rep_appends_expected_fields(tmp_path):
    log_path = tmp_path / "reps_log.csv"
    logger = RepLogger(str(log_path))

    logger.log_rep(make_rep(index=0, time_up=0.321, time_down=0.456, max_speed=1.234))
    rows = read_rows(log_path)

    assert len(rows) == 1
    row = rows[0]
    assert row["rep_index_in_set"] == "0"
    assert row["time_up_s"] == "0.321"
    assert row["time_down_s"] == "0.456"
    assert row["max_speed_up_mps"] == "1.234"
    assert row["set_start_time"]  # non-empty ISO timestamp
    assert row["logged_at"]


def test_clear_set_does_not_delete_prior_rows(tmp_path):
    log_path = tmp_path / "reps_log.csv"
    logger = RepLogger(str(log_path))

    logger.log_rep(make_rep(index=0))
    first_set_start = read_rows(log_path)[0]["set_start_time"]

    logger.clear_set()
    logger.log_rep(make_rep(index=0))  # index resets to 0 for the new set

    rows = read_rows(log_path)
    assert len(rows) == 2  # nothing deleted -- both rows present
    assert rows[0]["set_start_time"] == first_set_start
    assert rows[1]["set_start_time"] != first_set_start
    assert rows[1]["rep_index_in_set"] == "0"


def test_rep_index_in_set_increments_within_a_set(tmp_path):
    log_path = tmp_path / "reps_log.csv"
    logger = RepLogger(str(log_path))

    logger.log_rep(make_rep(index=0))
    logger.log_rep(make_rep(index=1))
    logger.log_rep(make_rep(index=2))

    rows = read_rows(log_path)
    assert [r["rep_index_in_set"] for r in rows] == ["0", "1", "2"]
