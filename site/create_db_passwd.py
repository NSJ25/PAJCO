import sqlite3
import hashlib

# Fonction pour hacher le mot de passe
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Connexion à la base de données
conn = sqlite3.connect("parking.db")
db = conn.cursor()

# ---- Table utilisateurs ----
db.execute("""
CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,   -- identifiant pour login
    password TEXT NOT NULL,          -- mot de passe haché
    etat INTEGER CHECK (etat IN (0,1)) DEFAULT 0
)
""")

# Trigger pour limiter le nombre d'utilisateurs à 20
db.execute("""
CREATE TRIGGER IF NOT EXISTS limite_utilisateurs
BEFORE INSERT ON utilisateurs
FOR EACH ROW
WHEN (SELECT COUNT(*) FROM utilisateurs) >= 20
BEGIN
    SELECT RAISE(ABORT, 'Nombre maximum d utilisateurs atteint (20)');
END;
""")

# ---- Table passages (historique) ----
db.execute("""
CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date_entree TEXT,
    date_sortie TEXT,
    FOREIGN KEY(user_id) REFERENCES utilisateurs(id)
)
""")

print("La base de données a été créée avec succès.")

# ---- Ajout d'utilisateurs exemples ----
users = [
    ('Ravalison', 'Audrey', 'RA0000', hash_password('0272'), 0),
    ('Lawson', 'Clara', 'LA0000', hash_password('8638'), 0),
    ('Fofana', 'Oumou', 'FO0000', hash_password('8776'), 0),
    ('Ngassam', 'Paule', 'NP0000', hash_password('2753'), 0),
    ('Nsenda', 'Jeremie', 'NJ0000', hash_password('2525'), 0)
]

db.executemany("""
INSERT INTO utilisateurs (nom, prenom, username, password, etat)
VALUES (?, ?, ?, ?, ?)
""", users)

conn.commit()
conn.close()
print("Les utilisateurs ont été ajoutés avec succès.")