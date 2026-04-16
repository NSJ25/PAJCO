from flask import Flask, request, jsonify
from flask_cors import CORS

import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

MAX_PLACES = 20
places = MAX_PLACES

# ======================
# INIT DB
# ======================
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # USERS
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        badge TEXT PRIMARY KEY,
        nom TEXT,
        prenom TEXT,
        adresse TEXT
    )''')

    # LOGS
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        badge TEXT,
        nom TEXT,
        prenom TEXT,
        action TEXT,
        date TEXT,
        heure TEXT
    )''')

    conn.commit()
    conn.close()

# ======================
# INSERT USERS
# ======================
def seed_users():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    users = [
        ("1234", "Fofana", "Oumou", "Bruxelles"),
        ("5678", "Ravalison", "Audrey", "Liège"),
        ("9999", "Nini", "Toto", "Namur")
    ]

    for u in users:
        try:
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", u)
        except:
            pass

    conn.commit()
    conn.close()

init_db()
seed_users()

# ======================
# CHECK BADGE
# ======================
@app.route("/check", methods=["POST"])
def check():
    global places

    badge = request.json.get("badge")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT nom, prenom FROM users WHERE badge=?", (badge,))
    user = c.fetchone()

    conn.close()

    if user and places > 0:
        return jsonify({
            "access": True,
            "nom": user[0],
            "prenom": user[1]
        })

    return jsonify({"access": False})

# ======================
# UPDATE ENTREE / SORTIE
# ======================
@app.route("/update", methods=["POST"])
def update():
    global places

    data = request.json
    badge = data.get("badge")
    action = data.get("action")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT nom, prenom FROM users WHERE badge=?", (badge,))
    user = c.fetchone()

    if not user:
        return jsonify({"error": "user inconnu"})

    nom, prenom = user

    if action == "entree" and places > 0:
        places -= 1
    elif action == "sortie" and places < MAX_PLACES:
        places += 1

    now = datetime.now()

    c.execute('''INSERT INTO logs (badge, nom, prenom, action, date, heure)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (badge, nom, prenom, action,
               str(now.date()), str(now.time())))

    conn.commit()
    conn.close()

    return jsonify({"places": places})

# ======================
# GET PLACES
# ======================
@app.route("/places")
def get_places():
    return jsonify({"places": places})

# ======================
# GET LOGS (optionnel)
# ======================
@app.route("/logs")
def logs():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM logs")
    data = c.fetchall()

    conn.close()

    return jsonify(data)

app.run(host="0.0.0.0", port=5000)