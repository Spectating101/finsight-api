# Monitoring & Alerting Setup Guide

Complete guide to set up monitoring so you know when things break (before customers do).

---

## 🎯 Monitoring Goals

1. **Uptime:** Know when API is down
2. **Errors:** Get notified of 500 errors
3. **Performance:** Track slow endpoints
4. **Business:** Monitor signups, revenue, churn
5. **Security:** Detect suspicious activity

---

## 1. Uptime Monitoring (Free - 5 minutes)

### UptimeRobot (Recommended)

**What it does:** Pings your API every 5 minutes, emails you if it's down.

**Setup:**

1. Go to: https://uptimerobot.com
2. Sign up (free plan: 50 monitors)
3. Click "Add New Monitor"
4. Configure:
   ```
   Monitor Type: HTTP(S)
   Friendly Name: FinSight API - Health
   URL: https://YOUR_DOMAIN/health
   Monitoring Interval: 5 minutes
   ```
5. Add alert contacts:
   - Email: your@email.com
   - Optional: SMS (paid), Slack webhook

6. Create additional monitors:
   ```
   Monitor 2:
   Name: FinSight API - Register
   URL: https://YOUR_DOMAIN/api/v1/auth/register
   Method: POST
   Headers: Content-Type: application/json
   Body: {"email": "test@test.com"}
   Expected: 200 or 400 (validates endpoint works)
   ```

**What you get:**
- Email when site goes down
- Weekly uptime reports
- Public status page (optional)

---

## 2. Error Monitoring (Already Set Up ✓)

### Sentry

**What it does:** Captures all Python exceptions, groups them, emails you.

**You already have this!** Just verify it's working:

1. Check `.env` has `SENTRY_DSN=https://...`
2. Go to: https://sentry.io
3. Check for events
4. Configure alerts:
   - Go to: Alerts → Create Alert
   - Condition: "When an event is first seen"
   - Action: Email you
   - Create another: "When error count > 10 in 1 hour"

**Test it:**
```python
# Add this to any endpoint temporarily
raise Exception("Test Sentry alert")
```

Visit that endpoint, check Sentry dashboard for the error.

---

## 3. Performance Monitoring (Free)

### Sentry Performance (Already Enabled)

Your `SENTRY_TRACES_SAMPLE_RATE=0.1` means 10% of requests tracked.

**View performance:**
1. Sentry dashboard → Performance
2. See slow endpoints
3. See database query times
4. Track API to third-party latency

**Create alert for slow endpoints:**
- Alert: "When p95 response time > 2000ms"
- Action: Email you

---

## 4. Log Aggregation (Optional - $0-20/mo)

### Better Stack (Formerly Logtail)

**What it does:** Collects all logs in one place, searchable.

**Setup:**

1. Go to: https://betterstack.com/logs
2. Create source: "FinSight API"
3. Get ingest token
4. Add to your app:

```python
# src/main.py
import logging
import better_stack_logs

# Add this in startup
if os.getenv("BETTERSTACK_SOURCE_TOKEN"):
    better_stack_logs.init(
        source_token=os.getenv("BETTERSTACK_SOURCE_TOKEN")
    )
```

5. Now search logs:
   - Filter by user_id
   - Filter by error level
   - Create dashboards

**Free tier:** 1GB/month (plenty for starting out)

---

## 5. Business Metrics Dashboard (Free)

### Stripe Dashboard

**What to monitor:**

1. **MRR (Monthly Recurring Revenue):**
   - Stripe Dashboard → Analytics → MRR
   - Check daily

2. **Churn:**
   - Stripe Dashboard → Customers → Cancelled
   - Goal: <5% monthly churn

3. **Failed Payments:**
   - Stripe Dashboard → Payments → Failed
   - Email these customers (card expired?)

**Set up alerts:**
- Stripe → Settings → Emails → Failed Payments
- Enable: "Email me when payment fails"

---

## 6. API Usage Analytics (Free)

### Prometheus + Grafana (Advanced - Optional)

**You already have Prometheus metrics exposed!**

Your app has: `/metrics` endpoint (hidden from docs)

**Quick setup:**

1. Install Grafana Cloud (free tier)
2. Add Prometheus data source
3. Point to: `https://YOUR_DOMAIN/metrics`
4. Import dashboard template

**Metrics you're already tracking:**
- Request count per endpoint
- Response times
- Error rates
- Active connections

---

## 7. Security Monitoring (Free)

### Cloudflare (Optional but Recommended)

**What it does:**
- DDoS protection
- Rate limiting (additional layer)
- Analytics
- SSL

**Setup:**

