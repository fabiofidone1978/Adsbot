PRODUCTION DEPLOYMENT CHECKLIST
===============================

## Deployment Version: 1.0
## Target Environment: PRODUCTION
## Estimated Duration: 3-4 hours (includes rollback testing)
## Deployment Window: [TO BE SCHEDULED - recommend off-peak hours]

---

# 1. PRE-DEPLOYMENT VERIFICATION (2-3 hours before)

## 1.1 Staging Validation Complete

| # | Requirement | Status | Verified By | Date |
|---|-------------|--------|-------------|------|
| 1.1.1 | Staging 7-day stable operation | ☐ | QA Lead | |
| 1.1.2 | All UAT tests passed | ☐ | QA Lead | |
| 1.1.3 | No critical bugs | ☐ | QA Lead | |
| 1.1.4 | Performance benchmarks met | ☐ | Tech Lead | |
| 1.1.5 | Security audit passed | ☐ | Security | |
| 1.1.6 | Database integrity verified | ☐ | DBA | |
| 1.1.7 | Backup/restore tested | ☐ | DBA | |
| 1.1.8 | Monitoring configured | ☐ | DevOps | |

## 1.2 Production Environment Ready

| # | Item | Expected | Status | Owner |
|---|------|----------|--------|-------|
| 1.2.1 | Production server online | Ping OK | ☐ | DevOps |
| 1.2.2 | Python 3.13 installed | version check OK | ☐ | DevOps |
| 1.2.3 | Full production backup | Backup > 1GB | ☐ | DBA |
| 1.2.4 | Load balancer configured | All nodes healthy | ☐ | DevOps |
| 1.2.5 | SSL/TLS certificates valid | > 30 days remaining | ☐ | DevOps |
| 1.2.6 | CDN configured | Cache headers set | ☐ | DevOps |
| 1.2.7 | Database replication | Primary + Replica OK | ☐ | DBA |
| 1.2.8 | Monitoring/Alerts active | All alerts enabled | ☐ | DevOps |
| 1.2.9 | Backup systems ready | Incremental + Full | ☐ | DBA |
| 1.2.10 | Rollback plan tested | Can restore in < 30 min | ☐ | DevOps |

## 1.3 Code & Documentation Ready

| # | Item | Status | Owner |
|---|------|--------|-------|
| 1.3.1 | Release notes finalized | ☐ | Product |
| 1.3.2 | Deployment runbook created | ☐ | DevOps |
| 1.3.3 | Known issues documented | ☐ | QA |
| 1.3.4 | Rollback procedure tested | ☐ | DevOps |
| 1.3.5 | Communication plan ready | ☐ | Product |
| 1.3.6 | Support team briefed | ☐ | Support Mgr |
| 1.3.7 | Customer communication ready | ☐ | Marketing |
| 1.3.8 | Database migration plan | ☐ | DBA |

## 1.4 Stakeholder Approval

| Stakeholder | Role | Approval | Date | Signature |
|-------------|------|----------|------|-----------|
| Tech Lead | Engineering | ☐ Approve ☐ Block | | |
| QA Lead | Quality | ☐ Approve ☐ Block | | |
| DevOps Lead | Operations | ☐ Approve ☐ Block | | |
| Product Owner | Product | ☐ Approve ☐ Block | | |
| CTO / VP Eng | Executive | ☐ Approve ☐ Block | | |

---

# 2. DEPLOYMENT EXECUTION PLAN

## 2.1 Pre-Deployment Tasks (30 minutes)

### Task 1: Communications Sent

```
[ ] Notify all stakeholders (30 min before deployment)
    Email: "AdsBot v1.0 deploying to production in 30 minutes"
    
[ ] Post status in #operations Slack channel
    "DEPLOYMENT STARTING: AdsBot v1.0 → Production (Est. 3 hours)"
    
[ ] Set incident status on status page
    "Maintenance scheduled: 14:00-17:00 UTC"
    
[ ] Enable "Maintenance Mode" on production API
    "Service under maintenance. We'll be back shortly!"
```

### Task 2: Final Backup & Snapshot

