"""
====================================================================
SYSTÈME DE PARKING INTELLIGENT - SERVEUR FLASK
====================================================================
Serveur web Flask pour la gestion du parking

Fonctionnalités:
- Interface web pour utilisateurs
- Gestion base de données SQLite
- Communication avec le Pico via HTTP
- Authentification utilisateurs
- Gestion des entrées/sorties

Auteur: Claude (refonte complète)
====================================================================
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import hashlib
import requests
import time

# ====================================================================
# CONFIGURATION
# ====================================================================

# Adresse IP du Pico
PICO_IP = "172.20.136.113"

# Timeout pour les requêtes au Pico
# Doit être > au CAPTEUR_TIMEOUT du Pico (20s) + marge
PICO_TIMEOUT = 30

# Capacité totale du parking
PARKING_CAPACITY = 20

# Base de données
DATABASE = "parking.db"

# ====================================================================
# APPLICATION FLASK
# ====================================================================

app = Flask(__name__)

print("\n" + "=" * 60)
print("SERVEUR PARKING INTELLIGENT")
print("=" * 60)
print(f"Pico IP: {PICO_IP}")
print(f"Timeout: {PICO_TIMEOUT}s")
print(f"Base de données: {DATABASE}")
print("=" * 60 + "\n")

# ====================================================================
# UTILITAIRES
# ====================================================================

def hash_password(password):
    """
    Hash un mot de passe en SHA-256
    
    Args:
        password: Mot de passe en clair
    
    Returns:
        str: Hash SHA-256 du mot de passe
    """
    return hashlib.sha256(password.encode()).hexdigest()

def connect_db():
    """
    Connecte à la base de données SQLite
    
    Returns:
        Connection: Objet de connexion SQLite
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    return conn

def log_action(action, username, success, details=""):
    """
    Log une action dans la console
    
    Args:
        action: Type d'action (openDoor, closeDoor, etc.)
        username: Utilisateur concerné
        success: True si succès, False sinon
        details: Détails supplémentaires
    """
    status = "✅" if success else "❌"
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {status} {action:15} | {username:15} | {details}")

# ====================================================================
# ROUTES - PAGES WEB
# ====================================================================

@app.route("/")
def home():
    """Page d'accueil (interface utilisateur)"""
    return render_template("index.html")

@app.route("/admin")
def admin():
    """Page d'administration"""
    return render_template("admin.html")

@app.route("/test", methods=["GET"])
def test():
    """Route de test pour vérifier que Flask fonctionne"""
    return jsonify({
        "message": "OK depuis Flask",
        "timestamp": time.time()
    })

# ====================================================================
# ROUTES - STATUT PARKING
# ====================================================================

@app.route("/parking/status", methods=["GET"])
def parking_status():
    """
    Retourne le statut actuel du parking
    
    Returns:
        JSON: {
            "used": nombre de places occupées,
            "free": nombre de places libres
        }
    """
    conn = connect_db()
    db = conn.cursor()
    
    # Compter le nombre de voitures dans le parking (etat=1)
    db.execute("SELECT COUNT(*) as count FROM utilisateurs WHERE etat = 1")
    result = db.fetchone()
    
    used = result["count"]
    free = PARKING_CAPACITY - used
    
    conn.close()
    
    return jsonify({
        "used": used,
        "free": free
    })

# ====================================================================
# ROUTES - CONTRÔLE DES BARRIÈRES
# ====================================================================

