from machine import Pin
import time
from CD4511 import CD4511  # si classe dans fichier CD4511.py

# Configuration des pins (ADAPTE SELON TON CABLAGE)
bcd_pins = [2, 3, 4, 5]         # A, B, C, D
transistor_pins = [6, 7]        # unités, dizaines
le_pin = 8
bi_pin = 9
lt_pin = 10

display = CD4511(
    bcd_pins=bcd_pins,
    transistor_pins=transistor_pins,
    le_pin=le_pin,
    bi_pin=bi_pin,
    lt_pin=lt_pin
)

# Test 1 : test segments
print("Test segments...")
display.test_segments()
time.sleep(2)
display.stop_test()

# Test 2 : compteur 0 → 99
print("Compteur 0 à 99")

while True:
    for i in range(100):
        display.set_value(i)

        # rafraîchissement rapide pendant 0.5 seconde
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 500:
            display.refresh()