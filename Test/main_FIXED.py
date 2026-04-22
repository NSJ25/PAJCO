from machine import Pin, PWM, ADC
from CD4511 import CD4511
from time import sleep
import network
import urequests
import ujson as json
import time
import socket

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
buzzer.duty_u16(0)  # Éteint au démarrage

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

# Variable globale pour le statut parking
current_free_places = 0
last_update_time = 0
UPDATE_INTERVAL = 5  # Mise à jour toutes les 5 secondes

# Fonction pour initialiser le serveur HTTP
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permet de redémarrer sans attendre
s.bind(addr)
s.listen(1)
s.setblocking(False)  # MODE NON-BLOQUANT ! Important !

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

# CORRECTION SERVOMOTEURS : Nouvelles valeurs duty
def open_barrier(servo, use_buzzer=False):
    """
    Fonction pour ouvrir la barrière.
    CORRECTION: duty_u16 pour 2ms = 6553 (180°)
    """
    duty = 6553  # 2ms → 180° (OUVERT)
    print(f"Ouverture de la barrière duty={duty}")
    servo.duty_u16(duty)
    
    # Buzzer optionnel pendant ouverture
    if use_buzzer:
        activate_buzzer(freq=2000, duration=0.5)

def close_barrier(servo):
    """
    Fonction pour fermer la barrière.
    CORRECTION: duty_u16 pour 1ms = 3276 (0°)
    Au lieu de 2048 qui était trop faible !
    """
    duty = 3276  # 1ms → 0° (FERMÉ) - CORRIGÉ !
    print(f"Fermeture de la barrière duty={duty}")
    servo.duty_u16(duty)

# CORRECTION BUZZER : Fonction dédiée avec duty cycle augmenté
def activate_buzzer(freq=1000, duration=1.0):
    """
    Active le buzzer à une fréquence donnée pendant une durée.
    CORRECTION: duty_u16 à 45000 (~70%) au lieu de 32767 (50%)
    """
    adc_value = pot.read_u16()
    adjusted_freq = freq + int((adc_value / 65535) * 1500)  # Variation avec potentiomètre
    
    buzzer.freq(adjusted_freq)
    buzzer.duty_u16(45000)  # 70% duty cycle - PLUS FORT !
    print(f"Buzzer activé: {adjusted_freq} Hz pendant {duration}s")
    
    sleep(duration)
    buzzer.duty_u16(0)
    print("Buzzer désactivé")

# Fonction pour gérer l'activation d'un capteur
def capteur_active(capteur, servo, blue_led=False, use_buzzer=False):
    """
    Fonction pour gérer l'activation d'un capteur.
    Attend 10 secondes et ferme la barrière si le capteur détecte un passage.
    """
    print("Activation du capteur : attente de détection pendant 10 secondes...")
    deadline = time.time() + 10
    triggered = False

    if use_buzzer:
        # Buzzer court au début
        activate_buzzer(freq=1500, duration=0.3)

    while time.time() < deadline:
        if capteur.value() == 0:  # Capteur déclenché
            triggered = True
            print("Capteur déclenché !")
            break

        if blue_led:
            led_blue.value(1)
            sleep(0.1)
            led_blue.value(0)
            sleep(0.1)
        else:
            sleep(0.1)

    led_blue.value(0)

    if triggered:
        print("Détection effectuée : fermeture de la barrière dans 2s")
        sleep(2)  # Laisser passer la voiture
        close_barrier(servo)
        return {"status": "ok", "message": "détection effectuée"}
    else:
        print("Timeout : aucune détection → fermeture immédiate")
        close_barrier(servo)
        # Buzzer d'alerte
        activate_buzzer(freq=500, duration=0.5)
        return {"status": "timeout", "message": "aucune voiture détectée"}

def update_led(places):
    """Mise à jour des LEDs selon le nombre de places libres"""
    if places == 0:
        # Parking plein
        led_green.value(0)
        led_orange.value(0)
        led_red.value(1)
    elif places <= 5:
        # Peu de places restantes
        led_green.value(0)
        led_orange.value(1)
        led_red.value(0)
    else:
        # Places disponibles
        led_green.value(1)
        led_orange.value(0)
        led_red.value(0)



def get_parking_status():
    """Récupère le statut du parking depuis Flask"""
    url = f"http://{FLASK_IP}:5000/parking/status"

    try:
        response = urequests.get(url, timeout=3)
        data = response.json()

        used = data["used"]
        free = data["free"]
        
        response.close()
        return free

    except Exception as e:
        print("Erreur get_parking_status:", e)
        return None

def update_parking_display():
    """
    Mise à jour de l'affichage du parking
    Appelée périodiquement dans la boucle principale
    """
    global current_free_places, last_update_time
    
    current_time = time.time()
    
    # Vérifier si c'est le moment de mettre à jour
    if current_time - last_update_time >= UPDATE_INTERVAL:
        try:
            free = get_parking_status()
            
            if free is not None:
                current_free_places = free
                aff.show(free)
                update_led(free)
                print(f"Places libres mises à jour: {free}")
            else:
                print("Impossible de récupérer le statut")
                
            last_update_time = current_time
            
        except Exception as e:
            print(f"Erreur update_parking_display: {e}")
            last_update_time = current_time

# Initialisation : première mise à jour
print("Initialisation de l'affichage...")
update_parking_display()

# Boucle principale NON-BLOQUANTE
print("Serveur HTTP en écoute (mode non-bloquant)...")

while True:
    try:
        # ÉTAPE 1: Mise à jour périodique de l'affichage (sans bloquer)
        update_parking_display()
        
        # ÉTAPE 2: Vérifier si une connexion HTTP est disponible (sans bloquer)
        try:
            cl, addr = s.accept()
            cl.setblocking(True)  # Passer en mode bloquant pour cette connexion
            cl.settimeout(5.0)
            
            request = cl.recv(1024)
            try:
                request = request.decode("utf-8")
            except Exception:
                request = str(request)

            print("=" * 50)
            print("Requête reçue :", request[:100])
            print("Adresse cliente :", addr)

            result = {"status": "error", "message": "commande HTTP non reconnue"}

            if "GET /open" in request:
                print("→ Commande OPEN reçue")
                open_barrier(servo_enter, use_buzzer=True)
                result = capteur_active(capteur_enter, servo_enter, blue_led=True, use_buzzer=True)
                # Forcer une mise à jour après l'action
                last_update_time = 0
                
            elif "GET /close" in request:
                print("→ Commande CLOSE reçue")
                open_barrier(servo_exit, use_buzzer=False)
                result = capteur_active(capteur_exit, servo_exit, blue_led=False, use_buzzer=False)
                # Forcer une mise à jour après l'action
                last_update_time = 0
                
            elif "GET /status" in request:
                # Route bonus pour vérifier le statut
                result = {
                    "status": "ok",
                    "free_places": current_free_places,
                    "message": "statut OK"
                }
            else:
                print("→ Commande non reconnue")

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
            print("Réponse envoyée et connexion fermée")
            
        except OSError as e:
            # Aucune connexion disponible (normal en mode non-bloquant)
            # On continue la boucle sans bloquer
            pass
            
    except KeyboardInterrupt:
        print("\nArrêt du serveur...")
        break
    except Exception as e:
        print(f"Erreur dans la boucle principale: {e}")
        sleep(0.1)  # Petit délai pour éviter de boucler trop vite en cas d'erreur

print("Serveur arrêté")