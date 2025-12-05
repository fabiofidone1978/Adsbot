# 📚 FASE 4-7 ROADMAP - CONTINUATION PLAN

**Project:** ADSBOT Marketplace V2  
**Current Status:** FASE 2 & 3 Complete ✅  
**Next Phase:** FASE 4 - Analytics & Reporting  
**Planning Date:** December 5, 2025

---

## 🎯 PROJECT OVERVIEW

### Completed Phases
- ✅ **FASE 1 (Foundation):** State machines, models, database (Tasks 1-7)
- ✅ **FASE 2 (Marketplace):** Catalog, notifications, editor panel (Tasks 11-15)
- ✅ **FASE 3 (Admin Panel):** Channel approval, user management, statistics

### Remaining Phases
- 📋 **FASE 4 (Analytics):** User analytics, reporting system
- 📋 **FASE 5 (Scheduled Tasks):** APScheduler integration
- 📋 **FASE 6 (Verification):** Advanced verification system
- 📋 **FASE 7 (Seed Data):** Test data generation

---

## 📊 FASE 4: ANALYTICS & REPORTING (Est. 4-6 hours)

### Objectives
- Implement comprehensive analytics for editors and advertisers
- Create reporting dashboard with KPIs
- Track user behavior and platform metrics
- Generate PDF/CSV export reports

### Tasks

#### Task 16: Editor Analytics Functions (2 hours)

**Functions to Create:**
```python
async def editor_analytics_dashboard(user_id, period='month')
    """Show editor performance metrics"""
    - Total orders (completed, pending, rejected)
    - Total earnings (by period)
    - Average order value
    - Completion rate
    - Top performing channels
    - Revenue trend chart data

async def editor_earnings_report(user_id, period='month')
    """Generate earnings report with breakdown"""
    - Daily/weekly/monthly breakdown
    - Commission details
    - Payment status
    - Export to CSV/PDF

async def editor_channel_performance(editor_id, channel_id)
    """Show performance per channel"""
    - Orders received
    - Completion rate
    - Average price
    - Subscriber growth (if available)
```

**Database Queries Needed:**
- Query MarketplaceOrder grouped by status
- Calculate SUM(total_price) for earnings
- Track order timeline
- Join with ChannelListing for channel metrics

**UI Components:**
- Statistics cards (completed orders, earnings, rate)
- Charts (revenue trend, completion rate over time)
- Export buttons (CSV, PDF)
- Date range selector

#### Task 17: Advertiser Analytics Functions (2 hours)

**Functions to Create:**
```python
async def advertiser_analytics_dashboard(user_id, period='month')
    """Show advertiser campaign performance"""
    - Total campaigns (active, completed, failed)
    - Total spent (with breakdown by channel)
    - Average ROI (if available)
    - Top performing channels
    - Campaign status distribution

async def advertiser_campaign_report(user_id, campaign_id)
    """Get detailed campaign report"""
    - Order details
    - Channel info
    - Status timeline
    - Estimated reach
    - Performance metrics (if available)

async def advertiser_spending_analytics(user_id, period='month')
    """Track spending patterns"""
    - Daily/weekly/monthly breakdown
    - Budget remaining
    - Payment history
    - Refund history
```

**Database Queries:**
- Query MarketplaceOrder where buyer_id = user_id
- Group by period (day, week, month)
- Calculate statistics
- Join with Channel for reach data

#### Task 18: Platform Statistics Functions (2 hours)

**Functions to Create:**
```python
async def platform_dashboard_stats()
    """Overall platform KPIs"""
    - Total users, channels, orders
    - Revenue (total, last 30 days, by category)
    - Completion rate
    - Average order value
    - Growth trends

async def platform_user_report()
    """User demographics and activity"""
    - Total users by role (admin, editor, advertiser)
    - Active users (last 24h, 7d, 30d)
    - User retention rate
    - Geographic distribution (if available)

async def platform_category_report()
    """Category-specific metrics"""
    - Orders by category
    - Revenue by category
    - Average price by category
    - Most popular categories
```