```bash
# 2.1 Create full production backup
pg_dump adsbot_prod > /backups/adsbot_prod_$(date +%Y%m%d_%H%M%S).sql.gz

# 2.2 Create database snapshot
aws rds create-db-snapshot \
  --db-instance-identifier adsbot-prod \
  --db-snapshot-identifier adsbot-prod-pre-deploy-$(date +%Y%m%d)

# 2.3 Create VM snapshot
aws ec2 create-snapshot \
  --volume-id vol-XXXXX \
  --description "Pre-deployment snapshot"

# 2.4 Verify backups created
aws s3 ls s3://adsbot-backups/ | tail -5
aws rds describe-db-snapshots | grep adsbot-prod-pre-deploy
```

**Verification:**
- [ ] SQL backup created (> 500MB)
- [ ] Database snapshot created
- [ ] VM snapshot created
- [ ] All backups verified

### Task 3: Scale Down Traffic (if applicable)

```bash
# 3.1 Reduce load balancer target count
aws elbv2 register-targets \
  --target-group-arn arn:aws:... \
  --targets Id=i-XXXXX

# 3.2 Route 90% traffic to old version (blue-green deployment)
# (Keep 10% on new version for smoke test)
```

**Verification:**
- [ ] Traffic reduced
- [ ] Old version still serving majority
- [ ] Health checks passing

---

## 2.2 Deployment Steps (1-1.5 hours)

### Step 1: Code Deployment (15 minutes)

```bash
# 1.1 SSH into production
ssh prod-server

# 1.2 Become deploy user
sudo su - deploy

# 1.3 Navigate to deployment directory
cd /opt/adsbot-prod

# 1.4 Create timestamped backup of current deployment
tar -czf adsbot.prod.$(date +%Y%m%d_%H%M%S).tar.gz adsbot/
echo "[$(date)] Backup created: adsbot.prod.*.tar.gz" >> deployment.log

# 1.5 Pull new code from Git (main branch, tag v1.0.0)
git fetch origin
git checkout tags/v1.0.0
git pull origin tags/v1.0.0

# 1.6 Verify no conflicts
git status
git log --oneline -3
```

**Verification:**
- [ ] SSH connection successful
- [ ] Current deployment backed up
- [ ] Git tag v1.0.0 checked out
- [ ] No merge conflicts
- [ ] Commit history visible

**Expected:**
```
On branch detached at tags/v1.0.0
nothing to commit, working tree clean

commit abc1234 FASE 7 completion - Final implementation
commit def5678 FASE 4-7 implementation
commit 174025c Model references fixed
```

### Step 2: Dependency Update (5 minutes)

```bash
# 2.1 Activate virtual environment
source /opt/adsbot-prod/.venv/bin/activate
python --version  # Should be 3.13.x

# 2.2 Upgrade pip to latest
pip install --upgrade pip

# 2.3 Install dependencies (production mode, no dev)
pip install -r requirements.txt --no-dev

# 2.4 Verify all critical imports
python << 'EOF'
import sys
required_modules = [
    'telegram',
    'sqlalchemy',
    'openai',
    'apscheduler',
    'flask',
    'dotenv'
]
print("Checking critical modules...")
for mod in required_modules:
    try:
        __import__(mod)
        print(f"✅ {mod}")
    except ImportError as e:
        print(f"❌ {mod}: {e}")
        sys.exit(1)
print("✅ All modules imported successfully")
EOF
```

**Verification:**
- [ ] Virtual environment activated
- [ ] Python 3.13.x
- [ ] All packages installed
- [ ] No import errors
- [ ] Requirements matches staging

### Step 3: Database Migration (10 minutes)

```bash
# 3.1 Create database backup (local, pre-migration)
sqlite3 adsbot.db ".dump" > adsbot.sql.backup
echo "[$(date)] Local DB backup created" >> deployment.log

# 3.2 Run schema migrations
python -m alembic upgrade head

# 3.3 Verify database integrity
python << 'EOF'
from adsbot.db import engine, inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
expected_tables = [
    'User', 'Channel', 'Campaign', 'MarketplaceOrder', 'Payment',
    'Notification', 'CampaignAnalytics', 'ScheduledTask', 'DisputeTicket',
    'ChannelListing', 'ChannelRating', 'RiskScore', 'VerificationRecord',
    'AIGeneratedContent', 'ContentTemplate', 'RateLimitRecord',
    'UserSettings', 'AdminLog', 'SystemMetric', 'WebhookEvent'
]
missing = set(expected_tables) - set(tables)
if missing:
    print(f"❌ Missing tables: {missing}")
    exit(1)
print(f"✅ All {len(tables)} tables present")
EOF

# 3.4 Run migration test
python scripts/test_migration.py

# 3.5 Seed any required static data (if applicable)
python scripts/seed_production_data.py
```

