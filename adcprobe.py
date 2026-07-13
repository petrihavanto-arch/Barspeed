# adc_probe.py — run directly, no Flask/threads/RepDetector involved
from ADCDACPi import ADCDACPi
import time

adc = ADCDACPi()
adc.set_adc_refvoltage(3.3)

while True:
    v1 = adc.read_adc_voltage(1, 0)
    v2 = adc.read_adc_voltage(2, 0)
    print(f"ch1: {v1:.3f}V  ch2: {v2:.3f}V")
    time.sleep(0.2)

    