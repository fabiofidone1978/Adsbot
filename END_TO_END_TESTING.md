# 🧪 END-TO-END TESTING PLAN

**Project:** ADSBOT Marketplace V2  
**Phase:** FASE 2 & FASE 3 Testing  
**Date:** December 5, 2025  
**Tester:** QA Team

---

## 📋 TEST SCENARIOS

### SCENARIO 1: Advertiser Orders a Post

**Preconditions:**
- Advertiser is registered and logged in
- At least 1 editor has registered a channel
- Advertiser has sufficient wallet balance

**Steps:**
1. Click "🛍️ Acquista Spazi Pubblicitari" (Buy Ad Spaces)
2. Click "🏪 Catalogo Inserzionista" (Advertiser Catalog)
3. **EXPECTED:** See list of available channels with prices
4. Click "🔍 Modifica Filtri" (Modify Filters)
5. Set category = "Crypto", max_price = 50
6. **EXPECTED:** Filtered list shows only crypto channels with price ≤ 50
7. Click on a channel to view details
8. **EXPECTED:** See channel info: handle, subscribers, reach, price
9. Click "🛒 Crea Ordine" (Create Order)
10. **EXPECTED:** Ask for duration (6, 12, 24 hours)
11. Select 24 hours
12. **EXPECTED:** Ask for content (text/photo/video)
13. Send content: "Check out our new app!"
14. **EXPECTED:** Show review screen with order details
15. Review order and click "✅ Conferma Ordine" (Confirm Order)
16. **EXPECTED:** 
    - Order created with ID
    - Payment processed (10% commission deducted)
    - Advertiser wallet updated
    - Editor receives notification

**Expected Result:** ✅ Order created, notifications sent

---

### SCENARIO 2: Editor Accepts Order

**Preconditions:**
- Order from Scenario 1 is pending
- Editor is logged in

**Steps:**
1. Editor receives notification: "📬 Nuovo Ordine in Sospeso"
2. **EXPECTED:** See order details with buttons:
   - ✅ Accetta (Accept)
   - ❌ Rifiuta (Reject)
   - 👁️ Visualizza Dettagli (View Details)
3. Click "✅ Accetta"
4. **EXPECTED:**
   - Order status → CONFIRMED
   - Payment status → CONFIRMED
   - Advertiser receives notification: "L'editore ha accettato il tuo ordine!"
   - Editor sees: "✅ Ordine Confermato! Status: CONFIRMED"

**Expected Result:** ✅ Order accepted, notifications sent to both parties

---

### SCENARIO 3: Editor Rejects Order

**Preconditions:**
- New order from advertiser (pending)
- Editor is logged in

**Steps:**
1. Editor receives order notification
2. Click "❌ Rifiuta" (Reject)
3. **EXPECTED:**
   - Order status → CANCELLED
   - Payment status → REFUNDED
   - MoneyTransaction created for refund audit
   - Advertiser wallet updated with refund
   - Advertiser receives notification: "❌ L'editore ha rifiutato il tuo ordine. Rimborso: €X.XX"
   - Editor sees: "✅ Ordine Rifiutato!"

**Expected Result:** ✅ Order rejected, refund processed, notifications sent

---

### SCENARIO 4: Editor Views Incoming Orders

**Preconditions:**
- Multiple pending orders exist
- Editor is logged in

**Steps:**
1. Click "📱 Miei Canali" or go to editor menu
2. Click "📬 Ordini in Sospeso" (Pending Orders)
3. **EXPECTED:**
   - List of pending orders (max 5)
   - Each order shows: ID, advertiser name, price, duration, content preview
4. Click on order to view full details
5. **EXPECTED:**
   - Full order information
   - Buttons: ✅ Accetta, ❌ Rifiuta, ◀️ Indietro

**Expected Result:** ✅ Orders list displayed correctly

---

### SCENARIO 5: Editor Views Order History

**Preconditions:**
- Editor has completed/rejected several orders
- Editor is logged in

**Steps:**
1. Go to editor menu
2. Click "📊 Storico Ordini" (Order History)
3. **EXPECTED:** See statistics:
   - 📈 Ordini Completati: X
   - 💰 Totale Guadagnato: €X.XX
   - 💵 Prezzo Medio: €X.XX
   - ✅ Tasso Completamento: X.X%
4. **EXPECTED:** Last 5 orders displayed with status (✅/❌/⚠️)

**Expected Result:** ✅ Statistics calculated correctly

---

### SCENARIO 6: Admin Approves Channel

**Preconditions:**
- Channel pending approval
- Admin is logged in

**Steps:**
1. Admin clicks "/admin" or accesses admin panel
2. Selects "✅ Approva Canali" (Approve Channels)
3. **EXPECTED:** See list of pending channels
4. Click "✅ Approva #123" for a channel
5. **EXPECTED:**
   - Channel state → ACTIVE
   - Admin audit log entry created
   - Channel becomes available for ordering

**Expected Result:** ✅ Channel approved, audit logged

---

### SCENARIO 7: Admin Views Platform Statistics

**Preconditions:**
- Multiple orders completed
- Admin is logged in

**Steps:**
1. Go to admin panel
2. Click "📊 Report Statistiche" (Statistics)
3. **EXPECTED:** See KPIs:
   - 👥 Utenti Totali: X
   - 📢 Canali Registrati: X
   - 📦 Ordini Totali: X
   - ✅ Ordini Completati: X (Y%)
   - 💰 Revenue Totale: €X.XX
   - 🏦 Commissione Platform: €X.XX (10%)

