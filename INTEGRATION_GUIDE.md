# Inside Ads Integration Guide

## Overview

Questa guida fornisce una panoramica completa dei nuovi sistemi integrati nel bot Adsbot: pagamenti reali, metriche Telegram, notifiche e flusso di acquisto campagne.

## 1. Sistema di Pagamenti (`adsbot/payments.py`)

### Supporto per Provider

- **Stripe**: Pagamenti tramite carte di credito
- **PayPal**: Pagamenti tramite conto PayPal

### Configurazione

Aggiungi al `.env`:

```env
STRIPE_API_KEY=sk_test_your_stripe_key
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_secret
PAYPAL_MODE=sandbox
```

### Utilizzo

```python
from adsbot.payments import PaymentProcessor

processor = PaymentProcessor()

# Stripe
result = processor.process_payment(
    provider="stripe",
    amount=5000,  # cents
    currency="usd",
    description="Campaign: My Ad",
    customer_email="user@example.com"
)

# PayPal
result = processor.process_payment(
    provider="paypal",
    amount=50,  # dollars
    currency="USD",
    description="Campaign: My Ad",
    return_url="https://yoursite.com/success",
    cancel_url="https://yoursite.com/cancel"
)
```

## 2. Sistema di Notifiche (`adsbot/notifications.py`)

### Tipi di Notifiche

- `CAMPAIGN_PURCHASED`: Campagna acquistata con successo
- `CAMPAIGN_EARNED`: Guadagni da una campagna
- `PAYMENT_RECEIVED`: Pagamento confermato
- `PAYMENT_FAILED`: Pagamento fallito
- `WITHDRAWAL_SUCCESS`: Prelievo completato
- `WITHDRAWAL_FAILED`: Prelievo fallito
- `NEW_OFFER`: Nuova offerta ricevuta
- `OFFER_ACCEPTED`: Offerta accettata

### Utilizzo

```python
from adsbot.notifications import NotificationDispatcher, NotificationType

dispatcher = NotificationDispatcher(bot)

await dispatcher.send_notification(
    user_id=12345,
    notification_type=NotificationType.CAMPAIGN_PURCHASED,
    data={
        "campaign_name": "My Campaign",
        "channel_handle": "mychannel",
    }
)
```

### Preferenze Notifiche

```python
from adsbot.notifications import NotificationPreferences

prefs = NotificationPreferences()

# Disabilita specifico tipo di notifica
prefs.set_preference(user_id, NotificationType.CAMPAIGN_PURCHASED, False)

# Abilita/disabilita tutte
prefs.toggle_all(user_id, True)
```

## 3. Metriche Telegram Real-Time (`adsbot/telegram_metrics.py`)

### Configurazione

Il bot utilizza il token Telegram automaticamente per raccogliere metriche reali.

### Utilizzo

```python
from adsbot.telegram_metrics import TelegramMetricsCollector

collector = TelegramMetricsCollector(bot)

# Ottenere numero di membri
members = await collector.get_channel_member_count("@mychannel")

# Informazioni canale complete
info = await collector.get_channel_info("@mychannel")
# {
#     "id": -1001234567890,
#     "title": "My Channel",
#     "members": 10000,
#     "description": "...",
#     "type": "supergroup"
# }

# Verificare se utente è membro
status = await collector.get_user_member_status("@mychannel", user_id)

# Metriche stimate per campagna
metrics = await collector.estimate_channel_metrics("@mychannel", advertiser_id)
# {
#     "members": 10000,
#     "user_is_member": True,
#     "estimated_reach": 6000,  # 60% engagement
#     "is_channel": True
# }
```

## 4. Flusso di Acquisto Campagne

### Flow Conversation

```
insideads:buy → insideads_buy_menu
    ↓
insideads:buy:create → purchase_campaign_start
    ↓
SELECT_CAMPAIGN: Scegli canale
    ↓
ENTER_AMOUNT: Inserisci nome e budget campagna
    ↓
SELECT_PAYMENT_PROVIDER: Scegli Stripe/PayPal
    ↓
CONFIRM_PAYMENT: Processa pagamento
    ↓
Notifica al buyer e seller → Menu principale
```

### Stati Conversazione

```python
SELECT_CAMPAIGN = 14      # Scelta del canale
ENTER_AMOUNT = 15         # Inserimento budget
SELECT_PAYMENT_PROVIDER = 16  # Scelta provider
CONFIRM_PAYMENT = 17      # Processamento pagamento
```

### Handler Implementati

1. **`purchase_campaign_start`**: Mostra canali disponibili
2. **`purchase_campaign_select`**: Utente seleziona canale
3. **`purchase_campaign_amount`**: Utente inserisce budget
4. **`purchase_campaign_provider`**: Utente seleziona provider pagamento
5. **`purchase_campaign_confirm`**: Processa pagamento e registra transazione

### Flusso Transazioni

```
User balance check (ENTER_AMOUNT)
    ↓
Payment processing (CONFIRM_PAYMENT)
    ↓
Deduct from buyer balance
    ↓
Add to seller balance (80% commission)
    ↓
Send notifications
    ↓
Log transaction
```

## 5. Servizi Backend (`adsbot/inside_ads_services.py`)

### Funzioni Disponibili

