USER ACCEPTANCE TESTING (UAT) SCRIPT
====================================

## UAT VERSION 1.0
## Date: 2024-12-27
## Scope: FASE 1-7 Complete Feature Testing
## Duration: ~8 hours

---

# SECTION 1: PRELIMINARY SETUP (30 minutes)

## 1.1 Environment Verification

| # | Test Case | Expected Result | Status | Notes |
|---|-----------|-----------------|--------|-------|
| 1.1.1 | Python 3.13 installed | `python --version` returns 3.13.x | ☐ | Command: `python --version` |
| 1.1.2 | Virtual environment active | `.venv\Scripts\activate.bat` works | ☐ | Windows: `cd d:\Documents and Settings\fabio-fidone\My Documents\Adsbot && .venv\Scripts\activate.bat` |
| 1.1.3 | All dependencies installed | `pip list` shows all packages | ☐ | Command: `pip install -r requirements.txt` |
| 1.1.4 | Database initialized | `adsbot.db` exists with 20 tables | ☐ | Check file size > 1MB |
| 1.1.5 | Config file present | `adsbot/config.py` has all secrets | ☐ | Verify TELEGRAM_TOKEN, OPENAI_API_KEY set |
| 1.1.6 | No syntax errors | `python -m py_compile adsbot/*.py` passes | ☐ | Command: py_compile all .py files |
| 1.1.7 | Requirements met | All imports work: `python -c "from adsbot.bot import *"` | ☐ | Should run without error |

**Tester:** ________________  **Date:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 2: DATABASE VERIFICATION (45 minutes)

## 2.1 Table Existence Check

| Table Name | Rows | Status | Notes |
|------------|------|--------|-------|
| User | - | ☐ | Should have test user seeded |
| Channel | - | ☐ | Should have sample channels |
| Campaign | - | ☐ | Should be empty initially |
| MarketplaceOrder | - | ☐ | Should be empty initially |
| Payment | - | ☐ | Should be empty initially |
| Notification | - | ☐ | Should track sent notifications |
| CampaignAnalytics | - | ☐ | Analytics data structure |
| ScheduledTask | - | ☐ | Should have scheduled jobs |
| DisputeTicket | - | ☐ | Dispute management |
| ChannelListing | - | ☐ | Channel marketplace |
| ChannelRating | - | ☐ | Channel ratings |
| RiskScore | - | ☐ | User risk assessment |
| VerificationRecord | - | ☐ | User verification status |
| AIGeneratedContent | - | ☐ | AI content cache |
| ContentTemplate | - | ☐ | Content templates |
| RateLimitRecord | - | ☐ | Rate limiting data |
| UserSettings | - | ☐ | User preferences |
| AdminLog | - | ☐ | Admin actions log |
| SystemMetric | - | ☐ | Performance metrics |
| WebhookEvent | - | ☐ | Webhook events log |

**Test Command:**
```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
```

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 2.2 Sample Data Seeding

| # | Test Case | Expected Result | Status |
|---|-----------|-----------------|--------|
| 2.2.1 | Run seeding script | Database populated with test data | ☐ |
| 2.2.2 | User table | At least 5 test users with different roles | ☐ |
| 2.2.3 | Channel table | At least 10 sample channels with metadata | ☐ |
| 2.2.4 | Campaign templates | 8+ content templates seeded | ☐ |

---

# SECTION 3: BOT INITIALIZATION (30 minutes)

## 3.1 Startup Tests

| # | Test Case | Expected Result | Status | Notes |
|---|-----------|-----------------|--------|-------|
| 3.1.1 | Bot starts | `python main.py` runs without errors | ☐ | Check console: "Bot started successfully" |
| 3.1.2 | Telegram connection | Bot connects to Telegram API | ☐ | No auth errors in logs |
| 3.1.3 | Database connection | SQLAlchemy connects to adsbot.db | ☐ | No DB errors in logs |
| 3.1.4 | OpenAI API | ChatGPT API key validated | ☐ | Log should confirm API key active |
| 3.1.5 | Scheduler started | APScheduler initialized | ☐ | "Scheduler started" in logs |
| 3.1.6 | Rate limiter ready | Rate limiter initialized | ☐ | Redis/SQLite connection OK |
| 3.1.7 | Handlers registered | All conversation handlers loaded | ☐ | No handler conflicts |

