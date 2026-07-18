"""Standalone hardware verification for the Sharp 2Y0A02 / MCP3202 ADC.
Run directly on the Pi: python3 adcprobe.py
Ctrl-C to stop. No Flask/threads/RepDetector involved.
"""
import time

from ADCDACPi import ADCDACPi


def main():
    adc = ADCDACPi()
    adc.set_adc_refvoltage(3.3)

    try:
        while True:
            v1 = adc.read_adc_voltage(1, 0)
            v2 = adc.read_adc_voltage(2, 0)
            print(f"ch1: {v1:.3f}V  ch2: {v2:.3f}V")
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
