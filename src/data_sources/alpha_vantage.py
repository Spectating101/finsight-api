"""
Alpha Vantage Data Source
Provides fundamental data, technical indicators, and forex/crypto data

Capabilities:
- Company fundamentals (income statement, balance sheet, cash flow)
- Technical indicators (SMA, EMA, RSI, MACD, etc.)
- Forex and crypto data
- Economic indicators

Rate Limits:
- Free tier: 25 requests/day
- Premium: 75+ requests/minute
- Recommend caching heavily for free tier
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from urllib.parse import urlencode

from .base import DataSource


class AlphaVantageSource(DataSource):
    """Alpha Vantage data source implementation"""

    def __init__(self, api_key: str, cache_ttl: int = 3600):
        """
        Initialize Alpha Vantage source

        Args:
            api_key: Alpha Vantage API key (get from https://www.alphavantage.co/support/#api-key)
            cache_ttl: Cache time-to-live in seconds (default: 1 hour, important for free tier!)
        """
        super().__init__(name="Alpha Vantage", source_type="fundamentals")
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.cache_ttl = cache_ttl
        self._cache = {}

    @property
    def available_metrics(self) -> List[str]:
        """Available metrics from Alpha Vantage"""
        return [
            # Income Statement
            "total_revenue",
            "gross_profit",
            "operating_income",
            "net_income",
            "ebitda",
            "eps",

            # Balance Sheet
            "total_assets",
            "total_liabilities",
            "total_shareholder_equity",
            "retained_earnings",
            "total_current_assets",
            "total_current_liabilities",

            # Cash Flow
            "operating_cashflow",
            "capital_expenditures",
            "free_cash_flow",

            # Company Overview
            "market_cap",
            "pe_ratio",
            "peg_ratio",
            "book_value",
            "dividend_per_share",
            "dividend_yield",
            "eps_ttm",
            "revenue_ttm",
            "profit_margin",
            "operating_margin",
            "return_on_assets",
            "return_on_equity",
            "52_week_high",
            "52_week_low",
            "50_day_moving_average",
            "200_day_moving_average"
        ]

    async def get_metric(self, ticker: str, metric_name: str) -> Dict:
        """
        Get a single metric

        Args:
            ticker: Stock ticker symbol
            metric_name: Name of metric

        Returns:
            Metric data with value, date, citation
        """
        # Determine which API endpoint to use based on metric
        if metric_name in ["total_revenue", "gross_profit", "operating_income", "net_income", "ebitda", "eps"]:
            data = await self.get_income_statement(ticker)
            statement = "income_statement"
        elif metric_name in ["total_assets", "total_liabilities", "total_shareholder_equity",
                             "retained_earnings", "total_current_assets", "total_current_liabilities"]:
            data = await self.get_balance_sheet(ticker)
            statement = "balance_sheet"
        elif metric_name in ["operating_cashflow", "capital_expenditures", "free_cash_flow"]:
            data = await self.get_cash_flow(ticker)
            statement = "cash_flow"
        else:
            # Company overview metrics
            data = await self.get_company_overview(ticker)
            statement = "company_overview"

        # Extract metric value
        metric_map = {
            "total_revenue": "totalRevenue",
            "gross_profit": "grossProfit",
            "operating_income": "operatingIncome",
            "net_income": "netIncome",
            "ebitda": "ebitda",
            "eps": "eps",
            "total_assets": "totalAssets",
            "total_liabilities": "totalLiabilities",
            "total_shareholder_equity": "totalShareholderEquity",
            "retained_earnings": "retainedEarnings",
            "total_current_assets": "totalCurrentAssets",
            "total_current_liabilities": "totalCurrentLiabilities",
            "operating_cashflow": "operatingCashflow",
            "capital_expenditures": "capitalExpenditures",
            "free_cash_flow": "freeCashFlow",
            "market_cap": "MarketCapitalization",
            "pe_ratio": "PERatio",
            "peg_ratio": "PEGRatio",
            "book_value": "BookValue",
            "dividend_per_share": "DividendPerShare",
            "dividend_yield": "DividendYield",
            "eps_ttm": "EPS",
            "revenue_ttm": "RevenueTTM",
            "profit_margin": "ProfitMargin",
            "operating_margin": "OperatingMarginTTM",
            "return_on_assets": "ReturnOnAssetsTTM",
            "return_on_equity": "ReturnOnEquityTTM",
            "52_week_high": "52WeekHigh",
            "52_week_low": "52WeekLow",
            "50_day_moving_average": "50DayMovingAverage",
            "200_day_moving_average": "200DayMovingAverage"
        }

        av_key = metric_map.get(metric_name)
        if not av_key:
            raise ValueError(f"Unknown metric: {metric_name}")

        # Extract value from response
        if statement == "company_overview":
            value = data.get(av_key)
            fiscal_date = data.get("LatestQuarter", "")
        else:
            # Financial statements return arrays, get most recent
            if isinstance(data, list) and len(data) > 0:
                most_recent = data[0]
                value = most_recent.get(av_key)
                fiscal_date = most_recent.get("fiscalDateEnding", "")
            else:
                raise ValueError("No financial data available")

        if value is None or value == "None":
            raise ValueError(f"Metric not available: {metric_name}")

        # Convert to float
        try:
            value = float(value)
        except ValueError:
            raise ValueError(f"Invalid value for {metric_name}: {value}")

        return {
            "value": value,
            "unit": "USD",
            "date": fiscal_date,
            "citation": {
                "source": "Alpha Vantage",
                "statement": statement,
                "url": f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}"
            }
        }

    async def get_income_statement(self, ticker: str) -> List[Dict]:
        """Get income statement data"""
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": ticker,
            "apikey": self.api_key
        }

        data = await self._make_request(params)
        return data.get("annualReports", [])

    async def get_balance_sheet(self, ticker: str) -> List[Dict]:
        """Get balance sheet data"""
        params = {
            "function": "BALANCE_SHEET",
            "symbol": ticker,
            "apikey": self.api_key
        }

        data = await self._make_request(params)
        return data.get("annualReports", [])

    async def get_cash_flow(self, ticker: str) -> List[Dict]:
        """Get cash flow statement data"""
        params = {
            "function": "CASH_FLOW",
            "symbol": ticker,
            "apikey": self.api_key
        }

        data = await self._make_request(params)
        return data.get("annualReports", [])

    async def get_company_overview(self, ticker: str) -> Dict:
        """Get company overview with key metrics"""
        params = {
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": self.api_key
        }

        return await self._make_request(params)

    async def get_earnings(self, ticker: str) -> Dict:
        """Get earnings data (quarterly and annual)"""
        params = {
            "function": "EARNINGS",
            "symbol": ticker,
            "apikey": self.api_key
        }

        return await self._make_request(params)

    async def get_technical_indicator(
        self,
        ticker: str,
        indicator: str,
        interval: str = "daily",
        time_period: int = 14
    ) -> Dict:
        """
        Get technical indicator

        Args:
            ticker: Stock ticker
            indicator: Indicator name (SMA, EMA, RSI, MACD, BBANDS, etc.)
            interval: Time interval (1min, 5min, 15min, 30min, 60min, daily, weekly, monthly)
            time_period: Number of data points used to calculate indicator

        Returns:
            Technical indicator data

        Example:
            rsi = await source.get_technical_indicator("AAPL", "RSI", "daily", 14)
        """
        params = {
            "function": indicator.upper(),
            "symbol": ticker,
            "interval": interval,
            "time_period": time_period,
            "apikey": self.api_key
        }

        return await self._make_request(params)

    async def _make_request(self, params: Dict) -> Dict:
        """Make API request with caching"""
        # Create cache key from params
        cache_key = f"{params['function']}_{params['symbol']}"

        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_data

        # Make request
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"API request failed: {response.status}")

                data = await response.json()

                # Check for error messages
                if "Error Message" in data:
                    raise ValueError(f"Alpha Vantage error: {data['Error Message']}")

                if "Note" in data:
                    # Rate limit message
                    raise ValueError("Rate limit exceeded. Please wait or upgrade your API key.")

                # Cache the result
                self._cache[cache_key] = (data, datetime.now())

                return data

    async def get_forex_rate(self, from_currency: str, to_currency: str) -> Dict:
        """
        Get forex exchange rate

        Args:
            from_currency: Base currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "EUR")

        Returns:
            Exchange rate data
        """
        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "apikey": self.api_key
        }

        data = await self._make_request(params)
        return data.get("Realtime Currency Exchange Rate", {})

    async def get_crypto_price(self, symbol: str, market: str = "USD") -> Dict:
        """
        Get cryptocurrency price

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            market: Market currency (e.g., "USD")

        Returns:
            Crypto price data
        """
        params = {
            "function": "DIGITAL_CURRENCY_DAILY",
            "symbol": symbol,
            "market": market,
            "apikey": self.api_key
        }

        return await self._make_request(params)


# Convenience functions
async def get_company_fundamentals(ticker: str, api_key: str) -> Dict:
    """Quick helper to get all fundamental data"""
    source = AlphaVantageSource(api_key=api_key)

    overview = await source.get_company_overview(ticker)
    income = await source.get_income_statement(ticker)
    balance = await source.get_balance_sheet(ticker)
    cashflow = await source.get_cash_flow(ticker)

    return {
        "overview": overview,
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cashflow
    }
