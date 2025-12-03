 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
index 1d04f8c0d42de389032fe3d2da0125537ae1e3bc..8c6bbfdadf89d8e594bedad9a6013d2e9eca5bc7 100644
--- a/README.md
 b/README.md
@@ -1 1,40 @@
-# Adsbot
\ No newline at end of file
# Adsbot

Bot Telegram per far crescere e monetizzare canali in stile `@InsideAds_Support_bot`.

## Architettura
- **python-telegram-bot 20.x** per gli handler asincroni.
- **SQLite  SQLAlchemy** per salvare utenti, canali, obiettivi, campagne, offerte ADV e template di broadcast.
- Struttura modulare (`adsbot/config.py`, `adsbot/db.py`, `adsbot/models.py`, `adsbot/services.py`, `adsbot/bot.py`) per separare config, persistenza e logica.

## Funzionalità attuali
- Registrazione utente automatica al primo `/start`.
- Menu inline con scorciatoie per:
  - Aggiungere canali.
  - Definire obiettivi di crescita (numero target  deadline opzionale).
  - Salvare offerte ADV (shoutout, post, pinned, takeover) con prezzo e note.
  - Registrare campagne con budget e call-to-action.
  - Creare template di broadcast.
  - Mostrare statistiche rapide per riepilogare canali, obiettivi, offerte e template.
- Comando `/help` per la guida rapida e `/stats` per il riepilogo.

## Requisiti
- Python 3.10
- Variabile ambiente `BOT_TOKEN` con il token BotFather.
- Opzionale: `DATABASE_URL` per puntare a un database diverso da SQLite locale (`sqlite:///adsbot.db` di default).

## Setup locale
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="<il_tuo_token_botfather>"
python main.py
```
Il bot usa il polling e creerà automaticamente il database SQLite `adsbot.db` nella root del progetto.

## Idee di evoluzione
- Job scheduler per reminder sulle deadline degli obiettivi.
- Collegamento a API di analytics (es. Combot, TGStat) per popolare metriche reali.
- Marketplace interno per incrociare offerte ADV tra canali registrati.
- Webhook  pannello web per reporting e gestione multi-team.
 
EOF
)