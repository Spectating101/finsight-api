# FinSight API - Quick Start Guide

Get stock market data and financial ratios in minutes.

---

## 🚀 **5-Minute Setup**

### **1. Get Your API Key**

```bash
curl -X POST https://api.finsight.io/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

**Response:**
```json
{
  "user_id": "usr_xxx",
  "api_key": "fsk_xxxxxxxxxxxx",
  "tier": "free",
  "message": "Save your API key - it won't be shown again"
}
```

💾 **Save your API key!** You'll need it for every request.

---

### **2. Make Your First Request**

```python
import requests

API_KEY = "fsk_xxxxxxxxxxxx"
headers = {"X-API-Key": API_KEY}

# Get Apple's financial ratios
response = requests.get(
    "https://api.finsight.io/api/v1/company/AAPL/ratios",
    headers=headers
)

data = response.json()
print(f"P/E Ratio: {data['ratios']['pe_ratio']}")
print(f"ROE: {data['ratios']['roe']}")
```

**Output:**
```
P/E Ratio: 28.5
ROE: 0.147
```

✅ **That's it!** You're getting financial data.

---

## 📊 **3 Most Useful Endpoints**

### **1. Financial Ratios (The Easy Button)**

Get pre-calculated ratios instead of doing math yourself.

```python
GET /api/v1/company/{ticker}/ratios
```

**Example:**
```python
response = requests.get(
    "https://api.finsight.io/api/v1/company/TSLA/ratios",
    headers={"X-API-Key": API_KEY}
)

ratios = response.json()['ratios']

print(f"Profit Margin: {ratios['profit_margin']:.1%}")
print(f"Debt to Equity: {ratios['debt_to_equity']}")
print(f"Current Ratio: {ratios['current_ratio']}")
```

**Returns:**
- Profitability: `profit_margin`, `gross_margin`, `operating_margin`, `roa`, `roe`
- Valuation: `pe_ratio`, `pb_ratio`, `eps_diluted`
- Liquidity: `current_ratio`, `quick_ratio`
- Leverage: `debt_to_equity`, `debt_to_assets`
- Efficiency: `asset_turnover`

---

### **2. Company Overview (Everything in One Call)**

Get fundamentals + ratios + per-share metrics in a single request.

```python
GET /api/v1/company/{ticker}/overview
```

**Example:**
```python
response = requests.get(
    "https://api.finsight.io/api/v1/company/GOOGL/overview",
    headers={"X-API-Key": API_KEY}
)

data = response.json()

print("Fundamentals:", data['fundamentals'])
print("Ratios:", data['ratios'])
print("Per Share:", data['per_share_metrics'])
```

**Use case:** Perfect for building dashboards - one call gets everything.

---

### **3. Batch Endpoint (Save API Calls)**

Get multiple companies at once instead of making separate requests.

```python
GET /api/v1/batch/companies?tickers=AAPL,GOOGL,MSFT,TSLA
```

**Example:**
```python
tickers = "AAPL,GOOGL,MSFT,TSLA"
response = requests.get(
    f"https://api.finsight.io/api/v1/batch/companies?tickers={tickers}",
    headers={"X-API-Key": API_KEY}
)

batch = response.json()

for company in batch['companies']:
    ticker = company['ticker']
    pe = company['ratios']['pe_ratio']
    print(f"{ticker}: P/E = {pe}")
```

**Use case:** Portfolio tracking, watchlists, screeners (20 stocks in 1 call)

---

## 💻 **Code Examples**

### **Python - Build a Stock Screener**

Find stocks with low P/E ratios:

```python
import requests

API_KEY = "fsk_xxxxxxxxxxxx"
headers = {"X-API-Key": API_KEY}

# Your watchlist
tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA"]

# Get all at once (batch endpoint)
response = requests.get(
    f"https://api.finsight.io/api/v1/batch/companies?tickers={','.join(tickers)}",
    headers=headers
)

companies = response.json()['companies']

# Filter: P/E < 25 and debt/equity < 1.0
undervalued = []

for company in companies:
    if not company.get('ratios'):
        continue

    pe = company['ratios'].get('pe_ratio')
    de = company['ratios'].get('debt_to_equity')

    if pe and de and pe < 25 and de < 1.0:
        undervalued.append({
            'ticker': company['ticker'],
            'pe_ratio': pe,
            'debt_to_equity': de
        })

