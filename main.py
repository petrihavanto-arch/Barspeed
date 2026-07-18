import argparse

from webapp.app import create_app


def parse_args():
    p = argparse.ArgumentParser(description="Bar speed meter and logger")
    p.add_argument("--platform", choices=["rpi", "pc"], default="rpi",
                   help="'rpi' uses a real sensor; 'pc' uses a dummy sensor for development")
    p.add_argument("--sensor", choices=["vl53l1x", "sharp2y0a02"], default="vl53l1x",
                   help="which real sensor to use (rpi only)")
    # VL53L1X (I2C)
    p.add_argument("--i2c-bus", type=int, default=1)
    p.add_argument("--i2c-address", type=lambda x: int(x, 0), default=0x29,
                   help="hex or decimal, e.g. 0x29")
    # Sharp 2Y0A02 (SPI/ADC)
    p.add_argument("--adc-channel", type=int, default=0)
    p.add_argument("--calib-file", default="calibration.json")
    p.add_argument("--log-file", default="reps_log.csv")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5000)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = create_app(args)
    app.run(host=args.host, port=args.port)
