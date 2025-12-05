STAGING DEPLOYMENT PLAN
=======================

## Deployment Version: 1.0
## Target Environment: STAGING
## Deployment Date: [TO BE SCHEDULED]
## Estimated Duration: 2-3 hours

---

# 1. PRE-DEPLOYMENT CHECKLIST (1 hour)

## 1.1 Code Readiness

| # | Item | Status | Owner |
|---|------|--------|-------|
| 1.1.1 | All tests passing (100% pass rate) | ☐ | Dev Team |
| 1.1.2 | No critical errors in codebase | ☐ | Dev Team |
| 1.1.3 | Code reviewed and approved | ☐ | Tech Lead |
| 1.1.4 | Security audit completed | ☐ | Security Team |
| 1.1.5 | Performance benchmark recorded | ☐ | QA Team |
| 1.1.6 | All documentation updated | ☐ | Tech Writer |
| 1.1.7 | Changelog prepared | ☐ | Dev Team |
| 1.1.8 | Release notes created | ☐ | Product |

## 1.2 Environment Preparation

| # | Item | Expected | Owner |
|---|------|----------|-------|
| 1.2.1 | Staging server online | ping responds | DevOps |
| 1.2.2 | Python 3.13 installed | version check OK | DevOps |
| 1.2.3 | Database backup created | adsbot.db.bak exists | DBA |
| 1.2.4 | Dependencies installable | pip install succeeds | DevOps |
| 1.2.5 | Environment variables set | All secrets configured | DevOps |
| 1.2.6 | Logs directory ready | /logs writable | DevOps |
| 1.2.7 | Monitoring configured | New Relic/DataDog ready | DevOps |
| 1.2.8 | Rollback procedure tested | Can restore from backup | DevOps |

## 1.3 Stakeholder Notification

| # | Recipient | Message | Status |
|---|-----------|---------|--------|
| 1.3.1 | QA Team | Staging deployment schedule | ☐ |
| 1.3.2 | Product Owner | Features for testing | ☐ |
| 1.3.3 | Support Team | Known issues/workarounds | ☐ |
| 1.3.4 | Marketing | Launch readiness status | ☐ |

---

# 2. DEPLOYMENT EXECUTION (1 hour)

## 2.1 Deployment Steps

### Step 1: Code Deployment (10 minutes)

```bash
# 1.1 SSH into staging server
ssh staging-server

# 1.2 Navigate to deployment directory
cd /opt/adsbot

# 1.3 Create backup of current deployment
cp -r adsbot adsbot.backup.$(date +%Y%m%d_%H%M%S)

# 1.4 Pull latest code from Git
git fetch origin
git checkout main
git pull origin main

# 1.5 Verify code integrity
git log --oneline -5
git status
```

**Deployment Checklist:**
- [ ] SSH connection successful
- [ ] Current deployment backed up
- [ ] Git pull completed
- [ ] No merge conflicts
- [ ] Latest code deployed

**Expected Output:**
```
Already on 'main'
Your branch is up to date with 'origin/main'.
```

### Step 2: Dependency Installation (5 minutes)

```bash
# 2.1 Activate virtual environment
source /opt/adsbot/.venv/bin/activate

# 2.2 Upgrade pip
pip install --upgrade pip

# 2.3 Install/upgrade dependencies
pip install -r requirements.txt

# 2.4 Verify all imports work
python -c "from adsbot.bot import *; print('✅ All imports successful')"
```

**Verification:**
- [ ] Virtual environment activated
- [ ] All packages installed
- [ ] No import errors
- [ ] Requirements match production

### Step 3: Database Migration (5 minutes)

```bash
# 3.1 Check current database version
python -c "from adsbot.db import engine; print(f'DB: {engine.url}')"

# 3.2 Run migrations
python scripts/migrate.py

# 3.3 Verify database integrity
python -c "from adsbot.db import get_session; s = get_session(); print(f'✅ {len(s.query(User).all())} users')"

# 3.4 Seed test data
python scripts/seed_data.py
```

**Verification:**
- [ ] Database connected
- [ ] Tables created/migrated
- [ ] Test data seeded
- [ ] No data loss

### Step 4: Configuration Deployment (5 minutes)

```bash
# 4.1 Copy configuration (if needed)
cp /secure/staging_config.env .env.staging

# 4.2 Verify required environment variables
python -c "
import os
required = ['TELEGRAM_TOKEN', 'OPENAI_API_KEY', 'DATABASE_URL']
for var in required:
    val = os.getenv(var)
    status = '✅' if val else '❌'
    print(f'{status} {var}')
"

# 4.3 Load configuration
export $(cat .env.staging | xargs)

# 4.4 Verify config
python -c "from adsbot.config import *; print('✅ Config loaded')"
```

