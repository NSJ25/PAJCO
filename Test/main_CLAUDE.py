"""
====================================================================
SYSTÈME DE PARKING INTELLIGENT - PI PICO
====================================================================
Code principal pour le microcontrôleur Raspberry Pi Pico

Fonctionnalités:
- Contrôle de 2 barrières (entrée/sortie) via servomoteurs
- Détection de passage via capteurs IR
- Affichage du nombre de places sur afficheurs 7-segments
- Communication HTTP avec serveur Flask
- Feedback visuel (LEDs) et sonore (buzzer)

Auteur: Claude (refonte complète)
====================================================================
"""

from machine import Pin, PWM, ADC
from CD4511 import CD4511
import network
import urequests
import ujson
import time
import socket

# ====================================================================
# CONFIGURATION - Modifie ces valeurs selon ton setup
# ====================================================================

# WiFi
WIFI_SSID = "Galaxy A25 5G F91E"
WIFI_PASSWORD = "ehef36fi6auwwq6"
WIFI_TIMEOUT = 15  # secondes

# Serveur Flask
FLASK_IP = "172.20.136.201"
FLASK_PORT = 5000

# Configuration des capteurs
CAPTEUR_TIMEOUT = 20  # Temps d'attente max pour détection (secondes)
PASSAGE_DELAY = 3     # Temps d'attente après détection avant fermeture (secondes)

# Configuration des servos (ajuste ces valeurs si nécessaire)
SERVO_FREQ = 50       # Fréquence PWM des servos (Hz)
SERVO_OPEN_DUTY = 6553   # Position ouverte (duty_u16 pour ~2ms)
SERVO_CLOSE_DUTY = 6553  # Position fermée (duty_u16 pour ~1ms)

# Configuration du buzzer
BUZZER_FREQ_DEFAULT = 1000  # Fréquence par défaut (Hz)
BUZZER_DUTY = 50000         # Duty cycle (0-65535, ~76%)
BUZZER_DURATION = 1.5       # Durée par défaut (secondes)

# Mise à jour de l'affichage
UPDATE_INTERVAL = 5  # Intervalle de rafraîchissement (secondes)

# ====================================================================
# INITIALISATION DU MATÉRIEL
# ====================================================================

print("\n" + "=" * 60)
print("SYSTÈME DE PARKING INTELLIGENT")
print("Initialisation du matériel...")
print("=" * 60)

# LEDs de statut (GPIO 0-3)
led_red = Pin(0, Pin.OUT)      # Rouge: parking plein
led_orange = Pin(1, Pin.OUT)   # Orange: peu de places
led_blue = Pin(2, Pin.OUT)     # Bleue: détection en cours
led_green = Pin(3, Pin.OUT)    # Verte: places disponibles

# Afficheur 7-segments (CD4511 + transistors)
bcd_pins = [6, 7, 8, 9]        # Pins BCD (A, B, C, D)
transistor_pins = [4, 5]       # Pins transistors (dizaines, unités)
aff = CD4511(bcd_pins, transistor_pins)

# Capteurs IR de détection
capteur_enter = Pin(21, Pin.IN, Pin.PULL_UP)  # Capteur entrée
capteur_exit = Pin(20, Pin.IN, Pin.PULL_UP)   # Capteur sortie

# Servomoteurs (barrières)
servo_enter = PWM(Pin(26))     # Servo barrière entrée
servo_exit = PWM(Pin(22))      # Servo barrière sortie
servo_enter.freq(SERVO_FREQ)
servo_exit.freq(SERVO_FREQ)

# Buzzer (feedback sonore)
buzzer = PWM(Pin(27))
buzzer.freq(BUZZER_FREQ_DEFAULT)
buzzer.duty_u16(0)  # Éteint au démarrage

# Potentiomètre (variation fréquence buzzer)
pot = ADC(Pin(28))

print("✅ Matériel initialisé")

# ====================================================================
# VARIABLES GLOBALES
# ====================================================================

current_free_places = 20  # Nombre de places libres (valeur par défaut)
last_update_time = 0      # Timestamp dernière mise à jour
flask_errors = 0          # Compteur d'erreurs Flask consécutives

# ====================================================================
# CONNEXION WIFI
# ====================================================================

def connect_wifi():
    """
    Connecte le Pico au réseau WiFi
    Retourne True si succès, False sinon
    """
    print("\nConnexion au WiFi...")
    print(f"  SSID: {WIFI_SSID}")
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # Attente de la connexion
    elapsed = 0
    while not wlan.isconnected() and elapsed < WIFI_TIMEOUT:
        time.sleep(1)
        elapsed += 1
        print(f"  {elapsed}/{WIFI_TIMEOUT}s...")
    
    if wlan.isconnected():
        ip, netmask, gateway, dns = wlan.ifconfig()
        print(f"\n✅ WiFi connecté !")
        print(f"  IP Pico    : {ip}")
        print(f"  Passerelle : {gateway}")
        return True
    else:
        print("\n❌ Échec connexion WiFi")
        return False

# Connexion WiFi
if not connect_wifi():
    raise SystemExit("Impossible de continuer sans WiFi")

