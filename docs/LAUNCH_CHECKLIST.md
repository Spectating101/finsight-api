# FinSight API - Production Launch Checklist

Complete this checklist before launching your API to production.

## Pre-Launch Phase

### 1. Environment Configuration ✓

- [ ] All environment variables configured in `.env` or Heroku Config Vars
- [ ] `DATABASE_URL` points to production PostgreSQL database
- [ ] `REDIS_URL` points to production Redis instance
- [ ] `ENVIRONMENT=production` is set
- [ ] `DEBUG=false` is set
- [ ] Secrets are strong and unique (not defaults):
  - [ ] `JWT_SECRET_KEY` is not "generate_random_secret_here"
  - [ ] `API_KEY_SALT` is random and secure
- [ ] `ALLOWED_ORIGINS` is configured (not `*`)
- [ ] `SEC_USER_AGENT` includes your contact email

### 2. Stripe Configuration ✓

- [ ] Stripe account created and verified
- [ ] Products created in Stripe Dashboard:
  - [ ] Starter ($49/month)
  - [ ] Professional ($199/month)
  - [ ] Enterprise ($999/month)
- [ ] Price IDs updated in `src/models/user.py`
- [ ] Switched from test mode to live mode
- [ ] Live API keys configured:
  - [ ] `STRIPE_SECRET_KEY` (starts with `sk_live_`)
  - [ ] `STRIPE_PUBLISHABLE_KEY` (starts with `pk_live_`)
- [ ] Webhook endpoint created and configured:
  - [ ] Endpoint URL: `https://your-api.com/api/v1/webhooks/stripe`
  - [ ] Events enabled: subscription.*, invoice.*
  - [ ] `STRIPE_WEBHOOK_SECRET` configured
- [ ] Test payment flow completed successfully

### 3. Database Setup ✓

- [ ] Production database created (PostgreSQL 14+)
- [ ] Database schema initialized: `psql $DATABASE_URL -f config/database_schema.sql`
- [ ] All required tables exist:
  - [ ] `users`
  - [ ] `api_keys`
  - [ ] `usage_records`
  - [ ] `subscription_history`
  - [ ] `webhook_events`
  - [ ] `feature_flags`
- [ ] Database backups configured
- [ ] Connection pooling configured (min: 5, max: 20)

### 4. Caching & Performance ✓

- [ ] Redis instance provisioned (Heroku Redis Mini or equivalent)
- [ ] Redis TLS configured for Heroku
- [ ] Cache TTLs configured appropriately
- [ ] Rate limiting tested and working

### 5. Monitoring & Logging ✓

- [ ] Sentry account created
- [ ] `SENTRY_DSN` configured
- [ ] Error tracking tested (trigger test error)
- [ ] Log level set to `INFO` or `WARNING` for production
- [ ] Prometheus metrics accessible at `/metrics`
- [ ] Health check endpoint working at `/health`

### 6. Security Hardening ✓

- [ ] HTTPS enabled (required, handled by Heroku/platform)
- [ ] Security headers configured (automated by middleware)
- [ ] Request size limits enforced (1MB max)
- [ ] Input validation on all endpoints
- [ ] API keys hashed with SHA256 (never plaintext)
- [ ] SQL injection protection (parameterized queries)
- [ ] No secrets in git repository (check with: `git secrets --scan`)
- [ ] CORS configured properly (not `*` in production)

### 7. Testing ✓

- [ ] All unit tests passing: `pytest tests/`
- [ ] Integration tests passing
- [ ] End-to-end user flow tested:
  - [ ] User registration
  - [ ] API key creation
  - [ ] Data fetching with API key
  - [ ] Stripe checkout flow
  - [ ] Subscription upgrade
  - [ ] Subscription cancellation
- [ ] Rate limiting tested
- [ ] Error handling tested (404s, 500s, etc.)
- [ ] Load testing completed (at least 100 concurrent users)

### 8. Documentation ✓

- [ ] README.md updated with production info
- [ ] API documentation accessible at `/docs`
- [ ] All endpoints documented with examples
- [ ] Stripe setup guide completed
- [ ] Deployment guide reviewed and up-to-date

### 9. Legal & Compliance

- [ ] Terms of Service created and linked
- [ ] Privacy Policy created and linked
- [ ] GDPR compliance reviewed (if serving EU users)
- [ ] Data retention policy defined
- [ ] Cookie policy configured (if using cookies)

### 10. Business Readiness

- [ ] Pricing tiers finalized and tested
- [ ] Payment flow tested with real credit card
- [ ] Refund policy defined
- [ ] Support email/system set up
- [ ] Analytics tracking configured (if using)
- [ ] Domain name purchased and configured (optional)

## Launch Day

### 1. Final Validation

Run the production validation script:

```bash
python scripts/validate_production.py
```

Expected output:
```
✓ PASS | Required Environment Variables
✓ PASS | Debug Mode
✓ PASS | JWT Secret
✓ PASS | Database Connection
✓ PASS | Redis Connection
✓ PASS | Stripe Configuration
✓ PASS | SEC User Agent
✓ PASS | Sentry Configuration
```

