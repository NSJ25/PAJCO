import network
import socket
import urequests
from machine import Pin, PWM
import time

# ==========================
# WIFI
# ==========================
ssid = "Toumi❤️"
password = "toumi123"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
while not wlan.isconnected():
    pass
print("Connecté :", wlan.ifconfig())

# ==========================
# SERVO
# ==========================
servo = PWM(Pin(15))
servo.freq(50)

def set_angle(angle):
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
# CAPTEUR IR
# ==========================
capteur = Pin(4, Pin.IN)

# ==========================
# FONCTION CYCLE BARRIERE
# ==========================
def cycle_barriere(badge):
    print("Ouverture barrière")
    
    # 1️⃣ Ouverture servo progressive
    for angle in range(0, 91, 5):
        set_angle(angle)
        time.sleep(0.03)

    # 2️⃣ Attente pour que la voiture atteigne le capteur
    print("Attente arrivée voiture au niveau du capteur...")
    time.sleep(1.5)  # <-- délai ajustable selon la distance

    print("Surveillance capteur IR pour passage voiture")
    voiture_passee = False
    start_time = time.time()
    max_attente = 10  # secondes max pour la détection

    # 3️⃣ Boucle détection
    while time.time() - start_time < max_attente:
        if capteur.value() == 1 and not voiture_passee:
            voiture_passee = True
            print("Voiture détectée")
            
            # 🔊 Buzzer uniquement au passage
            beep(duration=0.5, freq=1500, volume=40000)

            # Update DB
            try:
                urequests.post(
                    "http://172.20.10.2:5000/update",
                    json={"badge": badge, "action": "entree"}
                )
            except:
                print("Erreur envoi DB")
            break  # sortie de boucle après détection

        time.sleep(0.05)

    # 4️⃣ Fermeture servo progressive
    print("Fermeture barrière")
    for angle in range(90, -1, -5):
        set_angle(angle)
        time.sleep(0.03)

    print("Cycle terminé")
# ==========================
# SERVEUR PICO
# ==========================
addr = socket.getaddrinfo('0.0.0.0', 8080)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print("Serveur Pico en écoute sur le port 8080...")

while True:
    cl, addr = s.accept()
    req = cl.recv(1024)

    if b"/ouvrir" in req:
        try:
            badge = req.split(b"badge=")[1].split(b" ")[0].decode()
        except:
            badge = "unknown"

        cycle_barriere(badge)

    cl.send("HTTP/1.0 200 OK\r\n\r\nOK")
    cl.close()