# ====================================================================
# SERVEUR HTTP
# ====================================================================

print("\nDémarrage du serveur HTTP...")

# Configuration socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
server_socket = socket.socket()
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(addr)
server_socket.listen(1)
server_socket.setblocking(False)  # Mode non-bloquant (important!)

print(f"✅ Serveur HTTP prêt sur port 80")

# ====================================================================
# FONCTIONS UTILITAIRES
# ====================================================================

def play_buzzer(freq=None, duration=BUZZER_DURATION):
    """
    Active le buzzer avec une fréquence donnée
    
    Args:
        freq: Fréquence en Hz (si None, utilise le potentiomètre)
        duration: Durée en secondes
    """
    # Si pas de fréquence, utiliser le potentiomètre
    if freq is None:
        pot_value = pot.read_u16()
        freq = BUZZER_FREQ_DEFAULT + int((pot_value / 65535) * 1500)
    
    # Jouer le son
    buzzer.freq(freq)
    buzzer.duty_u16(BUZZER_DUTY)
    time.sleep(duration)
    buzzer.duty_u16(0)

def update_leds(places):
    """
    Met à jour les LEDs selon le nombre de places disponibles
    
    Args:
        places: Nombre de places libres
    """
    if places == 0:
        # Parking plein → LED rouge
        led_red.value(1)
        led_orange.value(0)
        led_green.value(0)
    elif places <= 5:
        # Peu de places → LED orange
        led_red.value(0)
        led_orange.value(1)
        led_green.value(0)
    else:
        # Places disponibles → LED verte
        led_red.value(0)
        led_orange.value(0)
        led_green.value(1)

# ====================================================================
# CONTRÔLE DES SERVOMOTEURS
# ====================================================================

def open_barrier(servo, with_sound=False):
    """
    Ouvre une barrière
    
    Args:
        servo: Objet PWM du servo à contrôler
        with_sound: Si True, active le buzzer
    """
    print("  🔓 Ouverture barrière...")
    servo.duty_u16(SERVO_OPEN_DUTY)
    
    if with_sound:
        play_buzzer(freq=2000, duration=1.0)

def close_barrier(servo):
    """
    Ferme une barrière
    
    Args:
        servo: Objet PWM du servo à contrôler
    """
    print("  🔒 Fermeture barrière...")
    servo.duty_u16(SERVO_CLOSE_DUTY)

# ====================================================================
# DÉTECTION DE PASSAGE
# ====================================================================

def wait_for_detection(capteur, servo, show_blue_led=False):
    """
    Attend la détection d'un passage par le capteur
    Retourne un dict avec le status de la détection
    
    Args:
        capteur: Pin du capteur IR
        servo: Servo à fermer après détection
        show_blue_led: Si True, clignote la LED bleue pendant l'attente
    
    Returns:
        dict: {"status": "ok"|"timeout", "message": "..."}
    """
    print(f"\n  ⏳ Attente détection (max {CAPTEUR_TIMEOUT}s)...")
    
    # État initial du capteur
    initial_state = capteur.value()
    print(f"     État initial: {initial_state} (0=objet, 1=libre)")
    
    deadline = time.time() + CAPTEUR_TIMEOUT
    detected = False
    
    # Boucle d'attente
    while time.time() < deadline:
        # Vérifier le capteur (0 = détection)
        if capteur.value() == 0:
            detected = True
            print("  ✅ Passage détecté !")
            break
        
        # LED bleue clignotante (feedback visuel)
        if show_blue_led:
            led_blue.value(1)
            time.sleep(0.05)
            led_blue.value(0)
            time.sleep(0.05)
        else:
            time.sleep(0.1)
    
    # Éteindre la LED bleue
    led_blue.value(0)
    
    if detected:
        # Passage détecté → attendre que le véhicule passe complètement
        print(f"  ⏳ Attente passage complet ({PASSAGE_DELAY}s)...")
        time.sleep(PASSAGE_DELAY)
        
        # Fermer la barrière
        close_barrier(servo)
        
        return {
            "status": "ok",
            "message": "détection effectuée"
        }
    else:
        # Timeout → aucune détection
        print("  ⏱️  Timeout - Aucun passage détecté")
        
        # Fermer quand même la barrière
        close_barrier(servo)
        
        # Bip d'alerte
        play_buzzer(freq=500, duration=1.0)
        
        return {
            "status": "timeout",
            "message": "aucune voiture détectée"
        }

# ====================================================================
# COMMUNICATION AVEC FLASK
# ====================================================================

def get_parking_status():
    """
    Récupère le statut du parking depuis Flask
    Retourne le nombre de places libres ou None si erreur
    """
    global flask_errors
    
    url = f"http://{FLASK_IP}:{FLASK_PORT}/parking/status"
    
    try:
        response = urequests.get(url, timeout=3)
        data = response.json()
        response.close()
        
        # Reset compteur d'erreurs
        flask_errors = 0
        
        return data.get("free", None)
        
    except Exception as e:
        flask_errors += 1
        
        # N'afficher l'erreur que les 3 premières fois
        if flask_errors <= 3:
            print(f"⚠️  Erreur Flask ({flask_errors}/3): {e}")
        elif flask_errors == 4:
            print("⚠️  Mode dégradé: Flask injoignable")
        
        return None

