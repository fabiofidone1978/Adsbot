# ⚡ ADSBOT MARKETPLACE V2 - QUICK REFERENCE CHEAT SHEET

**One-page reference for common tasks and patterns**

---

## 🎯 STATE MACHINE QUICK LOOKUP

### User States
```
NEW_USER → EDITOR_REGISTERING → EDITOR_ACTIVE
        → ADVERTISER_REGISTERING → ADVERTISER_ACTIVE
                                           ↓
                                      SUSPENDED
```

### Channel States
```
PENDING_REVIEW → ACTIVE → (in marketplace)
              → SUSPENDED (violations)
              → INACTIVE (removed)
              → DISPUTED (in contest)
```

### Order States
```
DRAFT → PENDING_EDITOR_CONFIRMATION (30 min timeout)
          ├→ CONFIRMED → PUBLISHED (6/12/24h) → COMPLETED
          ├→ CANCELLED
          └→ DISPUTED
```

---

## 💾 DATABASE QUICK LOOKUP

### Foreign Keys Pattern
```python
# New order
order = MarketplaceOrder(
    seller_id=editor.id,        # FK → users
    buyer_id=advertiser.id,      # FK → users
    channel_id=channel.id,       # FK → channels
    channel_listing_id=listing.id # FK → channel_listings
)

# Payment
payment = Payment(
    order_id=order.id,  # FK → marketplace_orders
    amount=100.0
)

# Dispute
dispute = DisputeTicket(
    order_id=order.id,      # FK → marketplace_orders
    initiator_id=user.id    # FK → users
)
```

### Common Queries
```python
# All active listings
listings = session.query(ChannelListing).filter_by(is_active=True).all()

# Editor's pending orders
orders = session.query(MarketplaceOrder)\
    .filter_by(seller_id=editor_id, status=OrderState.pending_editor_confirmation)

# High-risk advertisers
risky = session.query(AdvertiserProfile).filter_by(risk_level="high")

# Open disputes
disputes = session.query(DisputeTicket).filter_by(status=DisputeStatus.open)

# Audit log for user
logs = session.query(AuditLog).filter_by(user_id=user_id).order_by(AuditLog.created_at.desc())
```

---

## 🔧 SERVICE CALLS - COPY-PASTE SNIPPETS

### Calculate Price
```python
from adsbot.services import PriceCalculator

# Scenario: 100k subscribers crypto channel
reach = PriceCalculator.calculate_reach_estimate(100000)  # 20k
price, min_p, max_p = PriceCalculator.suggest_price(
    reach_24h=reach,
    category="crypto",
    quality_score=0.8,
    conversion_rate=1.0
)
# price ≈ €10.00, min ≈ €8.00, max ≈ €12.00

# Verify fairness
is_fair, msg = PriceCalculator.is_price_fair(proposed_price=15, suggested_price=10)
# is_fair = False, msg = "Prezzo sovraprezzato..."
```

### Validate Content
```python
from adsbot.services import ContentValidator

result = ContentValidator.validate(
    text="Click here for free money!!!!! 🎉🎉🎉",
    media_urls=["https://bit.ly/abc123"],
    strict=True  # Harsh validation
)
# (False, "Parola vietata: 'click here'")

# Non-strict validation (more lenient)
result = ContentValidator.validate(text, urls, strict=False)
# May pass same content
```

### Update Reputation
```python
from adsbot.services import ReputationManager

# After completing order
user.reputation_score = ReputationManager.apply_adjustment(
    current_score=user.reputation_score,
    factor_name="order_completed"  # +0.2
)

# After losing dispute
user.reputation_score = ReputationManager.apply_adjustment(
    user.reputation_score,
    factor_name="dispute_lost"  # -0.5
)

# Admin override
user.reputation_score = ReputationManager.apply_adjustment(
    user.reputation_score,
    factor_name="any_reason",
    admin_override=4.5  # Force to 4.5
)

# Get display label
label = ReputationManager.get_rating_label(user.reputation_score)
# "⭐⭐⭐⭐ Molto buono"
```

### Calculate Payment Split
```python
from adsbot.services import PaymentProcessor

# Order price: €100
seller_amount, platform_fee = PaymentProcessor.calculate_split(100)
# seller_amount = 90.00, platform_fee = 10.00

# Custom commission rate (if needed)
seller_amount, fee = PaymentProcessor.calculate_split(100, commission_rate=0.15)  # 15%
# seller_amount = 85.00, fee = 15.00
```

---

## 🎬 STATE TRANSITION PATTERNS

### Editor Accepts Order
```python
# Before: Order.status = PENDING_EDITOR_CONFIRMATION
order.status = OrderState.confirmed
order.confirmed_at = datetime.utcnow()
channel_listing.is_available = False  # Block new orders
session.add(order)
session.add(channel_listing)
session.commit()

# Notify advertiser
# await notify_advertiser(order.buyer_id, "Editore ha accettato!")
```

### Order Expires
```python
if now() > order.expires_at:
    order.status = OrderState.completed
    order.completed_at = now()
    
    # Release payment
    seller_earn, platform_fee = PaymentProcessor.calculate_split(order.price)
    
    # Update wallets
    update_user_balance(order.seller_id, +seller_earn)
    update_user_balance(PLATFORM_ACCOUNT_ID, +platform_fee)
    
    # Log transaction
    log_transaction(order.seller_id, "earn", seller_earn, order.id)
    log_transaction(PLATFORM_ACCOUNT_ID, "commission", platform_fee, order.id)
    
    # Update editor stats
    editor_profile.orders_completed += 1
    editor_profile.earnings_total += seller_earn
    
    session.commit()
```