### 2. Deploy to Production

```bash
# Push to main branch (triggers auto-deployment if CI/CD is set up)
git push origin main

# Or deploy manually to Heroku
git push heroku main

# Verify deployment
heroku logs --tail -a your-app-name
```

### 3. Smoke Tests

After deployment, test these endpoints:

```bash
API_URL="https://your-api.herokuapp.com"

# 1. Health check
curl $API_URL/health

# 2. Root endpoint
curl $API_URL/

# 3. Pricing info
curl $API_URL/api/v1/pricing

# 4. Register a test user
curl -X POST $API_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@yourdomain.com"}'

# 5. Test API with key (save key from step 4)
curl $API_URL/api/v1/metrics/available \
  -H "X-API-Key: fsk_your_test_key"

# 6. Test authentication requirement
curl $API_URL/api/v1/auth/me
# Should return 401 Unauthorized

# 7. Test Stripe checkout
curl -X POST $API_URL/api/v1/subscription/checkout \
  -H "X-API-Key: fsk_your_test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "starter",
    "success_url": "https://yoursite.com/success",
    "cancel_url": "https://yoursite.com/cancel"
  }'
```

### 4. Monitor Logs

```bash
# Heroku
heroku logs --tail -a your-app-name

# Check for errors in Sentry
# Visit https://sentry.io/your-org/your-project/

# Check Stripe webhook events
# Visit https://dashboard.stripe.com/webhooks
```

### 5. Announce Launch

- [ ] Update status page (if you have one)
- [ ] Send announcement to beta users (if applicable)
- [ ] Post on social media
- [ ] Update website/landing page
- [ ] Submit to API directories (RapidAPI, APIs.guru, etc.)

## Post-Launch (First 24 Hours)

### Monitoring

- [ ] Check error rates in Sentry every 2 hours
- [ ] Monitor API response times
- [ ] Watch for unusual traffic patterns
- [ ] Check database query performance
- [ ] Monitor Redis memory usage

### User Support

- [ ] Respond to support emails within 4 hours
- [ ] Monitor for user feedback
- [ ] Track common errors or issues
- [ ] Document any workarounds needed

### Metrics to Track

- [ ] Total API calls
- [ ] New user signups
- [ ] Paid subscription conversions
- [ ] Average response time
- [ ] Error rate
- [ ] Rate limit hits

## Post-Launch (First Week)

### Performance Optimization

- [ ] Review slow queries in database logs
- [ ] Optimize cache hit rates
- [ ] Adjust rate limits if needed
- [ ] Scale up resources if needed

### User Feedback

- [ ] Collect and review user feedback
- [ ] Fix critical bugs immediately
- [ ] Plan features based on requests
- [ ] Update documentation based on common questions

### Marketing

- [ ] Write launch blog post
- [ ] Share success metrics
- [ ] Reach out to potential customers
- [ ] Get listed on API directories

## Ongoing Maintenance

### Daily

- [ ] Check Sentry for new errors
- [ ] Monitor API uptime
- [ ] Review support tickets

### Weekly

- [ ] Review usage analytics
- [ ] Check billing/subscription stats
- [ ] Database backup verification
- [ ] Security updates check

### Monthly

- [ ] Review and rotate API keys if needed
- [ ] Database cleanup (old webhook events, etc.)
- [ ] Performance review and optimization
- [ ] Cost analysis and optimization
- [ ] Feature planning based on usage data

## Rollback Plan

If something goes wrong:

### 1. Immediate Actions

```bash
# Rollback to previous Heroku release
heroku rollback -a your-app-name

# Check status
heroku ps -a your-app-name
heroku logs --tail -a your-app-name
```

### 2. Disable Features

```bash
# Set maintenance mode if needed
heroku maintenance:on -a your-app-name

# Disable problematic features via environment variables
heroku config:set FEATURE_X_ENABLED=false -a your-app-name
```

### 3. Communication

- [ ] Update status page
- [ ] Email affected users
- [ ] Post on social media
- [ ] Document the incident

## Success Criteria

Launch is successful when:

- ✅ All smoke tests pass
- ✅ Health check returns 200 OK
- ✅ Error rate < 1%
- ✅ Average response time < 500ms
- ✅ At least one successful paid subscription
- ✅ No critical bugs in first 24 hours
- ✅ Uptime > 99.5%

## Emergency Contacts

- **Database Issues**: [Heroku Postgres Support]
- **Payment Issues**: [Stripe Support](https://support.stripe.com)
- **Infrastructure**: [Heroku Support]
- **Security Issues**: [Your security team email]

## Resources

- [Production Validation Script](../scripts/validate_production.py)
- [Stripe Setup Guide](./STRIPE_SETUP_GUIDE.md)
- [Deployment Guide](../DEPLOYMENT.md)
- [API Documentation](https://your-api.com/docs)
- [Sentry Dashboard](https://sentry.io)
- [Stripe Dashboard](https://dashboard.stripe.com)

---

**Last Updated**: 2025-01-11

**Status**: Ready for Launch ✅
