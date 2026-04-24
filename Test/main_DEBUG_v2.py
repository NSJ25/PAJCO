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

FLASK_IP = "172.20.136.201"

# Pins pour les leds
led_red = Pin(0, Pin.OUT)
led_orange = Pin(1, Pin.OUT)
led_blue = Pin(2, Pin.OUT)
led_green = Pin(3, Pin.OUT)

# Pin pour le buzzer
buzzer = PWM(Pin(27))
buzzer.freq(1000)
buzzer.duty_u16(0)

# Pin pour le potentiomètre
pot = ADC(Pin(28))

# Pins pour les servos (enter et exit)
servo_enter = PWM(Pin(26))
servo_exit = PWM(Pin(22))
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

# Variables globales
current_free_places = 20
last_update_time = 0
UPDATE_INTERVAL = 5
consecutive_errors = 0
MAX_ERRORS_BEFORE_PAUSE = 3

# Fonction pour initialiser le serveur HTTP
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
s.setblocking(False)

# Fonction helper pour envoyer des réponses JSON

def send_json_response(client, result):
    """Envoie une réponse JSON HTTP au client"""
    body = json.dumps(result)
    
    response_str = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body.encode('utf-8'))}\r\n"
        "Connection: close\r\n\r\n"
        f"{body}"
    )
    
    client.send(response_str.encode('utf-8'))
    client.close()

# Fonction pour se connecter/reconnecter au WiFi
def wifi_connect(timeout=15):
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True
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
        print(f"Adresse IP : {ip}")
        return True
    else:
        print("Impossible de se connecter au WiFi.")
        return False

# Vérification périodique de la connexion WiFi
def check_wifi_reconnect():
    if not wifi_connect(timeout=10):
        print("⚠️ WiFi perdu - Tentative de reconnexion dans 5s...")
        sleep(5)
        return wifi_connect(timeout=15)
    return True

if not wifi_connect():
    raise SystemExit("Impossible de connecter le WiFi")

print("Serveur HTTP prêt sur 0.0.0.0:80")

# ====================================================================
# CONFIGURATION SERVOS
# ====================================================================

SERVO_CLOSED = 2458
SERVO_OPEN = 6553

CAPTEUR_TIMEOUT = 15
PASSAGE_TIMEOUT = 8

# ====================================================================
# FONCTIONS SERVOS
# ====================================================================

def open_barrier(servo, use_buzzer=False):
    print(f">>> OUVERTURE barrière (duty={SERVO_OPEN} = 90°)")
    servo.duty_u16(SERVO_OPEN)
    sleep(1.0)
    print("    ✓ Barrière ouverte à 90°")
    
    if use_buzzer:
        activate_buzzer(freq=2000, duration=1.5)

def close_barrier(servo):
    print(f">>> FERMETURE barrière (duty={SERVO_CLOSED} = 0°)")
    servo.duty_u16(SERVO_CLOSED)
    sleep(1.0)
    print("    ✓ Barrière fermée à 0°")

def activate_buzzer(freq=1000, duration=1.5):
    adc_value = pot.read_u16()
    adjusted_freq = freq + int((adc_value / 65535) * 1500)
    buzzer.freq(adjusted_freq)
    buzzer.duty_u16(50000)
    print(f"🔊 Buzzer: {adjusted_freq} Hz pendant {duration}s")
    sleep(duration)
    buzzer.duty_u16(0)