**Verification:**
- [ ] Database backup created
- [ ] Migrations completed
- [ ] All 20 tables exist
- [ ] No migration errors
- [ ] Database integrity OK

### Step 4: Configuration Deployment (5 minutes)

```bash
# 4.1 Copy production secrets from vault
vault kv get -format=json secret/adsbot/prod > config.json
python scripts/load_config_from_vault.py config.json

# 4.2 Verify all required environment variables
python << 'EOF'
import os
required_vars = [
    'TELEGRAM_TOKEN',
    'OPENAI_API_KEY',
    'DATABASE_URL',
    'FLASK_SECRET_KEY',
    'STRIPE_API_KEY',
    'JWT_SECRET'
]
print("Verifying environment variables...")
missing = []
for var in required_vars:
    if not os.getenv(var):
        missing.append(var)
        print(f"❌ {var}")
    else:
        print(f"✅ {var}")
if missing:
    print(f"\n❌ MISSING VARIABLES: {missing}")
    exit(1)
print("\n✅ All environment variables configured")
EOF

# 4.3 Verify configuration loads without errors
python -c "from adsbot.config import *; print('✅ Configuration loaded successfully')"
```

**Verification:**
- [ ] Secrets retrieved from vault
- [ ] All environment variables set
- [ ] Config file loads
- [ ] No configuration errors

### Step 5: Start Application (15 minutes)

```bash
# 5.1 Run syntax check on all Python files
python -m py_compile adsbot/*.py
echo "[$(date)] Syntax check passed" >> deployment.log

# 5.2 Start application with supervisor
supervisorctl reread
supervisorctl update
supervisorctl start adsbot:*

# 5.3 Wait for application startup
echo "Waiting for application to start..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null; then
        echo "✅ Application started"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 1
done

# 5.4 Verify application is running
supervisorctl status

# 5.5 Check process
ps aux | grep "python" | grep -v grep
```

**Expected Output:**
```
adsbot:adsbot-1                  RUNNING   pid 12345, uptime 0:00:25
adsbot:adsbot-2                  RUNNING   pid 12346, uptime 0:00:25
adsbot:adsbot-3                  RUNNING   pid 12347, uptime 0:00:25
```

**Verification:**
- [ ] No syntax errors
- [ ] Supervisor started processes
- [ ] Processes in RUNNING state
- [ ] Health endpoint responds
- [ ] Application accessible

### Step 6: Health Checks (10 minutes)

```bash
# 6.1 Check API endpoint
curl -I https://api.adsbot.com/health
# Expected: HTTP/1.1 200 OK

# 6.2 Check Telegram webhook
curl -X GET https://api.adsbot.com/telegram/webhook-info

# 6.3 Check database connectivity
python << 'EOF'
from adsbot.db import get_session
try:
    s = get_session()
    user_count = s.query(User).count()
    print(f"✅ Database OK: {user_count} users")
except Exception as e:
    print(f"❌ Database ERROR: {e}")
    exit(1)
EOF

# 6.4 Check OpenAI API
python << 'EOF'
from adsbot.chatgpt_integration import ChatGPTCampaignGenerator
try:
    gen = ChatGPTCampaignGenerator()
    print("✅ OpenAI API OK")
except Exception as e:
    print(f"❌ OpenAI API ERROR: {e}")
    exit(1)
EOF

# 6.5 Check scheduler jobs
python << 'EOF'
from adsbot.bot import scheduler
jobs = scheduler.get_jobs()
print(f"✅ Scheduler OK: {len(jobs)} jobs")
for job in jobs:
    print(f"  - {job.name}: {job.next_run_time}")
EOF

# 6.6 Check all handler registrations
python << 'EOF'
from adsbot.bot import application
handlers = len(application.handlers)
print(f"✅ {handlers} handlers registered")
EOF

# 6.7 Monitor logs for errors
tail -100 /var/log/adsbot/production.log | grep -i error
echo "✅ Log check complete"
```

**Verification Checklist:**
- [ ] HTTP 200 on /health endpoint
- [ ] Telegram webhook configured
- [ ] Database connects and has users
- [ ] OpenAI API responds
- [ ] Scheduler initialized with jobs
- [ ] All handlers registered
- [ ] No errors in logs

---

## 2.3 Smoke Testing (20 minutes)

### Critical Path Testing

