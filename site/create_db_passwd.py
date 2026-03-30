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
    username TEXT PRIMARY KEY,   
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
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
    FOREIGN KEY(user_id) REFERENCES utilisateurs(username)
)
""")

print("La base de données a été créée avec succès.")

# ---- Ajout d'utilisateurs exemples ----
users = [
    ( 'RA0000','Ravalison', 'Audrey', hash_password('0272'), 0),
    ( 'LA0000','Lawson', 'Clara', hash_password('8638'), 0),
    ( 'FO0000','Fofana', 'Oumou', hash_password('8776'), 0),
    ( 'NP0000','Ngassam', 'Paule', hash_password('2753'), 0),
    ( 'NJ0000','Nsenda', 'Jeremie', hash_password('2525'), 0)
]

db.executemany("""
INSERT INTO utilisateurs ( username, nom, prenom, password, etat)
VALUES (?, ?, ?, ?, ?)
""", users)

conn.commit()
conn.close()
print("Les utilisateurs ont été ajoutés avec succès.")