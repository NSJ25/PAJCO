import network
import socket
import urequests
from machine import Pin, PWM
import time

# ==========================
# WIFI
# ==========================
ssid = "Galaxy A25 5G F91E"
password = "ehef36fi6auwwq6"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)


timeout = 15  # secondes max
start = time.time()

while not wlan.isconnected():
    if time.time() - start > timeout:
        print("Erreur : impossible de se connecter au Wifi")
        break
    time.sleep(0.5)

if wlan.isconnected():
    print("Connecté :", wlan.ifconfig())
else:
    print("Wifi non connecté, certaines fonctions réseau ne marcheront pas")
# ==========================
# SERVOS
# ==========================
servo_entree = PWM(Pin(15))
servo_entree.freq(50)

servo_sortie = PWM(Pin(14))  # nouveau servo pour la sortie
servo_sortie.freq(50)

def set_angle_servo(servo, angle):
    duty = int(1000 + (angle / 180) * 8000)
    servo.duty_u16(duty)

# ==========================
# BUZZER PASSIF
# ==========================
buzzer = PWM(Pin(1))
buzzer.freq(1000)
buzzer.duty_u16(0)

def beep(duration=0.3, freq=1500, volume=40000):
    buzzer.freq(freq)
    buzzer.duty_u16(volume)
    time.sleep(duration)
    buzzer.duty_u16(0)

# ==========================
# CAPTEURS IR
# ==========================
capteur_entree = Pin(16, Pin.IN)
capteur_sortie = Pin(17, Pin.IN)  # nouveau capteur pour la sortie

# ==========================
# FONCTION CYCLE BARRIERE
# ==========================
def cycle_barriere(badge, servo, capteur, action="entree"):
    print(f"{action} - ouverture")

    # ouvrir
    for angle in range(0, 91, 5):
        set_angle_servo(servo, angle)
        time.sleep(0.03)

    print("Attente voiture...")

    # 🔥 attendre que la voiture arrive (capteur actif)
    while capteur.value() == 1:
        time.sleep(0.05)

    print("Voiture détectée")

    # 🔊 buzzer uniquement ici
    beep(0.5, 1500, 40000)

    # 🔥 attendre que la voiture parte (capteur libéré)
    while capteur.value() == 0:
        time.sleep(0.05)

    print("Voiture passée")

    # update DB
    try:
        urequests.post(
            "http://172.20.10.2:5000/update",
            json={"badge": badge, "action": action}
        )
    except:
        print("Erreur DB")

    # fermer
    print("Fermeture")
    for angle in range(90, -1, -5):
        set_angle_servo(servo, angle)
        time.sleep(0.03)

    print("Cycle terminé")

# ==========================
# SERVEUR PICO
# ==========================
addr = socket.getaddrinfo('0.0.0.0', 8081)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)

print("Serveur Pico en écoute sur le port 8081...")

while True:
    cl, addr = s.accept()
    req = cl.recv(1024)

    if b"/ouvrir" in req:
        try:
            badge = req.split(b"badge=")[1].split(b" ")[0].decode()
        except:
            badge = "unknown"

        # ⚡ Entrée
        cycle_barriere(badge, servo_entree, capteur_entree, "entree")

    if b"/sortie" in req:
        try:
            badge = req.split(b"badge=")[1].split(b" ")[0].decode()
        except:
            badge = "unknown"

        # ⚡ Sortie
        cycle_barriere(badge, servo_sortie, capteur_sortie, "sortie")

    cl.send("HTTP/1.0 200 OK\r\n\r\nOK")
    cl.close()