**Verification:**
- [ ] All environment variables set
- [ ] Config loads without error
- [ ] Secrets properly configured
- [ ] No hardcoded credentials

### Step 5: Application Start (10 minutes)

```bash
# 5.1 Start bot in background with nohup
nohup python main.py > /var/log/adsbot/staging.log 2>&1 &

# 5.2 Wait for startup
sleep 10

# 5.3 Check if running
ps aux | grep "python main.py" | grep -v grep

# 5.4 Tail logs to verify startup
tail -f /var/log/adsbot/staging.log
```

**Expected Log Output:**
```
2024-12-27 10:00:00 - Bot started successfully
2024-12-27 10:00:01 - Telegram connection established
2024-12-27 10:00:02 - Database connected
2024-12-27 10:00:03 - OpenAI API key validated
2024-12-27 10:00:04 - APScheduler initialized
2024-12-27 10:00:05 - Conversation handlers registered
```

**Verification:**
- [ ] Process started (PID shown)
- [ ] No errors in logs
- [ ] Telegram connection OK
- [ ] Database OK
- [ ] OpenAI API OK
- [ ] Scheduler OK

### Step 6: Health Check (10 minutes)

```bash
# 6.1 Test bot /start command
curl -X POST https://staging-api.adsbot.com/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"update_id": 1, "message": {"text": "/start", "chat": {"id": 999999}}}'

# 6.2 Check database connectivity
python -c "
from adsbot.db import get_session
s = get_session()
users = s.query(User).count()
print(f'✅ Database OK: {users} users')
"

# 6.3 Verify OpenAI API
python -c "
from adsbot.chatgpt_integration import ChatGPTCampaignGenerator
gen = ChatGPTCampaignGenerator()
print('✅ OpenAI API OK')
"

# 6.4 Check scheduled tasks
python -c "
from adsbot.bot import scheduler
jobs = scheduler.get_jobs()
print(f'✅ Scheduler OK: {len(jobs)} jobs queued')
"
```

**Verification Checklist:**
- [ ] HTTP endpoint responds
- [ ] Database queries work
- [ ] OpenAI API responds
- [ ] Scheduler initialized
- [ ] All handlers registered

---

## 2.2 Deployment Timeline

| Step | Duration | Owner | Status |
|------|----------|-------|--------|
| Code Deployment | 10 min | DevOps | ☐ |
| Dependency Install | 5 min | DevOps | ☐ |
| Database Migration | 5 min | DBA | ☐ |
| Configuration | 5 min | DevOps | ☐ |
| Application Start | 10 min | DevOps | ☐ |
| Health Checks | 10 min | QA | ☐ |
| **TOTAL** | **45 min** | | |

---

# 3. POST-DEPLOYMENT VERIFICATION (30 minutes)

## 3.1 Automated Tests

```bash
# 3.1.1 Run all unit tests
cd /opt/adsbot
pytest tests/ -v --tb=short

# 3.1.2 Run integration tests
pytest tests/test_integration.py -v

# 3.1.3 Generate test report
pytest tests/ --html=report.html --self-contained-html

# 3.1.4 Check test coverage
pytest tests/ --cov=adsbot --cov-report=html
```

**Expected Results:**
```
tests/test_bot.py::test_start ✅ PASSED
tests/test_chatgpt_integration.py::test_campaign_generation ✅ PASSED
tests/test_notifications.py::test_notification_send ✅ PASSED
...
==================== 40 passed in 2.34s ====================
```

**Verification:**
- [ ] All tests pass (100%)
- [ ] Coverage > 80%
- [ ] No warnings
- [ ] Report generated

## 3.2 Manual Verification

| # | Test Case | Expected | Status | Tester |
|---|-----------|----------|--------|--------|
| 3.2.1 | /start command | Main menu displays | ☐ | QA |
| 3.2.2 | Campaign creation | Can create campaign | ☐ | QA |
| 3.2.3 | AI generation | ChatGPT works | ☐ | QA |
| 3.2.4 | Payment flow | Payment processes | ☐ | QA |
| 3.2.5 | Notifications | Notifications send | ☐ | QA |
| 3.2.6 | Analytics | Reports generate | ☐ | QA |
| 3.2.7 | Admin panel | Admin functions work | ☐ | QA |
| 3.2.8 | Error handling | Errors handled gracefully | ☐ | QA |