**Expected Result:** ✅ All calculations correct

---

### SCENARIO 8: Verify Channel Admin Before Registration

**Preconditions:**
- User attempting to register as editor
- User is NOT admin of specified channel

**Steps:**
1. User provides channel ID during registration
2. System calls bot.get_chat_member()
3. **EXPECTED:**
   - Verification fails (user is not admin)
   - Error message: "❌ Non sei amministratore del canale"
   - AdminAuditLog records failed verification

**Expected Result:** ✅ Non-admin rejected, verification logged

---

### SCENARIO 9: Payment Escrow Flow

**Preconditions:**
- Advertiser creates order for €50

**Steps:**
1. Order created: €50 charged to advertiser
2. **EXPECTED:**
   - Payment record created with status: PENDING
   - Funds held in escrow (not released)
   - Editor sees pending order notification
3. If editor accepts:
   - **EXPECTED:** Payment status → CONFIRMED
4. If editor rejects:
   - **EXPECTED:** Payment status → REFUNDED
   - Advertiser wallet receives €50 back

**Expected Result:** ✅ Escrow system working correctly

---

### SCENARIO 10: Order State Transitions

**Preconditions:**
- Track order through lifecycle

**Steps:**
1. Advertiser creates order
   - **EXPECTED:** Status = PENDING
2. Order sent to marketplace
   - **EXPECTED:** Status = PENDING (awaiting editor)
3. Editor receives notification
4. Editor accepts
   - **EXPECTED:** Status = CONFIRMED
5. After publication
   - **EXPECTED:** Status = PUBLISHED
6. After completion
   - **EXPECTED:** Status = COMPLETED

**Expected Result:** ✅ All state transitions atomic and logged

---

## 🔐 SECURITY TESTS

### Test 1: SQL Injection Prevention
**Steps:**
1. Try to filter catalog with SQL: `category = "crypto' OR '1'='1"`
2. **EXPECTED:** Query fails safely, no data leak

### Test 2: Admin Access Control
**Steps:**
1. Non-admin user tries to access /admin
2. **EXPECTED:** Access denied message

### Test 3: Channel Admin Verification
**Steps:**
1. Non-channel-admin tries to register as editor
2. **EXPECTED:** Registration blocked

### Test 4: Payment Tampering
**Steps:**
1. Try to modify order price in request
2. **EXPECTED:** Price retrieved from database, not from user input

---

## ⚡ PERFORMANCE TESTS

### Test 1: Catalog Query Performance
**Expected:** <500ms response time
- Load catalog with 1000+ channels
- Apply filters
- Verify pagination works

### Test 2: Order Creation Performance
**Expected:** <1s total time
- Complete 4-step order wizard
- Process payment
- Send notifications

### Test 3: Order History Aggregation
**Expected:** <1s response time
- Calculate statistics for 1000+ orders
- Verify accuracy of SUM/AVG/COUNT

### Test 4: Database Query Optimization
**Steps:**
1. Enable query logging
2. Create order and check queries
3. **EXPECTED:** No N+1 problems, all queries optimized

---

## 🐛 BUG TRACKING

### Template for Issues Found
```
**Title:** [Component] Brief description

**Steps to Reproduce:**
1. ...
2. ...

**Expected Result:**
...

**Actual Result:**
...

**Severity:** Critical / High / Medium / Low

**Assignee:** Developer name
```

---

## ✅ TEST PASS/FAIL CRITERIA

| Test Scenario | Pass | Fail | Notes |
|---|---|---|---|
| 1. Advertiser Orders Post | ✅ | ❌ | |
| 2. Editor Accepts Order | ✅ | ❌ | |
| 3. Editor Rejects Order | ✅ | ❌ | |
| 4. View Incoming Orders | ✅ | ❌ | |
| 5. View Order History | ✅ | ❌ | |
| 6. Admin Approves Channel | ✅ | ❌ | |
| 7. Admin Views Stats | ✅ | ❌ | |
| 8. Admin Verification | ✅ | ❌ | |
| 9. Payment Escrow | ✅ | ❌ | |
| 10. State Transitions | ✅ | ❌ | |
| SQL Injection | ✅ | ❌ | |
| Admin Access Control | ✅ | ❌ | |
| Channel Verification | ✅ | ❌ | |
| Payment Tampering | ✅ | ❌ | |
| Catalog Performance | ✅ | ❌ | |
| Order Performance | ✅ | ❌ | |
| History Performance | ✅ | ❌ | |
| Query Optimization | ✅ | ❌ | |

---

## 📊 TEST SUMMARY

**Total Tests:** 18  
**Passed:** ___  
**Failed:** ___  
**Skipped:** ___  
**Pass Rate:** ___%

**Overall Status:** ❌ FAILED / ⚠️ PARTIALLY PASSED / ✅ PASSED

---

## 👤 TESTER SIGN-OFF

**Tester Name:** ________________________  
**Date:** ________________________  
**Signature:** ________________________

**Issues Reported:** ____ (Critical: ____ | High: ____ | Medium: ____ | Low: ____)

**Ready for Deployment:** ❌ NO / ⚠️ CONDITIONAL / ✅ YES

**Deployment Conditions (if conditional):**
- _________________________________
- _________________________________

---

## 📝 NOTES

- All tests should be run in order (Scenario 1 → 10)
- Each test should start with clean database state
- Use test accounts for all testing
- Record all failures with screenshots
- Report issues with severity levels

---

**Testing Guide Version:** 1.0  
**Last Updated:** December 5, 2025
