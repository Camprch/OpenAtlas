#!/usr/bin/env python3
"""
Script de migration pour élargir la colonne 'source' de la table message (SQLite)
- Crée une nouvelle table message_tmp avec la bonne définition
- Copie toutes les données
- Remplace l'ancienne table
"""
import sqlite3
import shutil

DB_PATH = "data/osint.db"
BACKUP_PATH = "data/osint_backup.db"

# Sauvegarde de sécurité
shutil.copy(DB_PATH, BACKUP_PATH)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 1. Crée une nouvelle table avec la bonne définition
c.execute("""
CREATE TABLE IF NOT EXISTS message_tmp (
    id INTEGER PRIMARY KEY,
    telegram_message_id INTEGER,
    source VARCHAR(128) NOT NULL,
    channel VARCHAR,
    raw_text VARCHAR NOT NULL,
    translated_text VARCHAR,
    country VARCHAR,
    region VARCHAR,
    location VARCHAR,
    title VARCHAR,
    event_type VARCHAR,
    event_timestamp DATETIME,
    orientation VARCHAR,
    created_at DATETIME NOT NULL,
    country_norm TEXT
);
""")

# 2. Copie les données
c.execute("""
INSERT INTO message_tmp SELECT * FROM message;
""")

# 3. Supprime l'ancienne table
c.execute("DROP TABLE message;")

# 4. Renomme la nouvelle table
c.execute("ALTER TABLE message_tmp RENAME TO message;")

conn.commit()
conn.close()

print("Migration terminée. Sauvegarde :", BACKUP_PATH)
