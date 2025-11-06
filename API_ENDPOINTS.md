# FinSight API - Complete Endpoint Reference

**Base URL:** `https://api.finsight.io/api/v1`

---

## 🔑 Authentication

**All endpoints require authentication via API key.**

**Header:**
```
X-API-Key: fsk_xxxxxxxxxxxx
```

**Or:**
```
Authorization: Bearer fsk_xxxxxxxxxxxx
```

---

## 📊 Financial Data Endpoints

### 1. **Get Financial Ratios** ⭐ NEW

**Endpoint:** `GET /company/{ticker}/ratios`

**Description:** Get pre-calculated financial ratios for a company.

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  https://api.finsight.io/api/v1/company/AAPL/ratios
```

**Response:**
```json
{
  "ticker": "AAPL",
  "as_of_date": "2024-09-30",
  "ratios": {
    "profit_margin": 0.2134,
    "gross_margin": 0.4287,
    "operating_margin": 0.2956,
    "roa": 0.0871,
    "roe": 0.1473,
    "pe_ratio": 28.5,
    "pb_ratio": 45.2,
    "eps_diluted": 6.42,
    "current_ratio": 1.2,
    "quick_ratio": 1.2,
    "debt_to_equity": 1.8,
    "debt_to_assets": 0.35,
    "asset_turnover": 0.41
  },
  "source": "SEC EDGAR"
}
```

**Ratios Included:**
- **Profitability:** profit_margin, gross_margin, operating_margin, roa, roe
- **Valuation:** pe_ratio, pb_ratio, eps_diluted
- **Liquidity:** current_ratio, quick_ratio
- **Leverage:** debt_to_equity, debt_to_assets
- **Efficiency:** asset_turnover

---

### 2. **Get Company Overview** ⭐ NEW

**Endpoint:** `GET /company/{ticker}/overview`

**Description:** Get comprehensive company data (fundamentals + ratios + per-share metrics) in one call.

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  https://api.finsight.io/api/v1/company/TSLA/overview
```

**Response:**
```json
{
  "ticker": "TSLA",
  "fundamentals": {
    "revenue": 96773000000,
    "netIncome": 14974000000,
    "totalAssets": 106618000000,
    "currentAssets": 45146000000,
    "currentLiabilities": 28748000000,
    "shareholdersEquity": 62634000000,
    "totalDebt": 9583000000,
    "cashAndEquivalents": 26077000000,
    "grossProfit": 20853000000,
    "operatingIncome": 8891000000,
    "sharesDiluted": 3475000000
  },
  "ratios": {
    "profit_margin": 0.1547,
    "gross_margin": 0.2155,
    "roe": 0.2390,
    "pe_ratio": 58.3,
    "debt_to_equity": 0.1530,
    "current_ratio": 1.57
  },
  "per_share_metrics": {
    "book_value_per_share": 18.02,
    "revenue_per_share": 27.85,
    "cash_per_share": 7.50
  },
  "as_of_date": "2024-09-30",
  "source": "SEC EDGAR"
}
```

**Use case:** Perfect for company profile pages, dashboards - everything in one call.

---

### 3. **Get Batch Companies** ⭐ NEW

**Endpoint:** `GET /batch/companies?tickers=X,Y,Z&include_ratios=true`

**Description:** Get data for multiple companies in a single request (max 20).

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://api.finsight.io/api/v1/batch/companies?tickers=AAPL,GOOGL,MSFT,TSLA&include_ratios=true"
```

**Response:**
```json
{
  "companies": [
    {
      "ticker": "AAPL",
      "fundamentals": { ... },
      "ratios": { ... }
    },
    {
      "ticker": "GOOGL",
      "fundamentals": { ... },
      "ratios": { ... }
    },
    {
      "ticker": "MSFT",
      "fundamentals": { ... },
      "ratios": { ... }
    },
    {
      "ticker": "TSLA",
      "fundamentals": { ... },
      "ratios": { ... }
    }
  ],
  "requested": 4,
  "successful": 4,
  "failed": 0
}
```

**Parameters:**
- `tickers` (required): Comma-separated list of tickers (max 20)
- `include_ratios` (optional): Include calculated ratios (default: true)

**Use case:** Portfolio tracking, watchlists, screeners - save API calls!

---

### 4. **Get Financial Metrics**

**Endpoint:** `GET /metrics?ticker={ticker}&metrics={metrics}&period={period}`

**Description:** Get specific financial metrics for a company.

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://api.finsight.io/api/v1/metrics?ticker=AAPL&metrics=revenue,netIncome&period=2024-Q3"
```