**Startup Log Expected:**
```
2024-12-27 10:00:00 - Bot started successfully
2024-12-27 10:00:01 - Telegram connection established
2024-12-27 10:00:02 - Database connected: adsbot.db
2024-12-27 10:00:03 - OpenAI API key validated
2024-12-27 10:00:04 - APScheduler initialized
2024-12-27 10:00:05 - Conversation handlers registered
```

---

# SECTION 4: USER INTERFACE TESTING (90 minutes)

## 4.1 Main Menu String Verification

Test all 10 main menu strings appear correctly in `/start` command:

| # | String | Location in Code | Verification | Status |
|---|--------|------------------|--------------|--------|
| 4.1.1 | "👋 Welcome to AdsBot!" | bot.py:1629 | Send `/start`, verify emoji displays | ☐ |
| 4.1.2 | "🎯 Campaign Management" | bot.py:1650 | Visible in main menu | ☐ |
| 4.1.3 | "💰 Earnings & Payments" | bot.py:1651 | Visible in main menu | ☐ |
| 4.1.4 | "🔧 Settings & Preferences" | bot.py:1652 | Visible in main menu | ☐ |
| 4.1.5 | "📊 Analytics & Reports" | bot.py:1653 | Visible in main menu | ☐ |
| 4.1.6 | "🏪 Marketplace" | bot.py:1654 | Visible in main menu | ☐ |
| 4.1.7 | "⚙️ Admin Panel" | bot.py:1655 | Visible (admin users only) | ☐ |
| 4.1.8 | "📞 Support & Help" | bot.py:1656 | Visible in main menu | ☐ |
| 4.1.9 | "🌙 Dark Mode" | bot.py:1657 | Visible in settings | ☐ |
| 4.1.10 | "🌐 Language" | bot.py:1658 | Visible in settings | ☐ |

**Test Procedure:**
1. Start bot
2. Send `/start` from test Telegram account
3. Verify each string displays correctly with emoji
4. Check inline keyboard buttons render properly

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 4.2 Campaign Creation Flow (25+ strings)

| # | String | Step | Expected | Status |
|---|--------|------|----------|--------|
| 4.2.1 | "Select a channel to create campaign" | 1 | Channel list displayed | ☐ |
| 4.2.2 | "Channel: {name}\nTopic: {topic}" | 2 | Channel details shown | ☐ |
| 4.2.3 | "Select target platform for your campaign" | 3 | Platform buttons shown | ☐ |
| 4.2.4 | "Choose campaign tone" | 4 | Tone buttons shown | ☐ |
| 4.2.5 | "Generating campaign with AI..." | 5 | Loading message appears | ☐ |
| 4.2.6 | "✅ Campaign Generated!\nTitle: {title}" | 6 | Generated content shown | ☐ |
| 4.2.7 | "Set your daily budget (in USD)" | 7 | Budget input field | ☐ |
| 4.2.8 | "Campaign created successfully! ✅" | 8 | Confirmation message | ☐ |
| 4.2.9 | "❌ Campaign creation failed" | Error | Error message displayed | ☐ |

**Test Procedure:**
1. Click "Campaign Management" → "Create Campaign"
2. Follow each step and verify strings match UI
3. Verify inline keyboards work
4. Complete full campaign creation
5. Verify database entry created

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 4.3 AI Generator Strings (15+ strings)

| # | String | Expected Behavior | Status |
|---|--------|-------------------|--------|
| 4.3.1 | "🤖 AI Content Generator" | Menu button visible | ☐ |
| 4.3.2 | "Select content type" | 7 content types shown | ☐ |
| 4.3.3 | "Select tone of voice" | 4 tone options shown | ☐ |
| 4.3.4 | "Generating content..." | Loading message | ☐ |
| 4.3.5 | "✨ Generated Content:\n{content}" | Output displayed | ☐ |
| 4.3.6 | "👍 Like\n👎 Dislike\n🔄 Regenerate" | Action buttons shown | ☐ |
| 4.3.7 | "Save to library?\nYes / No" | Save confirmation | ☐ |
| 4.3.8 | "Saved to content library ✅" | Success message | ☐ |

