from decode import Decode

# Pins BCD : A,B,C,D = 0,1,2,3
# Transistors : unités/dizaines = 10,11
display = Decode(bcd_pins=[0,1,2,3], transistor_pins=[10,11])

# Allumer afficheurs
display.on()

# Variable externe
places = 7
display.set_value(places)  # affichera 07

# Boucle principale
while True:
    display.refresh(delay_ms=5)  # multiplexage non bloquant