**Response:**
```json
[
  {
    "ticker": "AAPL",
    "metric": "revenue",
    "value": 94930000000,
    "unit": "USD",
    "period": "2024-09-30",
    "citation": {
      "source": "SEC EDGAR",
      "accession": "0000320193-24-000123",
      "filing_date": "2024-11-01",
      "form": "10-Q",
      "url": "https://www.sec.gov/..."
    },
    "source": "sec_edgar"
  },
  {
    "ticker": "AAPL",
    "metric": "netIncome",
    "value": 14736000000,
    "unit": "USD",
    "period": "2024-09-30",
    "citation": { ... },
    "source": "sec_edgar"
  }
]
```

**Available metrics:**
- revenue, netIncome, totalAssets, currentAssets
- currentLiabilities, shareholdersEquity, totalDebt
- cashAndEquivalents, costOfRevenue, grossProfit
- operatingIncome, sharesDiluted, sharesBasic

---

## 🏢 Company Search

### 5. **Search Companies**

**Endpoint:** `GET /companies/search?q={query}`

**Description:** Search for companies by name or ticker.

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://api.finsight.io/api/v1/companies/search?q=apple"
```

**Response:**
```json
{
  "query": "apple",
  "results": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "cik": "0000320193"
    }
  ],
  "count": 1
}
```

---

## 🔐 Authentication & API Keys

### 6. **Register User**

**Endpoint:** `POST /auth/register`

**Description:** Create new user account and get API key.

**Example:**
```bash
curl -X POST https://api.finsight.io/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "company_name": "Your Company"
  }'
```

**Response:**
```json
{
  "user_id": "usr_xxxxxxxxxxxx",
  "email": "you@example.com",
  "tier": "free",
  "api_key": "fsk_xxxxxxxxxxxx",
  "key_prefix": "fsk_1234",
  "message": "Save your API key - it won't be shown again"
}
```

---

### 7. **Create Additional API Key**

**Endpoint:** `POST /auth/keys`

**Description:** Create additional API keys for your account.

**Example:**
```bash
curl -X POST https://api.finsight.io/api/v1/auth/keys \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "test_mode": false
  }'
```

**Response:**
```json
{
  "key_id": "key_xxxxxxxxxxxx",
  "api_key": "fsk_xxxxxxxxxxxx",
  "key_prefix": "fsk_5678",
  "name": "Production Key",
  "test_mode": false,
  "created_at": "2024-11-06T12:00:00Z",
  "message": "Save your API key - it won't be shown again"
}
```

---

### 8. **List API Keys**

**Endpoint:** `GET /auth/keys`

**Description:** List all API keys for your account.

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  https://api.finsight.io/api/v1/auth/keys
```

**Response:**
```json
[
  {
    "key_id": "key_xxxxxxxxxxxx",
    "key_prefix": "fsk_1234",
    "name": "Default Key",
    "is_active": true,
    "is_test_mode": false,
    "total_calls": 1524,
    "last_used_at": "2024-11-06T11:30:00Z",
    "created_at": "2024-11-01T10:00:00Z",
    "expires_at": null
  }
]
```

---

### 9. **Revoke API Key**

**Endpoint:** `DELETE /auth/keys/{key_id}`

**Description:** Revoke (deactivate) an API key.

**Example:**
```bash
curl -X DELETE https://api.finsight.io/api/v1/auth/keys/key_xxxxxxxxxxxx \
  -H "X-API-Key: YOUR_KEY"
```

**Response:**
```json
{
  "message": "API key revoked successfully",
  "key_id": "key_xxxxxxxxxxxx"
}
```

---

## 💳 Billing & Subscriptions

### 10. **Create Checkout Session**

**Endpoint:** `POST /billing/create-checkout`

**Description:** Create Stripe checkout session to upgrade plan.

**Example:**
```bash
curl -X POST https://api.finsight.io/api/v1/billing/create-checkout \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "starter",
    "success_url": "https://yoursite.com/success",
    "cancel_url": "https://yoursite.com/cancel"
  }'
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx...",
  "session_id": "cs_xxxxxxxxxxxx"
}
```

---

### 11. **Get Subscription Status**

**Endpoint:** `GET /billing/subscription`

