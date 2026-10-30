import argparse
import csv
import sys

from analysis.rep_detector import RepDetector
from sensors import create_sensor


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read sensor locations and report detected barbell reps"
    )
    parser.add_argument(
        "--platform",
        choices=["rpi", "pc"],
        default="rpi",
        help="'rpi' uses the VL53L1X sensor; 'pc' uses a dummy sensor",
    )
    parser.add_argument("--i2c-bus", type=int, default=1)
    parser.add_argument(
        "--i2c-address",
        type=lambda value: int(value, 0),
        default=0x29,
        help="hex or decimal, e.g. 0x29",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    sensor = create_sensor(args)

    def report_segment(segment):
        print(
            f"Segment {segment.direction} "
            f"(started at t={segment.start_t:.3f}s, ended at t={segment.end_t:.3f}s): "
            f"{segment.duration_s:.3f}s "
            f"(average speed: {segment.avg_speed_mps:.3f} m/s, "
            f"max speed: {segment.max_speed_mps:.3f} m/s)",
            file=sys.stdout,
            flush=True,
        )

    detector = RepDetector(on_segment=report_segment)
    locations = csv.writer(sys.stdout, lineterminator="\n")
    locations.writerow(["t", "distance_m", "diff", "valid"])
    sys.stdout.flush()

    sensor.open()
    reading = sensor.read()
    try:
        while True:
            reading_old=reading
            reading = sensor.read()
            locations.writerow(
                [f"{reading.t:.3f}", f"{reading.distance_m:.3f}", f"{reading_old.distance_m-reading.distance_m}", str(reading.valid)]
            )
            sys.stdout.flush()

            rep = detector.update(reading)
            if rep is not None:
                print(
                    f"Rep {rep.index}: up {rep.time_up_s:.3f}s, "
                    f"down {rep.time_down_s:.3f}s, "
                    f"average up speed {rep.avg_speed_up_mps:.3f} m/s, "
                    f"max up speed {rep.max_speed_up_mps:.3f} m/s",
                    file=sys.stdout,
                    flush=True,
                )
    except KeyboardInterrupt:
        pass
    finally:
        sensor.close()


if __name__ == "__main__":
    main()
