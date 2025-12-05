#!/usr/bin/env python3
"""
Migrazione: Aggiunge i campi image_file_id, image_url e content alla tabella campaigns.
"""

import sqlite3
import sys
from pathlib import Path

# Trova il percorso del database
config_path = Path(__file__).parent / "adsbot" / "config.py"
db_path = Path(__file__).parent / "adsbot.db"

if not db_path.exists():
    print(f"Database non trovato: {db_path}")
    print("Creazione nuovo database...")
    db_path.touch()

print(f"Connecting to: {db_path}")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Controlla se i colori esistono già
cursor.execute("PRAGMA table_info(campaigns)")
columns = {row[1] for row in cursor.fetchall()}

print(f"Colonne attuali: {columns}")

# Aggiungi i nuovi colori se non esistono
if 'image_file_id' not in columns:
    print("Aggiungendo colonna image_file_id...")
    cursor.execute("""
        ALTER TABLE campaigns ADD COLUMN image_file_id VARCHAR(255) NULL
    """)
    print("✓ image_file_id aggiunto")
else:
    print("✓ image_file_id già esiste")

if 'image_url' not in columns:
    print("Aggiungendo colonna image_url...")
    cursor.execute("""
        ALTER TABLE campaigns ADD COLUMN image_url TEXT NULL
    """)
    print("✓ image_url aggiunto")
else:
    print("✓ image_url già esiste")

if 'content' not in columns:
    print("Aggiungendo colonna content...")
    cursor.execute("""
        ALTER TABLE campaigns ADD COLUMN content TEXT NULL
    """)
    print("✓ content aggiunto")
else:
    print("✓ content già esiste")

conn.commit()
conn.close()

print("\n✅ Migrazione completata!")