**Test Procedure:**
1. Access "🤖 AI Content Generator"
2. Select content type (HEADLINE)
3. Select tone (PROFESSIONAL)
4. Enter topic
5. Verify content generates
6. Test like/dislike/regenerate buttons
7. Test save to library

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 5: NOTIFICATION SYSTEM (60 minutes)

## 5.1 Notification Type Testing

Test all 8 notification types trigger correctly:

| # | Notification Type | Trigger Condition | Expected String | Status |
|---|-------------------|-------------------|-----------------|--------|
| 5.1.1 | CAMPAIGN_PURCHASED | User buys campaign | "✅ Campaign Purchased!" | ☐ |
| 5.1.2 | CAMPAIGN_EARNED | Channel earns money | "💰 Earnings Received!" | ☐ |
| 5.1.3 | PAYMENT_RECEIVED | Payment confirmed | "✅ Payment Confirmed!" | ☐ |
| 5.1.4 | PAYMENT_FAILED | Payment fails | "❌ Payment Failed!" | ☐ |
| 5.1.5 | WITHDRAWAL_SUCCESS | Withdrawal completes | "✅ Withdrawal Successful!" | ☐ |
| 5.1.6 | WITHDRAWAL_FAILED | Withdrawal fails | "❌ Withdrawal Failed!" | ☐ |
| 5.1.7 | NEW_OFFER | New offer received | "📢 New Offer!" | ☐ |
| 5.1.8 | OFFER_ACCEPTED | Offer accepted | "✅ Offer Accepted!" | ☐ |

**Test Procedure (for each type):**
1. Trigger the condition
2. Verify notification sent to Telegram
3. Verify message format correct (HTML, emoji)
4. Verify all variables filled in ({name}, {amount}, {handle}, etc.)
5. Check database `Notification` table updated

**Notification Format Template:**
```
<b>✅ Notification Title</b>

Notification content here with {variables}
- Amount: ${amount}
- Channel: {channel_name}

Additional details...
```

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 5.2 Notification Delivery

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 5.2.1 | Single recipient | Message delivered in <2 seconds | ☐ |
| 5.2.2 | Multiple recipients | All receive notification | ☐ |
| 5.2.3 | Failed delivery | Logged, retry attempted | ☐ |
| 5.2.4 | HTML formatting | Emojis and bold render correctly | ☐ |

---

# SECTION 6: CHATGPT INTEGRATION (75 minutes)

## 6.1 Prompt Testing

Test all 3 ChatGPT prompt types with correct Italian output:

| # | Prompt Type | Input | Expected Output | Status |
|---|-------------|-------|-----------------|--------|
| 6.1.1 | Generic Campaign | Channel name, topic | JSON with title (Italian) | ☐ |
| 6.1.2 | Telegram-specific | Channel + Telegram | Concise, emoji format | ☐ |
| 6.1.3 | Instagram-specific | Channel + Instagram | Hashtags, engagement focus | ☐ |
| 6.1.4 | Facebook-specific | Channel + Facebook | Warm, interactive tone | ☐ |
| 6.1.5 | Twitter-specific | Channel + Twitter | Max 280 chars total | ☐ |
| 6.1.6 | Professional tone | Any channel + Pro | Formal language (Italian) | ☐ |
| 6.1.7 | Friendly tone | Any channel + Friendly | Warm, conversational (Italian) | ☐ |
| 6.1.8 | Aggressive tone | Any channel + Aggressive | Urgent, FOMO (Italian) | ☐ |
| 6.1.9 | Playful tone | Any channel + Playful | Fun, humor (Italian) | ☐ |

**Test Procedure:**
1. Trigger AI campaign generation through bot
2. Select platform (Telegram/Instagram/Facebook/Twitter)
3. Select tone (Professional/Friendly/Aggressive/Playful)
4. Verify JSON response contains all fields:
   - title (non-empty, Italian)
   - description (2-3 sentences, Italian)
   - cta_text (call-to-action, Italian)
   - suggested_budget (float > 0)
   - keywords (array, Italian)
   - target_audience (string, Italian)
5. Verify platform-specific constraints:
   - Twitter: total length ≤ 280 characters
   - Telegram: ≤ 4000 characters
   - Instagram: hashtags included
   - Facebook: warm tone evident

