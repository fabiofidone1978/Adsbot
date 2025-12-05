# 🏗️ ADSBOT MARKETPLACE V2 - ARCHITETTURA STATE MACHINE

## 📊 OVERVIEW

Adsbot è modellato come una **State Machine Complessa** con 3 dimensioni di stato:

1. **USER STATE** - Fase di registrazione/attivazione dell'utente
2. **CHANNEL STATE** - Stato del canale nel marketplace
3. **ORDER STATE** - Fase della transazione publicitaria

---

## 1. USER STATE MACHINE

**5 Stati Possibili:**

```
NEW_USER
    ↓ (seleziona ruolo)
    ├─→ EDITOR_REGISTERING ─→ admin verifica ─→ EDITOR_ACTIVE
    └─→ ADVERTISER_REGISTERING ─→ carica credito ─→ ADVERTISER_ACTIVE
                                                         ↓ (violazione)
                                                      SUSPENDED
```

### State Details

| State | Description | Allowed Actions |
|-------|-------------|-----------------|
| **NEW_USER** | Utente appena iscritto, non ha scelto ruolo | `/start`, scegli ruolo |
| **EDITOR_REGISTERING** | Editor sta registrando il primo canale | registra canale, verifica admin |
| **EDITOR_ACTIVE** | Editor attivo, può mettere canali in marketplace | create listing, view orders, accept/reject orders |
| **ADVERTISER_REGISTERING** | Advertiser sta caricando credito iniziale | deposit, add payment method |
| **ADVERTISER_ACTIVE** | Advertiser attivo, può cercare e acquistare | browse catalog, create orders, track campaigns |
| **SUSPENDED** | Utente sospeso (violazioni) | nessuna (solo contatta support) |

### Transitions & Business Rules

```python
# Transizione NEW_USER → EDITOR_REGISTERING
user.role = UserRole.editor
user.state = UserState.editor_registering
# Action: Mostra "Registra Primo Canale"

# Transizione EDITOR_REGISTERING → EDITOR_ACTIVE
if admin_verified_channel:
    user.state = UserState.editor_active
    channel.state = ChannelState.active
    notify_editor("Canale verificato! Ora puoi ricevere ordini")

# Transizione ADVERTISER_ACTIVE → SUSPENDED
if dispute_count > 2 or fraud_detected:
    user.is_suspended = True
    user.suspended_reason = "Troppe dispute / frode rilevata"
    user.suspended_until = now() + 30_days
    notify_user_suspend()
```

---

## 2. CHANNEL STATE MACHINE

**5 Stati Possibili:**

```
            ↓ (editor crea listing)
PENDING_REVIEW
    ↓ (admin approva)
ACTIVE ←─ (from SUSPENDED if appeal approved)
    ↓ (editor sospende)
INACTIVE
    ↓ (violation detected)
SUSPENDED
    ↓ (editor can appeal)
```

### State Details

