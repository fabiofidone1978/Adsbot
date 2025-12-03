"""Database migration script to add subscription_type column."""

from sqlalchemy import create_engine, text
from adsbot.config import Config

config = Config.load()
engine = create_engine(config.database_url)

with engine.connect() as conn:
    try:
        # Try to add the column
        conn.execute(text("ALTER TABLE users ADD COLUMN subscription_type VARCHAR(50) DEFAULT 'gratis'"))
        conn.commit()
        print("✅ Colonna subscription_type aggiunta con successo!")
    except Exception as e:
        if "already exists" in str(e) or "duplicate column" in str(e):
            print("✅ Colonna subscription_type già esiste")
        else:
            print(f"❌ Errore: {e}")
