import sqlite3

conn = sqlite3.connect("parking.db")
db = conn.cursor()

# Table utilisateurs
db.execute("""
CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    rfid TEXT UNIQUE NOT NULL,
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

# Table passages (historique)
db.execute("""
CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date_entree TEXT,
    date_sortie TEXT,
    FOREIGN KEY(user_id) REFERENCES utilisateurs(id)
)
""")

# Message de confirmation de la création de la base de données
print("The database has been created successfully.")

# Ajout des utilisateurs dans la base de données
db.execute("""
INSERT INTO utilisateurs (nom, prenom, rfid)
VALUES 
    ('Ravalison', 'Audrey', 'A007'),
    ('Lawson', 'Clara', 'L007'),
    ('Fofana', 'Oumou', 'F007'),
    ('Ngassam', 'Paule', 'N007'),
    ('Nsenda', 'Jeremie', 'J007')
""")

conn.commit()
conn.close()

# Message de confirmation de l'ajout des utilisateurs
print("The users have been added successfully.")