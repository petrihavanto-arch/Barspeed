from .base import DistanceSensor
from .dummy import DummySensor


def create_sensor(args) -> DistanceSensor:
    if args.platform == "pc":
        return DummySensor()
    elif args.platform == "rpi":
        if args.sensor == "vl53l1x":
            from .vl53l1x_sensor import VL53L1XSensor
            return VL53L1XSensor(i2c_bus=args.i2c_bus, i2c_address=args.i2c_address)
        elif args.sensor == "sharp2y0a02":
            from .sharp2y0a02 import Sharp2Y0A02Sensor
            from .calibration import load_calibration
            return Sharp2Y0A02Sensor(
                channel=args.adc_channel,
                calib=load_calibration(args.calib_file),
            )
        raise ValueError(f"unknown sensor: {args.sensor!r}")
    raise ValueError(f"unknown platform: {args.platform!r}")