# Stripe Setup Guide for FinSight API

This guide walks you through setting up Stripe for your FinSight API deployment.

## Prerequisites

- Stripe account (sign up at https://stripe.com)
- Access to Stripe Dashboard
- Stripe CLI installed (optional, for webhook testing)

## Step 1: Create Stripe Products

### 1.1 Log into Stripe Dashboard

Go to https://dashboard.stripe.com and log in.

### 1.2 Create Products

Navigate to **Products** → **Add Product** and create the following products:

#### Product 1: Starter Plan
- **Name**: FinSight API - Starter
- **Description**: 1,000 API calls per month, 50 requests/min, access to SEC & Yahoo Finance data
- **Pricing**:
  - Price: $49.00 USD
  - Billing period: Monthly
  - Pricing model: Standard pricing

**Save the Price ID** (starts with `price_...`)

#### Product 2: Professional Plan
- **Name**: FinSight API - Professional
- **Description**: 10,000 API calls per month, 200 requests/min, AI synthesis, webhooks
- **Pricing**:
  - Price: $199.00 USD
  - Billing period: Monthly
  - Pricing model: Standard pricing

**Save the Price ID** (starts with `price_...`)

#### Product 3: Enterprise Plan
- **Name**: FinSight API - Enterprise
- **Description**: Unlimited API calls, 1000 requests/min, priority support, SLA, custom metrics
- **Pricing**:
  - Price: $999.00 USD
  - Billing period: Monthly
  - Pricing model: Standard pricing

**Save the Price ID** (starts with `price_...`)

## Step 2: Update Price IDs in Code

### 2.1 Open `src/models/user.py`

Find the `STRIPE_PRICE_IDS` dictionary (around line 140):

```python
STRIPE_PRICE_IDS = {
    PricingTier.STARTER: "price_xxx_starter_monthly",
    PricingTier.PROFESSIONAL: "price_xxx_pro_monthly",
    PricingTier.ENTERPRISE: "price_xxx_enterprise_monthly",
}
```

### 2.2 Replace with Your Price IDs

```python
STRIPE_PRICE_IDS = {
    PricingTier.STARTER: "price_1234567890abcdef",  # Your Starter price ID
    PricingTier.PROFESSIONAL: "price_abcdef1234567890",  # Your Pro price ID
    PricingTier.ENTERPRISE: "price_xyz123abc456",  # Your Enterprise price ID
}
```

## Step 3: Configure Stripe API Keys

### 3.1 Get Your API Keys

In Stripe Dashboard:
1. Go to **Developers** → **API Keys**
2. Copy your **Secret key** (starts with `sk_test_` for test mode, `sk_live_` for production)
3. Copy your **Publishable key** (starts with `pk_test_` or `pk_live_`)

### 3.2 Add to Environment Variables

Update your `.env` file:

```bash
# For testing
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here

# For production
STRIPE_SECRET_KEY=sk_live_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_live_your_publishable_key_here
```

## Step 4: Set Up Webhooks

Stripe webhooks notify your API about subscription events (payments, cancellations, etc.).

### 4.1 Create Webhook Endpoint

In Stripe Dashboard:
1. Go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Set endpoint URL: `https://your-api-domain.com/api/v1/webhooks/stripe`
4. Select events to listen to:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `checkout.session.completed`

### 4.2 Get Webhook Secret

After creating the endpoint:
1. Click on the endpoint
2. Copy the **Signing secret** (starts with `whsec_`)
3. Add to `.env`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

## Step 5: Test Stripe Integration

### 5.1 Install Stripe CLI (Optional)

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Linux
wget https://github.com/stripe/stripe-cli/releases/download/v1.19.0/stripe_1.19.0_linux_x86_64.tar.gz
tar -xvf stripe_1.19.0_linux_x86_64.tar.gz
sudo mv stripe /usr/local/bin/
```

### 5.2 Test Webhook Locally

```bash
# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe

# In another terminal, trigger a test event
stripe trigger checkout.session.completed
```

### 5.3 Test Checkout Flow

Use Stripe's test card numbers:
- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **Requires authentication**: `4000 0025 0000 3155`

Use any future date for expiry, any 3-digit CVC, and any ZIP code.

## Step 6: Production Deployment

### 6.1 Switch to Live Mode

1. In Stripe Dashboard, toggle from **Test mode** to **Live mode**
2. Get new API keys (they'll start with `sk_live_` and `pk_live_`)
3. Create new webhook endpoint for production URL
4. Update environment variables with live keys

### 6.2 Update Environment Variables on Heroku

```bash
heroku config:set STRIPE_SECRET_KEY=sk_live_... -a your-app-name
heroku config:set STRIPE_WEBHOOK_SECRET=whsec_... -a your-app-name
heroku config:set STRIPE_PUBLISHABLE_KEY=pk_live_... -a your-app-name
```

### 6.3 Verify Configuration

Run the production validation script:

```bash
python scripts/validate_production.py
```

It will check:
- ✓ Stripe API keys are configured
- ✓ Stripe connection works
- ⚠ Price IDs are not placeholders

## Step 7: Test End-to-End Flow

### 7.1 Create a Test Subscription

```bash
# 1. Register a user
curl -X POST https://your-api.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "company_name": "Test Corp"}'

# Save the API key returned

# 2. Create checkout session
curl -X POST https://your-api.com/api/v1/subscription/checkout \
  -H "X-API-Key: fsk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "starter",
    "success_url": "https://your-frontend.com/success",
    "cancel_url": "https://your-frontend.com/cancel"
  }'