def update_display():
    """
    Met à jour l'affichage et les LEDs avec le statut du parking
    Appelé périodiquement (toutes les UPDATE_INTERVAL secondes)
    """
    global current_free_places, last_update_time
    
    current_time = time.time()
    
    # Vérifier si c'est le moment de mettre à jour
    if current_time - last_update_time < UPDATE_INTERVAL:
        return
    
    # Récupérer le statut depuis Flask
    free_places = get_parking_status()
    
    if free_places is not None:
        # Mise à jour réussie
        if current_free_places != free_places:
            print(f"📊 Places: {current_free_places} → {free_places}")
        
        current_free_places = free_places
    
    # Mettre à jour l'affichage (même si Flask a échoué)
    aff.show(current_free_places)
    update_leds(current_free_places)
    
    last_update_time = current_time

# ====================================================================
# GESTION DES REQUÊTES HTTP
# ====================================================================

def handle_http_request(request_text):
    """
    Traite une requête HTTP et retourne la réponse
    
    Args:
        request_text: Texte brut de la requête HTTP
    
    Returns:
        dict: Résultat de l'opération
    """
    # Route: /open (entrée véhicule)
    if "GET /open" in request_text:
        print("\n" + "🚗" * 30)
        print("ENTRÉE VÉHICULE")
        print("-" * 60)
        
        # Ouvrir la barrière d'entrée
        open_barrier(servo_enter, with_sound=True)
        
        # Attendre la détection
        result = wait_for_detection(capteur_enter, servo_enter, show_blue_led=True)
        
        print("-" * 60)
        print("🚗" * 30 + "\n")
        
        return result
    
    # Route: /close (sortie véhicule)
    elif "GET /close" in request_text:
        print("\n" + "🚗" * 30)
        print("SORTIE VÉHICULE")
        print("-" * 60)
        
        # Ouvrir la barrière de sortie
        open_barrier(servo_exit, with_sound=False)
        
        # Attendre la détection
        result = wait_for_detection(capteur_exit, servo_exit, show_blue_led=False)
        
        print("-" * 60)
        print("🚗" * 30 + "\n")
        
        return result
    
    # Route: /status (info système)
    elif "GET /status" in request_text:
        return {
            "status": "ok",
            "free_places": current_free_places,
            "flask_reachable": flask_errors == 0
        }
    
    # Route inconnue
    else:
        return {
            "status": "error",
            "message": "Route non reconnue"
        }

def send_http_response(client, result):
    """
    Envoie une réponse HTTP au client
    
    Args:
        client: Socket client
        result: Dict à retourner en JSON
    """
    body = ujson.dumps(result)
    
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
        f"{body}"
    )
    
    client.send(response)
    client.close()

# ====================================================================
# INITIALISATION FINALE
# ====================================================================

print("\n" + "=" * 60)
print("INITIALISATION TERMINÉE")
print("=" * 60)

# Affichage initial
aff.show(current_free_places)
update_leds(current_free_places)

print(f"\n📊 Affichage initial: {current_free_places} places libres")
print(f"🔄 Mise à jour automatique: toutes les {UPDATE_INTERVAL}s")
print(f"⏱️  Timeout détection: {CAPTEUR_TIMEOUT}s")

# Test rapide des capteurs
print("\n🔍 État des capteurs:")
print(f"  Entrée (GPIO 21): {capteur_enter.value()}")
print(f"  Sortie (GPIO 20): {capteur_exit.value()}")
print("  (0=objet détecté, 1=libre)")

print("\n" + "=" * 60)
print("🚀 SERVEUR PRÊT - En attente de requêtes...")
print("=" * 60 + "\n")

# ====================================================================
# BOUCLE PRINCIPALE
# ====================================================================

while True:
    try:
        # Mise à jour périodique de l'affichage
        update_display()
        
        # Vérifier s'il y a une requête HTTP (mode non-bloquant)
        try:
            client, addr = server_socket.accept()
            
            # Passer en mode bloquant pour cette connexion
            client.setblocking(True)
            client.settimeout(5.0)
            
            # Lire la requête
            request = client.recv(1024)
            try:
                request_text = request.decode("utf-8")
            except:
                request_text = str(request)
            
            # Afficher l'info de connexion
            print(f"📥 Requête de {addr[0]}")
            
            # Traiter la requête
            result = handle_http_request(request_text)
            
            # Envoyer la réponse
            send_http_response(client, result)
            
            # Forcer une mise à jour de l'affichage après une action
            last_update_time = 0
            
        except OSError:
            # Aucune connexion disponible (normal en non-bloquant)
            pass
        
        # Petit délai pour éviter de saturer le CPU
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        # Arrêt propre
        print("\n\n🛑 Arrêt du serveur...")
        break
        
    except Exception as e:
        # Erreur inattendue
        print(f"❌ Erreur: {e}")
        time.sleep(0.5)

# Nettoyage
server_socket.close()
print("✅ Serveur arrêté proprement\n")