**Dashboard Integration:**
- Route `/analytics` shows appropriate dashboard based on user role
- Editor sees: earnings, channel performance, revenue trends
- Advertiser sees: spending, campaign performance, ROI
- Admin sees: platform stats, user metrics, category breakdown

#### Task 19: Export & Report Generation (1-2 hours)

**Functions to Create:**
```python
async def export_analytics_csv(user_id, analytics_type, period)
    """Export analytics to CSV"""
    - Create CSV with data
    - Return file for download

async def export_analytics_pdf(user_id, analytics_type, period)
    """Generate PDF report with charts"""
    - Use reportlab or similar
    - Include charts
    - Professional formatting
    - Email option

async def schedule_report_email(user_id, frequency='weekly')
    """Setup automated report emails"""
    - Configure email frequency
    - Select report type
    - Store schedule in database
```

**Technologies:**
- Python CSV module for exports
- ReportLab or WeasyPrint for PDF generation
- SMTP for email sending

### Estimated Time
- Task 16 (Editor Analytics): 2 hours
- Task 17 (Advertiser Analytics): 2 hours
- Task 18 (Platform Analytics): 1 hour
- Task 19 (Export/Reports): 1-2 hours
- **Total: 6-7 hours**

### Dependencies
- Existing models: MarketplaceOrder, Payment, User, Channel
- Database queries must be optimized (use aggregations)
- UI templates for analytics dashboard

---

## ⏰ FASE 5: SCHEDULED TASKS (Est. 3-4 hours)

### Objectives
- Implement background jobs using APScheduler
- Automate routine platform tasks
- Handle order expiration and cleanup
- Update channel metrics periodically

### Tasks

#### Task 20: APScheduler Setup (1 hour)

**Setup Required:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Configure jobs:
scheduler.add_job(check_expired_orders, 'interval', minutes=30)
scheduler.add_job(auto_cancel_pending, 'interval', minutes=15)
scheduler.add_job(update_reach_metrics, 'interval', hours=6)
scheduler.add_job(generate_daily_report, 'cron', hour=0, minute=0)

scheduler.start()
```

#### Task 21: Scheduled Order Management (1.5 hours)

**Functions to Create:**
```python
async def check_expired_orders()
    """Check for expired orders and mark as COMPLETED"""
    - Query orders where expires_at < now()
    - Update status to COMPLETED
    - Create payment completion record
    - Notify users
    - Cleanup database

async def auto_cancel_pending()
    """Auto-cancel orders pending >48 hours"""
    - Query orders with status=PENDING and created_at > 48h
    - Cancel order
    - Process refund
    - Notify advertiser
    - Log event

async def cleanup_abandoned_orders()
    """Remove DRAFT orders older than 7 days"""
    - Query DRAFT orders older than 7 days
    - Delete safely
    - Log cleanup
```

#### Task 22: Metrics Update Jobs (1 hour)

**Functions to Create:**
```python
async def update_reach_metrics()
    """Update channel reach_24h from telegram API"""
    - For each channel:
      - Get updated subscriber count via bot.get_chat()
      - Calculate reach_24h (estimated)
      - Update ChannelMetrics table
      - Log update

async def update_channel_stats()
    """Update channel engagement metrics"""
    - Calculate average engagement rate
    - Update category popularity
    - Identify trending channels
```

#### Task 23: Reporting Jobs (0.5 hours)

**Functions to Create:**
```python
async def generate_daily_report()
    """Generate daily platform report"""
    - Count orders created yesterday
    - Calculate revenue
    - Identify top editors, advertisers
    - Email to admin

async def weekly_editor_report(editor_id)
    """Send weekly earnings report to editor"""
    - Calculate weekly earnings
    - List completed orders
    - Format nicely
    - Send via Telegram/Email
