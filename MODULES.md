# Barspeed — Module Reference

Per-file reference: public interface, invariants, and sharp edges. See
[ARCHITECTURE.md](ARCHITECTURE.md) for the overall data flow.

---

## `sensors/base.py`

The contract every layer above sensors depends on.

```python
@dataclass
class Reading:
    t: float          # seconds, monotonic clock, relative to sensor open()
    distance_m: float
    valid: bool = True

class DistanceSensor(ABC):
    def open(self) -> None: ...
    def read(self) -> Reading: ...
    def close(self) -> None: ...
    @property
    def nominal_rate_hz(self) -> float: ...
```

**Invariant:** `t` is relative to *that sensor instance's* `open()` call,
not wall-clock time or epoch time. Don't compare `t` values across a
sensor swap or a restart without accounting for this.

**Invariant:** `valid=False` means "no usable distance" (e.g. VL53L1X
out-of-range/no-target read returning 0). Every consumer of a `Reading`
stream must check `valid` before treating `distance_m` as real —
`RepDetector.update()` does this at the very top of the method.

---

## `sensors/factory.py`

```python
def create_sensor(args) -> DistanceSensor
```

The **only** branch point between sensor implementations. Reads
`args.platform` and `args.sensor` (from `main.py`'s argparse
namespace) and lazily imports the concrete sensor class — hardware
libraries (`VL53L1X`, `ADCDACPi`) are only imported inside the branch
that needs them, so the module tree stays importable on a PC with no
I2C/SPI hardware present.

Raises `ValueError` on an unrecognized `platform` or `sensor` string
rather than failing silently.

---

## `sensors/dummy.py`

```python
class DummySensor(DistanceSensor):
    def __init__(self, rate_hz: float = 25.0): ...
```