**Description:** Get current subscription status and usage.

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  https://api.finsight.io/api/v1/billing/subscription
```

**Response:**
```json
{
  "user_id": "usr_xxxxxxxxxxxx",
  "tier": "starter",
  "status": "active",
  "api_calls_this_month": 1247,
  "api_calls_limit": 5000,
  "billing_period_start": "2024-11-01",
  "billing_period_end": "2024-12-01",
  "stripe_subscription_id": "sub_xxxxxxxxxxxx"
}
```

---

### 12. **Cancel Subscription**

**Endpoint:** `POST /billing/subscription/cancel`

**Description:** Cancel active subscription (downgrades to free tier at period end).

**Example:**
```bash
curl -X POST https://api.finsight.io/api/v1/billing/subscription/cancel \
  -H "X-API-Key: YOUR_KEY"
```

**Response:**
```json
{
  "message": "Subscription will be cancelled at period end",
  "cancel_at": "2024-12-01T00:00:00Z",
  "access_until": "2024-12-01T00:00:00Z"
}
```

---

## 🔒 GDPR Compliance

### 13. **Export User Data**

**Endpoint:** `GET /gdpr/export`

**Description:** Export all personal data (GDPR Article 15 - Right of Access).

**Example:**
```bash
curl -H "X-API-Key: YOUR_KEY" \
  https://api.finsight.io/api/v1/gdpr/export
```

**Response:**
```json
{
  "user_data": { ... },
  "api_keys": [ ... ],
  "usage_records": [ ... ],
  "subscription_history": [ ... ],
  "export_timestamp": "2024-11-06T12:00:00Z",
  "format_version": "1.0"
}
```

---

### 14. **Delete Account**

**Endpoint:** `POST /gdpr/delete`

**Description:** Permanently delete account (GDPR Article 17 - Right to Erasure).

**Example:**
```bash
curl -X POST https://api.finsight.io/api/v1/gdpr/delete \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm_email": "you@example.com",
    "reason": "No longer needed"
  }'
```

**Response:**
```json
{
  "status": "deleted",
  "message": "Your account has been successfully deleted",
  "deleted_at": "2024-11-06T12:00:00Z",
  "data_retained": {
    "subscription_history": "Retained for 7 years per tax law",
    "usage_records": "Aggregated anonymously for analytics"
  }
}
```

---

### 15. **GDPR Information**

**Endpoint:** `GET /gdpr/info`

**Description:** Get information about GDPR rights and data processing (public, no auth required).

**Example:**
```bash
curl https://api.finsight.io/api/v1/gdpr/info
```

**Response:**
```json
{
  "data_controller": {
    "name": "FinSight API",
    "contact": "privacy@finsight.io"
  },
  "user_rights": {
    "right_of_access": { ... },
    "right_to_erasure": { ... }
  },
  "data_processing": { ... }
}
```

---

## 🏥 Health & Status

### 16. **Health Check**

**Endpoint:** `GET /health`

**Description:** Check API health status (no auth required).

**Example:**
```bash
curl https://api.finsight.io/health
```

**Response (Healthy):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-11-06T12:00:00Z",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "data_sources": {
      "sec_edgar": "ok"
    }
  }
}
```

**Response (Degraded):** Returns HTTP 503

---

## 📝 Rate Limits

| Tier | Calls/Month | Calls/Minute |
|------|-------------|--------------|
| Free | 100 | 10 |
| Starter ($19/mo) | 5,000 | 50 |
| Pro ($49/mo) | 50,000 | 200 |
| Enterprise ($149/mo) | 500,000 | 1,000 |

**Rate limit headers in every response:**
```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1699564800
```

---

## ⚠️ Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | - |
| 400 | Bad Request | Check your parameters |
| 401 | Unauthorized | Check your API key |
| 404 | Not Found | Ticker doesn't exist |
| 429 | Rate Limit | Wait or upgrade plan |
| 500 | Server Error | We're notified, try again |
| 503 | Service Unavailable | Maintenance or degraded |

**Error response format:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "You have exceeded your rate limit",
  "details": {
    "limit": 10,
    "reset_at": "2024-11-06T13:00:00Z"
  }
}
```

---

## 📚 Interactive Documentation

**Swagger UI:** https://api.finsight.io/docs

- Try all endpoints in browser
- See request/response schemas
- Copy code examples

**ReDoc:** https://api.finsight.io/redoc

- Cleaner documentation view
- Search functionality
- Printable

---

## 🚀 Quick Start

1. **Register:** `POST /auth/register`
2. **Get API key:** Save it from response
3. **Test:** `GET /company/AAPL/ratios` with your key
4. **Build:** Use batch endpoint for multiple stocks
5. **Upgrade:** When you hit 100 calls/month

**Questions?** support@finsight.io

---

**Last Updated:** 2025-11-06
**API Version:** 1.0.0