def detect_vehicle_and_wait_passage(capteur, servo, blue_led=False, use_buzzer=False):
    """
    CORRIGÉ: Attend que la voiture soit PASSÉE (retour à l'état initial)
    """
    DETECTION_TIMEOUT = 12
    PASSAGE_TIMEOUT = 8
    
    print(f"\n{'='*50}")
    print(f"ATTENTE DÉTECTION CAPTEUR ({DETECTION_TIMEOUT}s)")
    print(f"{'='*50}")
    
    # État initial du capteur (devrait être 1 = libre)
    initial_state =capteur.value()
    print(f"État initial: {initial_state} (0=objet près, 1=libre)")
    print(f"→ Attend que le capteurs revienne a {initial_state}")
    
    detection_deadline = time.time() + DETECTION_TIMEOUT
    detected = False
    passed = False
    check_count = 0
    
    if use_buzzer:
        activate_buzzer(freq=1500, duration=1.0)
    
    # Phase 1: Attendre que le capteurs detecte quelque chose (passage a 0)
    print("Phase 1: En attente d'une voiture...")
    while time.time() < detection_deadline and not detected:
        check_count += 1
        current_value =capteur.value()
        
        if check_count % 20 == 0:
            remaining = int(detection_deadline - time.time())
            print(f"  [{remaining}s] Capteur={current_value}")
        
        if current_value == 0:
            detected = True
            print(f"VOITURE DETECTEE ! (apres {check_count * 0.1:.1f}s)")
            break
        
        if blue_led:
            led_blue.value(1)
            sleep(0.05)
            led_blue.value(0)
            sleep(0.05)
        else:
            sleep(0.1)
    
    led_blue.value(0)
    
    if not detected:
        print(f"TIMEOUT apres {DETECTION_TIMEOUT}s - Aucune detection !")
        print(f"   DIAGNOSTIC:")
        print(f"   - Capteur alimente ? (etat initial = {initial_state})")
        print(f"   - Portee de detection OK ? (essayez de rapprocher la main)")
        print(f"   - Voiture assez proche ? (au moins 10-20cm)")
        print(f"   -Etat du capteurs ACTUEL: {capteur.value()}")
        close_barrier(servo)
        activate_buzzer(freq=500, duration=2.0)
        return {"status": "timeout", "message": "aucune voiture detectee - verifiez le capteurs"}
    
    # Phase 2: Attendre que la voiture soit PASSEE (retour a l'etat initial)
    print(f"Phase 2: Attente passage complet (timeout={PASSAGE_TIMEOUT}s)...")
    passage_deadline = time.time() + PASSAGE_TIMEOUT
    
    while time.time() < passage_deadline and not passed:
        current_value =capteur.value()
        
        if current_value == initial_state:
            passed = True
            print(f"VOITURE PASSEE ! (capteur revenu a {current_value})")
            break
        
        remaining = int(passage_deadline - time.time())
        if int(time.time()) % 2 == 0:
            print(f"  [Attente passage] Capteur={current_value}, {remaining}s restantes")
        
        sleep(0.2)
    
    if not passed:
        print(f"Voiture detectee mais pas completement passee apres {PASSAGE_TIMEOUT}s")
        print("   Fermeture de la barreire avec delai supplementaire...")
        sleep(2.0)
    else:
        sleep(0.5)
    
    close_barrier(servo)
    print("Barriere fermee")
    return {"status": "ok", "message": "detection effectuee"}

def update_led(places):
    if places == 0:
        led_green.value(0)
        led_orange.value(0)
        led_red.value(1)
    elif places <= 5:
        led_green.value(0)
        led_orange.value(1)
        led_red.value(0)
    else:
        led_green.value(1)
        led_orange.value(0)
        led_red.value(0)

def get_parking_status():
    global consecutive_errors
    
    url = f"http://{FLASK_IP}:5000/parking/status"
    
    try:
        response = urequests.get(url, timeout=2)
        data = response.json()
        
        used = data["used"]
        free = data["free"]
        
        response.close()
        consecutive_errors = 0
        
        return free
        
    except Exception as e:
        consecutive_errors += 1
        
        if consecutive_errors <= MAX_ERRORS_BEFORE_PAUSE:
            print(f"Erreur Flask (tentative {consecutive_errors}): {e}")
        elif consecutive_errors == MAX_ERRORS_BEFORE_PAUSE + 1:
            print(f"Flask injoignable apres {MAX_ERRORS_BEFORE_PAUSE} tentatives")
            print("Mode degrade active")
        
        return None