```bash
# Test 1: User flow - Campaign Creation
echo "Test 1: Campaign Creation Flow..."
python tests/smoke_tests/test_campaign_creation.py
# Expected: PASSED ✅

# Test 2: AI Generation
echo "Test 2: ChatGPT Integration..."
python tests/smoke_tests/test_chatgpt_integration.py
# Expected: PASSED ✅

# Test 3: Payments
echo "Test 3: Payment Processing..."
python tests/smoke_tests/test_payment_flow.py
# Expected: PASSED ✅

# Test 4: Notifications
echo "Test 4: Notification System..."
python tests/smoke_tests/test_notifications.py
# Expected: PASSED ✅

# Test 5: Database
echo "Test 5: Database Operations..."
python tests/smoke_tests/test_database.py
# Expected: PASSED ✅

# Run all smoke tests
pytest tests/smoke_tests/ -v --tb=short
```

**Expected Result:**
```
test_campaign_creation.py::test_create_campaign PASSED
test_chatgpt_integration.py::test_generate_campaign PASSED
test_payment_flow.py::test_process_payment PASSED
test_notifications.py::test_send_notification PASSED
test_database.py::test_crud_operations PASSED

==================== 5 passed in 3.42s ====================
```

**Verification:**
- [ ] All 5 smoke tests pass
- [ ] No failures
- [ ] Response times < 1s each

### Manual Smoke Tests

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 1 | /start command | Main menu displays | ☐ |
| 2 | Create campaign | Campaign created successfully | ☐ |
| 3 | AI generation | Campaign content generated | ☐ |
| 4 | View earnings | Earnings displayed | ☐ |
| 5 | Send notification | Notification received | ☐ |

---

## 2.4 Traffic Migration (10 minutes)

```bash
# 4.1 Start routing traffic to new version
# Gradual ramp-up:
aws elbv2 modify-rule \
  --rule-arn arn:aws:... \
  --conditions Field=path-pattern,Values="/v1/*" \
  --actions Type=forward,TargetGroupArn=arn:aws:...-new

# 4.2 Monitor for errors
watch 'tail -20 /var/log/adsbot/production.log | tail -5'

# 4.3 Check error rates
# Expected: error rate stays < 0.5%

# 4.4 Gradually increase traffic to 100% new version
# Wait 5 minutes between steps:
# 10% → 50% → 100%
```

**Verification:**
- [ ] Traffic routing updated
- [ ] Error rate < 0.5%
- [ ] Response times normal
- [ ] No 5xx errors
- [ ] User reports normal

---

# 3. POST-DEPLOYMENT VALIDATION (30-60 minutes)

## 3.1 Automated Monitoring

```bash
# Monitor key metrics for 1 hour
watch -n 5 'ps aux | grep python | head -5'
watch -n 5 'tail -5 /var/log/adsbot/production.log'

# Check APM (Application Performance Monitoring)
# New Relic Dashboard → Check:
# - Error Rate (should be < 1%)
# - Response Time (should be < 500ms)
# - Throughput (should match expected)
# - Database query time (should be < 200ms)
```

## 3.2 Full Feature Validation

**Complete all UAT test cases from UAT_SCRIPT.md:**

| Section | Status | Time | Tester |
|---------|--------|------|--------|
| User Interface | ☐ Pass | | |
| Notifications | ☐ Pass | | |
| ChatGPT Integration | ☐ Pass | | |
| Payments | ☐ Pass | | |
| Analytics | ☐ Pass | | |
| Admin Panel | ☐ Pass | | |
| End-to-End Workflows | ☐ Pass | | |

## 3.3 Performance Validation

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| API Response Time (p95) | < 500ms | ___ | ☐ |
| Database Query (p95) | < 200ms | ___ | ☐ |
| Telegram Webhook Latency | < 3s | ___ | ☐ |
| Error Rate | < 1% | ___ | ☐ |
| CPU Usage | < 70% | ___ | ☐ |
| Memory Usage | < 80% | ___ | ☐ |

## 3.4 Customer Validation

| # | Task | Owner | Status |
|---|------|-------|--------|
| 3.4.1 | Run production smoke tests | QA | ☐ |
| 3.4.2 | Monitor for support tickets | Support | ☐ |
| 3.4.3 | Check social media mentions | Community | ☐ |
| 3.4.4 | Get customer feedback | Product | ☐ |

---

# 4. ISSUE RESPONSE PROCEDURES

## 4.1 Severity Levels

