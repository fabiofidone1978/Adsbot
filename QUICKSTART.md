# 🚀 Quick Start Guide - Adsbot Advanced Features

## 5-Minute Setup

### 1. Verify Installation ✅
```bash
cd "D:\Documents and Settings\fabio-fidone\My Documents\Adsbot"
python -m py_compile adsbot/bot.py adsbot/payments.py adsbot/notifications.py adsbot/telegram_metrics.py
# Should complete without errors
```

### 2. Run Tests ✅
```bash
python test_integration.py
# Should see: ✓ ALL TESTS PASSED
```

### 3. Start Bot 🎬
```bash
# Set your bot token
set BOT_TOKEN=your_telegram_bot_token

# Run the bot
python main.py
# Bot will be polling for messages
```

### 4. Test Purchase Flow 🛒
In Telegram:
1. Send `/start`
2. Click "🛒 Acquista"
3. Click "Crea Campagna"
4. Select a channel
5. Enter campaign name (e.g., "Test Ad")
6. Enter budget (e.g., "25.00")
7. Choose payment provider (Stripe/PayPal)
8. See transaction confirmation

---

## Configuration

### Essential
```bash
set BOT_TOKEN=your_real_telegram_bot_token_here
```

### Optional (for Real Payments)
```bash
# Stripe
set STRIPE_API_KEY=sk_test_YOUR_KEY_HERE

# PayPal
set PAYPAL_CLIENT_ID=YOUR_CLIENT_ID
set PAYPAL_CLIENT_SECRET=YOUR_SECRET
set PAYPAL_MODE=sandbox
```

---

## File Guide

| File | Purpose | Size |
|------|---------|------|
| `adsbot/bot.py` | Main bot handler | 1300+ |
| `adsbot/payments.py` | Payment processing | 180 |
| `adsbot/notifications.py` | Notifications | 170 |
| `adsbot/telegram_metrics.py` | Metrics | 90 |
| `test_integration.py` | Integration tests | 284 |

---

## Common Commands

```bash
# Verify code
python -m py_compile adsbot/*.py

# Run tests
python test_integration.py

# Start bot
python main.py

# Check Python version
python --version
```

---

## What's Included

✅ **Payments**: Stripe + PayPal support
✅ **Metrics**: Real Telegram API integration
✅ **Notifications**: 8 notification types
✅ **Purchases**: Complete buyer/seller flow
✅ **Transactions**: Automatic commission (80/20)
✅ **Tests**: 100% passing

---

## Next Steps

1. **Read** `IMPLEMENTATION_COMPLETE.md` for full overview
2. **Reference** `INTEGRATION_GUIDE.md` for API details
3. **Deploy** `DEPLOYMENT_READY.md` when ready
4. **Test** `TEST_GUIDE.md` for manual testing

---

## Support

- Questions? Check docstrings in code
- Integration help? See `INTEGRATION_GUIDE.md`
- Deployment? See `DEPLOYMENT_READY.md`
- Changes? See `CHANGELOG.md`

---

**Ready to go! 🎉**
