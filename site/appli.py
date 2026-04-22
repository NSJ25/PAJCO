from flask import Flask, render_template, request, jsonify
import sqlite3
import hashlib
import requests

PICO_IP = "172.20.136.113"

app = Flask(__name__)

@app.route("/test", methods=["GET"])

def test():
    return jsonify({"message": "OK depuis Flask"})

# Fonction pour obtenir le statut du parking
@app.route("/parking/status", methods=["GET"])
def parking_status():

    connect = connect_db()
    db = connect.cursor()

    # compter voitures dans le parking
    db.execute("SELECT COUNT(*) as count FROM utilisateurs WHERE etat = 1")
    result = db.fetchone()

    used = result["count"]
    free = 20 - used

    connect.close()

    return jsonify({
        "used": used,
        "free": free
    })

# Fonction pour hacher le mot de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Fonction pour se connecter à la base de données
def connect_db():
    connect = sqlite3.connect("parking.db")
    connect.row_factory = sqlite3.Row
    return connect

# Route pour acceder a page d'accueil
@app.route("/")
def home():
    return render_template("index.html")

# Route pour acceder a page admin
@app.route("/admin")
def admin():
    return render_template("admin.html")

# Route pour ouvrir la porte
@app.route("/openDoor", methods=["POST"])
def open_door():

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
    print(f"openDoor request from {request.remote_addr} user={username}")

    # Login incorrect
    if not user:
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": "identifiants incorrects"
        })

    # Vérifier état
    if user["etat"] == 1:
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": "déjà dans le parking"
        })

    # Update state before la commande Pico, puis corriger si la détection échoue.
    db.execute("""
        UPDATE utilisateurs
        SET etat = 1
        WHERE username=?
    """, (username,))

    connect.commit()

    pico_error = None
    pico_status = None
    response_payload = {
        "status": "autorisé",
        "message": "entrée acceptée",
        "nom": user["nom"],
        "prenom": user["prenom"]
    }

    try:
        print(f"Envoi de la commande /open au Pico {PICO_IP}")
        pico_response = requests.get(f"http://{PICO_IP}/open", timeout=30)
        pico_response.raise_for_status()
        pico_data = pico_response.json()
        pico_status = pico_data.get("status")
        print("Réponse Pico open:", pico_data)

        if pico_status == "timeout":
            db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
            connect.commit()
            response_payload = {
                "status": "refusé",
                "reason": "aucune voiture détectée, entrée annulée",
                "message": "entrée annulée",
                "pico_status": pico_status
            }
            connect.close()
            return jsonify(response_payload)
        elif pico_status and pico_status != "ok":
            response_payload["pico_status"] = pico_status

    except Exception as e:
        pico_error = str(e)
        print("Erreur Pico:", e)
        db.execute("UPDATE utilisateurs SET etat = 0 WHERE username=?", (username,))
        connect.commit()
        response_payload = {
            "status": "refusé",
            "reason": "commande Pico échouée",
            "message": "entrée annulée",
            "pico_error": pico_error
        }
        connect.close()
        return jsonify(response_payload)

    if pico_error:
        response_payload["pico_error"] = pico_error
        response_payload["message"] = "entrée acceptée (commande Pico échouée)"

    connect.close()
    return jsonify(response_payload)
      

# Route pour fermer la porte
@app.route("/closeDoor", methods=["POST"])
def close_door():

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
    print(f"closeDoor request from {request.remote_addr} user={username}")

    # identifiants incorrects
    if not user:
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": "identifiants incorrects"
        })

    # vérifier état (doit être 1 pour sortir)
    if user["etat"] == 0:
        connect.close()
        return jsonify({
            "status": "refusé",
            "reason": "utilisateur déjà à l'extérieur"
        })

    # mise à jour état (sortie du parking)
    db.execute("""
        UPDATE utilisateurs
        SET etat = 0
        WHERE username=?
    """, (username,))

    connect.commit()

    pico_error = None
    pico_status = None
    response_payload = {
        "status": "autorisé",
        "message": "sortie acceptée",
        "nom": user["nom"],
        "prenom": user["prenom"]
    }

    try:
        print(f"Envoi de la commande /close au Pico {PICO_IP}")
        pico_response = requests.get(f"http://{PICO_IP}/close", timeout=30)
        pico_response.raise_for_status()
        pico_data = pico_response.json()
        pico_status = pico_data.get("status")
        print("Réponse Pico close:", pico_data)

        if pico_status == "timeout":
            db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
            connect.commit()
            response_payload = {
                "status": "refusé",
                "reason": "aucune détection, sortie annulée",
                "message": "sortie annulée",
                "pico_status": pico_status
            }
            connect.close()
            return jsonify(response_payload)
        elif pico_status and pico_status != "ok":
            response_payload["pico_status"] = pico_status

    except Exception as e:
        pico_error = str(e)
        print("Erreur Pico:", e)
        db.execute("UPDATE utilisateurs SET etat = 1 WHERE username=?", (username,))
        connect.commit()
        response_payload = {
            "status": "refusé",
            "reason": "commande Pico échouée",
            "message": "sortie annulée",
            "pico_error": pico_error
        }
        connect.close()
        return jsonify(response_payload)

    if pico_error:
        response_payload["pico_error"] = pico_error
        response_payload["message"] = "sortie acceptée (commande Pico échouée)"

    connect.close()
    return jsonify(response_payload)

       
# Route pour charger les utilisateurs
@app.route("/users", methods=["GET"])
def load_users():
    connect = connect_db()
    db = connect.cursor()
    db.execute("SELECT nom, prenom, username, etat FROM utilisateurs")
    users = db.fetchall()
    connect.close()
    
    users_list = []

    # Convertir les données en liste de dictionnairesc
    for user in users:
        users_list.append({
            "nom": user["nom"],
            "prenom": user["prenom"],
            "username": user["username"],
            "etat": user["etat"]
        })
    return jsonify(users_list)
    
# Route pour ajouter un utilisateur   
@app.route("/addUser", methods=["POST"])
def add_user():
    # Récupérer les données du formulaire
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    username = request.form["username"]
    password = request.form["password"]
    
    # Hacher le mot de passe
    password = hash_password(password)
    
    # Se connecter à la base de données
    connect = connect_db()
    db = connect.cursor()
    
    # Insérer l'utilisateur dans la base de données
    db.execute(
        "INSERT INTO utilisateurs (nom, prenom, username, password, etat) VALUES (?, ?, ?, ?, ?)",
        (nom, prenom, username, password, 0)
    )
    connect.commit()
    connect.close()
    return jsonify({"status": "utilisateur ajouté avec succès"})

# Route pour supprimer un utilisateur
@app.route("/removeUser", methods=["POST"])
def remove_user():
    username = request.form["username"]
    password = request.form["password"]

    password = hash_password(password)
    
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
        return jsonify({"status": "utilisateur supprimé avec succès"})
    else:
        return jsonify({"status": "utilisateur inexistant ou mot de passe incorrect"}) 
if __name__ == "__main__":
    print("Server is running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
