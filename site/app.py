"""
====================================================================
SYSTÈME DE PARKING INTELLIGENT - SERVEUR FLASK (VERSION CORRIGÉE)
====================================================================
Serveur web Flask pour la gestion du parking

Corrections appliquées:
- ✅ Vérification code HTTP avec raise_for_status()
- ✅ Gestion robuste des erreurs JSON
- ✅ Validation stricte du statut Pico (ok/timeout/autre)
- ✅ Logs détaillés pour debugging
- ✅ Timeout adapté (30s)
====================================================================
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import hashlib
import requests

# ====================================================================
# CONFIGURATION
# ====================================================================

PICO_IP = "172.20.136.113"  # ← Vérifier que c'est bien l'IP du Pico
PICO_TIMEOUT = 30  # Timeout pour les requêtes au Pico (secondes)

app = Flask(__name__)

# ====================================================================
# UTILITAIRES
# ====================================================================

def hash_password(password):
    """Hash un mot de passe en SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def connect_db():
    """Connecte à la base de données SQLite"""
    connect = sqlite3.connect("parking.db")
    connect.row_factory = sqlite3.Row
    return connect

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
    return jsonify({"message": "OK depuis Flask"})

# ====================================================================
# ROUTES - STATUT PARKING
# ====================================================================

@app.route("/parking/status", methods=["GET"])
def parking_status():
    """Retourne le statut actuel du parking"""
    connect = connect_db()
    db = connect.cursor()

    # Compter voitures dans le parking
    db.execute("SELECT COUNT(*) as count FROM utilisateurs WHERE etat = 1")
    result = db.fetchone()

    used = result["count"]
    free = 20 - used

    connect.close()

    return jsonify({
        "used": used,
        "free": free
    })

# ====================================================================
# ROUTES - CONTRÔLE DES BARRIÈRES (VERSION CORRIGÉE)
# ====================================================================

@app.route("/openDoor", methods=["POST"])
def open_door():
    """
    Ouvre la barrière d'entrée pour un utilisateur
    VERSION CORRIGÉE avec gestion d'erreurs robuste
    """
    username = request.form["username"]
    password = hash_password(request.form["password"])

    connect = connect_db()
    db = connect.cursor()

    # Vérifier login + mot de passe
    db.execute("""
        SELECT nom, prenom, username, etat
        FROM utilisateurs
        WHERE username=? AND password=?
    """, (username, password))

    user = db.fetchone()
    print(f"[openDoor] User: {username} from {request.remote_addr}")

    # Login incorrect
    if not user:
        connect.close()
        print(f"[openDoor] ❌ Identifiants incorrects")
        return jsonify({
            "status": "refusé",
            "reason": "identifiants incorrects"
        })

    # Vérifier état
    if user["etat"] == 1:
        connect.close()
        print(f"[openDoor] ❌ Déjà dans le parking")
        return jsonify({
            "status": "refusé",
            "reason": "déjà dans le parking"
        })

    # Mise à jour optimiste : on marque l'entrée, on rollback si le Pico échoue
    db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
    connect.commit()
    print(f"[openDoor] ✅ BD mise à jour (optimiste): etat=1")

    # ================================================================
    # COMMUNICATION AVEC LE PICO - VERSION CORRIGÉE
    # ================================================================

    try:
        print(f"[openDoor] 📡 Envoi /open au Pico {PICO_IP}...")

        # Envoyer la requête
        pico_response = requests.get(
            f"http://{PICO_IP}/open",
            timeout=PICO_TIMEOUT
        )

        # ✅ AJOUT : Debug ultra-détaillé
        print(f"\n{'='*60}")
        print(f"DEBUG RÉPONSE PICO")
        print(f"{'='*60}")
        print(f"Code HTTP    : {pico_response.status_code}")
        print(f"Headers      :")
        for k, v in pico_response.headers.items():
            print(f"  {k}: {v}")
        print(f"\nContenu TEXT ({len(pico_response.text)} chars):")
        print(f"  {repr(pico_response.text)}")  # ← repr() montre les \r\n
        print(f"\nContenu BYTES ({len(pico_response.content)} bytes):")
        print(f"  {pico_response.content[:200]}")  # ← Montre les bytes bruts
        print(f"{'='*60}\n")

        # ✅ CORRECTION #1: Vérifier le code HTTP
        try:
            pico_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"[openDoor] ❌ Erreur HTTP Pico: {e}")
            raise Exception(f"Pico retourne code HTTP {pico_response.status_code}")

        # ✅ CORRECTION #2: Parser le JSON avec gestion d'erreur
        try:
            pico_data = pico_response.json()
        except ValueError as e:
            print(f"[openDoor] ❌ Réponse Pico invalide (pas JSON)")
            print(f"[openDoor]    Contenu reçu: {pico_response.text[:200]}")
            raise Exception("Pico n'a pas retourné du JSON valide")

        pico_status = pico_data.get("status")
        pico_message = pico_data.get("message", "")

        print(f"[openDoor] 📥 Réponse Pico: status={pico_status}, message={pico_message}")

        # ✅ CORRECTION #3: Validation stricte du statut
        if pico_status == "ok":
            # ✅ Détection réussie
            connect.close()
            print(f"[openDoor] ✅ Entrée autorisée")
            return jsonify({
                "status": "autorisé",
                "message": "entrée acceptée",
                "nom": user["nom"],
                "prenom": user["prenom"]
            })

        elif pico_status == "timeout":
            # ❌ Aucune voiture détectée → rollback
            print(f"[openDoor] ⏱️  Timeout capteur → Rollback BD")
            db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
            connect.commit()
            connect.close()
            return jsonify({
                "status": "refusé",
                "reason": "aucune voiture détectée",
                "message": "entrée annulée",
                "pico_status": pico_status
            })

        else:
            # ❌ Statut inconnu → rollback (sécurité)
            print(f"[openDoor] ❓ Statut Pico inconnu: '{pico_status}' → Rollback BD")
            db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
            connect.commit()
            connect.close()
            return jsonify({
                "status": "refusé",
                "reason": f"statut Pico inconnu: {pico_status}",
                "message": "entrée annulée (erreur Pico)",
                "pico_status": pico_status,
                "pico_message": pico_message
            })

    except requests.exceptions.Timeout:
        # ❌ Le Pico ne répond pas dans les temps → rollback
        print(f"[openDoor] ⏱️  Timeout réseau ({PICO_TIMEOUT}s) → Rollback BD")
        db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
        connect.commit()
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": f"Pico ne répond pas (timeout {PICO_TIMEOUT}s)",
            "message": "entrée annulée"
        })

    except requests.exceptions.ConnectionError as e:
        # ❌ Le Pico est hors ligne → rollback
        print(f"[openDoor] 🔌 Erreur connexion: {e} → Rollback BD")
        db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
        connect.commit()
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": "Pico hors ligne",
            "message": "entrée annulée"
        })

    except Exception as e:
        # ❌ Erreur inattendue → rollback
        print(f"[openDoor] ❌ Erreur inattendue: {e} → Rollback BD")
        db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
        connect.commit()
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": f"erreur: {str(e)}",
            "message": "entrée annulée"
        })