print("Undervalued stocks:")
for stock in undervalued:
    print(f"{stock['ticker']}: P/E={stock['pe_ratio']:.1f}, D/E={stock['debt_to_equity']:.2f}")
```

---

### **JavaScript - Build a Dashboard**

```javascript
const API_KEY = 'fsk_xxxxxxxxxxxx';

async function getCompanyData(ticker) {
  const response = await fetch(
    `https://api.finsight.io/api/v1/company/${ticker}/overview`,
    {
      headers: { 'X-API-Key': API_KEY }
    }
  );

  return await response.json();
}

// Usage
const data = await getCompanyData('AAPL');

console.log('Revenue:', data.fundamentals.revenue);
console.log('P/E Ratio:', data.ratios.pe_ratio);
console.log('EPS:', data.per_share_metrics.eps_diluted);
```

---

### **Python - Portfolio Tracker**

Track your portfolio value:

```python
import requests

API_KEY = "fsk_xxxxxxxxxxxx"
headers = {"X-API-Key": API_KEY}

# Your holdings
portfolio = {
    "AAPL": 10,   # 10 shares
    "GOOGL": 5,   # 5 shares
    "MSFT": 15    # 15 shares
}

tickers = ",".join(portfolio.keys())

# Get current data
response = requests.get(
    f"https://api.finsight.io/api/v1/batch/companies?tickers={tickers}",
    headers=headers
)

companies = response.json()['companies']

total_value = 0

for company in companies:
    ticker = company['ticker']
    # You'd need to add current price separately (not in this API)
    # But you get all the fundamental data
    shares = portfolio[ticker]
    book_value = company.get('per_share_metrics', {}).get('book_value_per_share', 0)

    print(f"{ticker}: {shares} shares, Book value/share: ${book_value:.2f}")
```

---

## 🔑 **Authentication**

Include your API key in every request:

**Option 1: Header (Recommended)**
```bash
curl -H "X-API-Key: fsk_xxxxxxxxxxxx" https://api.finsight.io/api/v1/...
```

**Option 2: Bearer Token**
```bash
curl -H "Authorization: Bearer fsk_xxxxxxxxxxxx" https://api.finsight.io/api/v1/...
```

---

## 📊 **Rate Limits**

| Tier | Calls/Month | Calls/Minute |
|------|-------------|--------------|
| Free | 100 | 10 |
| Starter ($19/mo) | 5,000 | 50 |
| Pro ($49/mo) | 50,000 | 200 |
| Enterprise ($149/mo) | 500,000 | 1,000 |

**Rate limit headers:**
```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1699564800
```

---

## ⚠️ **Error Handling**

```python
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    # Success!

elif response.status_code == 401:
    print("Invalid API key")

elif response.status_code == 404:
    print("Ticker not found")

elif response.status_code == 429:
    print("Rate limit exceeded - upgrade your plan")

else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

**Common errors:**
- `401`: Invalid/expired API key
- `404`: Ticker not found (check spelling)
- `429`: Rate limit exceeded (wait or upgrade)
- `500`: Server error (we're notified automatically)

---

## 📚 **Full Documentation**

**Interactive docs:** https://api.finsight.io/docs

Includes:
- All endpoints
- Request/response examples
- Try it out in browser
- Response schemas

---

## 🆘 **Need Help?**

**Email:** support@finsight.io (we respond within 24 hours)

**Common questions:**

**Q: How fresh is the data?**
A: SEC EDGAR data (quarterly filings). Updated within 24 hours of SEC filing.

**Q: Can I get real-time prices?**
A: Not currently - we focus on fundamentals. Use Yahoo Finance/IEX for prices.

**Q: What stocks are covered?**
A: All US public companies that file with SEC (~5,000+ companies).

**Q: Can I use this commercially?**
A: Yes! All plans include commercial use.

**Q: Do you have historical data?**
A: Yes, via `/api/v1/metrics` endpoint with `period` parameter.

---

## 🚀 **Next Steps**

1. ✅ Got your API key
2. ✅ Made first request
3. 📖 Read full docs: https://api.finsight.io/docs
4. 🔨 Build something cool
5. 💰 Upgrade when you need more calls: https://api.finsight.io/pricing

---

**Happy building! 🎉**