```

### Estimated Time
- Task 20 (Setup): 1 hour
- Task 21 (Order Management): 1.5 hours
- Task 22 (Metrics): 1 hour
- Task 23 (Reporting): 0.5 hours
- **Total: 4 hours**

### Dependencies
- APScheduler library
- Existing order management functions
- Telegram bot API for metrics

---

## 🔐 FASE 6: VERIFICATION SYSTEM (Est. 3-4 hours)

### Objectives
- Implement advanced verification for users
- Add identity verification
- Implement risk scoring
- Add dispute resolution automation

### Tasks

#### Task 24: Identity Verification (1.5 hours)

**Functions to Create:**
```python
async def verify_user_identity(user_id, verification_data)
    """Verify user identity"""
    - Request ID/docs from user
    - Store encrypted verification data
    - Update user.verified_at
    - Update user.is_verified flag

async def verify_payment_method(user_id, payment_method)
    """Verify payment method"""
    - Check payment method is valid
    - Verify ownership
    - Store verification status
```

#### Task 25: Risk Scoring (1.5 hours)

**Functions to Create:**
```python
async def calculate_user_risk_score(user_id) -> float
    """Calculate risk score 0-100"""
    - New user: +30 points
    - Unverified: +20 points
    - High dispute rate: +40 points
    - Positive reviews: -20 points
    - Long history: -10 points
    - Return: score (0-100)

async def update_risk_flags(user_id)
    """Update risk flags based on score"""
    - If score > 70: flag for review
    - If score > 85: suspend account
    - Notify admin if flagged
```

#### Task 26: Dispute Resolution (1 hour)

**Functions to Create:**
```python
async def auto_resolve_disputes()
    """Attempt automatic dispute resolution"""
    - For each open dispute:
      - Analyze evidence
      - Apply resolution rules
      - If clear winner: auto-resolve
      - Notify parties

async def escalate_dispute(dispute_id, reason)
    """Escalate dispute to admin"""
    - Mark as requires_admin_review
    - Notify admin
    - Set priority level
```

### Estimated Time
- Task 24 (Identity Verification): 1.5 hours
- Task 25 (Risk Scoring): 1.5 hours
- Task 26 (Dispute Resolution): 1 hour
- **Total: 4 hours**

---

## 🌱 FASE 7: SEED DATA (Est. 1-2 hours)

### Objectives
- Create test data for development and demos
- Setup environment-specific data
- Generate realistic usage patterns

### Tasks

#### Task 27: Seed Database Script (1-2 hours)

**Create `scripts/seed_database.py`:**
```python
def create_test_users()
    """Create test users"""
    - 5 advertisers
    - 3 editors
    - 1 admin
    - Return user_ids

def create_test_channels()
    """Create test channels"""
    - 10 channels (5 crypto, 3 tech, 2 lifestyle)
    - Different price ranges
    - Different subscriber counts
    - Return channel_ids

def create_test_orders()
    """Create sample orders at different stages"""
    - 8 orders in various states:
      - 2 COMPLETED
      - 2 PENDING
      - 2 CONFIRMED
      - 1 REJECTED
      - 1 DISPUTED
    - Return order_ids

def create_payments()
    """Create payment records for orders"""

def populate_database()
    """Master function to populate everything"""
    - Create users
    - Create channels
    - Create orders
    - Create payments
    - Print summary
