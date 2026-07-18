# Barspeed — Known Issues, Decisions & Resolved Gotchas

This is the "why is it built this way" and "don't re-debug this" log —
separate from [MODULES.md](MODULES.md) so it stays skimmable on its
own. Update it as things get resolved or superseded; don't delete
resolved entries, move them to the "Resolved" section instead so the
reasoning stays discoverable.

## Open

### `up_is_decreasing` unverified

`RepDetector` defaults to assuming distance *decreases* as the bar
moves up (`up_is_decreasing=True` in `analysis/rep_detector.py`). This
has not been checked against the actual VL53L1X mounting orientation.
If it's wrong, every logged rep will have `time_up_s`/`time_down_s`
swapped — silently, since both are plausible-looking numbers. Check
once with a known up/down motion and a print statement before trusting
logged data.

### `MIN_ROM_M` untuned for VL53L1X

`analysis/constants.py` sets `MIN_ROM_M = 0.05`. This value's history
is Sharp-sensor-specific tuning discussion; it has not been
re-characterized against real VL53L1X noise. VL53L1X is meaningfully
cleaner than Sharp was, so this may now be more conservative than
necessary — or it may still need adjustment depending on mounting
distance and target reflectivity. Recommended approach: log raw
`Reading` streams from real sets and look at the actual noise floor
before changing this value.

### No dedicated kinematics module

There's no separate distance→velocity module. `max_speed_up_mps` is
computed inline in `analysis/rep_detector.py`'s
`_max_speed_in_window()` as a simple point-to-point max
(`|Δdistance|/Δt` between consecutive samples), not a
filtered/smoothed velocity curve. At ~20Hz with VL53L1X's lower noise
floor this has been acceptable so far, but worth revisiting once more
real rep data is available — particularly whether point-to-point max
is systematically biased high by any single noisy sample pair, versus
a smoothed estimate.

### Acquisition thread death is logged but still silent to the UI

`Session._run()` wraps `sensor.read()`/`detector.update()` in a
`try/except`, logs the exception via `logging.exception(...)`, then
re-raises. This is an improvement over the original silent-death
behavior (it's now in the server log), but the thread still dies and
Flask keeps serving stale `/api/reps` JSON indefinitely with nothing
visible in the UI itself. If long unattended sessions matter, consider
either a supervisory restart of the acquisition thread, or surfacing
thread-health state through `/api/reps` (e.g. a `stale: true` flag)
so `index.html` can show something visibly wrong rather than a frozen
table.

### Duplicate `DummySensor` in `sharp2y0a02.py`

`sensors/sharp2y0a02.py` contains a second, near-identical
`class DummySensor(DistanceSensor)` at the bottom of the file,
duplicating `sensors/dummy.py`. It isn't imported or referenced
anywhere — `factory.py` imports `DummySensor` from `.dummy` — so it's
inert dead code, but it's the kind of duplication that invites
"which one is actually used?" confusion later, or a fix applied to one
copy and not the other. Safe to delete.

### No automated tests

No test suite exists yet. `sensors/dummy.py`'s deterministic sine-wave
`DummySensor` was earlier suggested as a reasonable fixture for a
`pytest` suite exercising `RepDetector` directly — feeding it a
hand-constructed list of `Reading`s with known turnarounds is more
useful for validating detector logic than driving it through the live
sine wave, since you can encode exact expected `Rep` outputs (known
ROM, known noise spikes to confirm debounce behavior, known invalid
reads to confirm the `valid` gate) rather than asserting against a
continuously-running signal.

## Resolved

### VL53L1X `start_ranging`/`set_distance_mode` ordering bug

**Symptom:** `get_distance()` blocked ~4.4s per call instead of the
intended ~20Hz.

**Root cause:** calling `set_distance_mode()` separately *before*
`set_timing()` + `start_ranging(0)` left the sensor in its power-on
default (Long range) distance mode, which has a much longer minimum
timing budget than the custom timing requested — the custom timing
was applied, but to the wrong mode.

**Fix:** set distance mode via the argument to `start_ranging()`
itself (`start_ranging(_DISTANCE_MODE_SHORT)`), immediately after
`set_timing()`, with no separate `set_distance_mode()` call in
between. Applied in both `sensors/vl53l1x_sensor.py` and
`tof_probe.py` — confirmed present in both as of this doc.

**Root-caused via:** instrumenting `get_distance()` directly with
`time.perf_counter()`, checking the I2C driver (`i2c_bcm2835`, ruled
out), checking bus clock (100kHz, normal), then comparing the
library's bare-bones example (fast) against the custom config (slow) —
isolated to the `set_distance_mode()`/`start_ranging(0)` call
ordering.

### Rep-detector false triggers from single-sample noise

**Symptom:** noisy individual samples near a real turnaround were
occasionally confirmed as spurious extra rep completions.

**Fix:** two changes to `analysis/rep_detector.py`:
1. `update()` now drops any `Reading` with `valid=False` before it
   touches trend/extremum state, so an invalid 0-distance VL53L1X read
   can't be mistaken for a huge, fast reversal.
2. Added `debounce_samples` (default 2): a reversal only confirms
   after that many *consecutive* non-extending samples past
   `MIN_ROM_M`, rather than on the first sample that crosses the
   threshold. The extremum stays frozen during the debounce window and
   only advances again if a sample resumes extending the original
   trend — so a single noisy blip that bounces back correctly
   un-triggers instead of partially confirming.

This was chosen over a low-pass filter on the input signal because it
fixes the actual mechanism (single-sample confirmation with no
debounce) without adding phase lag to the timing/peak-speed
calculations, which a filter upstream of `_build_segment()` would have
introduced.

### `webapp/app.py` leftover dead entry-point block

An earlier leftover `if __name__ == "__main__":` block (predating
`main.py` as the actual entry point) has been removed. `create_app()`
is now the only way this module is invoked, always via `main.py`.

### `adcprobe.py` recreated

The standalone Sharp/MCP3202 hardware tester was originally written
ad hoc and not saved to a canonical file path. It now exists at
`adcprobe.py` (note: no underscore — differs slightly from
`tof_probe.py`'s naming, worth aligning if you rename either later).

## Environment notes

- RPi is an older board: `i2c_bcm2835` driver (not `bcm2708`), single
  I2C bus (`i2c-1` only, no legacy `i2c-0`), 100kHz clock. Nothing
  unusual here once the VL53L1X ordering bug above was fixed.
- Running Python 3.14.6 on `armv7` on the Pi itself; the checked-in
  `pyproject.toml` requires `>=3.12`, and the dev-machine `.venv`
  captured in this snapshot is Python 3.12 — worth keeping the two
  environments' dependency versions in sync manually since there's no
  lockfile constraining them together.
- PC dev machine: Kubuntu on a ThinkPad X250.
- Git remote is a bare repo under a Dropbox-synced path,
  `/mnt/sda5/Dropbox/Cloud7/git/Barspeed.git`. Hit a permission error
  once from mixed file ownership (`petri` vs `git` user) on loose
  objects — fixed via `chown -R`, `chmod -R g+rwX`,
  `find -exec chmod g+s`, and `git config core.sharedRepository
  group`. Watch for recurrence if anything else writes to this repo as
  a different user.