@app.route("/closeDoor", methods=["POST"])
def close_door():
    """
    Ouvre la barrière de sortie pour un utilisateur
    VERSION CORRIGÉE avec gestion d'erreurs robuste
    """
    username = request.form["username"]
    password = hash_password(request.form["password"])

    connect = connect_db()
    db = connect.cursor()

    # Vérifier login + mot de passe
    db.execute("""
        SELECT nom, prenom, username, etat
        FROM utilisateurs
        WHERE username=? AND password=?
    """, (username, password))

    user = db.fetchone()
    print(f"[closeDoor] User: {username} from {request.remote_addr}")

    # Identifiants incorrects
    if not user:
        connect.close()
        print(f"[closeDoor] ❌ Identifiants incorrects")
        return jsonify({
            "status": "refusé",
            "reason": "identifiants incorrects"
        })

    # Vérifier état (doit être 1 pour sortir)
    if user["etat"] == 0:
        connect.close()
        print(f"[closeDoor] ❌ Déjà à l'extérieur")
        return jsonify({
            "status": "refusé",
            "reason": "utilisateur déjà à l'extérieur"
        })

    # Mise à jour optimiste : on marque la sortie, on rollback si le Pico échoue
    db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
    connect.commit()
    print(f"[closeDoor] ✅ BD mise à jour (optimiste): etat=0")

    # ================================================================
    # COMMUNICATION AVEC LE PICO - VERSION CORRIGÉE
    # ================================================================

    try:
        print(f"[closeDoor] 📡 Envoi /close au Pico {PICO_IP}...")

        # Envoyer la requête
        pico_response = requests.get(
            f"http://{PICO_IP}/close",
            timeout=PICO_TIMEOUT
        )

        # ✅ CORRECTION #1: Vérifier le code HTTP
        try:
            pico_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"[closeDoor] ❌ Erreur HTTP Pico: {e}")
            raise Exception(f"Pico retourne code HTTP {pico_response.status_code}")

        # ✅ CORRECTION #2: Parser le JSON avec gestion d'erreur
        try:
            pico_data = pico_response.json()
        except ValueError as e:
            print(f"[closeDoor] ❌ Réponse Pico invalide (pas JSON)")
            print(f"[closeDoor]    Contenu reçu: {pico_response.text[:200]}")
            raise Exception("Pico n'a pas retourné du JSON valide")

        pico_status = pico_data.get("status")
        pico_message = pico_data.get("message", "")

        print(f"[closeDoor] 📥 Réponse Pico: status={pico_status}, message={pico_message}")

        # ✅ CORRECTION #3: Validation stricte du statut
        if pico_status == "ok":
            # ✅ Détection réussie
            connect.close()
            print(f"[closeDoor] ✅ Sortie autorisée")
            return jsonify({
                "status": "autorisé",
                "message": "sortie acceptée",
                "nom": user["nom"],
                "prenom": user["prenom"]
            })

        elif pico_status == "timeout":
            # ❌ Aucune voiture détectée → rollback
            print(f"[closeDoor] ⏱️  Timeout capteur → Rollback BD")
            db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
            connect.commit()
            connect.close()
            return jsonify({
                "status": "refusé",
                "reason": "aucune détection",
                "message": "sortie annulée",
                "pico_status": pico_status
            })

        else:
            # ❌ Statut inconnu → rollback (sécurité)
            print(f"[closeDoor] ❓ Statut Pico inconnu: '{pico_status}' → Rollback BD")
            db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
            connect.commit()
            connect.close()
            return jsonify({
                "status": "refusé",
                "reason": f"statut Pico inconnu: {pico_status}",
                "message": "sortie annulée (erreur Pico)",
                "pico_status": pico_status,
                "pico_message": pico_message
            })

    except requests.exceptions.Timeout:
        # ❌ Le Pico ne répond pas dans les temps → rollback
        print(f"[closeDoor] ⏱️  Timeout réseau ({PICO_TIMEOUT}s) → Rollback BD")
        db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
        connect.commit()
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": f"Pico ne répond pas (timeout {PICO_TIMEOUT}s)",
            "message": "sortie annulée"
        })

    except requests.exceptions.ConnectionError as e:
        # ❌ Le Pico est hors ligne → rollback
        print(f"[closeDoor] 🔌 Erreur connexion: {e} → Rollback BD")
        db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
        connect.commit()
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": "Pico hors ligne",
            "message": "sortie annulée"
        })

    except Exception as e:
        # ❌ Erreur inattendue → rollback
        print(f"[closeDoor] ❌ Erreur inattendue: {e} → Rollback BD")
        db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
        connect.commit()
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": f"erreur: {str(e)}",
            "message": "sortie annulée"
        })