| Severity | Definition | Response Time | Action |
|----------|-----------|---|---|
| **CRITICAL** | Service down, data loss, security breach | IMMEDIATE | ROLLBACK |
| **HIGH** | Major feature broken, > 10% users affected | 15 minutes | INVESTIGATE |
| **MEDIUM** | Feature partially broken, < 10% affected | 1 hour | FIX or ROLLBACK |
| **LOW** | Minor UI issue, no user impact | 4 hours | Monitor, fix later |

## 4.2 Rollback Triggers

**ROLLBACK IMMEDIATELY if:**
- [ ] Database corruption detected
- [ ] Service unavailable for > 5 minutes
- [ ] Security vulnerability discovered
- [ ] Data loss occurring
- [ ] API error rate > 10%
- [ ] Customer facing critical issues

**DO NOT ROLLBACK if:**
- [ ] Minor UI glitch (fix in patch)
- [ ] Documentation issue
- [ ] Performance slightly degraded (< 5%)

## 4.3 Rollback Procedure

```bash
# 4.3.1 STOP everything
supervisorctl stop adsbot:*

# 4.3.2 Restore database from pre-deployment snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier adsbot-prod \
  --db-snapshot-identifier adsbot-prod-pre-deploy-YYYYMMDD

# Wait for restore to complete (~10 minutes)
aws rds describe-db-instances | grep DBInstanceStatus

# 4.3.3 Restore code from backup
cd /opt/adsbot-prod
rm -rf adsbot/
tar -xzf adsbot.prod.YYYYMMDD_HHMMSS.tar.gz

# 4.3.4 Start application
supervisorctl start adsbot:*

# 4.3.5 Verify rollback complete
curl -I https://api.adsbot.com/health

# 4.3.6 Route traffic back to old version
aws elbv2 modify-rule --rule-arn ... --actions Type=forward,TargetGroupArn=arn:aws:...-old

# 4.3.7 Notify stakeholders
# Email: "Production rolled back. Service restored. Post-mortem at 15:00."
```

**Rollback Verification:**
- [ ] Database restored
- [ ] Code restored
- [ ] Service responding
- [ ] All tests passing
- [ ] Traffic routed correctly
- [ ] Stakeholders notified

**Estimated Rollback Time:** 15-20 minutes

---

# 5. COMMUNICATION PLAN

## 5.1 Pre-Deployment Communication

**24 hours before:**
- Email to all stakeholders
- Slack announcement
- Status page update

**Content:**
```
Subject: AdsBot v1.0 Production Deployment - [DATE]

We will be deploying AdsBot v1.0 to production on [DATE] at [TIME] UTC.

Expected duration: 2-3 hours
Service availability: Expected to remain available (no downtime)
New features: [list major features]
Breaking changes: None

Questions? Contact: devops@adsbot.com
```

## 5.2 During Deployment

**Every 30 minutes:**
- [ ] Post status update to #operations
- [ ] Monitor support queue
- [ ] Check error rates
- [ ] Record any issues

**Deployment Status Template:**
```
🚀 DEPLOYMENT UPDATE [14:30 UTC]
Status: ✅ On track
Current step: Step 4 - Configuration Deployment
ETA completion: 15:30 UTC
Error rate: 0.2%
Issues: None
```

## 5.3 Post-Deployment Communication

**1 hour after successful deployment:**
```
✅ DEPLOYMENT SUCCESSFUL

AdsBot v1.0 is now live in production!

New features:
- Feature 1
- Feature 2
- Feature 3

Performance: All metrics normal
Error rate: 0.1%

Release notes: https://docs.adsbot.com/releases/v1.0.0
Questions? Contact: support@adsbot.com
```

**If rollback occurs:**
```
🔄 ROLLBACK EXECUTED

We rolled back to the previous version due to [issue].
We've restored all services and operations are normal.

Next steps:
- We're investigating the issue
- Post-mortem will be conducted
- We'll reschedule the deployment for [date]

Impact: None to users
Data: All data safe and restored
```

---

# 6. POST-DEPLOYMENT TASKS (24-48 hours)

## 6.1 First 24 Hours

| # | Task | Owner | Status | Time |
|---|------|-------|--------|------|
| 6.1.1 | Monitor error logs | DevOps | ☐ | Continuous |
| 6.1.2 | Monitor performance metrics | DevOps | ☐ | Continuous |
| 6.1.3 | Review customer feedback | Support | ☐ | Every 2 hours |
| 6.1.4 | Verify all notifications working | QA | ☐ | 6 times |
| 6.1.5 | Run health check script | DevOps | ☐ | Every 6 hours |
| 6.1.6 | Backup production database | DBA | ☐ | 12h mark |

