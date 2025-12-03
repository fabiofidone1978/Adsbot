# Test Guide - Inside Ads Bot

## Overview
Questo documento descrive come testare i menu e i flussi di Inside Ads implementati nel bot Telegram.

## Prerequisiti
- Bot Telegram attivo (token configurato)
- Variabile d'ambiente `BOT_TOKEN` impostata
- Database SQLite inizializzato (creato automaticamente al primo avvio)

## Come Avviare
```bash
set BOT_TOKEN=il_tuo_token_reale_qui
python main.py
```

## Test Cases

### 1. Menu Principale Inside Ads
**Comando**: `/insideads` (oppure clicca menu inline)

**Expected Output**:
- Menu con 5 pulsanti: Guadagna, Acquista, Scambio, Statistiche, Account

---

### 2. Flusso "Guadagna" (💰)
**Step 1**: Clicca "Guadagna" dal menu principale

**Expected Output**:
- Sottomenu con: Editore, Inserizionista, Iscritti gratis, Analisi canale, Indietro

**Step 2**: Clicca "Editore"

**Expected Output**:
- Descrizione: "Monetizza il tuo contenuto e guadagna mostrando annunci sul tuo canale"
- Badge verde "GUADAGNA DENARO"

---

### 3. Flusso "Acquista" (🛒)
**Step 1**: Clicca "Acquista" dal menu principale

**Expected Output**:
- Saldo attuale visualizzato (es. $0.00)
- Pulsanti: Crea campagna, Le mie campagne, Indietro

**Step 2**: Clicca "Crea campagna"

**Expected Output**:
- Messaggio: "Funzionalità di creazione campagna non ancora disponibile"

**Step 3**: Clicca "Le mie campagne"

**Expected Output**:
- Lista campagne (vuota se non ne sono state create)

---

### 4. Flusso "Scambio" (🔄)
**Step 1**: Clicca "Scambio" dal menu principale

**Expected Output**:
- Messaggio: "Sistema di scambio automatico di iscritti tra canali"
- Pulsanti: Metriche, Configura scambio, Indietro

**Step 2**: Clicca "Metriche"

**Expected Output**:
- Elenco canali dell'utente con metriche (Follower: 0, Click: 0)

**Step 3**: Clicca "Configura scambio"

**Expected Output**:
- Messaggio: "Funzionalità di configurazione scambio non ancora disponibile"

---

### 5. Flusso "Statistiche" (📊)
**Step 1**: Clicca "Statistiche" dal menu principale

**Expected Output**:
- Dashboard con saldo, canali, campagne, metriche (follower, click, visualizzazioni)
- Pulsanti: Pubblicità, Monetizzazione, Indietro

**Step 2**: Clicca "Pubblicità"

**Expected Output**:
- Statistiche campagne: numero campagne, follower, click, visualizzazioni
- Pulsanti: Nuova campagna, Indietro

**Step 3**: Clicca "Monetizzazione"

**Expected Output**:
- Canali attivi, entrate totali, entrate settimanali
- Pulsanti: Configura, Indietro

---

### 6. Flusso "Account" (👤)
**Step 1**: Clicca "Account" dal menu principale

**Expected Output**:
- Profilo: nome, username
- Pulsanti: Transazioni, Impostazioni, Indietro

**Step 2**: Clicca "Transazioni"

**Expected Output**:
- Lista transazioni recenti (vuota se nessuna transazione)
- Mostra fino a 5 transazioni con importo e descrizione

**Step 3**: Clicca "Impostazioni"

**Expected Output**:
- Messaggio: "Funzionalità di impostazioni non ancora disponibile"

---

### 7. Navigazione Indietro
**Test**: Clicca "Indietro" da qualsiasi sottomenu

**Expected Output**:
- Torna al menu precedente (es. da Editore → Guadagna → Menu Principale)

---

## Problemi Comuni

### Errore: "Message is not modified"
- Questo è un warning noto quando il messaggio non cambia
- È stato gestito con try/except nel codice

### Errore: "No error handlers are registered"
- Normale se non hai handler di errore personalizzati
- Il bot continua a funzionare

### Token rifiutato
- Verifica che il token sia corretto e attivo su @BotFather
- Assicurati di usare il comando `set BOT_TOKEN=...` corretto

---

## Prossimi Passi

1. **Integrazione Database**: Creare schema DB e testare persistenza dati
2. **Pagamenti Reali**: Integrare provider (Stripe, PayPal, etc.)
3. **Sistema di Offerte**: Implementare logica di acquisto/vendita campagne
4. **Automazione Metriche**: Connettere API Telegram per metriche reali
5. **Notifiche**: Aggiungere notifiche per transazioni e nuove campagne

---

## Checklist di Test
- [ ] Menu principale si apre correttamente
- [ ] Navigazione tra sottomenu fluida
- [ ] Pulsanti "Indietro" riportano al menu precedente
- [ ] Saldo visualizzato correttamente
- [ ] Transazioni visualizzate (una volta create)
- [ ] Nessun errore di sintassi nei log
- [ ] Bot rimane online durante la navigazione