# ====================================================================
# ROUTES - GESTION DES UTILISATEURS
# ====================================================================

@app.route("/users", methods=["GET"])
def load_users():
    """Retourne la liste de tous les utilisateurs"""
    connect = connect_db()
    db = connect.cursor()
    db.execute("SELECT nom, prenom, username, etat FROM utilisateurs")
    users = db.fetchall()
    connect.close()

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
    """Ajoute un nouvel utilisateur"""
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    username = request.form["username"]
    password = hash_password(request.form["password"])

    connect = connect_db()
    db = connect.cursor()

    db.execute(
        "INSERT INTO utilisateurs (nom, prenom, username, password, etat) VALUES (?, ?, ?, ?, ?)",
        (nom, prenom, username, password, 0)
    )
    connect.commit()
    connect.close()
    
    print(f"[addUser] ✅ Utilisateur ajouté: {username}")
    return jsonify({"status": "utilisateur ajouté avec succès"})

@app.route("/removeUser", methods=["POST"])
def remove_user():
    """Supprime un utilisateur"""
    username = request.form["username"]
    password = hash_password(request.form["password"])

    connect = connect_db()
    db = connect.cursor()

    db.execute(
        "DELETE FROM utilisateurs WHERE username=? AND password=?",
        (username, password)
    )

    affected = db.rowcount
    connect.commit()
    connect.close()

    if affected > 0:
        print(f"[removeUser] ✅ Utilisateur supprimé: {username}")
        return jsonify({"status": "utilisateur supprimé avec succès"})
    else:
        print(f"[removeUser] ❌ Échec suppression: {username}")
        return jsonify({"status": "utilisateur inexistant ou mot de passe incorrect"})

# ====================================================================
# LANCEMENT DU SERVEUR
# ====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SERVEUR PARKING INTELLIGENT (VERSION CORRIGÉE)")
    print("=" * 60)
    print(f"Pico IP       : {PICO_IP}")
    print(f"Pico Timeout  : {PICO_TIMEOUT}s")
    print(f"Interface web : http://0.0.0.0:5000")
    print("=" * 60)
    print("\nCorrections appliquées:")
    print("  ✅ Vérification code HTTP")
    print("  ✅ Gestion erreurs JSON")
    print("  ✅ Validation stricte statut")
    print("  ✅ Logs détaillés")
    print("=" * 60)
    print("\nAppuyez sur Ctrl+C pour arrêter")
    print("=" * 60 + "\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)