@app.route("/openDoor", methods=["POST"])
def open_door():
    """
    Ouvre la barrière d'entrée pour un utilisateur
    
    Form data:
        username: Nom d'utilisateur
        password: Mot de passe
    
    Returns:
        JSON: Résultat de l'opération
    """
    # Récupérer les données du formulaire
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    password_hash = hash_password(password)
    
    log_action("openDoor", username, False, "Tentative")
    
    # ================================================================
    # ÉTAPE 1: Vérifier les identifiants
    # ================================================================
    
    conn = connect_db()
    db = conn.cursor()
    
    db.execute("""
        SELECT nom, prenom, username, etat
        FROM utilisateurs
        WHERE username=? AND password=?
    """, (username, password_hash))
    
    user = db.fetchone()
    
    # Identifiants incorrects
    if not user:
        conn.close()
        log_action("openDoor", username, False, "Identifiants incorrects")
        return jsonify({
            "status": "refusé",
            "reason": "identifiants incorrects"
        })
    
    # Vérifier que l'utilisateur n'est pas déjà dans le parking
    if user["etat"] == 1:
        conn.close()
        log_action("openDoor", username, False, "Déjà dans le parking")
        return jsonify({
            "status": "refusé",
            "reason": "déjà dans le parking"
        })
    
    # ================================================================
    # ÉTAPE 2: Mettre à jour la BD (optimiste)
    # ================================================================
    
    # On met l'utilisateur à etat=1 AVANT de commander le Pico
    # Si le Pico timeout, on annulera
    db.execute("""
        UPDATE utilisateurs
        SET etat = 1
        WHERE username=?
    """, (username,))
    
    conn.commit()
    
    # ================================================================
    # ÉTAPE 3: Commander le Pico
    # ================================================================
    
    pico_success = False
    pico_status = None
    pico_error = None
    
    try:
        log_action("openDoor", username, False, f"Envoi /open au Pico...")
        
        url = f"http://{PICO_IP}/open"
        pico_response = requests.get(url, timeout=PICO_TIMEOUT)
        pico_response.raise_for_status()
        
        pico_data = pico_response.json()
        pico_status = pico_data.get("status")
        
        log_action("openDoor", username, False, f"Pico répond: {pico_status}")
        
        # Analyser la réponse du Pico
        if pico_status == "ok":
            # Détection OK → tout est bon
            pico_success = True
            
        elif pico_status == "timeout":
            # Timeout → aucune voiture détectée
            # Annuler l'entrée dans la BD
            db.execute("""
                UPDATE utilisateurs
                SET etat = 0
                WHERE username=?
            """, (username,))
            conn.commit()
            conn.close()
            
            log_action("openDoor", username, False, "Timeout capteur - Entrée annulée")
            
            return jsonify({
                "status": "refusé",
                "reason": "aucune voiture détectée",
                "message": "entrée annulée",
                "pico_status": pico_status
            })
    
    except requests.exceptions.Timeout:
        # Timeout réseau → le Pico ne répond pas
        pico_error = "Timeout réseau - Pico ne répond pas"
        
    except requests.exceptions.ConnectionError:
        # Erreur de connexion → le Pico est injoignable
        pico_error = "Pico injoignable"
        
    except Exception as e:
        # Autre erreur
        pico_error = str(e)
    
    # Si erreur Pico, annuler l'opération
    if pico_error:
        db.execute("""
            UPDATE utilisateurs
            SET etat = 0
            WHERE username=?
        """, (username,))
        conn.commit()
        conn.close()
        
        log_action("openDoor", username, False, f"Erreur Pico: {pico_error}")
        
        return jsonify({
            "status": "refusé",
            "reason": "commande Pico échouée",
            "message": "entrée annulée",
            "pico_error": pico_error
        })
    
    # ================================================================
    # ÉTAPE 4: Succès
    # ================================================================
    
    conn.close()
    log_action("openDoor", username, True, "Entrée autorisée")
    
    return jsonify({
        "status": "autorisé",
        "message": "entrée acceptée",
        "nom": user["nom"],
        "prenom": user["prenom"]
    })

@app.route("/closeDoor", methods=["POST"])
def close_door():
    """
    Ouvre la barrière de sortie pour un utilisateur
    
    Form data:
        username: Nom d'utilisateur
        password: Mot de passe
    
    Returns:
        JSON: Résultat de l'opération
    """
    # Récupérer les données du formulaire
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    password_hash = hash_password(password)
    
    log_action("closeDoor", username, False, "Tentative")
    
    # ================================================================
    # ÉTAPE 1: Vérifier les identifiants
    # ================================================================
    
    conn = connect_db()
    db = conn.cursor()
    
    db.execute("""
        SELECT nom, prenom, username, etat
        FROM utilisateurs
        WHERE username=? AND password=?
    """, (username, password_hash))
    
    user = db.fetchone()
    
    # Identifiants incorrects
    if not user:
        conn.close()
        log_action("closeDoor", username, False, "Identifiants incorrects")
        return jsonify({
            "status": "refusé",
            "reason": "identifiants incorrects"
        })
    
    # Vérifier que l'utilisateur est bien dans le parking
    if user["etat"] == 0:
        conn.close()
        log_action("closeDoor", username, False, "Déjà à l'extérieur")
        return jsonify({
            "status": "refusé",
            "reason": "utilisateur déjà à l'extérieur"
        })
    
    # ================================================================
    # ÉTAPE 2: Mettre à jour la BD (optimiste)
    # ================================================================
    
    # On met l'utilisateur à etat=0 AVANT de commander le Pico
    # Si le Pico timeout, on annulera
    db.execute("""
        UPDATE utilisateurs
        SET etat = 0
        WHERE username=?
    """, (username,))
    
    conn.commit()
    
    # ================================================================
    # ÉTAPE 3: Commander le Pico
    # ================================================================
    
    pico_success = False
    pico_status = None
    pico_error = None
    
    try:
        log_action("closeDoor", username, False, f"Envoi /close au Pico...")
        
        url = f"http://{PICO_IP}/close"
        pico_response = requests.get(url, timeout=PICO_TIMEOUT)
        pico_response.raise_for_status()
        
        pico_data = pico_response.json()
        pico_status = pico_data.get("status")
        
        log_action("closeDoor", username, False, f"Pico répond: {pico_status}")
        
        # Analyser la réponse du Pico
        if pico_status == "ok":
            # Détection OK → tout est bon
            pico_success = True
            
        elif pico_status == "timeout":
            # Timeout → aucune voiture détectée
            # Annuler la sortie dans la BD
            db.execute("""
                UPDATE utilisateurs
                SET etat = 1
                WHERE username=?
            """, (username,))
            conn.commit()
            conn.close()
            
            log_action("closeDoor", username, False, "Timeout capteur - Sortie annulée")
            
            return jsonify({
                "status": "refusé",
                "reason": "aucune détection",
                "message": "sortie annulée",
                "pico_status": pico_status
            })
    
    except requests.exceptions.Timeout:
        # Timeout réseau → le Pico ne répond pas
        pico_error = "Timeout réseau - Pico ne répond pas"
        
    except requests.exceptions.ConnectionError:
        # Erreur de connexion → le Pico est injoignable
        pico_error = "Pico injoignable"
        
    except Exception as e:
        # Autre erreur
        pico_error = str(e)
    
    # Si erreur Pico, annuler l'opération
    if pico_error:
        db.execute("""
            UPDATE utilisateurs
            SET etat = 1
            WHERE username=?
        """, (username,))
        conn.commit()
        conn.close()
        
        log_action("closeDoor", username, False, f"Erreur Pico: {pico_error}")
        
        return jsonify({
            "status": "refusé",
            "reason": "commande Pico échouée",
            "message": "sortie annulée",
            "pico_error": pico_error
        })
    
    # ================================================================
    # ÉTAPE 4: Succès
    # ================================================================
    
    conn.close()
    log_action("closeDoor", username, True, "Sortie autorisée")
    
    return jsonify({
        "status": "autorisé",
        "message": "sortie acceptée",
        "nom": user["nom"],
        "prenom": user["prenom"]
    })

