# FinSight API - Python SDK

Official Python client for the FinSight Financial Data API.

Get stock market fundamentals and pre-calculated financial ratios with just a few lines of code.

## Installation

```bash
pip install finsight-api
```

## Quick Start

```python
from finsight import FinSightClient

# Initialize client
client = FinSightClient(api_key="fsk_xxxxxxxxxxxx")

# Get financial ratios
ratios = client.get_ratios("AAPL")
print(f"P/E Ratio: {ratios['ratios']['pe_ratio']}")
print(f"ROE: {ratios['ratios']['roe']}")
print(f"Debt/Equity: {ratios['ratios']['debt_to_equity']}")
```

## Features

- ✅ **Pre-calculated Financial Ratios** - P/E, ROE, debt/equity, margins, and more
- ✅ **Batch Requests** - Get 20 companies in one API call
- ✅ **Company Overviews** - Fundamentals + ratios in a single response
- ✅ **Type Hints** - Full typing support for better IDE integration
- ✅ **Error Handling** - Clear exceptions for different error types
- ✅ **Stock Screener** - Built-in filtering by financial criteria

## Examples

### Get Financial Ratios

```python
from finsight import FinSightClient

client = FinSightClient(api_key="your_api_key")

# Get all ratios for a company
ratios = client.get_ratios("TSLA")

print(f"Profit Margin: {ratios['ratios']['profit_margin']:.1%}")
print(f"Current Ratio: {ratios['ratios']['current_ratio']}")
print(f"ROE: {ratios['ratios']['roe']:.1%}")
```

### Get Company Overview

```python
# Get everything in one call
data = client.get_overview("GOOGL")

# Fundamentals
print(f"Revenue: ${data['fundamentals']['revenue']:,.0f}")
print(f"Net Income: ${data['fundamentals']['netIncome']:,.0f}")

# Ratios
print(f"P/E Ratio: {data['ratios']['pe_ratio']}")

# Per-share metrics
print(f"EPS: ${data['per_share_metrics']['eps_diluted']:.2f}")
```

### Batch Request (Multiple Companies)

```python
# Get data for multiple companies in one call
tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

data = client.get_batch(tickers)

for company in data['companies']:
    ticker = company['ticker']
    pe = company['ratios']['pe_ratio']
    print(f"{ticker}: P/E = {pe}")
```

### Stock Screener

```python
# Find undervalued stocks
tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA"]

filters = {
    "pe_ratio": {"max": 25},
    "debt_to_equity": {"max": 1.0},
    "roe": {"min": 0.15}
}

matches = client.screen_stocks(tickers, filters)

print("Undervalued stocks:")
for company in matches:
    print(f"{company['ticker']}: P/E={company['ratios']['pe_ratio']}")
```

### Get Specific Metrics

```python
# Get specific metrics with SEC citations
metrics = client.get_metrics("AAPL", ["revenue", "netIncome"])

for metric in metrics:
    print(f"{metric['metric']}: ${metric['value']:,.0f}")
    print(f"Filed: {metric['citation']['filing_date']}")
    print(f"Form: {metric['citation']['form']}")
```

### Search Companies

```python
# Search by company name or ticker
results = client.search_companies("apple")

for company in results['results']:
    print(f"{company['ticker']}: {company['name']}")
```

### Check Subscription Usage

```python
# Check your API usage and limits
sub = client.get_subscription()

print(f"Tier: {sub['tier']}")
print(f"Calls this month: {sub['api_calls_this_month']}")
print(f"Limit: {sub['api_calls_limit']}")

remaining = sub['api_calls_limit'] - sub['api_calls_this_month']
print(f"Remaining: {remaining}")
```

### Convenience Methods

```python
# Quick access to specific ratios
pe_ratio = client.get_pe_ratio("AAPL")
debt_to_equity = client.get_debt_to_equity("AAPL")
roe = client.get_roe("AAPL")
profit_margin = client.get_profit_margin("AAPL")
```

## Error Handling

```python
from finsight import FinSightClient
from finsight.exceptions import (
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError
)

client = FinSightClient(api_key="your_api_key")

try:
    ratios = client.get_ratios("AAPL")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit exceeded. Resets at: {e.reset_at}")
except NotFoundError:
    print("Ticker not found")
except ValidationError as e:
    print(f"Invalid request: {e.message}")
```

## Available Ratios

### Profitability
- `profit_margin` - Net income / Revenue
- `gross_margin` - Gross profit / Revenue
- `operating_margin` - Operating income / Revenue
- `roa` - Return on Assets
- `roe` - Return on Equity

### Valuation
- `pe_ratio` - Price-to-Earnings ratio
- `pb_ratio` - Price-to-Book ratio
- `eps_diluted` - Earnings per share (diluted)

### Liquidity
- `current_ratio` - Current assets / Current liabilities
- `quick_ratio` - (Current assets - Inventory) / Current liabilities

### Leverage
- `debt_to_equity` - Total debt / Shareholders equity
- `debt_to_assets` - Total debt / Total assets

### Efficiency
- `asset_turnover` - Revenue / Total assets

## Available Metrics

Financial metrics from SEC filings:
- `revenue`, `netIncome`, `totalAssets`, `currentAssets`
- `currentLiabilities`, `shareholdersEquity`, `totalDebt`
- `cashAndEquivalents`, `costOfRevenue`, `grossProfit`
- `operatingIncome`, `sharesDiluted`, `sharesBasic`
- And more...

## API Documentation

Full API documentation: https://docs.finsight.io

Interactive API explorer: https://api.finsight.io/docs

## Rate Limits

| Tier | Calls/Month | Calls/Minute |
|------|-------------|--------------|
| Free | 100 | 10 |
| Starter ($19/mo) | 5,000 | 50 |
| Pro ($49/mo) | 50,000 | 200 |
| Enterprise ($149/mo) | 500,000 | 1,000 |

## Support

- **Email:** support@finsight.io
- **Documentation:** https://docs.finsight.io
- **Issues:** https://github.com/yourusername/finsight-python/issues

## License

MIT License - see LICENSE file for details.

## Links

- **API Website:** https://finsight.io
- **API Documentation:** https://docs.finsight.io
- **Python SDK:** https://github.com/yourusername/finsight-python
- **PyPI:** https://pypi.org/project/finsight-api/
