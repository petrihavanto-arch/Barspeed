from .base import DistanceSensor
from .dummy import DummySensor


def create_sensor(args) -> DistanceSensor:
    """Only place in the codebase that branches on --platform.
    The 'rpi' import is deferred to inside this function (rather than
    at module top-level) so that importing sensors/factory.py on a PC
    never pulls in ADCDACPi/spidev."""
    if args.platform == "pc":
        return DummySensor()
    elif args.platform == "rpi":
        from .sharp2y0a02 import Sharp2Y0A02Sensor
        from .calibration import load_calibration  # your voltage->distance loader
        return Sharp2Y0A02Sensor(
            channel=args.adc_channel,
            calib=load_calibration(args.calib_file),
        )
    raise ValueError(f"unknown platform: {args.platform!r}")