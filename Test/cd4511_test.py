from CD4511 import CD4511
import time

bcd_pins = [6, 7, 8, 9]
transistor_pins = [4, 5]

aff = CD4511(bcd_pins, transistor_pins)

for i in range(0, 100):
    aff.show(i)
    time.sleep(0.5)

aff.stop()