1. Go to: https://cloudflare.com
2. Add your domain
3. Update nameservers
4. Enable:
   - Auto HTTPS
   - Rate limiting (backup to your Redis)
   - Bot protection

**Free tier includes:**
- DDoS mitigation
- SSL certificates
- CDN for static files
- Analytics dashboard

---

## 8. Database Monitoring

### PostgreSQL Logs

**If using Heroku:**
```bash
heroku logs --tail --app YOUR_APP | grep postgres
```

**If using Railway/Render:**
- Check dashboard → Database → Metrics

**Monitor:**
- Active connections (should be < pool size)
- Slow queries (> 1 second)
- Connection errors

**Set up alerts:**
- Database CPU > 80% for 5 minutes
- Connection pool exhausted
- Disk space > 80%

---

## 9. Alerting Rules

### Critical Alerts (Wake you up)

Set these to SMS/phone call:

1. **API down for 5+ minutes**
   - UptimeRobot alert
   - Action: Check immediately

2. **Error rate > 50% for 5 minutes**
   - Sentry alert
   - Action: Roll back deploy

3. **Database down**
   - Sentry alert (connection errors)
   - Action: Check provider status

### Warning Alerts (Email is fine)

1. **API slow (p95 > 2 seconds)**
   - Sentry performance alert
   - Action: Investigate next day

2. **Error spike (10+ errors in 1 hour)**
   - Sentry alert
   - Action: Check logs

3. **Failed payment**
   - Stripe email
   - Action: Email customer

4. **Churn (customer cancels)**
   - Stripe email
   - Action: Send exit survey

---

## 10. Status Page (Optional - Build Trust)

### StatusPage.io OR Build Your Own

**Option A: StatusPage.io** ($29/mo)
- Professional status page
- Incident management
- Subscriber notifications

**Option B: DIY (Free)**

Add to your site:

```html
<div class="status">
  <h3>System Status</h3>
  <div class="status-item">
    <span>API</span>
    <span class="status-badge operational">Operational</span>
  </div>
  <div class="status-item">
    <span>Database</span>
    <span class="status-badge operational">Operational</span>
  </div>
  <small>Last updated: <span id="last-check"></span></small>
</div>

<script>
  // Fetch from /health every 60 seconds
  setInterval(async () => {
    const response = await fetch('/health');
    const data = await response.json();
    // Update badges based on data.status
  }, 60000);
</script>
```

---

## 11. Monitoring Checklist

### Daily (5 minutes)

- [ ] Check Stripe dashboard (new customers?)
- [ ] Check Sentry (any new errors?)
- [ ] Check UptimeRobot (any downtime?)

### Weekly (15 minutes)

- [ ] Review slow endpoints (Sentry performance)
- [ ] Check churn rate (Stripe)
- [ ] Review failed payments (Stripe)
- [ ] Check database usage (disk space, connections)

### Monthly (30 minutes)

- [ ] Review all alerting rules (still relevant?)
- [ ] Check log storage usage (upgrade if needed)
- [ ] Review security logs (suspicious activity?)
- [ ] Update dependencies (security patches)

---

## 12. Incident Response Plan

### When Something Breaks

**Step 1: Assess (2 minutes)**
- Check UptimeRobot: Is site down?
- Check Sentry: What's the error?
- Check logs: When did it start?

**Step 2: Communicate (5 minutes)**
- If affecting users: Post on status page
- If major: Email active users
- Tweet: "We're investigating an issue..."

**Step 3: Fix (Variable)**
- Rollback deploy if recent
- Restart server if needed
- Fix bug and deploy
- Monitor for 30 minutes

**Step 4: Post-Mortem (1 day later)**
- Write what happened
- What we did
- How we prevent it
- Post publicly (builds trust)

---

## 13. Monitoring Budget

### Free Tier (Good for <$1K MRR)

| Service | Cost | What You Get |
|---------|------|--------------|
| UptimeRobot | $0 | 50 monitors, 5-min checks |
| Sentry | $0 | 5K events/mo |
| Stripe | $0 | Dashboard + basic analytics |
| Cloudflare | $0 | DDoS + SSL + CDN |
| **Total** | **$0/mo** | **Covers basics** |

### Paid Tier (At $1K+ MRR)

| Service | Cost | What You Get |
|---------|------|--------------|
| UptimeRobot Pro | $7/mo | 1-min checks, SMS alerts |
| Sentry Team | $26/mo | 50K events/mo, performance |
| Better Stack | $20/mo | 5GB logs/mo |
| StatusPage | $29/mo | Professional status page |
| **Total** | **$82/mo** | **Professional setup** |

---

## 14. Key Metrics to Track

### Technical Metrics