# ====================================================================
# ROUTES - GESTION DES UTILISATEURS
# ====================================================================

@app.route("/users", methods=["GET"])
def load_users():
    """
    Retourne la liste de tous les utilisateurs
    
    Returns:
        JSON: Liste des utilisateurs avec leurs infos
    """
    conn = connect_db()
    db = conn.cursor()
    
    db.execute("SELECT nom, prenom, username, etat FROM utilisateurs")
    users = db.fetchall()
    
    conn.close()
    
    # Convertir en liste de dicts
    users_list = []
    for user in users:
        users_list.append({
            "nom": user["nom"],
            "prenom": user["prenom"],
            "username": user["username"],
            "etat": user["etat"]
        })
    
    return jsonify(users_list)

@app.route("/addUser", methods=["POST"])
def add_user():
    """
    Ajoute un nouvel utilisateur
    
    Form data:
        nom: Nom de famille
        prenom: Prénom
        username: Nom d'utilisateur (unique)
        password: Mot de passe
    
    Returns:
        JSON: Confirmation de l'ajout
    """
    # Récupérer les données
    nom = request.form.get("nom", "")
    prenom = request.form.get("prenom", "")
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    password_hash = hash_password(password)
    
    # Insérer dans la BD
    conn = connect_db()
    db = conn.cursor()
    
    try:
        db.execute("""
            INSERT INTO utilisateurs (nom, prenom, username, password, etat)
            VALUES (?, ?, ?, ?, 0)
        """, (nom, prenom, username, password_hash))
        
        conn.commit()
        conn.close()
        
        log_action("addUser", username, True, f"{prenom} {nom}")
        
        return jsonify({
            "status": "utilisateur ajouté avec succès"
        })
        
    except sqlite3.IntegrityError:
        # Username déjà existant
        conn.close()
        log_action("addUser", username, False, "Username déjà existant")
        
        return jsonify({
            "status": "erreur",
            "reason": "username déjà existant"
        })

@app.route("/removeUser", methods=["POST"])
def remove_user():
    """
    Supprime un utilisateur
    
    Form data:
        username: Nom d'utilisateur
        password: Mot de passe (pour confirmation)
    
    Returns:
        JSON: Confirmation de la suppression
    """
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    password_hash = hash_password(password)
    
    conn = connect_db()
    db = conn.cursor()
    
    # Supprimer seulement si le mot de passe est correct
    db.execute("""
        DELETE FROM utilisateurs
        WHERE username=? AND password=?
    """, (username, password_hash))
    
    affected = db.rowcount
    conn.commit()
    conn.close()
    
    if affected > 0:
        log_action("removeUser", username, True, "Supprimé")
        return jsonify({
            "status": "utilisateur supprimé avec succès"
        })
    else:
        log_action("removeUser", username, False, "Échec")
        return jsonify({
            "status": "utilisateur inexistant ou mot de passe incorrect"
        })

# ====================================================================
# LANCEMENT DU SERVEUR
# ====================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SERVEUR PRÊT")
    print("=" * 60)
    print("Interface web: http://0.0.0.0:5000")
    print("Appuie sur Ctrl+C pour arrêter")
    print("=" * 60 + "\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)