```python
# Bilancio
get_or_create_balance(session, user) -> UserBalance
get_user_balance(session, user) -> UserBalance

# Transazioni
add_transaction(session, user, tx_type, amount, description, reference_id)
get_recent_transactions(session, user, days=30) -> list[Transaction]

# Campagne
get_user_campaigns(session, user) -> list[Campaign]
get_user_offers(session, user) -> list[PromoOffer]

# Acquisto
create_campaign_purchase(session, buyer, seller_channel, campaign_name, budget, duration_days)
list_available_channels_for_ads(session, min_subscribers=100) -> list[Channel]

# Statistiche
get_campaign_performance(session, campaign_id) -> dict
get_user_statistics(session, user) -> dict
record_metrics(session, campaign_id, followers, clicks, impressions)
get_channel_metrics(session, channel, days=7) -> dict
```

## 6. Integrazione Completa

### Esempio: Flusso di Acquisto Completo

```python
# 1. Utente clicca "🛒 Acquista"
await insideads_buy_menu(update, context)
# Mostra: "Crea Campagna", "Le mie campagne"

# 2. Utente clicca "Crea Campagna"
state = await insideads_buy_create(update, context)
# Avvia ConversationHandler, stato = SELECT_CAMPAIGN
# Mostra canali disponibili: @channel1, @channel2, ...

# 3. Utente seleziona @channel1
state = await purchase_campaign_select(update, context)
# stato = ENTER_AMOUNT
# Chiede: "Inserisci nome campagna"

# 4. Utente inserisce "MyAd"
state = await purchase_campaign_amount(update, context)
# stato = SELECT_PAYMENT_PROVIDER
# Chiede: "Qual è il budget?"

# 5. Utente inserisce "50.00"
state = await purchase_campaign_provider(update, context)
# Verifica saldo: OK
# stato = CONFIRM_PAYMENT
# Mostra provider: Stripe, PayPal

# 6. Utente seleziona Stripe
state = await purchase_campaign_confirm(update, context)
# Processa pagamento Stripe
# Deduce $50 dal buyer
# Aggiunge $40 al seller (80%)
# Invia notifiche
# Mostra: "✅ Campagna acquistata!"
# Return: ConversationHandler.END
```

## 7. Testing

### Test Pagamenti (Sandbox)

```bash
# Stripe test card
4242 4242 4242 4242 (any future expiry, any CVC)

# PayPal sandbox
Use account: sb-xxxxx@personal.example.com
```

### Test Flusso Acquisto

```
1. /start → Menu principale
2. Clicca "🛒 Acquista"
3. Clicca "Crea Campagna"
4. Scegli canale disponibile
5. Inserisci nome campagna (es: "Test Campaign")
6. Inserisci budget (es: "25.00")
7. Scegli payment provider (Stripe/PayPal)
8. Verifica notifica di acquisto
```

### Test Metriche

```python
# Nel handler, aggiungi:
metrics_collector = TelegramMetricsCollector(context.bot)
member_count = await metrics_collector.get_channel_member_count("@testchannel")
# Dovrebbe ritornare il valore reale
```

## 8. Troubleshooting

### Errore: "Payment provider not configured"
- Assicurati che STRIPE_API_KEY o PAYPAL_CLIENT_ID siano nel `.env`
- Verifica le credenziali

### Errore: "Channel not found for ads"
- Assicurati che il canale sia nel database
- Verifica che non sia stato eliminato

### Errore: "Insufficient balance"
- L'utente non ha abbastanza saldo
- Potrebbe aver bisogno di guadagnare prima di acquistare

### Notifiche non ricevute
- Verifica che il bot abbia il permesso di scrivere privati all'utente
- Controlla i log del bot

## 9. Prossimi Passi

- [ ] Integrare webhook per conferme pagamento real-time
- [ ] Implementare sistema di rating per canali/inserzionisti
- [ ] Aggiungere analytics dashboard
- [ ] Implementare withdrawal (prelievo fondi)
- [ ] Aggiungere affiliate system
- [ ] Creare API pubblica per integrazioni third-party

## 10. Architettura

```
adsbot/
├── bot.py                    # Main handlers e conversation flows
├── models.py                 # Database models (User, Channel, Campaign, etc.)
├── db.py                     # Session management
├── config.py                 # Configuration loading
├── services.py               # Original services
├── inside_ads_services.py    # New backend logic
├── payments.py               # Payment processor (Stripe, PayPal)
├── notifications.py          # Notification system
├── telegram_metrics.py       # Real Telegram metrics
└── __init__.py
```

## 11. API Reference

### PaymentProcessor.process_payment()

```python
def process_payment(
    provider: str,           # "stripe" or "paypal"
    amount: int,             # cents for Stripe, dollars for PayPal
    currency: str,           # "usd" or other ISO code
    description: str,        # Payment description
    customer_email: str,     # For Stripe receipts
    return_url: str = None,  # For PayPal redirect
    cancel_url: str = None   # For PayPal redirect
) -> dict | None:
    # Returns: {"status": "...", "payment_intent_id": "...", "approval_url": "..."}
```

### NotificationDispatcher.send_notification()

```python
async def send_notification(
    user_id: int,
    notification_type: NotificationType,
    data: dict
) -> bool:
    # Returns: True if sent successfully, False otherwise
```

### TelegramMetricsCollector.estimate_channel_metrics()

```python
async def estimate_channel_metrics(
    channel_username: str,
    user_id: int
) -> dict | None:
    # Returns: {
    #     "members": int,
    #     "user_is_member": bool,
    #     "estimated_reach": int,
    #     "is_channel": bool
    # }
```

---

**Last Updated**: 2024
**Version**: 2.0 (with payments, metrics, and notifications)
