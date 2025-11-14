# FinSight Python SDK

Official Python client for the FinSight Financial Data API.

## Installation

```bash
pip install finsight
```

## Quick Start

```python
from finsight import FinSightClient

# Initialize client
client = FinSightClient(api_key="your_api_key_here")

# Get financial metrics
metrics = client.get_metrics("AAPL", ["revenue", "net_income", "total_assets"])

for metric in metrics:
    print(f"{metric.name}: ${metric.value:,.0f}")
    print(f"  Source: {metric.citation}")
```

Output:
```
revenue: $394,328,000,000
  Source: SEC EDGAR 10-K (2022-09-30)
net_income: $99,803,000,000
  Source: SEC EDGAR 10-K (2022-09-30)
total_assets: $352,755,000,000
  Source: SEC EDGAR 10-K (2022-09-30)
```

## Features

- ✅ **Simple API**: Clean, intuitive interface
- ✅ **Type hints**: Full type annotations for better IDE support
- ✅ **Async support**: Async/await client for high-performance applications
- ✅ **Citations**: Every data point includes source citation
- ✅ **Error handling**: Comprehensive exception hierarchy
- ✅ **Rate limiting**: Automatic rate limit detection and helpful errors

## Usage

### Get Financial Metrics

```python
# Single metric
revenue = client.get_metrics("TSLA", "revenue")

# Multiple metrics
metrics = client.get_metrics("GOOGL", ["revenue", "net_income", "total_debt"])

# With time period
metrics = client.get_metrics("MSFT", "revenue", period="annual")
```

### Search Companies

```python
# Search by name or ticker
companies = client.search_companies("tesla")

for company in companies:
    print(f"{company.ticker}: {company.name} ({company.sector})")
```

Output:
```
TSLA: Tesla, Inc. (Automotive)
```

### Get Company Details

```python
company = client.get_company("AAPL")

print(f"Name: {company.name}")
print(f"Sector: {company.sector}")
print(f"Industry: {company.industry}")
print(f"Website: {company.website}")
```

### Check Subscription Status

```python
subscription = client.get_subscription()

print(f"Tier: {subscription.tier}")
print(f"Usage: {subscription.usage}/{subscription.limit}")
print(f"Remaining: {subscription.requests_remaining}")

if subscription.is_near_limit:
    print("⚠️ Warning: Approaching usage limit!")
```

### Manage API Keys

```python
# List API keys
keys = client.list_api_keys()
for key in keys:
    print(f"{key.name}: {key.prefix}... (created {key.created_at})")

# Create new key
new_key = client.create_api_key(name="Production Key")
print(f"New API key: {new_key['api_key']}")
# ⚠️ SAVE THIS! It's only shown once

# Revoke key
client.revoke_api_key(key_id=123)
```

## Async Usage

For high-performance applications, use the async client:

```python
import asyncio
from finsight import AsyncFinSightClient

async def main():
    async with AsyncFinSightClient(api_key="your_key") as client:
        # Concurrent requests
        tasks = [
            client.get_metrics("AAPL", "revenue"),
            client.get_metrics("MSFT", "revenue"),
            client.get_metrics("GOOGL", "revenue")
        ]

        results = await asyncio.gather(*tasks)

        for metrics in results:
            print(metrics[0])

asyncio.run(main())
```

## Error Handling

```python
from finsight import (
    FinSightClient,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError
)

client = FinSightClient(api_key="your_key")

try:
    metrics = client.get_metrics("AAPL", "revenue")

except AuthenticationError:
    print("Invalid API key")

except RateLimitError as e:
    print(f"Rate limited! {e}")
    # Could implement exponential backoff here

except ValidationError as e:
    print(f"Invalid parameters: {e}")

except NotFoundError:
    print("Company or metric not found")
```

## Advanced Examples

### Batch Processing

```python
tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "JPM"]
metrics = ["revenue", "net_income", "total_assets"]

for ticker in tickers:
    try:
        data = client.get_metrics(ticker, metrics)
        print(f"\n{ticker}:")
        for metric in data:
            print(f"  {metric.name}: ${metric.value:,.0f}")

    except NotFoundError:
        print(f"{ticker}: Data not available")
```

### Context Manager

```python
# Automatically closes session
with FinSightClient(api_key="your_key") as client:
    metrics = client.get_metrics("AAPL", "revenue")
    print(metrics)

# Session is closed automatically
```

### Custom Base URL (for testing/on-premise)

```python
client = FinSightClient(
    api_key="your_key",
    base_url="https://your-instance.finsight.com"
)
```

## Available Metrics

Get a list of all available metrics:

```python
metrics = client.get_available_metrics()

for m in metrics:
    print(f"{m['name']}: {m['description']} ({m['unit']})")
```

Common metrics:
- `revenue` - Total Revenue
- `net_income` - Net Income
- `total_assets` - Total Assets
- `total_debt` - Total Debt
- `cash` - Cash and Cash Equivalents
- `operating_cash_flow` - Operating Cash Flow
- `shareholders_equity` - Shareholders' Equity
- `current_assets` - Current Assets
- `current_liabilities` - Current Liabilities

## Pricing Tiers

View pricing information:

```python
pricing = client.get_pricing()

for tier_name, details in pricing['tiers'].items():
    print(f"{tier_name.upper()}: {details['price']}")
    print(f"  Requests/month: {details['limits']['monthly']}")
    print(f"  Requests/minute: {details['limits']['per_minute']}")
```

## Rate Limits

| Tier | Requests/Minute | Requests/Month |
|------|----------------|----------------|
| Free | 10 | 1,000 |
| Starter | 60 | 10,000 |
| Professional | 300 | 100,000 |
| Enterprise | 1,000 | 1,000,000 |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Time when limit resets

## Support

- **Documentation**: https://docs.finsight.com
- **Email**: support@finsight.com
- **GitHub**: https://github.com/finsight/finsight-python/issues

## License

MIT License - see LICENSE file for details

## Changelog

### 1.0.0 (2024-01-15)
- Initial release
- Sync and async clients
- Full API coverage
- Comprehensive error handling
- Type hints throughout
