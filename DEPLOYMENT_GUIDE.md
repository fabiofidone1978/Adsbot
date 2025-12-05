# 🚀 DEPLOYMENT GUIDE

**Project:** ADSBOT Marketplace V2  
**Version:** 2.0.0  
**Release Date:** December 5, 2025

---

## 📋 PRE-DEPLOYMENT CHECKLIST

- [x] Code review completed
- [x] All tests passed
- [x] No critical bugs
- [x] Database migrations tested
- [x] Configuration files prepared
- [x] Environment variables set
- [x] Secrets properly configured
- [x] Backups created

---

## 🔧 DEPLOYMENT STEPS

### 1. STAGING DEPLOYMENT

#### 1.1 Clone/Update Repository
```bash
cd /path/to/deployment
git clone https://github.com/fabiofidone1978/Adsbot.git adsbot-staging
cd adsbot-staging
git checkout main
```

#### 1.2 Setup Python Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 1.3 Configure Environment
```bash
cp .env.example .env
# Edit .env with staging values:
# - TELEGRAM_BOT_TOKEN=<staging-token>
# - DATABASE_URL=sqlite:///./adsbot_staging.db
# - ENVIRONMENT=staging
```

#### 1.4 Initialize Database
```bash
python -c "from adsbot.db import init_db; init_db()"
```

#### 1.5 Run Tests
```bash
pytest tests/ -v
python -m py_compile adsbot/bot.py
python -m py_compile adsbot/models.py
```

#### 1.6 Start Bot
```bash
python main.py
# Or with gunicorn (for production):
gunicorn -w 1 -k uvicorn.workers.UvicornWorker adsbot.bot:application
```

#### 1.7 Verify Staging
- [ ] Bot is online and responding to /start
- [ ] Catalog loads with channels
- [ ] Order creation works
- [ ] Editor notifications received
- [ ] Admin panel accessible
- [ ] Database queries working

---

### 2. PRODUCTION DEPLOYMENT

#### 2.1 Prepare Production Environment
```bash
# Create production directory
mkdir /opt/adsbot-prod
cd /opt/adsbot-prod

# Clone repository
git clone https://github.com/fabiofidone1978/Adsbot.git .
git checkout main
```

#### 2.2 Setup Production Python Environment
```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

#### 2.3 Configure Production Environment
```bash
# Create .env file with production values
cat > .env << EOF
TELEGRAM_BOT_TOKEN=<production-token>
DATABASE_URL=postgresql://user:password@db.example.com/adsbot_prod
ENVIRONMENT=production
LOG_LEVEL=INFO
SENTRY_DSN=<sentry-dsn-if-using>
STRIPE_KEY=<stripe-key>
STRIPE_SECRET=<stripe-secret>
EOF

# Secure permissions
chmod 600 .env
```

#### 2.4 Database Migration (Production)
```bash
# Backup existing database first
pg_dump adsbot_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migrations
python -c "from adsbot.db import init_db; init_db()"

# Verify migrations
psql adsbot_prod -c "SELECT COUNT(*) FROM users;"
```

#### 2.5 Setup Systemd Service
```bash
# Create systemd service file
sudo tee /etc/systemd/system/adsbot.service << EOF
[Unit]
Description=ADSBOT Telegram Bot
After=network.target