**API Validation:**
- Model: gpt-3.5-turbo ✓
- Temperature: 0.7 ✓
- Max tokens: 500 ✓
- Language: Italian only ✓

**Test ChatGPT Call:**
```bash
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Test prompt"}],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 6.2 Content Generation (Content Types)

Test all 7 content types generate correctly:

| Content Type | Input Example | Expected Output | Status |
|--------------|---------------|-----------------|--------|
| HEADLINE | "Tech product" | Short, punchy title | ☐ |
| POST | "Summer sale" | Multi-line content | ☐ |
| EMAIL_SUBJECT | "Newsletter" | Compelling subject line | ☐ |
| EMAIL_BODY | "Product launch" | Full email content (Italian) | ☐ |
| AD_COPY | "Fitness app" | Persuasive ad text | ☐ |
| CALL_TO_ACTION | "Free trial" | Action-oriented CTA | ☐ |
| PRODUCT_DESCRIPTION | "Camera" | Detailed feature list | ☐ |

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 6.3 Error Handling

| # | Error Scenario | Expected Behavior | Status |
|---|---|---|---|
| 6.3.1 | Invalid API key | Error message, no crash | ☐ |
| 6.3.2 | API timeout (>30s) | Fallback to template | ☐ |
| 6.3.3 | JSON parse error | Retry with markdown extraction | ☐ |
| 6.3.4 | Rate limit (429) | Queue and retry | ☐ |
| 6.3.5 | Non-Italian response | Reject and regenerate | ☐ |

---

# SECTION 7: PAYMENT PROCESSING (60 minutes)

## 7.1 Payment Strings (10+ strings)

| # | String | Context | Status |
|---|--------|---------|--------|
| 7.1.1 | "💰 Earnings & Payments" | Main menu button | ☐ |
| 7.1.2 | "View your earnings" | Earnings submenu | ☐ |
| 7.1.3 | "Total Earned: ${amount}" | Earnings display | ☐ |
| 7.1.4 | "Available for Withdrawal: ${amount}" | Withdrawal amount | ☐ |
| 7.1.5 | "Request Withdrawal" | Action button | ☐ |
| 7.1.6 | "Enter amount to withdraw (USD)" | Input prompt | ☐ |
| 7.1.7 | "✅ Withdrawal requested!" | Success message | ☐ |
| 7.1.8 | "Minimum withdrawal: $10" | Validation error | ☐ |
| 7.1.9 | "Insufficient funds" | Error message | ☐ |
| 7.1.10 | "💳 Payment Method" | Settings option | ☐ |

**Test Procedure:**
1. Access earnings section
2. Verify all strings display
3. Request withdrawal
4. Verify success/error messages
5. Check database Payment table updated

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 7.2 Payment Flow

| # | Test Case | Expected Result | Status |
|---|-----------|-----------------|--------|
| 7.2.1 | User has earnings | Amount calculated correctly | ☐ |
| 7.2.2 | Request withdrawal | Creates withdrawal record | ☐ |
| 7.2.3 | Valid amount | Processes withdrawal | ☐ |
| 7.2.4 | Below minimum | Rejects with message | ☐ |
| 7.2.5 | Insufficient funds | Error message shown | ☐ |

---

# SECTION 8: ADMIN PANEL (45 minutes)

## 8.1 Admin Menu Strings

| # | String | Visible to | Status |
|---|--------|-----------|--------|
| 8.1.1 | "⚙️ Admin Panel" | Admin only | ☐ |
| 8.1.2 | "📊 System Statistics" | Admin | ☐ |
| 8.1.3 | "👥 User Management" | Admin | ☐ |
| 8.1.4 | "🔐 Moderation" | Admin | ☐ |
| 8.1.5 | "📋 Logs" | Admin | ☐ |

**Test Procedure:**
1. Login as regular user
2. Verify admin panel NOT visible
3. Login as admin
4. Verify all admin options visible
5. Test each admin function

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 8.2 Admin Functions

| # | Function | Expected | Status |
|---|----------|----------|--------|
| 8.2.1 | View system stats | Stats display (users, campaigns, etc.) | ☐ |
| 8.2.2 | User management | Can disable/enable/delete users | ☐ |
| 8.2.3 | Moderation | Can review flagged content | ☐ |
| 8.2.4 | View logs | Admin actions logged | ☐ |

---

# SECTION 9: ANALYTICS & REPORTING (60 minutes)

## 9.1 Analytics Data

| # | Metric | Expected | Status |
|---|--------|----------|--------|
| 9.1.1 | Active Users | Count > 0 | ☐ |
| 9.1.2 | Campaigns Created | Count ≥ 0 | ☐ |
| 9.1.3 | Total Revenue | Sum of payments | ☐ |
| 9.1.4 | Avg Campaign CTR | % calculated | ☐ |
| 9.1.5 | Top Performing Channel | Name + stats | ☐ |

**Test Procedure:**
1. Access analytics section
2. Verify all metrics display
3. Check database CampaignAnalytics table
4. Validate calculations

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

## 9.2 Report Generation

| # | Report Type | Expected Output | Status |
|---|-------------|-----------------|--------|
| 9.2.1 | Daily report | Revenue, users, campaigns | ☐ |
| 9.2.2 | Weekly report | Trends, top performers | ☐ |
| 9.2.3 | Monthly report | Summary, growth metrics | ☐ |
| 9.2.4 | Export CSV | Downloadable data | ☐ |

---

# SECTION 10: SCHEDULED TASKS (45 minutes)

## 10.1 Background Jobs

| # | Job Name | Trigger | Expected | Status |
|---|----------|---------|----------|--------|
| 10.1.1 | Process pending payments | Hourly | Payments processed | ☐ |
| 10.1.2 | Generate analytics | Daily 01:00 | CampaignAnalytics updated | ☐ |
| 10.1.3 | Send reminders | Daily 08:00 | Notifications queued | ☐ |
| 10.1.4 | Cleanup old logs | Weekly | Logs archived | ☐ |
| 10.1.5 | Update risk scores | Daily | RiskScore updated | ☐ |
| 10.1.6 | Process disputes | As triggered | DisputeTicket resolved | ☐ |

**Test Procedure:**
1. Check APScheduler is running
2. Verify jobs in scheduler
3. Monitor logs for job execution
4. Verify database updated by jobs

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 11: DATABASE OPERATIONS (45 minutes)

## 11.1 CRUD Operations

Test all major database operations:

| # | Operation | Table | Expected | Status |
|---|-----------|-------|----------|--------|
| 11.1.1 | Create user | User | New record inserted | ☐ |
| 11.1.2 | Read user | User | Data retrieved correctly | ☐ |
| 11.1.3 | Update user | User | Changes saved | ☐ |
| 11.1.4 | Delete user | User | Record removed safely | ☐ |
| 11.1.5 | Create campaign | Campaign | Record with all fields | ☐ |
| 11.1.6 | List campaigns | Campaign | All user's campaigns returned | ☐ |
| 11.1.7 | Create payment | Payment | Transaction logged | ☐ |
| 11.1.8 | Calculate earnings | Campaign | Sum calculated correctly | ☐ |

**Database Integrity Checks:**
```sql
-- Foreign key check
PRAGMA foreign_keys = ON;