# 3. Visit the checkout URL and complete payment
# 4. Check subscription status
curl https://your-api.com/api/v1/subscription \
  -H "X-API-Key: fsk_your_api_key"
```

## Step 8: Monitor Subscriptions

### 8.1 Stripe Dashboard

Monitor subscriptions in **Customers** → **Subscriptions**

### 8.2 Database

Check subscription status in your database:

```sql
SELECT user_id, email, tier, stripe_subscription_id, billing_period_end
FROM users
WHERE tier != 'free';
```

### 8.3 Webhook Events

Check webhook events were processed:

```sql
SELECT event_id, event_type, processed, created_at
FROM webhook_events
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### Issue: Webhook not receiving events

**Solution:**
1. Check webhook URL is correct and publicly accessible
2. Verify webhook secret matches in `.env`
3. Check webhook events in Stripe Dashboard → Webhooks → Event logs
4. Look for errors in your application logs

### Issue: "Invalid API key" error

**Solution:**
1. Verify `STRIPE_SECRET_KEY` is correct
2. Make sure you're using test keys in test mode, live keys in production
3. Check for typos or extra spaces in `.env`

### Issue: Checkout session fails

**Solution:**
1. Verify price IDs are correct in `src/models/user.py`
2. Check that products are active in Stripe Dashboard
3. Look for errors in Sentry or application logs
4. Test with Stripe CLI: `stripe listen --print-json`

### Issue: Subscription not updating in database

**Solution:**
1. Check webhook is configured and working
2. Verify `subscription.updated` event is enabled
3. Check `webhook_events` table for errors
4. Look for database connection issues in logs

## Security Checklist

Before going live:

- [ ] Using live API keys (not test keys)
- [ ] Webhook secret is configured
- [ ] HTTPS is enabled (required by Stripe)
- [ ] API keys are in environment variables (not hardcoded)
- [ ] Webhook signature verification is enabled (automatic in code)
- [ ] Test mode is disabled in Stripe Dashboard

## Additional Resources

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Subscriptions Guide](https://stripe.com/docs/billing/subscriptions/overview)

## Support

If you encounter issues:
1. Check Stripe Dashboard → Developers → Logs
2. Check application logs (Heroku logs or Sentry)
3. Review webhook events in Stripe Dashboard
4. Contact Stripe support: https://support.stripe.com

---

**Next Steps**: After completing Stripe setup, proceed to [DEPLOYMENT.md](../DEPLOYMENT.md) for full deployment instructions.