PC development stand-in. Produces a sine wave (`0.85 + 0.15*sin(t)`)
so the whole pipeline can be exercised end-to-end without hardware.
**Not** meant to mimic a real rep waveform (no distinct up/down phases,
no realistic velocity profile) — it exists to prove the plumbing
works, not to validate `RepDetector` logic. A `pytest` suite driving
`RepDetector` directly with a hand-built `Reading` list would be more
useful for that than this class (see [KNOWN_ISSUES.md](KNOWN_ISSUES.md#no-automated-tests)).

`read()` calls `time.sleep(1/rate_hz)` internally — it paces itself,
callers don't need their own sleep.

---

## `sensors/vl53l1x_sensor.py`

Current primary sensor. ToF laser distance sensor via I2C (pimoroni's
`VL53L1X` python package). Returns distance directly in mm — **no
calibration curve needed**, unlike Sharp.

```python
_DISTANCE_MODE_SHORT = 1     # passed directly to start_ranging()
_TIMING_BUDGET_US = 20000
_INTER_MEASUREMENT_MS = 50   # ~20Hz; must be >= timing budget in ms
```

**Critical ordering requirement** (this was a real, already-debugged
bug — see [KNOWN_ISSUES.md](KNOWN_ISSUES.md#vl53l1x-start_ranging-ordering-bug)
for the full story): `open()` must call `set_timing()` then
`start_ranging(_DISTANCE_MODE_SHORT)` — **never** a separate
`set_distance_mode()` call before `start_ranging(0)`. The wrong
ordering silently leaves the sensor in its power-on default (Long
range) distance mode, which has a much longer minimum timing budget
than requested, making `get_distance()` block ~4.4s per call instead
of the intended ~20Hz.

`read()`:
- `get_distance()` **blocks** until a reading is ready (polls
  `VL53L1_WaitMeasurementDataReady()` internally in ST's driver) — do
  not wrap it in your own `time.sleep()`.
- Returns `0` on an invalid/no-target read; `Reading.valid` reflects
  this (`valid = distance_mm > 0`).

`open()` and `close()` are lazy-import friendly: the `import VL53L1X`
happens inside `__init__`, not at module load, so this file is
importable (just not instantiable) on a PC with no hardware.

---

## `sensors/sharp2y0a02.py`

Legacy/fallback sensor. Analog IR via MCP3202 ADC
(`ABElectronics_Python_Libraries` `ADCDACPi` class — SPI bus 0
hardcoded internally by that library; device 0 = ADC/CE0, device 1 =
DAC/CE1, not configurable without editing the library source).

- `read_adc_voltage(channel, mode)` needs both args; `mode=0` is
  single-ended (what's used here), `mode=1` is differential.
- Known hardware limits (documented, still valid): ~38ms±10ms response
  (~20–26Hz ceiling), ~±10cm accuracy at 80cm, nonlinear
  voltage-vs-distance requiring calibration, reflectivity-dependent.
  This is why the project moved to VL53L1X.
- `close()` is a no-op — `ADCDACPi` has no explicit close call.

**Dead code found in this file:** a second `class DummySensor(...)` is
defined at the bottom of `sharp2y0a02.py`, duplicating
`sensors/dummy.py` almost verbatim. It is not imported or used
anywhere — `factory.py` imports `DummySensor` from `.dummy`, not from
here. Safe to delete; see
[KNOWN_ISSUES.md](KNOWN_ISSUES.md#duplicate-dummysensor-in-sharp2y0a02py).

---

## `sensors/calibration.py`

```python
def load_calibration(path: str) -> Callable[[float], float]
```

Sharp-only. Returns a callable `voltage -> distance_m`. Currently
**always** returns the nominal datasheet curve
(`distance_cm ≈ 60.374 * V^-1.16`, clamped to 0.20–1.50m), regardless
of whether `path` exists — if the calibration file is present, it's
read (`json.load`) but the parsed data is discarded (`# noqa: F841`)
rather than fitted. This is an explicit, documented stub, not a bug —
but it means any `calibration.json` you point at it today has no
effect. Irrelevant while VL53L1X (which needs no calibration curve) is
primary.

---

## `analysis/constants.py`

```python
REP_START_FRACTION = 0.10   # "start" of a movement, as a fraction into that segment's own ROM
REP_END_FRACTION = 0.90     # "end" of a movement, same basis
MIN_ROM_M = 0.05            # minimum excursion to confirm a real turnaround
DISPLAY_REP_COUNT = 5
```

**`MIN_ROM_M` was tuned against the Sharp sensor's noise floor**, not
VL53L1X's. VL53L1X is meaningfully cleaner (~20Hz, low noise vs.
Sharp's ~25Hz-with-large-noise), so this value may now be more
conservative than necessary, or may still be too small depending on
mounting and target reflectivity — it hasn't been re-characterized
against real VL53L1X data. See
[KNOWN_ISSUES.md](KNOWN_ISSUES.md#min_rom_m-untuned-for-vl53l1x).

---

## `analysis/rep_detector.py`

Core turnaround-detection and segment-building logic. Two public
dataclasses:

```python
@dataclass
class Segment:
    direction: str        # "up" or "down"
    duration_s: float     # time between the 10% and 90% crossings
    max_speed_mps: float  # peak point-to-point speed within that window

@dataclass
class Rep:
    index: int
    time_up_s: float
    time_down_s: float
    max_speed_up_mps: float
    completed_at: float
```

### `RepDetector`

```python
RepDetector(up_is_decreasing: bool = True, debounce_samples: int = 2)
```

Streaming detector — feed one `Reading` at a time via `update()`,
which returns a completed `Rep` or `None`.

- **`up_is_decreasing`** encodes the sensor's mounting orientation:
  default assumes distance *decreases* as the bar moves up. **Not yet
  verified against the real VL53L1X mounting** — if wrong, "time up"
  and "time down" will be swapped in every logged rep. See
  [KNOWN_ISSUES.md](KNOWN_ISSUES.md#up_is_decreasing-unverified).
- **`debounce_samples`** — number of consecutive non-extending samples
  required before a reversal is confirmed as a real turnaround,
  instead of acting on the first sample past `MIN_ROM_M`. Added to
  reject single-sample noise spikes near a true turnaround being
  mistaken for a direction change. The extremum is frozen during the
  debounce window; it only advances again on a sample that resumes
  extending the original trend (i.e. a reversal candidate that turns
  out to be noise correctly un-triggers rather than partially firing).

`update()` invariants:
1. Drops any reading with `valid=False` immediately, before it touches
   trend/extremum state.
2. A `Rep` is only emitted once a full up-then-down cycle completes —
   a completed down-segment with no preceding pending up-segment is
   silently discarded in `_consume()` (handles the stream starting
   mid-rep cleanly, at the cost of that first partial segment's data).
3. `Segment.duration_s` and `max_speed_mps` are computed only over the
   **10%–90%-of-that-segment's-own-ROM window** (`_build_segment`),
   not the full excursion — this excludes the noisier
   near-endpoint samples from both timing and peak-speed calculations,
   which is a form of noise mitigation independent of the debounce
   logic above.

`_max_speed_in_window()` computes a simple point-to-point max
(`|Δdistance| / Δt` between consecutive readings within the window) —
this is **not** a filtered or smoothed velocity curve. See
[ARCHITECTURE.md](ARCHITECTURE.md) and
[KNOWN_ISSUES.md](KNOWN_ISSUES.md#no-dedicated-kinematics-module) for
context on why there's no separate kinematics module yet.

---

## `analysis/rep_logger.py`

```python
class RepLogger:
    def __init__(self, path: str): ...
    def clear_set(self) -> None: ...
    def log_rep(self, rep: Rep) -> None: ...
```

CSV fields: `set_start_time, rep_index_in_set, logged_at, time_up_s,
time_down_s, max_speed_up_mps`.

**Invariant:** every rep ever detected is logged permanently.
`clear_set()` never deletes rows — it only starts a new
`set_start_time` and resets `rep_index_in_set` to 0 for subsequent
rows. The header is written once, on first construction, only if
`path` doesn't already exist (so re-running against an existing log
file appends rather than truncating).

A rep mid-flight when `clear_set()` is called will still complete and
log normally as rep 0 of the new set — this is a deliberate choice
(display-buffer clearing in `Session.clear()` is separate from
`RepLogger`'s own state), flagged as worth reconsidering if it proves
surprising in practice.

---

## `analysis/session.py`

```python
class Session:
    def __init__(self, sensor: DistanceSensor, log_path: str): ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def clear(self) -> None: ...
    def latest_reps(self) -> List[Rep]: ...
```

Owns the sensor, detector, logger, and the background acquisition
thread. This is the seam between the acquisition/analysis layers and
the web layer — `webapp/app.py` only ever calls `start()`, `clear()`,
and `latest_reps()`.

**Threading:** `_run()` loops `sensor.read()` → `detector.update()` on
a daemon thread. Completed reps go to `RepLogger.log_rep()` and to a
`deque(maxlen=DISPLAY_REP_COUNT)` guarded by a `threading.Lock`.
`latest_reps()` takes the same lock to read the deque — this is the
only synchronization point between the acquisition thread and Flask's
request-handling threads.

**Error handling:** `_run()` wraps `detector.update(sensor.read())` in
a `try/except Exception`, logs via `logging.exception(...)`, and then
**re-raises**. The exception is no longer silent (the earlier concern
in the project notes was that the loop died with zero visible
indication) — but the thread still dies and Flask keeps serving stale
`/api/reps` data indefinitely afterward, with nothing surfaced to the
UI itself. See
[KNOWN_ISSUES.md](KNOWN_ISSUES.md#acquisition-thread-death-is-logged-but-still-silent-to-the-ui).

`stop()` joins the thread with a 2-second timeout before closing the
sensor — if `_run()` is blocked inside a hardware `read()` call longer
than that (e.g. the VL53L1X `get_distance()` blocking call under some
fault condition), `stop()` will return without the thread having
actually exited.

---

## `webapp/app.py`

```python
def create_app(args) -> Flask
```

Single-file Flask app factory. Constructs one `Session` per app
instance (via `create_sensor(args)`) and starts it immediately inside
`create_app()` — there's no separate "arm" step; the acquisition
thread is running before the first HTTP request arrives.

Routes:

| Route | Method | Behavior |
|---|---|---|
| `/` | GET | Renders `templates/index.html` |
| `/api/reps` | GET | JSON list of the last `DISPLAY_REP_COUNT` reps (rounded to 3 decimals) |
| `/api/clear` | POST | Calls `session.clear()`, returns `{"status": "cleared"}` |

No authentication, no CSRF protection, no rate limiting — appropriate
for a LAN-only single-user tool, worth reconsidering only if this is
ever exposed beyond `localhost`/trusted LAN.

---

## `webapp/templates/index.html`

Single static page, no build step. Polls `/api/reps` every 1000ms via
`fetch()` and re-renders a table of the last 5 reps client-side. The
clear-set button POSTs to `/api/clear` then immediately calls
`refresh()` — no optimistic UI update, so there's a brief
network-round-trip delay before the table reflects the clear.

---

## `main.py`

Argument parsing and process entry point. See
[ARCHITECTURE.md](ARCHITECTURE.md#cli-mainpy) for the full CLI
reference. Notable: `--i2c-address` uses `type=lambda x: int(x, 0)` so
it accepts both hex (`0x29`) and decimal on the command line.

---

## `tof_probe.py` / `adcprobe.py`

Standalone hardware verification scripts — run directly on the Pi,
independent of Flask/`analysis`/`Session`. Useful for isolating
whether a problem is in the sensor wiring/config or in the pipeline
above it.

- `tof_probe.py`: prints distance + rolling average sample rate at a
  configurable print rate (`--hz`, default 10). Ranging config mirrors
  `vl53l1x_sensor.py` but hardcodes `start_ranging(1)` rather than
  referencing the `_DISTANCE_MODE_SHORT` constant — functionally
  correct today since the constant's value is 1, but the duplication
  means the two files can silently drift out of sync if the mode ever
  changes in one place and not the other.
- `adcprobe.py`: prints raw voltage on ADC channels 1 and 2 at 5Hz.
  Note this reads different channels (1, 2) than the default
  `--adc-channel 0` used by `main.py`/`Sharp2Y0A02Sensor` — intentional
  for probing both channels during wiring checks, not meant to mirror
  the app's runtime channel selection.
