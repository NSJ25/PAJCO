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
    body = json.dumps(result)  # Utilise json (qui est ujson)
    
    # Construire la réponse HTTP (encoder en bytes)
    response_str = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body.encode('utf-8'))}\r\n"  # Longueur en bytes
        "Connection: close\r\n\r\n"
        f"{body}"
    )
    
    # Envoyer en bytes
    client.send(response_str.encode('utf-8'))
    client.close()

# Fonction pour se connecter/reconnecter au WiFi
def wifi_connect(timeout=15):
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True  # Déjà connecté
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
# CONFIGURATION SERVOS CORRIGÉE
# ====================================================================

# Valeurs duty pour les servos (50 Hz)
SERVO_CLOSED = 2458
#0120 1ms → 0° (barrière FERMÉE, baissée)
SERVO_OPEN = 6553   # 1.5ms → 90° (barrière OUVERTE, levée)

# Plus besoin de SERVO_NEUTRAL !

# Configuration des timeouts
CAPTEUR_TIMEOUT = 15  # Temps d'attente max pour détection (secondes)
PASSAGE_DELAY = 3     # Temps d'attente après détection (secondes)

# ====================================================================
# FONCTIONS SERVOS CORRIGÉES
# ====================================================================

def open_barrier(servo, use_buzzer=False):
    """
    Ouvre la barrière (servo à 90°)
    
    Args:
        servo: Objet PWM du servo
        use_buzzer: Si True, active le buzzer
    """
    print(f">>> OUVERTURE barrière (duty={SERVO_OPEN} = 90°)")
    servo.duty_u16(SERVO_OPEN)
    
    # Laisser le temps au servo de bouger
    sleep(1.0)
    print("    ✓ Barrière ouverte à 90°")
    
    # Buzzer si demandé
    if use_buzzer:
        activate_buzzer(freq=2000, duration=1.5)

def close_barrier(servo):
    """
    Ferme la barrière (servo à 0°)
    ET LA LAISSE FERMÉE !
    
    Args:
        servo: Objet PWM du servo
    """
    print(f">>> FERMETURE barrière (duty={SERVO_CLOSED} = 0°)")
    servo.duty_u16(SERVO_CLOSED)
    
    # Laisser le temps au servo de bouger
    sleep(1.0)
    print("    ✓ Barrière fermée à 0°")
    
    # ✅ ON NE REVIENT PAS EN POSITION NEUTRE !
    # La barrière RESTE fermée

# CORRECTION BUZZER : Durées augmentées
def activate_buzzer(freq=1000, duration=1.5):  # AUGMENTÉ : 1.5s par défaut
    """
    CORRECTION: Buzzer plus long et plus fort
    """
    adc_value = pot.read_u16()
    adjusted_freq = freq + int((adc_value / 65535) * 1500)
    buzzer.freq(adjusted_freq)
    buzzer.duty_u16(50000)  # AUGMENTÉ : 76% au lieu de 70%
    print(f"🔊 Buzzer: {adjusted_freq} Hz pendant {duration}s")
    sleep(duration)
    buzzer.duty_u16(0)

def capteur_active(capteur, servo, blue_led=False, use_buzzer=False):
    """
    AMÉLIORÉ: Plus de debug + augmentation du délai de passage
    """
    TIMEOUT = 12  # Timeout pour attendre la détection
    PASSAGE_DELAY = 5  # Délai pour laisser passer complètement la voiture
    
    print(f"\n{'='*50}")
    print(f"ATTENTE DÉTECTION CAPTEUR ({TIMEOUT}s)")
    print(f"{'='*50}")
    
    # État initial du capteur
    initial_state = capteur.value()
    print(f"État initial capteur: {initial_state} (0=objet près, 1=libre)")
    print(f"DEBUG: Vérifiez que le capteur change d'état quand une voiture passe")
    
    deadline = time.time() + TIMEOUT
    triggered = False
    check_count = 0
    
    if use_buzzer:
        activate_buzzer(freq=1500, duration=1.0)  # AUGMENTÉ : 1s au lieu de 0.3s
    
    while time.time() < deadline:
        check_count += 1
        current_value = capteur.value()
        
        # DEBUG: Afficher toutes les 2 secondes
        if check_count % 20 == 0:
            remaining = int(deadline - time.time())
            print(f"  [{remaining}s restantes] Capteur={current_value}")
        
        if current_value == 0:  # Capteur déclenché (0 = détection)
            triggered = True
            print(f"✅ CAPTEUR DÉCLENCHÉ ! (après {check_count * 0.1:.1f}s)")
            print(f"   Changement d'état détecté: {initial_state} → {current_value}")
            break
        
        if blue_led:
            led_blue.value(1)
            sleep(0.05)
            led_blue.value(0)
            sleep(0.05)
        else:
            sleep(0.1)
    
    led_blue.value(0)
    
    if triggered:
        print("✅ Détection réussie")
        PASSAGE_DELAY = 5
        print(f"Attente passage complet ({PASSAGE_DELAY}s)...")
        # Garder le servo ouvert pendant le passage
        for i in range(PASSAGE_DELAY * 10):
            if i % 10 == 0:
                print(f"  [{PASSAGE_DELAY - i//10}s] Barrière ouverte...")
            sleep(0.1)
        close_barrier(servo)
        print("Barrière fermée")
        return {"status": "ok", "message": "détection effectuée"}
    else:
        print(f"❌ TIMEOUT après {TIMEOUT}s - Aucune détection !")
        print(f"   🔍 DIAGNOSTIC:")
        print(f"   - Capteur alimenté ? (état initial = {initial_state})")
        print(f"   - Portée de détection OK ? (essayez de rapprocher la main)")
        print(f"   - Voiture assez proche ? (au moins 10-20cm du capteur)")
        print(f"   - État du capteur ACTUEL: {capteur.value()}")
        print(f"   💡 CONSEIL: Testez le capteur isolément avec capteur_test.py")
        close_barrier(servo)
        activate_buzzer(freq=500, duration=2.0)  # Alerte plus longue
        return {"status": "timeout", "message": "aucune voiture détectée - vérifiez le capteur"}

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
            print(f"⚠️ Erreur Flask (tentative {consecutive_errors}): {e}")
        elif consecutive_errors == MAX_ERRORS_BEFORE_PAUSE + 1:
            print(f"❌ Flask injoignable après {MAX_ERRORS_BEFORE_PAUSE} tentatives")
            print("→ Mode dégradé activé")
        
        return None

