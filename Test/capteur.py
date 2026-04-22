from machine import Pin
import time

# Configuration du bouton sur la broche GP14 (à adapter selon ton câblage)
# pull_up interne activée : le bouton relie la broche au GND
bouton = Pin(20, Pin.IN, Pin.PULL_UP)

print("Test bouton démarré...")

while True:
    if bouton.value() == 0:  # LOW = bouton appuyé (avec PULL_UP)
        print("Bouton APPUYÉ !")
    else:
        print("Bouton relâché")
    
    time.sleep(0.1)  # Pause 100ms pour éviter le flood