### Open Dispute
```python
dispute = DisputeTicket(
    order_id=order.id,
    initiator_id=user_id,
    initiator_role="editor" if user_id == order.seller_id else "advertiser",
    description="Post non era visibile / Contenuto non conforme",
    status=DisputeStatus.open,
)
order.status = OrderState.disputed
session.add(dispute)
session.add(order)
session.commit()

# Notify admin
# send_admin_alert(f"Disputa aperta: ordine {order.id}")
```

---

## 🔍 COMMON VALIDATIONS

### Can Create Order?
```python
def can_create_order(advertiser_id, channel_id):
    advertiser = get_user(advertiser_id)
    channel = get_channel(channel_id)
    listing = session.query(ChannelListing).filter_by(channel_id=channel_id).first()
    
    # 1. Advertiser active
    if advertiser.state != UserState.advertiser_active:
        return False, "Profilo non attivo"
    
    # 2. Has credits
    if get_balance(advertiser_id) < listing.price:
        return False, "Credito insufficiente"
    
    # 3. Channel active
    if channel.state != ChannelState.active:
        return False, "Canale non disponibile"
    
    # 4. No duplicate
    existing = session.query(MarketplaceOrder).filter(
        MarketplaceOrder.channel_id == channel_id,
        MarketplaceOrder.status.in_([
            OrderState.pending_editor_confirmation,
            OrderState.confirmed,
            OrderState.published
        ])
    ).first()
    if existing:
        return False, "Ordine già in corso"
    
    # 5. Editor not suspended
    if channel.owner.is_suspended:
        return False, "Editore non disponibile"
    
    return True, "OK"
```

### Can Accept Order?
```python
def can_accept_order(order_id, editor_id):
    order = session.query(MarketplaceOrder).get(order_id)
    
    # 1. Order is pending
    if order.status != OrderState.pending_editor_confirmation:
        return False, "Ordine non è pending"
    
    # 2. User is seller
    if order.seller_id != editor_id:
        return False, "Non sei il venditore"
    
    # 3. User is active editor
    user = get_user(editor_id)
    if user.state != UserState.editor_active:
        return False, "Profilo non attivo"
    
    # 4. Not yet expired (30 min)
    if now() > order.created_at + timedelta(minutes=30):
        return False, "Timeout scaduto"
    
    return True, "OK"
```

---

## 📊 QUICK STATS

### Editor Dashboard
```python
profile = editor.editor_profile
stats = {
    "orders_received": profile.orders_received,
    "completion_rate": profile.completion_rate,  # 0-1
    "earnings_total": profile.earnings_total,
    "reputation": f"{editor.reputation_score:.1f}⭐",
    "earnings_this_month": profile.earnings_month,
}
```

### Advertiser Dashboard
```python
profile = advertiser.advertiser_profile
stats = {
    "orders_placed": profile.orders_placed,
    "completion_rate": profile.completion_rate,
    "total_spent": profile.total_spent,
    "cost_per_subscriber": profile.cost_per_subscriber,
    "roi_average": f"{profile.roi_average:.1f}%",
    "reputation": f"{advertiser.reputation_score:.1f}⭐",
}
```

---

## 🚨 ERROR MESSAGES

### To User
```python
"❌ Profilo non attivo (completa la registrazione)"
"❌ Credito insufficiente (carica €X più)"
"❌ Canale non disponibile"
"❌ Ordine già in corso su questo canale"
"❌ Editore non disponibile"
"❌ Timeout scaduto (editore non ha risposto)"
```

### To Dev (Logging)
```python
logger.error(f"Order {order_id} transition failed: {reason}")
logger.warning(f"High-risk user {user_id} detected: {risk_level}")
logger.info(f"Dispute #{ticket_id} opened by {initiator_id}")
```

---

## 📚 FILE LOCATIONS

| What | Where |
|------|-------|
| **Models** | `adsbot/models.py` line 1-550 |
| **Services** | `adsbot/services.py` line 120-350 |
| **Enums** | `adsbot/models.py` line 1-100 |
| **State Flows** | `ARCHITECTURE.md` section 1-3 |
| **Requirements** | `MARKETPLACE_SPEC.md` |
| **Examples** | `DOCUMENTATION_INDEX.md` usage section |

---

## ⚡ COPY-PASTE IMPORTS

```python
# Models & Enums
from adsbot.models import (
    User, Channel, UserState, ChannelState, OrderState,
    EditorProfile, AdvertiserProfile,
    Payment, MoneyTransaction,
    DisputeTicket, AuditLog,
    ChannelListing, MarketplaceOrder
)

# Services
from adsbot.services import (
    PriceCalculator,
    ContentValidator,
    ReputationManager,
    PaymentProcessor,
    format_currency
)

# Database
from adsbot.db import create_session_factory
from adsbot.config import Config

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
```

---

**Last Updated:** 2025-12-05  
**Format:** Quick Reference  
**Use:** Copy-paste for common patterns
