import time
import pytest
from sensors.base import DistanceSensor, Reading
from analysis.session import Session, SAMPLING_TIMEOUT_S
from webapp.app import create_app


class MockSensor(DistanceSensor):
    def __init__(self, readings=None):
        self.readings = readings or []
        self._index = 0
        self.opened = False
        self.closed = False

    def open(self):
        self.opened = True

    @property
    def nominal_rate_hz(self) -> float:
        return 25.0

    def read(self):
        if self._index < len(self.readings):
            r = self.readings[self._index]
            self._index += 1
            return r
        return Reading(t=time.monotonic(), distance_m=1.0)

    def close(self):
        self.closed = True


class MockArgs:
    platform = "pc"
    log_file = "test_log.csv"
    json_log_file = "test_log.json"
    print = False
    rep = False
    dump = None


def test_session_sampling_toggle_and_timeout(tmp_path):
    readings = [
        Reading(t=0.0, distance_m=1.0),
        Reading(t=1.0, distance_m=0.9),
        Reading(t=9.0, distance_m=0.1),
        Reading(t=10.0, distance_m=0.0),
    ]
    sensor = MockSensor(readings)
    log_path = str(tmp_path / "test_session.csv")
    session = Session(sensor, log_path=log_path)

    status = session.get_sampling_status()
    assert not status["is_sampling"]
    assert status["result"] is None

    # Toggle to start sampling
    session.toggle_sampling()
    status = session.get_sampling_status()
    assert status["is_sampling"]
    assert status["result"] is None
    assert len(session.latest_reps()) == 0

    # Simulate buffering during sampling
    for r in readings:
        with session._lock:
            if session._is_sampling:
                if session._sampling_start_t is None:
                    session._sampling_start_t = r.t
                session._sampling_buffer.append(r)

    # Toggle to stop sampling
    session.toggle_sampling()
    status = session.get_sampling_status()
    assert not status["is_sampling"]
    assert status["result"] is not None
    assert status["result"]["highest_distance_m"] == 1.0
    assert status["result"]["lowest_distance_m"] == 0.0

    # Verify starting a new set clears metrics and reps table
    session.toggle_sampling()
    status_new = session.get_sampling_status()
    assert status_new["is_sampling"]
    assert status_new["result"] is None
    assert len(session.latest_reps()) == 0


def test_webapp_sampling_endpoints(tmp_path):
    log_path = str(tmp_path / "test_reps.csv")
    dump_path = str(tmp_path / "sensor_dump.csv")
    args = MockArgs()
    args.log_file = log_path
    args.dump = dump_path

    app = create_app(args)
    client = app.test_client()

    time.sleep(0.1)
    with open(dump_path, newline="") as dump_file:
        dump_lines = dump_file.readlines()
    assert dump_lines[0].strip() == "t,distance_m,valid"
    assert len(dump_lines) > 1

    res = client.get("/api/reps")
    assert res.status_code == 200
    data = res.get_json()
    assert "sampling" in data
    assert not data["sampling"]["is_sampling"]

    # Toggle clear/sampling
    post_res = client.post("/api/clear")
    assert post_res.status_code == 200
    post_data = post_res.get_json()
    assert post_data["sampling"]["is_sampling"] is True
