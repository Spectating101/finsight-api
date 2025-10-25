# FinSight API

**Production-grade financial data API with AI-powered synthesis**

## Overview

FinSight provides SEC EDGAR data, market data, and financial calculations through a clean REST API with built-in AI synthesis capabilities.

## Features

- **Multi-Source Financial Data**
  - SEC EDGAR (10-K, 10-Q, 8-K filings)
  - Yahoo Finance (market data, prices)
  - Alpha Vantage (real-time data)
  - Extensible plugin architecture for new sources

- **Advanced Calculations**
  - 100+ financial metrics
  - Trailing Twelve Months (TTM)
  - Year-over-Year (YoY) growth
  - Custom formula engine

- **AI Synthesis**
  - Natural language queries
  - Citation-backed responses
  - Multi-source validation

- **Production Ready**
  - API key authentication
  - Usage-based billing
  - Rate limiting
  - Comprehensive logging

## Architecture

```
finsight-api/
├── src/
│   ├── api/          # API routes (FastAPI)
│   ├── core/         # Business logic (calculations, metrics)
│   ├── data_sources/ # Plugin-based data source adapters
│   ├── auth/         # API key management
│   ├── billing/      # Stripe integration, usage tracking
│   ├── middleware/   # Rate limiting, auth
│   ├── models/       # Pydantic models
│   └── utils/        # Shared utilities
├── tests/            # Test suite
├── docs/             # API documentation
└── config/           # Configuration files
```

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Run
```bash
uvicorn src.main:app --reload
```

### API Documentation
Once running, visit: http://localhost:8000/docs

## Pricing Tiers

- **Free**: 100 API calls/month
- **Starter**: $49/mo - 1,000 calls/month
- **Professional**: $199/mo - 10,000 calls/month
- **Enterprise**: $999/mo - Unlimited + SLA

## API Example

```bash
curl -H "X-API-Key: your-key-here" \
  "https://api.finsight.io/v1/metrics?ticker=AAPL&metric=revenue&period=ttm"
```

Response:
```json
{
  "ticker": "AAPL",
  "metric": "revenue",
  "value": 383285000000,
  "period": "ttm",
  "unit": "USD",
  "citations": [
    {
      "source": "SEC EDGAR",
      "filing": "10-K",
      "accession": "0000320193-23-000077",
      "url": "https://www.sec.gov/..."
    }
  ]
}
```

## License

Proprietary - All Rights Reserved