[Service]
Type=simple
User=adsbot
WorkingDirectory=/opt/adsbot-prod
Environment="PATH=/opt/adsbot-prod/venv/bin"
ExecStart=/opt/adsbot-prod/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable adsbot
sudo systemctl start adsbot
```

#### 2.6 Setup Nginx Reverse Proxy (Optional)
```nginx
server {
    listen 443 ssl http2;
    server_name api.adsbot.example.com;

    ssl_certificate /etc/letsencrypt/live/adsbot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/adsbot.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2.7 Setup Logging
```bash
# Create logs directory
mkdir -p /var/log/adsbot
chown adsbot:adsbot /var/log/adsbot

# Configure log rotation
sudo tee /etc/logrotate.d/adsbot << EOF
/var/log/adsbot/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 adsbot adsbot
    sharedscripts
}
EOF
```

#### 2.8 Verify Production Deployment
```bash
# Check service status
sudo systemctl status adsbot

# Check logs
tail -f /var/log/adsbot/adsbot.log

# Test bot API
curl -X POST https://api.adsbot.example.com/health
```

---

## 📊 DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] Code review approved
- [ ] All tests passing
- [ ] Database backups created
- [ ] DNS configured
- [ ] SSL certificates ready
- [ ] Environment variables prepared
- [ ] Secrets manager configured
- [ ] Monitoring setup ready

### Staging
- [ ] Repository cloned
- [ ] Dependencies installed
- [ ] Database initialized
- [ ] Bot online
- [ ] Manual testing completed
- [ ] Performance acceptable
- [ ] No errors in logs

### Production
- [ ] Directory created
- [ ] Code deployed
- [ ] Database migrated
- [ ] Service running
- [ ] Health checks passing
- [ ] Monitoring active
- [ ] Logs configured
- [ ] Rollback plan ready

---

## 🔄 ROLLBACK PROCEDURE

### If Issues Occur:

**Option 1: Quick Restart**
```bash
sudo systemctl restart adsbot
```

**Option 2: Revert to Previous Commit**
```bash
cd /opt/adsbot-prod
git reset --hard HEAD~1
python main.py
```

**Option 3: Database Rollback**
```bash
# Restore from backup
psql adsbot_prod < backup_$(date +%Y%m%d_%H%M%S).sql

# Verify
psql adsbot_prod -c "SELECT COUNT(*) FROM users;"
```

**Option 4: Full Environment Revert**
```bash
# Stop service
sudo systemctl stop adsbot

# Remove current deployment
rm -rf /opt/adsbot-prod

# Redeploy from last known good commit
git clone -b <last-stable-tag> https://github.com/fabiofidone1978/Adsbot.git /opt/adsbot-prod

# Restore
sudo systemctl start adsbot
```

---

## 📈 POST-DEPLOYMENT MONITORING

### Health Checks (Every 5 minutes)
```bash
# Check bot is running
curl http://localhost:8000/health

# Check database connection
python -c "from adsbot.db import get_session; print('DB OK')"

# Check telegram API connectivity
python -c "import asyncio; from telegram import Bot; asyncio.run(Bot(token='xxx').get_me())"
```

### Key Metrics to Monitor
- **Bot Response Time:** <1s
- **Database Query Time:** <500ms
- **API Error Rate:** <0.1%
- **Order Processing Time:** <2s
- **Memory Usage:** <500MB
- **CPU Usage:** <20%

### Alert Conditions
- [ ] High error rate (>1%)
- [ ] Slow response (>5s)
- [ ] Database connection failed
- [ ] Out of memory
- [ ] High CPU usage (>80%)
- [ ] Disk space low (<10%)

---

## 🔐 SECURITY CHECKLIST

- [ ] All secrets in environment variables (not in code)
- [ ] Database passwords strong and unique
- [ ] SSL/TLS enabled
- [ ] Firewall rules configured
- [ ] API rate limiting enabled
- [ ] SQL injection prevention verified
- [ ] XSS prevention verified
- [ ] CSRF tokens in forms
- [ ] User input sanitized
- [ ] Logs don't contain sensitive data

---

## 📱 TELEGRAM BOT TOKEN MANAGEMENT

### Getting Bot Token
1. Open Telegram app
2. Search for `@BotFather`
3. Create new bot with `/newbot`
4. Store token securely in `.env`

### Token Security
- ⚠️ NEVER commit token to git
- ⚠️ NEVER share token in messages
- ✅ Use environment variables
- ✅ Use secrets manager (e.g., AWS Secrets Manager)
- ✅ Rotate token if compromised

---

## 📊 DEPLOYMENT METRICS

After deployment, track:

```markdown
| Metric | Target | Actual |
|--------|--------|--------|
| Bot Uptime | >99.9% | ___% |
| Response Time | <1s | ___ms |
| Error Rate | <0.1% | ___%  |
| DB Query Time | <500ms | ___ms |
| Memory Usage | <500MB | ___MB |
| CPU Usage | <20% | ___%  |
```

---

## 🆘 TROUBLESHOOTING

### Bot Not Responding
**Solution:**
```bash
sudo systemctl status adsbot
tail -f /var/log/adsbot/adsbot.log
sudo systemctl restart adsbot
```

### Database Connection Failed
**Solution:**
```bash
# Check database is running
psql -U adsbot -d adsbot_prod -c "SELECT 1"

# Check connection string in .env
cat .env | grep DATABASE_URL

# Restart bot
sudo systemctl restart adsbot
```

### High Memory Usage
**Solution:**
```bash
# Kill bot process
kill -9 $(pgrep -f 'python main.py')

# Check for memory leaks
python -m memory_profiler main.py

# Restart with limits
systemd-run --scope -p MemoryLimit=1G python main.py
```

### Missing Orders After Restart
**Solution:**
```bash
# Check database integrity
python -c "from adsbot.models import MarketplaceOrder; print(MarketplaceOrder.query.count())"

# If missing, restore from backup
psql adsbot_prod < backup_*.sql
```

---

## 📞 SUPPORT CONTACTS

**On-Call Team:** [Contact info]  
**Emergency Number:** [Number]  
**Escalation:** [Process]

---

## 📝 DEPLOYMENT SIGN-OFF

**Deployed By:** ________________________  
**Date/Time:** ________________________  
**Environment:** Staging / Production  
**Version:** 2.0.0  
**Commit:** eef79f5

**Pre-Deployment Testing:** ✅ Passed / ❌ Failed  
**Post-Deployment Verification:** ✅ Passed / ❌ Failed

**Approved By:** ________________________  
**Approval Date:** ________________________

---

**Document Version:** 1.0  
**Last Updated:** December 5, 2025
