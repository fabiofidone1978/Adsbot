# 🏪 ADSBOT MARKETPLACE - SPECIFICA TECNICA COMPLETA

## 📋 INDICE
1. [Ruoli Formali](#ruoli-formali)
2. [Metadati Canale](#metadati-canale)
3. [Filtri Inserzionista](#filtri-inserzionista)
4. [Flusso Transazionale](#flusso-transazionale)
5. [Regole Validazione](#regole-validazione)
6. [Schema Database](#schema-database)
7. [Automazioni](#automazioni)
8. [Sicurezza](#sicurezza)

---

## 1. RUOLI FORMALI

### EDITORE (Publisher/Seller)
**Responsabilità:**
- Registra il suo canale nel marketplace
- Imposta prezzo per post/promo
- Riceve notifiche di nuovi ordini
- Approva/Rifiuta ordini
- Pubblica il contenuto per durata richiesta (6/12/24h)
- Conferma pubblicazione completata
- Ritira guadagni

**Dati Associati:**
- User ID (Telegram)
- Canali amministrati
- Prezzi impostati
- Storico ordini accettati/rifiutati
- Wallet/Saldo
- Performance media (CTR, iscritti acquisiti)

---

### INSERZIONISTA (Advertiser/Buyer)
**Responsabilità:**
- Filtra e ricerca canali nel catalogo
- Seleziona canale e invia ordine
- Carica credito (paga 10% fee a noi)
- Prepara contenuto (testo + media)
- Invia contenuto all'editore
- Osserva risultati e performance
- Re-acquista se ROI positivo

**Dati Associati:**
- User ID (Telegram)
- Wallet/Saldo disponibile
- Storico ordini acquistati
- Preferenze filtri (salvate)
- Performance acquisti (ROI, conversioni)

---

## 2. METADATI CANALE

**Dati Obbligatori:**
```
channel_id (INT)                      # ID Telegram canale
username (STRING)                     # Handle canale @username
title (STRING)                        # Nome completo canale
categoria (STRING)                    # "crypto", "tech", "marketing", ecc
owner_telegram_id (INT)               # ID creatore
admin_verified_at (DATETIME)          # Quando verificato come admin
```

**Metriche (aggiornate ogni 6 ore):**
```
subscribers (INT)                     # Numero iscritti TOTALI
reach_24h (INT)                       # Reach ultime 24 ore
engagement_rate (FLOAT)               # 0-1 (interazioni/impressioni)
quality_score (FLOAT)                 # 0-1 (calcolato da algo)
traffic_origin (STRING)               # "organic", "ads", "mixed"
last_metrics_update (DATETIME)        # Timestamp ultimo refresh
```

**Storico Performance:**
```
avg_ctr (FLOAT)                       # Click-Through-Rate medio
total_subscribers_acquired (INT)      # Iscritti acquisiti da promos
fraud_reports (INT)                   # Segnalazioni iscritti fake
verified_reach_score (FLOAT)          # Score affidabilità reach
```

**Marketplace Specifico:**
```
listing_price (FLOAT)                 # Prezzo suggerito/impostato
price_currency (STRING)               # "EUR"
is_active (BOOLEAN)                   # Canale è ancora attivo
is_available (BOOLEAN)                # Disponibile per new orders
last_order_date (DATETIME)            # Ultimo ordine completato
consecutive_cancellations (INT)       # Flag se editor cancella spesso
```

---

## 3. FILTRI INSERZIONISTA

**Filtri Disponibili:**
```
categoria (ARRAY)                     # Multi-select: crypto, tech, lifestyle, ecc
prezzo_minimo (FLOAT)                 # €
prezzo_massimo (FLOAT)                # €
lingua (ARRAY)                        # it, en, es, ecc
nazionalita_pubblico (STRING)         # IT, US, EU, ecc
dimensione_canale (RANGE)             # 1k-10k, 10k-100k, 100k+
engagement_minimo (FLOAT)             # Minimo engagement_rate
formato_post (ARRAY)                  # "text", "image", "video", "story"
reach_minimo_24h (INT)                # Minimo reach richiesto
quality_score_minimo (FLOAT)          # Minimo 0.7, ecc
```

**Salvataggio Preferenze:**
```
advertiser_id
saved_filter_name (STRING)            # "Crypto Italia Top"
filter_config (JSON)                  # Tutta la config
created_at
last_used_at
```

---

## 4. FLUSSO TRANSAZIONALE

```
STEP 1: ORDINE CREATO
├─ Inserzionista sceglie canale
├─ Seleziona durata (6/12/24 ore)
├─ Sistema crea ordine con status=PENDING
└─ Order ID generato

STEP 2: NOTIFICA EDITORE
├─ Editor riceve notifica Telegram
├─ Vede: Canale, Prezzo, Durata, Contenuto preview
├─ Scadenza: 30 min per decidere
└─ Se non risponde → AUTO-CANCEL

STEP 3: DECISIONE EDITORE
├─ Editor clicca "ACCETTA" o "RIFIUTA"
├─ Se RIFIUTA:
│  ├─ Ordine → status=CANCELLED
│  ├─ Credito inserzionista RESTITUITO (100%)
│  └─ Inserzionista notificato
└─ Se ACCETTA:
   ├─ Ordine → status=CONFIRMED
   ├─ Notifica inserzionista: "Editore ha accettato"
   └─ Inserzionista invia contenuto finale

STEP 4: INVIO CONTENUTO
├─ Inserzionista carica testo + media
├─ Sistema valida (anti-spam)
├─ Notifica editore: "Contenuto pronto"
└─ Editor ha 2 ore per pubblicare

STEP 5: PUBBLICAZIONE
├─ Editor pubblica nel canale
├─ Ordine → status=PUBLISHED
├─ Sistema registra timestamp pubblicazione
├─ Notifica inserzionista: "Promo online"
└─ Timer avviato per scadenza

STEP 6: DURATA PROMO
├─ Post rimane online per durata (6/12/24h)
├─ Sistema monitora engagement
├─ Scadenza raggiunta → Ordine → status=EXPIRED
└─ Reminder editore: "Rimuovi la promo"

STEP 7: CONFERMA COMPLETAMENTO
├─ Editor clicca "Promo rimossa"
├─ Ordine → status=COMPLETED
└─ Trigger pagamento

STEP 8: PAGAMENTO
├─ Calcola: importo_ordine * (1 - 0.10)
├─ Esempio: €100 → €90 editore, €10 a noi
├─ Credito editore aggiornato
├─ Transazione loggata
└─ Notifiche: "Guadagno registrato!"

STEP 9: CHIUSURA TICKET
├─ Ordine archiviato
├─ Dati tracciati per analytics
├─ Metadati canale aggiornati
└─ Fine
```

---

## 5. REGOLE VALIDAZIONE

### VALIDAZIONE CANALE (Al Momento Registrazione)
```python
# 1. Verifica admin
if not is_admin_in_channel(editor_id, channel_id):
    return ERROR("Non sei admin del canale")

# 2. Verifica reach minimo
if channel_reach_24h < 100:
    return ERROR("Reach insufficiente (minimo 100)")

# 3. Verifica iscritti
if channel_subscribers < 500:
    return ERROR("Minimo 500 iscritti")

# 4. Verifica iscritti fake (se possibile)
if suspected_fake_subscribers(channel_id) > 0.2:  # >20% fake
    return ERROR("Rilevati iscritti fake")

# 5. Verifica engagement
if engagement_rate < 0.001:  # Meno di 0.1%
    return WARNING("Engagement molto basso")

# 6. Blocca se cancellazioni consecutive
if consecutive_cancellations > 3:
    return ERROR("Troppi ordini cancellati")
```

### VALIDAZIONE ORDINE
```python
# 1. Blocca ordine doppio
if exists_active_order_for_channel(channel_id):
    return ERROR("Canale non disponibile (ordine in corso)")

# 2. Valida credito inserzionista
if advertiser_balance < order_price:
    return ERROR("Credito insufficiente")

# 3. Valida contenuto (anti-spam)
if spam_detected(content_text):
    return ERROR("Contenuto sospetto (spam/scam)")

# 4. Blocca se editor offline (30+ giorni)
if editor_last_activity > 30_days:
    return ERROR("Editore inattivo")

# 5. Valida lingua/categoria match
if not category_match(advertiser_pref, channel_category):
    return WARNING("Categoria non corrisponde a preferenze")
```

### VALIDAZIONE PUBBLICAZIONE
```python
# 1. Controllo timeline
if time_elapsed > duration_hours:
    return ERROR("Tempo scaduto per pubblicare")

# 2. Verifica post in canale
if not post_found_in_channel(order_id, channel_id):
    return ERROR("Post non trovato nel canale")

# 3. Log pubblicazione
log_publication(order_id, editor_id, timestamp, post_link)
```

---

## 6. SCHEMA DATABASE

### Tabella: `editors`
```sql
CREATE TABLE editors (
    id INT PRIMARY KEY,
    user_id INT FOREIGN KEY users(id),
    verified_admin_channels INT,
    total_earnings FLOAT,
    wallet_balance FLOAT,
    rating FLOAT,  -- Media 1-5 stelle
    cancellation_rate FLOAT,
    created_at DATETIME,
    verified_at DATETIME,
    is_active BOOLEAN
);
```

### Tabella: `advertisers`
```sql
CREATE TABLE advertisers (
    id INT PRIMARY KEY,
    user_id INT FOREIGN KEY users(id),
    wallet_balance FLOAT,
    total_spent FLOAT,
    total_orders INT,
    roi_average FLOAT,
    saved_filters JSON,
    created_at DATETIME,
    is_active BOOLEAN
);
```

### Tabella: `channels_metadata`
```sql
CREATE TABLE channels_metadata (
    id INT PRIMARY KEY,
    channel_id INT FOREIGN KEY channels(id),
    owner_id INT FOREIGN KEY users(id),
    
    -- Metriche
    subscribers INT,
    reach_24h INT,
    engagement_rate FLOAT,
    quality_score FLOAT,
    traffic_origin STRING,
    
    -- Performance storico
    avg_ctr FLOAT,
    total_acquired_subscribers INT,
    fraud_reports INT,
    
    -- Marketplace
    listing_price FLOAT,
    is_active BOOLEAN,
    is_available BOOLEAN,
    
    -- Timeline
    created_at DATETIME,
    last_metrics_update DATETIME,
    last_order_date DATETIME,
    consecutive_cancellations INT
);
```

### Tabella: `marketplace_orders`
```sql
CREATE TABLE marketplace_orders (
    id INT PRIMARY KEY,
    
    -- Parti
    seller_id INT FOREIGN KEY editors(id),
    buyer_id INT FOREIGN KEY advertisers(id),
    channel_id INT FOREIGN KEY channels_metadata(id),
    
    -- Dettagli
    price_charged FLOAT,
    duration_hours INT,  -- 6, 12, 24
    status ENUM(PENDING, CONFIRMED, PUBLISHED, EXPIRED, COMPLETED, CANCELLED),
    
    -- Contenuto
    content_text TEXT,
    content_media_urls JSON,
    
    -- Timeline
    created_at DATETIME,
    confirmed_at DATETIME,
    published_at DATETIME,
    expires_at DATETIME,
    completed_at DATETIME,
    
    -- Pagamento
    seller_earned FLOAT,
    platform_commission FLOAT,  -- 10%
    payment_confirmed_at DATETIME,
    
    -- Metrics
    clicks INT,
    new_subscribers INT,
    engagement INT
);
```

### Tabella: `transactions`
```sql
CREATE TABLE transactions (
    id INT PRIMARY KEY,
    user_id INT FOREIGN KEY users(id),
    type ENUM(DEPOSIT, WITHDRAWAL, EARN, COMMISSION, REFUND),
    amount FLOAT,
    balance_after FLOAT,
    order_id INT FOREIGN KEY marketplace_orders(id),
    reference_id STRING,
    description TEXT,
    created_at DATETIME
);
```

### Tabella: `advertiser_saved_filters`
```sql
CREATE TABLE advertiser_saved_filters (
    id INT PRIMARY KEY,
    advertiser_id INT FOREIGN KEY advertisers(id),
    filter_name STRING,
    filter_config JSON,
    created_at DATETIME,
    last_used_at DATETIME
);
```

---

## 7. AUTOMAZIONI

### Scheduled Task: UPDATE REACH (ogni 6 ore)
```python
async def update_all_channels_reach():
    """Aggiorna reach 24h di tutti i canali attivi"""
    for listing in ChannelListing.query.filter_by(is_active=True):
        try:
            chat = await bot.get_chat(chat_id=listing.channel_id)
            reach = get_reach_24h(chat)  # Da API Telegram o stima
            listing.reach_24h = reach
            listing.last_metrics_update = now()
            db.commit()
        except:
            logger.error(f"Failed to update reach for {listing.channel_id}")
```

### Scheduled Task: CHECK EXPIRED ORDERS (ogni 30 min)
```python
async def check_expired_orders():
    """Controlla ordini scaduti, invia reminder, auto-cancella"""
    expired = MarketplaceOrder.query.filter(
        status='PUBLISHED',
        expires_at < now()
    ).all()
    
    for order in expired:
        # Notifica editor
        await notify_editor(order.seller_id, 
            f"Promot #{order.id} scaduta nel canale {order.channel.title}")
        # Set a reminder
        order.status = 'EXPIRED'
        db.commit()
```

### Scheduled Task: AUTO-CANCEL PENDING (dopo 30 min)
```python
async def auto_cancel_pending_orders():
    """Se editor non decide in 30 min, cancella ordine"""
    pending = MarketplaceOrder.query.filter(
        status='PENDING',
        created_at < now() - 30_minutes
    ).all()
    
    for order in pending:
        order.status = 'CANCELLED'
        # Refund advertiser
        refund_advertiser(order.buyer_id, order.price_charged)
        await notify_advertiser(order.buyer_id, 
            f"Ordine #{order.id} cancellato (editore non ha risposto)")
```

### Event: ON PUBLICATION
```python
async def on_order_published(order_id):
    """Quando editor pubblica il post"""
    order = MarketplaceOrder.get(order_id)
    order.status = 'PUBLISHED'
    order.published_at = now()
    order.expires_at = now() + order.duration_hours
    db.commit()
    
    # Notifica inserzionista
    await notify_advertiser(order.buyer_id,
        f"✅ Tua promo è online nel canale {order.channel.title}!")
```

### Event: ON COMPLETION
```python
async def on_order_completed(order_id):
    """Quando ordine è completato, paga editore"""
    order = MarketplaceOrder.get(order_id)
    order.status = 'COMPLETED'
    order.completed_at = now()
    
    # Calcola pagamento
    seller_earn = order.price_charged * 0.90
    platform_commission = order.price_charged * 0.10
    
    # Registra transazioni
    add_transaction(order.seller_id, 'EARN', seller_earn, order_id)
    add_transaction(US_COMPANY_ID, 'COMMISSION', platform_commission, order_id)
    
    # Aggiorna wallet editor
    editor = Editor.get(order.seller_id)
    editor.wallet_balance += seller_earn
    editor.total_earnings += seller_earn
    db.commit()
    
    # Notifiche
    await notify_editor(order.seller_id,
        f"💰 Guadagno €{seller_earn:.2f} da ordine #{order_id}")
```

---

## 8. SICUREZZA

### Verifica Admin Canale
```python
async def verify_channel_admin(user_id, channel_id):
    """Verifica che user_id è davvero admin del canale"""
    try:
        member = await bot.get_chat_member(
            chat_id=channel_id,
            user_id=user_id
        )
        is_admin = member.status in ['administrator', 'creator']
        timestamp = now()
        log_admin_check(user_id, channel_id, is_admin, timestamp)
        return is_admin
    except:
        return False
```

### Anti-Spam Contenuto
```python
def validate_content(text, media_urls):
    """Valida contenuto per spam/scam"""
    # Check blacklist keywords
    if any(keyword in text.lower() for keyword in BLACKLIST):
        return False, "Contenuto contiene keywords vietate"
    
    # Check URL reputation
    for url in media_urls:
        if url_reputation_check(url) == 'MALICIOUS':
            return False, "URL sospetto rilevato"
    
    # Check spam patterns
    if excessive_emojis(text) or excessive_caps(text):
        return False, "Formato sospetto (spam)"
    
    return True, None
```

### Protezione Ordini Doppi
```python
def check_duplicate_order(channel_id):
    """Blocca ordini doppi sullo stesso canale"""
    active = MarketplaceOrder.query.filter(
        channel_id=channel_id,
        status__in=['PENDING', 'CONFIRMED', 'PUBLISHED']
    ).first()
    return active is not None
```

### Webhook Cleanup
```python
async def cleanup_webhooks():
    """Pulisci webhook falliti/vecchi"""
    stale_webhooks = get_stale_webhooks(age_days=30)
    for webhook in stale_webhooks:
        try:
            await deregister_webhook(webhook.id)
        except:
            pass
```

### Logging Completo
```python
def log_action(user_id, action, details, timestamp=now()):
    """Registra OGNI azione importante"""
    log_entry = {
        'user_id': user_id,
        'action': action,  # 'register_channel', 'publish_post', ecc
        'details': details,
        'timestamp': timestamp,
        'ip_address': get_user_ip(),  # Se applicabile
    }
    db.audit_logs.insert(log_entry)
```

---

## CHECKLIST IMPLEMENTAZIONE

- [ ] Database schema creato e migrato
- [ ] Verifica admin canale implementata
- [ ] Reach 24h auto-update via scheduled task
- [ ] Filtri inserzionista con salvataggio preferenze
- [ ] State machine ordini implementato
- [ ] Pagamenti e wallet tracciati
- [ ] Notifiche bidirezionali (Telegram)
- [ ] Validazioni anti-spam
- [ ] Logging audit completo
- [ ] Test end-to-end (editor registra → inserzionista compra → pubblica → paga)

---

**Data Creazione:** 2025-12-05  
**Versione:** 1.0  
**Status:** In Implementazione
