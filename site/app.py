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

# Route d'accueil
@app.route("/")
def home():
    return render_template("index.html")

# Route pour ouvrir la porte
@app.route("/openDoor", methods=["POST"])
def open_door():
    username = request.form["username"]
    password = request.form["password"]
    password = hash_password(password)
    
    connect = connect_db()
    db = connect.cursor()
    
    db.execute(
        "SELECT username FROM utilisateurs WHERE username=? AND password=?",
        (username, password)
    )
    user = db.fetchone()
    connect.close()

    if user:
        # ID et mot de passe corrects
        return jsonify({"status": "ACCESS_GRANTED"})
    else:
        # ID inexistant ou mot de passe incorrect
        return jsonify({"status": "ACCESS_DENIED"})
    
   







if __name__ == "__main__":
    app.run(debug=True) 