from machine import Pin, PWM, ADC
import time

# Initialisation des composants
buzzer = PWM(Pin(15))   # PWM pour contrôler le buzzer
buzzer.freq(1000)               # Fréquence fixe à 1000 Hz
buzzer.duty_u16(0)              # Buzzer éteint au départ

pot = ADC(Pin(26))         # Potentiomètre en entrée analogique


# Boucle principale

try:
    while True:
        # Lire la valeur du potentiomètre (0 à 65535)
        pot_val = pot.read_u16()

        # Calcul du duty cycle proportionnel pour le volume
        duty = pot_val  # 0 = silence, 65535 = volume max
        buzzer.duty_u16(duty)  # Appliquer le volume

        # Affichage debug pour vérifier
        print("Potentiomètre:", pot_val, "=> Volume duty:", duty)

        # Petit délai pour ne pas saturer le CPU
        time.sleep(0.01)  # 10 ms, court, pour boucle fluide

except KeyboardInterrupt:
    # Éteindre le buzzer si on interrompt le programme
    buzzer.duty_u16(0)
    print("Buzzer éteint")