1. **Uptime:** >99.9% (43 minutes downtime/month allowed)
2. **Response Time:** p95 < 500ms, p99 < 1000ms
3. **Error Rate:** <0.1% (1 in 1000 requests)
4. **Database Connections:** <80% of pool

### Business Metrics

1. **MRR:** Monthly Recurring Revenue
2. **Churn:** % of customers who cancel monthly (goal: <5%)
3. **LTV:** Lifetime Value = Avg subscription length × Monthly price
4. **CAC:** Customer Acquisition Cost = Marketing spend / New customers
5. **Free → Paid Conversion:** % of free users who upgrade (goal: >10%)

### Product Metrics

1. **Daily Active Users:** Track via API calls
2. **API Calls per User:** Average usage
3. **Most Used Endpoints:** What's valuable?
4. **Failed Requests:** What's breaking for users?

---

## 15. Automation Scripts

### Monitor Health Every 5 Minutes (Cron Job)

```bash
#!/bin/bash
# save as: monitor_health.sh

API_URL="https://YOUR_DOMAIN/health"
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK"

response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $response -ne 200 ]; then
    curl -X POST $SLACK_WEBHOOK \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"🚨 API Health Check Failed: HTTP $response\"}"
fi
```

Add to crontab:
```bash
*/5 * * * * /path/to/monitor_health.sh
```

---

### Daily Metrics Report (Email Yourself)

```python
# daily_report.py
import os
import stripe
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Get yesterday's metrics
yesterday = datetime.now() - timedelta(days=1)

# Count new customers
customers = stripe.Customer.list(
    created={"gte": int(yesterday.timestamp())}
)

# Get MRR
subscriptions = stripe.Subscription.list(status="active")
mrr = sum(sub.plan.amount for sub in subscriptions.data) / 100

# Send email
message = Mail(
    from_email='noreply@yourdomain.com',
    to_emails='you@email.com',
    subject=f'Daily Report - {datetime.now().strftime("%Y-%m-%d")}',
    html_content=f'''
    <h2>Daily Metrics</h2>
    <ul>
      <li>New customers: {len(customers.data)}</li>
      <li>MRR: ${mrr:,.2f}</li>
      <li>Active subscriptions: {len(subscriptions.data)}</li>
    </ul>
    '''
)

sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
sg.send(message)
```

Run daily:
```bash
0 9 * * * python3 /path/to/daily_report.py
```

---

## 16. Dashboard Template

### Create Simple Dashboard (HTML)

```html
<!DOCTYPE html>
<html>
<head>
    <title>FinSight API - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>FinSight API Dashboard</h1>

    <div class="metrics">
        <div class="metric">
            <h3>MRR</h3>
            <p id="mrr">Loading...</p>
        </div>
        <div class="metric">
            <h3>Customers</h3>
            <p id="customers">Loading...</p>
        </div>
        <div class="metric">
            <h3>API Calls (24h)</h3>
            <p id="api-calls">Loading...</p>
        </div>
    </div>

    <canvas id="chart"></canvas>

    <script>
        // Fetch from your admin API endpoint
        fetch('/admin/metrics')
            .then(r => r.json())
            .then(data => {
                document.getElementById('mrr').textContent = '$' + data.mrr;
                document.getElementById('customers').textContent = data.customers;
                document.getElementById('api-calls').textContent = data.api_calls;

                // Render chart
                new Chart(document.getElementById('chart'), {
                    type: 'line',
                    data: {
                        labels: data.dates,
                        datasets: [{
                            label: 'API Calls',
                            data: data.calls_per_day
                        }]
                    }
                });
            });
    </script>
</body>
</html>
```

---

## ✅ Setup Checklist

**Before launch:**

- [ ] UptimeRobot configured (health endpoint)
- [ ] Sentry configured (check .env has SENTRY_DSN)
- [ ] Sentry alerts set up (first error, error spike)
- [ ] Stripe email alerts enabled (failed payments)
- [ ] Test all alerts (trigger each once)

**Week 1:**

- [ ] Check monitoring daily
- [ ] Verify alerts working
- [ ] No false positives?

**Month 1:**

- [ ] Review metrics weekly
- [ ] Adjust alert thresholds if needed
- [ ] Add business metrics dashboard

---

## 🎯 Most Important Metrics

If you only track 5 things:

1. **Uptime** (UptimeRobot) - Is it working?
2. **Error Rate** (Sentry) - Are users hitting errors?
3. **MRR** (Stripe) - Am I making money?
4. **Churn** (Stripe) - Am I losing customers?
5. **Free → Paid Conversion** (Database query) - Is my funnel working?

Everything else is nice-to-have.

---

**You're monitoring 80% of what matters with just free tools. Add paid tools as you grow.** 🚀