| State | Description | Allowed Orders? |
|-------|-------------|-----------------|
| **PENDING_REVIEW** | Admin non ha ancora verificato admin ownership | ❌ No |
| **ACTIVE** | Disponibile nel marketplace | ✅ Yes |
| **INACTIVE** | Editor ha rimosso voluntariamente | ❌ No |
| **SUSPENDED** | Sospeso per violazioni (fake subs, spam) | ❌ No |
| **DISPUTED** | In contestazione | ❌ No (can't accept new orders) |

### Transitions

```python
# Editor registra canale
channel.state = ChannelState.pending_review
channel.owner = editor
# Admin verifica
admin_verify_channel(channel_id):
    channel.state = ChannelState.active
    channel.admin_verified_at = now()
    notify_editor("✅ Canale approvato!")

# Se rilevate fake subscribers
if check_fake_subscribers(channel_id) > 0.2:
    channel.state = ChannelState.suspended
    channel.suspended_reason = "Fake subscribers rilevati"
    notify_editor("⚠️ Canale sospeso per qualità insufficiente")
```

---

## 3. ORDER STATE MACHINE

**7 Stati Possibili:**

```
DRAFT (inserzionista prepara contenuto)
    ↓ (clicca "Crea Ordine")
PENDING_EDITOR_CONFIRMATION (scadenza: 30 min)
    ├─→ CONFIRMED (editor accetta)
    │       ↓ (editor pubblica)
    │   PUBLISHED (timer avviato)
    │       ↓ (scadenza raggiunta)
    │   COMPLETED (pagamento inviato)
    │
    ├─→ CANCELLED (editor rifiuta, or timeout 30 min)
    │
    └─→ DISPUTED (disputa aperta)
```

### State Details

| State | Description | Next Transition | Timeout |
|-------|-------------|-----------------|---------|
| **DRAFT** | Inserzionista sta preparando l'ordine | → PENDING_EDITOR_CONFIRMATION on /create | - |
| **PENDING_EDITOR_CONFIRMATION** | In attesa editor | → CONFIRMED or CANCELLED | 30 min auto-cancel |
| **CONFIRMED** | Editor ha accettato | → PUBLISHED on publication | - |
| **PUBLISHED** | Post online, timer attivo | → COMPLETED on expiry | 6/12/24h |
| **COMPLETED** | Ordine completato, pagamento processato | FINAL | - |
| **DISPUTED** | Disputa aperta, in attesa admin | → COMPLETED or CANCELLED | 7 days |
| **CANCELLED** | Cancellato da utente o auto-cancel | FINAL | - |

### Transitions with Business Logic

```python
# 1. Inserzionista crea ordine
order = MarketplaceOrder(
    buyer_id=advertiser_id,
    seller_id=editor_id,
    channel_id=channel_id,
    price=price,
    duration_hours=24,
    status=OrderState.pending_editor_confirmation,
    created_at=now()
)
# → Notifica editor

# 2. Se editor non risponde entro 30 min
if order.created_at + 30_minutes < now():
    order.status = OrderState.cancelled
    refund_advertiser(order)
    # Auto-cancel, notifica advertiser

# 3. Editor accetta
order.status = OrderState.confirmed
order.confirmed_at = now()
# → Notifica advertiser "Editore ha accettato, invia contenuto"

# 4. Advertiser invia contenuto, editor pubblica
order.status = OrderState.published
order.published_at = now()
order.expires_at = now() + duration_hours
# → Notifica advertiser "Promo online!"

# 5. Scadenza raggiunta
if now() > order.expires_at:
    order.status = OrderState.completed
    order.completed_at = now()
    # Processa pagamento
    seller_earn, platform_fee = PaymentProcessor.calculate_split(order.price)
    update_wallet(order.seller_id, +seller_earn)
    update_wallet(PLATFORM_ACCOUNT, +platform_fee)
    # Notifica entrambi

# 6. Disputa aperta (in qualsiasi momento prima di COMPLETED)
if advertiser.open_dispute(order_id, reason):
    order.status = OrderState.disputed
    # Notifica admin
```

---

## 4. DATABASE SCHEMA - FOREIGN KEYS & RELATIONSHIPS

### Users & Profiles
```
users (id, role, state, reputation_score, is_suspended)
    ├─→ editor_profiles (user_id, orders_received, earnings_total)
    ├─→ advertiser_profiles (user_id, orders_placed, risk_level)
    └─→ reputation_scores (user_id, score_change, reason)
```

### Marketplace
```
channels (id, state, owner_id, category, subscribers, reach_24h)
    ├─→ channel_listings (id, channel_id, user_id, price, is_active)
    │       └─→ marketplace_orders (id, channel_listing_id, ...)
    │
    └─→ channel_metrics (id, channel_id, subscribers, reach_24h)
```

### Payments & Transactions
```
marketplace_orders (id, seller_id, buyer_id, price, status)
    ├─→ payments (id, order_id, amount, status)
    │       └─→ money_transactions (id, payment_id, type, amount)
    │
    └─→ dispute_tickets (id, order_id, initiator_id, status)
```

### Audit
```
audit_logs (id, user_id, action, details, timestamp)
    └─ Registra OGNI azione importante
```

---

## 5. ACTION MATRIX - CHI PUÒ FARE COSA

### Editor (chi vende spazio pubblicitario)

| Action | State | Preconditions | Effect |
|--------|-------|---------------|--------|
| Registra Canale | EDITOR_REGISTERING | Ha admin perms | Channel → PENDING_REVIEW |
| Vedi Catalogo Ordini | EDITOR_ACTIVE | Almeno 1 canale active | Mostra pending orders |
| Accetta Ordine | EDITOR_ACTIVE | Order.status = PENDING | Order → CONFIRMED |
| Rifiuta Ordine | EDITOR_ACTIVE | Order.status = PENDING | Order → CANCELLED |
| Pubblica Promo | EDITOR_ACTIVE | Order.status = CONFIRMED | Order → PUBLISHED, timer starts |
| Rimuovi Promo | EDITOR_ACTIVE | Order.status = PUBLISHED | Editor marks as removed |
| Apri Disputa | EDITOR_ACTIVE | Order.status ≥ CONFIRMED | Order → DISPUTED |

### Advertiser (chi compra spazio)

| Action | State | Preconditions | Effect |
|--------|-------|---------------|--------|
| Sfoglia Catalogo | ADVERTISER_ACTIVE | Credito > 0 | Mostra ChannelListings con filtri |
| Crea Ordine | ADVERTISER_ACTIVE | Credito ≥ price | Order → PENDING_EDITOR_CONFIRMATION |
| Carica Contenuto | ADVERTISER_ACTIVE | Order.status = CONFIRMED | Stores content_text + media |
| Apri Disputa | ADVERTISER_ACTIVE | Order.status ≥ PUBLISHED | Order → DISPUTED |
| Ritira Guadagni | EDITOR_ACTIVE | Earnings > 0 | Withdrawal request |

### Admin (noi)

| Action | Targets | Effect |
|--------|---------|--------|
| Approva Canale | PENDING_REVIEW channel | Channel → ACTIVE |
| Sospendi Canale | ACTIVE channel | Channel → SUSPENDED |
| Sospendi Utente | Any user | User → SUSPENDED |
| Override Prezzo | Listing | Update price, log action |
| Risolvi Disputa | DISPUTED order | Decide refund, close ticket |
| Rilascia Fondi Escrow | Completed order | Move payment from escrow to wallet |

---

## 6. NOTIFICATION STRATEGY

### Bidirectional Notifications

Ogni cambio di stato trigger notifiche:

```python
# Quando ORDER → PENDING_EDITOR_CONFIRMATION
notify_editor(
    editor_id,
    "📩 Nuovo ordine!\n"
    f"Canale: {order.channel.title}\n"
    f"Prezzo: €{order.price}\n"
    f"Durata: {order.duration_hours}h\n\n"
    "Decidi entro 30 minuti",
    buttons=[Accept, Reject, ViewDetails]
)

# Quando ORDER → CONFIRMED
notify_advertiser(
    advertiser_id,
    "✅ Editore ha accettato!\n"
    f"Canale: {order.channel.title}\n\n"
    "Carica il tuo contenuto",
    buttons=[UploadContent]
)

# Quando ORDER → PUBLISHED
notify_advertiser(
    advertiser_id,
    "🎉 Promo online nel canale {channel}!\n"
    f"Visibile fino a: {order.expires_at}\n"
    f"Link: {post_link}",
    buttons=[ViewStats]
)

# Quando ORDER → COMPLETED
notify_editor(
    editor_id,
    f"💰 Guadagno ricevuto!\n"
    f"Importo: €{seller_earn:.2f}",
    buttons=[ViewWallet, WithdrawFunds]
)

notify_advertiser(
    advertiser_id,
    f"✨ Campagna completata!\n"
    f"Iscritti generati: {order.new_subscribers}\n"
    f"Costo per iscritto: €{cps:.2f}",
    buttons=[ViewStats, NewCampaign]
)
```

### Notification Channels
- **Telegram**: In-app messages + buttons
- **Email**: Daily digest (opzionale)
- **Dashboard**: Interno al bot con /analytics

---

## 7. SCHEDULED TASKS

```
Every 6 hours:
  └─ Update all active channel metrics (subscribers, reach_24h)

Every 30 minutes:
  └─ Check expired PUBLISHED orders → auto-transition to COMPLETED

Every 15 minutes:
  └─ Check PENDING orders with timeout >30 min → auto-cancel

Every 24 hours:
  ├─ Recalculate price suggestions for all channels
  ├─ Generate editor performance reports
  └─ Process any withdrawals

Every 7 days:
  └─ Auto-resolve old disputes (no activity)
```

---

## 8. ERROR HANDLING & VALIDATION

### Pre-Order Creation Validation

```python
def can_create_order(advertiser_id, channel_id):
    # 1. Advertiser must be ADVERTISER_ACTIVE
    advertiser = get_user(advertiser_id)
    if advertiser.state != UserState.advertiser_active:
        return False, "Profilo non attivo"
    
    # 2. Advertiser must have sufficient credits
    if advertiser.wallet < order_price:
        return False, "Credito insufficiente"
    
    # 3. Channel must be ACTIVE
    channel = get_channel(channel_id)
    if channel.state != ChannelState.active:
        return False, "Canale non disponibile"
    
    # 4. No duplicate orders (check PENDING/CONFIRMED/PUBLISHED)
    existing = get_active_orders(channel_id)
    if existing:
        return False, "Ordine già in corso su questo canale"
    
    # 5. Editor must not be SUSPENDED
    editor = channel.owner
    if editor.is_suspended:
        return False, "Editore non disponibile"
    
    # 6. Content must pass validation
    if not ContentValidator.validate(content_text):
        return False, "Contenuto non conforme"
    
    return True, "OK"
```

---

## 9. FILE STRUCTURE

```
adsbot/
├── models.py                    # Enums + 15 SQLAlchemy models
├── services.py                  # Business logic (PriceCalculator, etc)
├── bot.py                       # Telegram handlers + state machine logic
├── db.py                        # Database session management
├── config.py                    # Configuration
└── (existing files)

Root/
├── migrate_marketplace_v2.py    # Database migration script
├── MARKETPLACE_SPEC.md          # Specification (this was created earlier)
└── ARCHITECTURE.md              # This file
```

---

## 10. EXAMPLE FLOW: COMPLETE ORDER LIFECYCLE

```
T+0min: ADVERTISER creates order
  ├─ Advertiser.state = ADVERTISER_ACTIVE
  ├─ Order.status = DRAFT
  └─ User fills: duration (24h), content (testo+media)

T+0min: Order validated
  ├─ ContentValidator.validate(content_text) ✓
  ├─ Order price deducted from wallet (ESCROW)
  ├─ Order.status → PENDING_EDITOR_CONFIRMATION
  └─ Notify EDITOR

T+5min: EDITOR accepts order
  ├─ Order.status → CONFIRMED
  ├─ Notify ADVERTISER "Invia contenuto finale"
  └─ Content can be modified until publication

T+30min: EDITOR publishes post
  ├─ Order.status → PUBLISHED
  ├─ Order.published_at = now()
  ├─ Order.expires_at = now() + 24h
  ├─ Timer started
  └─ Notify ADVERTISER "Promo online!"

T+24h: Expiry reached, auto-complete
  ├─ Order.status → COMPLETED
  ├─ Order.completed_at = now()
  ├─ seller_earn, platform_fee = PaymentProcessor.split(price)
  ├─ Editor.wallet += seller_earn
  ├─ Platform.wallet += platform_fee
  ├─ Notify EDITOR "€X guadagnato!"
  ├─ Notify ADVERTISER "Campagna completata"
  └─ Order archived

OR Alternative at any point:

T+Xmin: DISPUTE opened
  ├─ Order.status → DISPUTED
  ├─ DisputeTicket created
  ├─ Funds held in ESCROW
  ├─ Admin notified
  ├─ Evidence collected from both parties
  └─ Admin decides → refund/keep/split

T+7days: Auto-resolve old disputes
  ├─ If no activity
  └─ Decision: default to refund advertiser
```

---

## 11. SECURITY CONSIDERATIONS

✅ **Implemented:**
- Escrow payment system (funds held until completion)
- Role-based access control (editor vs advertiser vs admin)
- Content validation (anti-spam, anti-scam)
- Dispute resolution mechanism
- Admin audit logs for every action
- Reputation scoring to flag high-risk users

⚠️ **TODO:**
- Admin verification of channel ownership (before accepting orders)
- Rate limiting on order creation
- IP logging for fraud detection
- Email verification for wallet withdrawals
- 2FA for admin actions

---

**Last Updated:** 2025-12-05  
**Version:** 2.0 - Complete State Machine Architecture