## 3.3 Performance Verification

```bash
# 3.3.1 Monitor system resources
top -p $(pgrep -f "python main.py")

# 3.3.2 Check memory usage
ps aux | grep "python main.py" | awk '{print $6}' # MB

# 3.3.3 Monitor database connections
python -c "
from adsbot.db import engine
print(f'DB Pool: {engine.pool}')
"

# 3.3.4 Check API response times
time curl -X POST https://staging-api.adsbot.com/webhook/telegram -d '{}'
```

**Performance Targets:**
- Memory usage: < 500 MB
- CPU usage: < 10% idle
- API response time: < 1 second
- Database queries: < 500ms

**Verification:**
- [ ] Memory usage acceptable
- [ ] CPU usage normal
- [ ] Response times good
- [ ] No memory leaks

## 3.4 Security Verification

```bash
# 3.4.1 Check for hardcoded credentials
grep -r "password\|token\|key" --include="*.py" | grep -v "os.getenv\|config\|secrets"

# 3.4.2 Verify environment variables
env | grep -E "API|TOKEN|SECRET"

# 3.4.3 Check file permissions
ls -la /opt/adsbot/.env*

# 3.4.4 Verify SSL/TLS
curl -I https://staging-api.adsbot.com
```

**Verification:**
- [ ] No hardcoded credentials
- [ ] SSL/TLS enabled
- [ ] File permissions correct
- [ ] Secrets properly stored

---

# 4. USER ACCEPTANCE TESTING (STAGING) (4-6 hours)

## 4.1 UAT Scope

**Duration:** 4-6 hours (running in parallel with deployment)
**Location:** Staging environment
**Reference:** See UAT_SCRIPT.md for full test procedures

**Testing Phases:**

| Phase | Duration | Focus | Responsible |
|-------|----------|-------|-------------|
| Basic Features | 1 hour | UI, menus, basic flows | QA |
| ChatGPT Integration | 1 hour | AI generation, all prompts | QA |
| Payment Processing | 1 hour | Payment flows, notifications | QA |
| End-to-End Workflows | 1 hour | Complete user journeys | QA |
| Error Scenarios | 1 hour | Edge cases, error handling | QA |
| Performance | 0.5 hours | Load testing, response times | QA |
| Security | 0.5 hours | Rate limiting, validation | QA |

## 4.2 Critical Test Cases (Priority)

**MUST PASS before production:**

1. ✅ Bot starts and responds to /start
2. ✅ Campaign creation flow works end-to-end
3. ✅ ChatGPT generates campaigns in Italian
4. ✅ Payments process without errors
5. ✅ Notifications send correctly
6. ✅ Database operations work
7. ✅ Error messages display properly
8. ✅ Admin panel accessible to admins only

## 4.3 UAT Signoff

| Tester | Test Date | Pass/Fail | Signature |
|--------|-----------|-----------|-----------|
| QA Lead | | ☐ Pass ☐ Fail | |
| Product Owner | | ☐ Pass ☐ Fail | |
| Tech Lead | | ☐ Pass ☐ Fail | |

---

# 5. MONITORING & LOGGING (STAGING)

## 5.1 Monitoring Setup

**Tools:** New Relic / DataDog / CloudWatch

**Metrics to Monitor:**
- CPU usage
- Memory usage
- Database connection pool
- API response times
- Error rate
- Telegram webhook latency
- OpenAI API call success rate

## 5.2 Log Aggregation

**Log Files:**
- `/var/log/adsbot/staging.log` - Main application log
- `/var/log/adsbot/error.log` - Error log
- `/var/log/adsbot/access.log` - HTTP access log
- `/var/log/adsbot/database.log` - Database queries

**Log Retention:** Keep 30 days on staging

## 5.3 Alert Configuration

| Alert | Trigger | Action | Owner |
|-------|---------|--------|-------|
| High CPU | > 80% for 5 min | Email DevOps | DevOps |
| High Memory | > 80% for 5 min | Email DevOps | DevOps |
| DB Connection Error | Any connection error | Slack alert | DevOps |
| API Error Rate | > 5% errors | Slack + Email | DevOps |
| Telegram Webhook Failures | > 3 consecutive failures | Page on-call | DevOps |

---

# 6. STAGING VALIDATION (DAILY FOR 1 WEEK)

## 6.1 Daily Health Checks

**Run every morning for 7 days:**

