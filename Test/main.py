from machine import Pin, PWM, ADC
from CD4511 import CD4511
from time import sleep
import network
import urequests
import ujson as json
import time
import socket

FLASK_IP = "172.20.136.201"

# SSID et mot de passe WiFi
ssid = "Galaxy A25 5G F91E"
passwd = "ehef36fi6auwwq6"

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

# Fonction pour initialiser le serveur HTTP
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

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
if not wifi_connect():
    raise SystemExit("Impossible de connecter le WiFi")
print("Serveur HTTP prêt sur 0.0.0.0:80")

# Fonction pour gérer l'activation d'un capteur
def capteur_active(capteur, servo, blue_led=False, use_buzzer=False):
    """
    Fonction pour gérer l'activation d'un capteur.
    Attend 10 secondes et ferme la barrière si le capteur détecte un passage.
    Si rien n'est détecté, on ferme la barrière et on renvoie un timeout.
    """
    print("Activation du capteur : attente de détection pendant 10 secondes...")
    deadline = time.time() + 10
    triggered = False

    if use_buzzer:
        adc_value = pot.read_u16()
        freq = 500 + int((adc_value / 65535) * 2000)  # 500-2500 Hz
        buzzer.freq(freq)
        buzzer.duty_u16(32767)
        print(f"Buzzer activé à {freq} Hz pendant 5 secondes pendant l'attente de détection")
        buzzer_deadline = time.time() + 5
    else:
        buzzer_deadline = None

    while time.time() < deadline:
        if capteur.value() == 0:
            triggered = True
            break

        if blue_led:
            led_blue.value(1)
            sleep(0.1)
            led_blue.value(0)
            sleep(0.1)
        else:
            sleep(0.1)

        if use_buzzer and time.time() >= buzzer_deadline:
            buzzer.duty_u16(0)
            use_buzzer = False

    buzzer.duty_u16(0)
    led_blue.value(0)

    if triggered:
        print("Capteur déclenché : fermeture de la barrière")
        close_barrier(servo)
        return {"status": "ok", "message": "détection effectuée"}
    else:
        print("Aucune détection pendant 10 secondes : fermeture de la barrière")
        close_barrier(servo)
        return {"status": "timeout", "message": "aucune voiture détectée"}

# Fonction pour ouvrir la barrière
def open_barrier(servo, use_buzzer=False):
    """
    Fonction pour ouvrir la barrière.
    Utilise le servo pour ouvrir la barrière à 180 degrés.
    """
    duty = 6553  # Environ 2ms pour 180°
    print(f"Ouverture de la barrière sur servo {servo} duty={duty}")
    servo.duty_u16(duty)

# Fonction pour fermer la barrière
def close_barrier(servo):
    """
    Fonction pour fermer la barrière.
    Utilise le servo pour fermer la barrière à la position fermée.
    """
    duty = 2048  # Environ 0.625ms pour bien fermer
    print(f"Fermeture de la barrière sur servo {servo} duty={duty}")
    servo.duty_u16(duty)
    buzzer.duty_u16(0)
    print("Buzzer désactivé")

def update_led(places):
    # places = nombre de places libres
    if places == 0:
        # Parking plein
        led_green.value(0)
        led_orange.value(0)
        led_red.value(1)
    elif places <= 5:
        # Peu de places restantes (utilisé >=15)
        led_green.value(0)
        led_orange.value(1)
        led_red.value(0)
    else:
        # Places disponibles
        led_green.value(1)
        led_orange.value(0)
        led_red.value(0)

def get_parking_status():

    url = f"http://{FLASK_IP}:5000/parking/status"

    try:
        response = urequests.get(url)
        data = response.json()

        used = data["used"]
        free = data["free"]
    
        aff.show(free)
        update_led(free)
        response.close()

        return free

    except Exception as e:
        print("Erreur :", e)
        return None

while True:
    free_places = get_parking_status()
    print(f"Places libres: {free_places}")
    
    time.sleep(5)
    
    print("En attente de connexion HTTP...")
    cl, addr = s.accept()
    request = cl.recv(1024)
    try:
        request = request.decode("utf-8")
    except Exception:
        request = str(request)

    print("Requête reçue :", request)
    print("Adresse cliente :", addr)

    # SI FLASK ENVOIE /open
    result = {"status": "error", "message": "commande HTTP non reconnue"}

    if "GET /open" in request:
        print("Commande OPEN reçue")
        open_barrier(servo_enter)
        result = capteur_active(capteur_enter, servo_enter, blue_led=True, use_buzzer=True)
    elif "GET /close" in request:
        print("Commande CLOSE reçue")
        open_barrier(servo_exit)
        result = capteur_active(capteur_exit, servo_exit, blue_led=False, use_buzzer=False)
    else:
        print("Commande HTTP non reconnue")

    body = json.dumps(result)
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n"
        f"{body}"
    )
    cl.send(response)
    cl.close()