```

**Usage:**
```bash
cd adsbot
python ../scripts/seed_database.py --environment=development
```

### Estimated Time
- Task 27 (Seed Script): 1-2 hours
- **Total: 2 hours**

---

## 📅 IMPLEMENTATION TIMELINE

### Week 1 (Days 1-3)
- [ ] FASE 4: Analytics & Reporting (6-7 hours)
  - Day 1: Tasks 16-17 (Editor + Advertiser analytics)
  - Day 2: Tasks 18-19 (Platform analytics + Export)
  - Day 3: Testing + Review

### Week 1 (Days 4-5)
- [ ] FASE 5: Scheduled Tasks (4 hours)
  - Day 4: Tasks 20-22 (APScheduler + Jobs)
  - Day 5: Task 23 + Testing

### Week 2 (Days 1-3)
- [ ] FASE 6: Verification System (4 hours)
  - Day 1: Tasks 24-25 (Identity + Risk scoring)
  - Day 2: Task 26 (Dispute resolution)
  - Day 3: Testing + Review

### Week 2 (Days 4-5)
- [ ] FASE 7: Seed Data (2 hours)
  - Day 4: Task 27 (Seed script)
  - Day 5: Final integration + deployment

### Week 3
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Production deployment

---

## 🎯 SUCCESS CRITERIA

### FASE 4 Success
- ✅ Editors can view earnings analytics
- ✅ Advertisers can track spending
- ✅ Admin sees platform KPIs
- ✅ Reports can be exported (CSV/PDF)
- ✅ Performance: <1s for analytics queries

### FASE 5 Success
- ✅ Orders auto-expire after duration
- ✅ Pending orders auto-cancel after 48h
- ✅ Metrics updated regularly
- ✅ Daily reports generated and sent
- ✅ Scheduler runs without errors

### FASE 6 Success
- ✅ User identity verification working
- ✅ Risk scores calculated accurately
- ✅ High-risk users flagged/suspended
- ✅ Some disputes auto-resolved
- ✅ Admin notified of escalations

### FASE 7 Success
- ✅ Database can be seeded with test data
- ✅ Realistic data for demos
- ✅ Quick setup for new environments
- ✅ Reproducible test scenarios

---

## 🛠️ TECHNICAL STACK

### New Dependencies
```
apscheduler>=3.10.0          # Scheduled tasks
reportlab>=4.0.0            # PDF generation
weasyprint>=58.0            # Alternative PDF generation
pandas>=1.5.0              # Data analysis
matplotlib>=3.6.0          # Charts (optional)
```

### Update requirements.txt
```bash
pip install -r requirements.txt
pip freeze > requirements.txt
```

---

## 📝 IMPLEMENTATION GUIDELINES

### Code Quality Standards
- All functions must have docstrings
- Type hints required for all parameters
- Error handling with try-except
- Logging for all significant operations
- Unit tests for business logic

### Database Queries
- Use SQLAlchemy ORM (no raw SQL)
- Always use .limit() to prevent large resultsets
- Add proper indexes before deployment
- Test queries with realistic data volumes

### Async/Await
- All Telegram bot calls must be async
- All database operations should be async-aware
- Use proper exception handling in async functions

### Testing
- Write unit tests for each function
- Integration tests for workflows
- Load testing for analytics queries
- Test database backup/restore before deploying

---

## 🚀 DEPLOYMENT NOTES

### Before Each Phase
1. Create feature branch: `git checkout -b fase-4-analytics`
2. Implement features
3. Write tests
4. Code review
5. Merge to main
6. Tag release: `git tag v2.1.0-fase4`
7. Deploy to staging
8. Test in staging
9. Deploy to production

### Rollback Plan
- Each phase is independently reversible
- Database migrations must be backward compatible
- Keep feature flags for gradual rollout

---

## 📞 SUPPORT & ESCALATION

**For Questions About:**
- FASE 4: Analytics & Reporting
- FASE 5: Scheduled Tasks
- FASE 6: Verification
- FASE 7: Seed Data

**Contact:** [Developer contact info]

---

## 📋 CHECKLIST FOR NEXT SESSION

- [ ] Review this roadmap with team
- [ ] Create GitHub milestones for FASE 4-7
- [ ] Assign developers to each FASE
- [ ] Setup staging environment
- [ ] Create feature branches
- [ ] Start implementing FASE 4
- [ ] Setup monitoring for scheduled tasks
- [ ] Prepare documentation for each FASE

---

**Document Version:** 1.0  
**Created:** December 5, 2025  
**Next Review:** After FASE 4 completion