```bash
#!/bin/bash
# daily_health_check.sh

echo "=== STAGING HEALTH CHECK ==="
echo "Date: $(date)"
echo ""

# 6.1.1 Check process running
echo "1. Process Status:"
ps aux | grep "python main.py" | grep -v grep
if [ $? -eq 0 ]; then echo "✅ Bot running"; else echo "❌ Bot NOT running"; fi

# 6.1.2 Check database
echo ""
echo "2. Database Status:"
python -c "
from adsbot.db import get_session
try:
    s = get_session()
    count = s.query(User).count()
    print(f'✅ Database OK ({count} users)')
except Exception as e:
    print(f'❌ Database ERROR: {e}')
"

# 6.1.3 Check logs for errors
echo ""
echo "3. Recent Errors:"
tail -20 /var/log/adsbot/staging.log | grep -i error || echo "✅ No errors"

# 6.1.4 Check OpenAI API
echo ""
echo "4. OpenAI API Status:"
python -c "
try:
    from adsbot.chatgpt_integration import ChatGPTCampaignGenerator
    gen = ChatGPTCampaignGenerator()
    print('✅ OpenAI API responding')
except Exception as e:
    print(f'❌ OpenAI API ERROR: {e}')
"

# 6.1.5 System resources
echo ""
echo "5. System Resources:"
ps aux | grep "python main.py" | grep -v grep | awk '{print "Memory: " $6 "MB, CPU: " $3 "%"}'

echo ""
echo "=== END HEALTH CHECK ==="
```

## 6.2 Weekly Comprehensive Tests

**Run once per week, full UAT:**

- All 18 test sections from UAT_SCRIPT.md
- Performance benchmarking
- Load testing (50+ concurrent users)
- Security testing
- Database integrity checks
- Backup/restore testing

---

# 7. KNOWN ISSUES & WORKAROUNDS

| Issue | Workaround | Severity | Status |
|-------|-----------|----------|--------|
| Database locks on high load | Reduce connection pool | Medium | Monitored |
| OpenAI rate limits | Implement queue | Low | Planned |
| Telegram webhook timeouts | Increase timeout to 30s | Low | Configured |
| Memory leak in scheduler | Restart daily at 3 AM | Medium | Scheduled |

---

# 8. ROLLBACK PROCEDURE

**If critical issues found:**

```bash
# 8.1 Stop current deployment
pkill -f "python main.py"

# 8.2 Restore database backup
cp adsbot.db adsbot.db.backup
cp adsbot.db.bak adsbot.db

# 8.3 Restore code from backup
rm -rf adsbot/
cp -r adsbot.backup.20241227_100000/ adsbot/

# 8.4 Restart bot
source .venv/bin/activate
nohup python main.py > /var/log/adsbot/staging.log 2>&1 &

# 8.5 Verify rollback
sleep 5
ps aux | grep "python main.py" | grep -v grep
```

**Rollback Decision Criteria:**
- Database corruption: ROLLBACK
- Data loss: ROLLBACK
- Security breach: ROLLBACK
- Unrecoverable errors: ROLLBACK
- Performance degradation > 50%: INVESTIGATE, then decide
- Minor UI bugs: DO NOT ROLLBACK (fix in next release)

---

# 9. PROMOTION CRITERIA TO PRODUCTION

**STAGING deployment must meet ALL criteria:**

- [ ] All 40 unit tests pass (100%)
- [ ] All UAT test cases pass
- [ ] No critical bugs found
- [ ] No data loss
- [ ] Performance meets targets
- [ ] Security review passed
- [ ] 7 days stable operation without issues
- [ ] QA sign-off received
- [ ] Product Owner approval
- [ ] Tech Lead sign-off

---

# 10. SIGN-OFF

## Deployment Authorization

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tech Lead | | | |
| QA Lead | | | |
| DevOps Lead | | | |
| Product Owner | | | |

## Deployment Record

**Deployment ID:** STAGING-001
**Deployment Date:** ________________
**Deployed By:** ________________
**Duration:** ________________
**Status:** ☐ SUCCESSFUL ☐ FAILED ☐ ROLLBACK

## Issues Found During Staging

| # | Issue | Severity | Resolution | Date Resolved |
|---|-------|----------|-----------|---|
| 1 | | | | |
| 2 | | | | |

## Readiness for Production

**Ready for Production:** ☐ YES ☐ NO ☐ PENDING

**Approval Date:** ________________

**Next Steps:** 
- [ ] Schedule production deployment
- [ ] Prepare production deployment plan
- [ ] Notify stakeholders
- [ ] Create production runbook

---

END OF STAGING DEPLOYMENT PLAN v1.0

