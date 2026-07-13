import argparse

from webapp.app import create_app


def parse_args():
    p = argparse.ArgumentParser(description="Bar speed meter and logger")
    p.add_argument("--platform", choices=["rpi", "pc"], default="rpi",
                    help="'rpi' uses the real Sharp 2Y0A02 sensor via MCP3202; "
                         "'pc' uses a dummy sensor for development, no hardware required")
    p.add_argument("--adc-channel", type=int, default=0,
                    help="MCP3202 ADC channel the sensor is wired to (rpi only)")
    p.add_argument("--calib-file", default="calibration.json",
                    help="path to sensor calibration data (rpi only)")
    p.add_argument("--log-file", default="reps_log.csv",
                    help="path to append-only rep log CSV")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5000)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = create_app(args)
    app.run(host=args.host, port=args.port)