def update_parking_display():
    global current_free_places, last_update_time, consecutive_errors
    
    current_time = time.time()
    
    # Vérifier WiFi avant mise à jour
    if not check_wifi_reconnect():
        print("❌ WiFi indisponible - Mise à jour annulée")
        return
    
    if current_time - last_update_time >= UPDATE_INTERVAL:
        
        if consecutive_errors > MAX_ERRORS_BEFORE_PAUSE:
            if current_time - last_update_time < 30:
                return
        
        try:
            free = get_parking_status()
            
            if free is not None:
                # Détecter les changements
                if current_free_places != free:
                    print(f"📊 Places libres: {current_free_places} → {free}")
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
print("INITIALISATION DU SYSTÈME PARKING")
print("=" * 50)
aff.show(current_free_places)
update_led(current_free_places)
print(f"Affichage initial: {current_free_places} places")
print("=" * 50 + "\n")

# Test initial des capteurs
print("\n" + "="*50)
print("TEST INITIAL DES CAPTEURS")
print("="*50)
print(f"  Capteur ENTRÉE (GPIO 21): {capteur_enter.value()}")
print(f"  Capteur SORTIE (GPIO 20): {capteur_exit.value()}")
print("  (0=objet détecté/proche, 1=libre/loin)")
print("💡 ASTUCE: Passez votre main à 5-10cm du capteur pour tester")
print("="*50)
print()

# Boucle principale
print("🚀 Serveur HTTP actif")
print("En attente de requêtes /open ou /close...\n")

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
            
            print("\n" + "🔔" * 25)
            print(f"📥 Requête HTTP de {addr}")
            
            result = {"status": "error", "message": "commande non reconnue"}
            
            if "GET /open" in request:
                print("🚗 COMMANDE: ENTRÉE VÉHICULE")
                print("-" * 50)
                print(f"État capteur AVANT ouverture: {capteur_enter.value()}")
                open_barrier(servo_enter, use_buzzer=True)
                sleep(0.5)  # Laisser temps au servo de s'ouvrir
                result = capteur_active(capteur_enter, servo_enter, blue_led=True, use_buzzer=True)
                update_parking_display()  # Forcer mise à jour immédiate
                print(f"Résultat: {result['status']} - Message: {result['message']}")
                
            elif "GET /close" in request:
                print("🚗 COMMANDE: SORTIE VÉHICULE")
                print("-" * 50)
                print(f"État capteur AVANT ouverture: {capteur_exit.value()}")
                open_barrier(servo_exit, use_buzzer=False)
                sleep(0.5)  # Laisser temps au servo de s'ouvrir
                result = capteur_active(capteur_exit, servo_exit, blue_led=False, use_buzzer=False)
                update_parking_display()  # Forcer mise à jour immédiate
                print(f"Résultat: {result['status']} - Message: {result['message']}")
                
            elif "GET /status" in request:
                print("📊 COMMANDE: DEMANDE STATUT")
                result = {
                    "status": "ok",
                    "free_places": current_free_places,
                    "flask_reachable": consecutive_errors == 0
                }
            else:
                print("❌ Commande inconnue")
            
            # Envoyer la réponse JSON
            send_json_response(cl, result)
            print("🔔" * 25 + "\n")
            
        except OSError:
            pass
        
        sleep(0.1)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du serveur...")
        break
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sleep(0.5)

print("Serveur arrêté")