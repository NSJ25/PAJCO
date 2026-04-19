from machine import Pin, PWM, ADC
from umqtt.simple import MQTTClient
from CD4511 import CD4511
from time import sleep
import network

# SSID et mot de passe WiFi
ssid = "Techno"
passwd = "jeremie25"

# Pins pour les leds
led_red = Pin(0, Pin.OUT)
led_orange = Pin(1, Pin.OUT)
led_blue = Pin(2, Pin.OUT)
led_green = Pin(3, Pin.OUT)

# Pin pour le buzzer
buzzer = PWM(Pin(27))
buzzer.freq(1000)

# Pin pour le potentiomètre
pot = ADC(Pin(28))

# Pins pour les servos (enter et exit)
servo_enter = PWM(Pin(26))
servo_exit = PWM(Pin(22))
# Frequence des servos
servo_enter.freq(50)
servo_exit.freq(50)

# Pins pour les capteurs (enter et exit)
capteur_enter = Pin(21, Pin.IN, Pin.PULL_UP)
capteur_exit = Pin(20, Pin.IN, Pin.PULL_UP)

# Pins pour le decodeur 4511 et les transistors
bcd_pins = [6, 7, 8, 9]
transistor_pins = [4, 5]

# Afficheur 7 segments
aff = CD4511(bcd_pins, transistor_pins)

# Fonction pour se connecter au WiFi
def wifi_connect(timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    wlan.connect(ssid, passwd)
    print("Connexion au WiFi...")

    t = 0
    while not wlan.isconnected() and t < timeout:
        sleep(1)
        t += 1

    if wlan.isconnected():
        print("Connecté !")
        ip, masque, passerelle, dns = wlan.ifconfig()
        print(f"Adresse IP : {ip}, Masque réseau : {masque}, Passerelle : {passerelle}, DNS : {dns}")
        return True
    else:
        print("Impossible de se connecter au WiFi.")
        return False
# appel
wifi_connect()

# Fonction pour gérer l'activation d'un capteur
def capteur_active(capteur, servo):
    """
    Fonction pour gérer l'activation d'un capteur.
    Si le capteur est actif (valeur 0), ferme la barriere.
    Sinon, ouvre la barriere.
    """
    if capteur.value() == 0:
        close_barrier(servo)
        print("fermeture de la barriere")
    

# Fonction pour ouvrir la barriere
def open_barrier(servo):
    """
    Fonction pour ouvrir la barriere.
    Utilise le servo_enter pour ouvrir la barriere.
    """
    duty = int(1638 + (180 / 180) * (8192 - 1638))
    servo.duty_u16(duty)

# Fonction pour fermer la barriere
def close_barrier(servo):
    """
    Fonction pour fermer la barriere.
    Utilise le servo_exit pour fermer la barriere.
    """
    duty = int(1638 + (0 / 180) * (8192 - 1638))
    servo.duty_u16(duty)

