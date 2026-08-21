import argparse
from datetime import datetime, timezone

from webapp.app import create_app


def parse_args():
    p = argparse.ArgumentParser(description="Bar speed meter and logger")
    p.add_argument("--platform", choices=["rpi", "pc"], default="rpi",
                    help="'rpi' uses VL53L1X sensor; 'pc' uses a dummy sensor for development")
    # VL53L1X (I2C)
    p.add_argument("--i2c-bus", type=int, default=1)
    p.add_argument("--i2c-address", type=lambda x: int(x, 0), default=0x29,
                    help="hex or decimal, e.g. 0x29")
    # Logging - both default to a fresh, paired pair of files per run
    p.add_argument("--log-file", default=None,
                    help="defaults to reps_<run-start-timestamp>.csv, a fresh file each run")
    p.add_argument("--json-log-file", default=None,
                    help="defaults to reps_<run-start-timestamp>.json, a fresh file each run")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("-p", "--print", action="store_true",
                    help="print raw sensor readings to stdout in runtime")
    p.add_argument("-r", "--rep", action="store_true",
                    help="print detected rep details to stdout in runtime")
    p.add_argument("-vw", "--verbose-web", action="store_true",
                    help="enable verbose web server request printing")
    args = p.parse_args()

    if args.log_file is None or args.json_log_file is None:
        run_start = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if args.log_file is None:
            args.log_file = f"reps_{run_start}.csv"
        if args.json_log_file is None:
            args.json_log_file = f"reps_{run_start}.json"

    return args


if __name__ == "__main__":
    args = parse_args()
    if not args.verbose_web:
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = create_app(args)
    print(f" * Bar speed logger: http://{args.host}:{args.port}/")
    app.run(host=args.host, port=args.port)