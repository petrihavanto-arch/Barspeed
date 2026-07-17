"""Standalone hardware verification for the VL53L1X ToF sensor.
Run directly on the Pi: python3 tof_probe.py
Ctrl-C to stop.
"""

import argparse
import time

import VL53L1X

_DISTANCE_MODE_SHORT = 1
_TIMING_BUDGET_US = 50000
_INTER_MEASUREMENT_MS = 65


def main():
    p = argparse.ArgumentParser(description="VL53L1X hardware verification probe")
    p.add_argument("--i2c-bus", type=int, default=1)
    p.add_argument("--i2c-address", type=lambda x: int(x, 0), default=0x29)
    p.add_argument("--hz", type=float, default=10.0, help="print rate (sensor is read as fast as it's ready regardless)")
    args = p.parse_args()

    tof = VL53L1X.VL53L1X(i2c_bus=args.i2c_bus, i2c_address=args.i2c_address)
    tof.open()

 #   tof.set_distance_mode(_DISTANCE_MODE_SHORT)               # Set distance mode first
 #   tof.set_timing(_TIMING_BUDGET_US, _INTER_MEASUREMENT_MS) # Set custom budget second
    tof.start_ranging(1)                                      # Use 0 to preserve custom timing

    print(f"Ranging started (bus={args.i2c_bus}, addr=0x{args.i2c_address:02x}). "
          f"Move a target through ~0.2-1.5m. Ctrl-C to stop.")

    t0 = time.monotonic()
    n = 0
    print_interval = 1.0 / args.hz

    try:
        last_print = 0.0
        while True:
            distance_mm = tof.get_distance()  # blocks until a reading is ready
            t = time.monotonic() - t0
            n += 1
            valid = distance_mm > 0

            if t - last_print >= print_interval:
                status = f"{distance_mm:5d} mm" if valid else "  INVALID  "
                actual_rate = n / t if t > 0 else 0.0
                print(f"t={t:7.2f}s  {status}  (n={n}, avg_rate={actual_rate:5.1f} Hz)")
                last_print = t
    except KeyboardInterrupt:
        pass
    finally:
        tof.stop_ranging()
        tof.close()
        print("\nStopped.")


if __name__ == "__main__":
    main()