-- Check relationships
SELECT COUNT(*) FROM Campaign WHERE user_id NOT IN (SELECT id FROM User);

-- Verify constraints
PRAGMA index_list(Campaign);
```

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 12: ERROR HANDLING (45 minutes)

## 12.1 Error Messages (12+ strings)

| # | Error | Message | Status |
|---|-------|---------|--------|
| 12.1.1 | Invalid input | "❌ Invalid input. Please try again." | ☐ |
| 12.1.2 | User not found | "❌ User not found." | ☐ |
| 12.1.3 | Campaign limit | "⚠️ Maximum campaigns reached." | ☐ |
| 12.1.4 | Insufficient balance | "❌ Insufficient balance for this action." | ☐ |
| 12.1.5 | API timeout | "⏱️ Request timed out. Please try again." | ☐ |
| 12.1.6 | Database error | "❌ Database error. Support team notified." | ☐ |
| 12.1.7 | Permission denied | "🔒 You don't have permission for this." | ☐ |
| 12.1.8 | Invalid campaign | "❌ Campaign not found or expired." | ☐ |
| 12.1.9 | Rate limit | "⚠️ Too many requests. Try again later." | ☐ |
| 12.1.10 | Verification required | "🔐 Please verify your account first." | ☐ |
| 12.1.11 | Channel offline | "⚠️ Channel is currently offline." | ☐ |
| 12.1.12 | Invalid token | "🔑 Your session expired. Please login again." | ☐ |

**Test Procedure:**
1. Trigger each error condition
2. Verify error message displays
3. Verify user not confused
4. Check error logged
5. Verify bot doesn't crash

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 13: SECURITY TESTING (60 minutes)

## 13.1 Risk Scoring

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 13.1.1 | New user | Risk score calculated | ☐ |
| 13.1.2 | High activity | Score adjusted | ☐ |
| 13.1.3 | Suspicious pattern | Score increases | ☐ |
| 13.1.4 | Verified user | Score decreases | ☐ |

## 13.2 Rate Limiting

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 13.2.1 | Normal usage | No throttling | ☐ |
| 13.2.2 | Rapid requests (10/sec) | Throttled after limit | ☐ |
| 13.2.3 | Multiple users | Per-user limits work | ☐ |
| 13.2.4 | Rate limit expiry | Limit resets after window | ☐ |

## 13.3 Input Validation

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 13.3.1 | SQL injection attempt | Rejected, no DB impact | ☐ |
| 13.3.2 | XSS payload | Escaped, harmless display | ☐ |
| 13.3.3 | Very long input | Truncated or rejected | ☐ |
| 13.3.4 | Special characters | Handled safely | ☐ |

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 14: PERFORMANCE TESTING (60 minutes)

## 14.1 Response Times

| # | Operation | Expected Time | Actual | Status |
|---|-----------|---|---|---|
| 14.1.1 | `/start` command | < 1 second | ___ | ☐ |
| 14.1.2 | Campaign list | < 2 seconds | ___ | ☐ |
| 14.1.3 | AI generation | < 10 seconds | ___ | ☐ |
| 14.1.4 | Payment processing | < 5 seconds | ___ | ☐ |
| 14.1.5 | Analytics load | < 3 seconds | ___ | ☐ |
| 14.1.6 | Database query | < 500ms | ___ | ☐ |

## 14.2 Load Testing

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 14.2.1 | 10 concurrent users | All requests succeed | ☐ |
| 14.2.2 | 50 concurrent users | No timeouts | ☐ |
| 14.2.3 | 100 concurrent users | Graceful degradation | ☐ |
| 14.2.4 | Memory usage | < 500MB | ☐ |

**Load Test Tool:**
```bash
# Install: pip install locust
# Create locustfile.py and run:
locust -f locustfile.py --headless -u 50 -r 10 -t 5m
```

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 15: COMPLIANCE & VERIFICATION (45 minutes)

## 15.1 User Verification

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 15.1.1 | New user flow | Verification required | ☐ |
| 15.1.2 | Email verification | Code sent + verified | ☐ |
| 15.1.3 | Phone verification | SMS/Telegram code | ☐ |
| 15.1.4 | Verified status | Stored in DB | ☐ |

## 15.2 KYC Compliance

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 15.2.1 | Identity verification | Required for > $1000 | ☐ |
| 15.2.2 | Document upload | Secure storage | ☐ |
| 15.2.3 | Admin review | Manual approval | ☐ |
| 15.2.4 | Compliance log | Audit trail | ☐ |

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 16: INTEGRATION TESTS (90 minutes)

## 16.1 End-to-End Workflows

| # | Workflow | Steps | Expected Result | Status |
|---|----------|-------|-----------------|--------|
| 16.1.1 | Create & Sell Campaign | 1. Create → 2. Publish → 3. Buyer purchases → 4. Seller earns | Earnings recorded, payment made | ☐ |
| 16.1.2 | Payment & Withdrawal | 1. Earn $ → 2. Request withdrawal → 3. Process → 4. Transfer complete | Money transferred successfully | ☐ |
| 16.1.3 | AI Generation Workflow | 1. Request → 2. Generate → 3. Review → 4. Publish | Campaign live with AI content | ☐ |
| 16.1.4 | Dispute Resolution | 1. Dispute opened → 2. Evidence submitted → 3. Admin review → 4. Resolution | DisputeTicket resolved | ☐ |
| 16.1.5 | Marketplace Transaction | 1. List channel → 2. Buyer interested → 3. Negotiate → 4. Transfer | ChannelListing marked sold | ☐ |

**Test Procedure:**
1. Follow each workflow from start to finish
2. Verify all database changes
3. Check all notifications sent
4. Validate all strings displayed correctly
5. Ensure no errors logged

**Tester:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 17: DOCUMENTATION VERIFICATION (30 minutes)

## 17.1 Code Documentation

| # | File | Expected | Status |
|---|------|----------|--------|
| 17.1.1 | bot.py | Functions documented | ☐ |
| 17.1.2 | chatgpt_integration.py | Prompts documented | ☐ |
| 17.1.3 | ai_content.py | Content types documented | ☐ |
| 17.1.4 | config.py | All settings documented | ☐ |
| 17.1.5 | models.py | All models documented | ☐ |

## 17.2 User Documentation

| # | Document | Complete | Status |
|---|----------|----------|--------|
| 17.2.1 | README.md | Full setup guide | ☐ |
| 17.2.2 | QUICK_START.md | Getting started | ☐ |
| 17.2.3 | USER_FACING_STRINGS.md | All UI strings | ☐ |
| 17.2.4 | CHATGPT_PROMPTS.md | AI integration | ☐ |

---

# SECTION 18: FINAL VERIFICATION (60 minutes)

## 18.1 Build Verification

| # | Test | Expected | Status |
|---|------|----------|--------|
| 18.1.1 | Compile all Python files | No syntax errors | ☐ |
| 18.1.2 | Import all modules | No import errors | ☐ |
| 18.1.3 | Database migrations | All tables created | ☐ |
| 18.1.4 | Run unit tests | 100% pass rate | ☐ |
| 18.1.5 | Run integration tests | All tests pass | ☐ |

## 18.2 Feature Checklist

- [ ] All 135+ user-facing strings display correctly
- [ ] All 8 notification types work
- [ ] ChatGPT integration works (all 3 prompt types)
- [ ] All 7 content types generate
- [ ] All 4 platform guidelines respected
- [ ] All 4 tone variants work
- [ ] Database has 20 tables with correct structure
- [ ] FASE 1-7 features all working (27 tasks)
- [ ] No critical errors in logs
- [ ] Performance meets targets
- [ ] Security measures in place
- [ ] Documentation complete

**Tester:** ________________  **Date:** ________________  **Pass/Fail:** ☐ Pass ☐ Fail

---

# SECTION 19: SIGN-OFF

## UAT Completion Checklist

- [ ] All 18 test sections completed
- [ ] All critical features verified
- [ ] No showstopper bugs found
- [ ] Performance acceptable
- [ ] Security verified
- [ ] Documentation complete
- [ ] Ready for staging deployment

## Defects Found

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| D1 | | | |
| D2 | | | |
| D3 | | | |

## Overall Result

**UAT Status:** ☐ PASSED ☐ FAILED ☐ PASSED WITH EXCEPTIONS

**Tester Name:** ________________  **Signature:** ________________  **Date:** ________________

**QA Lead Name:** ________________  **Signature:** ________________  **Date:** ________________

**Project Manager Name:** ________________  **Signature:** ________________  **Date:** ________________

---

## APPENDIX A: Test Environment

**OS:** Windows 11
**Python:** 3.13.x
**Database:** SQLite (adsbot.db)
**Bot Platform:** Telegram
**API:** OpenAI ChatGPT
**Scheduler:** APScheduler
**Rate Limiter:** SQLite
**Test Duration:** ~8 hours

---

## APPENDIX B: Test Execution Timeline

| Phase | Start | End | Duration |
|-------|-------|-----|----------|
| Setup | | | 30 min |
| Database | | | 45 min |
| Bot Init | | | 30 min |
| UI Testing | | | 90 min |
| Notifications | | | 60 min |
| ChatGPT | | | 75 min |
| Payments | | | 60 min |
| Admin | | | 45 min |
| Analytics | | | 60 min |
| Scheduled Jobs | | | 45 min |
| Database Ops | | | 45 min |
| Error Handling | | | 45 min |
| Security | | | 60 min |
| Performance | | | 60 min |
| Compliance | | | 45 min |
| Integration | | | 90 min |
| Documentation | | | 30 min |
| Final Verification | | | 60 min |
| **TOTAL** | | | **~8 hours** |

---

END OF UAT SCRIPT v1.0