def update_parking_display():
    global current_free_places, last_update_time, consecutive_errors
    
    current_time = time.time()
    
    if not check_wifi_reconnect():
        print("WiFi indisponible - Mise a jour annulee")
        return
    
    if current_time - last_update_time >= UPDATE_INTERVAL:
        
        if consecutive_errors > MAX_ERRORS_BEFORE_PAUSE:
            if current_time - last_update_time < 30:
                return
        
        try:
            free = get_parking_status()
            
            if free is not None:
                if current_free_places != free:
                    print(f"Places libres: {current_free_places} -> {free}")
                current_free_places = free
                aff.show(free)
                update_led(free)
            else:
                aff.show(current_free_places)
                update_led(current_free_places)
            
            last_update_time = current_time
            
        except Exception as e:
            print(f"Erreur update: {e}")
            last_update_time = current_time

# Initialisation
print("\n" + "=" * 50)
print("INITIALISATION DU SYSTEME PARKING")
print("=" * 50)
aff.show(current_free_places)
update_led(current_free_places)
print(f"Affichage initial: {current_free_places} places")
print("=" * 50 + "\n")

# Test initial des capteurs
print("\n" + "="*50)
print("TEST INITIAL DES CAPTEURS")
print("="*50)
print(f"  Capteur ENTREE (GPIO 21): {capteur_enter.value()}")
print(f"  Capteur SORTIE (GPIO 20): {capteur_exit.value()}")
print("  (0=objet detecte/proche, 1=libre/loin)")
print("ASTUCE: Passez votre main a 5-10cm du capteurs pour tester")
print("="*50)
print()

# Boucle principale
print("Serveur HTTP actif")
print("En attente de requetes /open ou /close...\n")

while True:
    try:
        update_parking_display()
        
        try:
            cl, addr = s.accept()
            cl.setblocking(True)
            cl.settimeout(5.0)
            
            request = cl.recv(1024)
            try:
                request = request.decode("utf-8")
            except:
                request = str(request)
            
            print("\n" + "REQUETE HTTP de " + str(addr))
            
            result = {"status": "error", "message": "commande non reconnue"}
            
            if "GET /open" in request:
                print("COMMANDE: ENTREE VEHICULE")
                print("-" * 50)
                print(f"Etat capteurs AVANT ouverture: {capteur_enter.value()}")
                open_barrier(servo_enter, use_buzzer=True)
                sleep(0.5)
                result = detect_vehicle_and_wait_passage(capteur_enter, servo_enter, blue_led=True, use_buzzer=True)
                update_parking_display()
                print(f"Resultat: {result['status']} - Message: {result['message']}")
                
            elif "GET /close" in request:
                print("COMMANDE: SORTIE VEHICULE")
                print("-" * 50)
                print(f"Etat capteurs AVANT ouverture: {capteur_exit.value()}")
                open_barrier(servo_exit, use_buzzer=False)
                sleep(0.5)
                result = detect_vehicle_and_wait_passage(capteur_exit, servo_exit, blue_led=False, use_buzzer=False)
                update_parking_display()
                print(f"Resultat: {result['status']} - Message: {result['message']}")
                
            elif "GET /status" in request:
                print("COMMANDE: DEMANDE STATUT")
                result = {
                    "status": "ok",
                    "free_places": current_free_places,
                    "flask_reachable": consecutive_errors == 0
                }
            else:
                print("Commande inconnue")
            
            send_json_response(cl, result)
            print("\n")
            
        except OSError:
            pass
        
        sleep(0.1)
        
    except KeyboardInterrupt:
        print("\n\nArret du serveur...")
        break
    except Exception as e:
        print(f"Erreur: {e}")
        sleep(0.5)

print("Serveur arrete")
