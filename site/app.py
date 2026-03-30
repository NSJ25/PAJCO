from flask import Flask, render_template, request, jsonify
import sqlite3
import hashlib


app = Flask(__name__)

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
    # Récupérer les données du formulaire
    username = request.form["username"]
    password = request.form["password"]
    
    # Hacher le mot de passe
    password = hash_password(password)
    
    # Se connecter à la base de données
    connect = connect_db()
    db = connect.cursor()
    
    # Rechercher l'utilisateur dans la base de données
    db.execute(
        "SELECT nom, prenom, username FROM utilisateurs WHERE username=? AND password=?",
        (username, password)
    )
    user = db.fetchone()
    connect.close()

    # Vérifier si l'utilisateur existe
    if user:
        # ID et mot de passe corrects
         return jsonify({
            "status": "access authorisé",
            "nom": user["nom"],
            "prenom": user["prenom"]
        })
    else:
        # ID inexistant ou mot de passe incorrect
        return jsonify({"status": "access refusé"})
    
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
    app.run(debug=True) 