## 6.2 First 48 Hours

| # | Task | Owner | Status |
|---|------|-------|--------|
| 6.2.1 | Conduct deployment post-mortem | Tech Lead | ☐ |
| 6.2.2 | Review all error logs | DevOps | ☐ |
| 6.2.3 | Document lessons learned | QA | ☐ |
| 6.2.4 | Update runbooks with findings | DevOps | ☐ |
| 6.2.5 | Verify no data loss | DBA | ☐ |
| 6.2.6 | Document metrics/performance | Tech Lead | ☐ |

---

# 7. DEPLOYMENT SIGN-OFF

## Final Approvals Required

| Role | Name | Approval | Date | Time | Signature |
|------|------|----------|------|------|-----------|
| Deployment Lead | | ☐ APPROVED ☐ DENIED | | | |
| Tech Lead | | ☐ APPROVED ☐ DENIED | | | |
| QA Lead | | ☐ APPROVED ☐ DENIED | | | |
| Product Owner | | ☐ APPROVED ☐ DENIED | | | |
| CTO/VP Eng | | ☐ APPROVED ☐ DENIED | | | |

## Deployment Record

| Item | Value |
|------|-------|
| **Deployment ID** | PROD-001 |
| **Version** | v1.0.0 |
| **Start Time** | __________ |
| **End Time** | __________ |
| **Duration** | __________ |
| **Status** | ☐ SUCCESS ☐ FAILURE ☐ ROLLBACK |
| **Deployed By** | __________ |
| **Approved By** | __________ |

## Deployment Summary

| Metric | Result |
|--------|--------|
| All pre-checks passed | ☐ YES ☐ NO |
| Code deployment successful | ☐ YES ☐ NO |
| Database migration successful | ☐ YES ☐ NO |
| Health checks passed | ☐ YES ☐ NO |
| Smoke tests passed | ☐ YES ☐ NO |
| Error rate < 1% | ☐ YES ☐ NO |
| Performance targets met | ☐ YES ☐ NO |
| No customer impact | ☐ YES ☐ NO |

## Issues Encountered

| # | Issue | Severity | Resolution | Time to Resolve |
|---|-------|----------|-----------|---|
| 1 | | | | |
| 2 | | | | |

---

# 8. APPENDIX: ROLLBACK DECISION TREE

```
Decision: Rollback?
│
├─→ Service Down?
│   └─→ YES → ROLLBACK IMMEDIATELY
│   └─→ NO → Continue
│
├─→ Database Corruption?
│   └─→ YES → ROLLBACK IMMEDIATELY
│   └─→ NO → Continue
│
├─→ Data Loss?
│   └─→ YES → ROLLBACK IMMEDIATELY
│   └─→ NO → Continue
│
├─→ Security Breach?
│   └─→ YES → ROLLBACK IMMEDIATELY
│   └─→ NO → Continue
│
├─→ Error Rate > 10%?
│   └─→ YES → INVESTIGATE
│       ├─→ Can fix in < 1 hour? → FIX
│       └─→ Cannot fix? → ROLLBACK
│   └─→ NO → Continue
│
├─→ Critical Feature Broken?
│   └─→ YES → INVESTIGATE
│       ├─→ Can fix in < 2 hours? → FIX
│       └─→ Cannot fix? → ROLLBACK
│   └─→ NO → Continue
│
└─→ Performance Degraded > 50%?
    └─→ YES → INVESTIGATE
        ├─→ Can optimize in < 4 hours? → OPTIMIZE
        └─→ Cannot optimize? → ROLLBACK
    └─→ NO → MONITOR (24-48 hours)
```

---

# 9. EMERGENCY CONTACTS

| Role | Name | Phone | Email | Slack |
|------|------|-------|-------|-------|
| On-Call DevOps | | | | |
| On-Call Tech Lead | | | | |
| VP Engineering | | | | |
| CTO | | | | |
| Head of Support | | | | |

**Escalation Path:**
1. Try to resolve → 15 min
2. Escalate to Tech Lead → 5 min
3. Escalate to VP Eng → 5 min
4. ROLLBACK decision by CTO → IMMEDIATE

---

END OF PRODUCTION DEPLOYMENT CHECKLIST v1.0

