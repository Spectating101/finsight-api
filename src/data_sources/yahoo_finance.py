"""
Yahoo Finance Data Source
Provides real-time stock prices, historical data, and market statistics

Capabilities:
- Real-time stock quotes
- Historical price data
- Market statistics (P/E, Beta, Market Cap, etc.)
- Dividends and splits
- Intraday data

Rate Limits:
- 2,000 requests/hour
- Recommend caching for production use
"""

import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache

from .base import DataSourcePlugin


class YahooFinanceSource(DataSourcePlugin):
    """Yahoo Finance data source implementation"""

    def __init__(self, cache_ttl: int = 300):
        """
        Initialize Yahoo Finance source

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        super().__init__(name="Yahoo Finance", source_type="market_data")
        self.cache_ttl = cache_ttl
        self._cache = {}

    @property
    def available_metrics(self) -> List[str]:
        """List of available metrics from Yahoo Finance"""
        return [
            "current_price",
            "previous_close",
            "open",
            "day_high",
            "day_low",
            "volume",
            "market_cap",
            "pe_ratio",
            "forward_pe",
            "peg_ratio",
            "price_to_book",
            "dividend_yield",
            "beta",
            "52_week_high",
            "52_week_low",
            "50_day_avg",
            "200_day_avg",
            "avg_volume",
            "shares_outstanding"
        ]

    async def get_metric(self, ticker: str, metric_name: str) -> Dict:
        """
        Get a single metric for a ticker

        Args:
            ticker: Stock ticker symbol
            metric_name: Name of metric to retrieve

        Returns:
            Dictionary with value, unit, date, and citation

        Example:
            data = await source.get_metric("AAPL", "current_price")
            # {'value': 150.23, 'unit': 'USD', 'date': '2024-01-15', 'citation': {...}}
        """
        # Get full stock info (cached)
        stock_data = await self._get_stock_info(ticker)

        # Extract requested metric
        metric_map = {
            "current_price": "regularMarketPrice",
            "previous_close": "previousClose",
            "open": "regularMarketOpen",
            "day_high": "dayHigh",
            "day_low": "dayLow",
            "volume": "regularMarketVolume",
            "market_cap": "marketCap",
            "pe_ratio": "trailingPE",
            "forward_pe": "forwardPE",
            "peg_ratio": "pegRatio",
            "price_to_book": "priceToBook",
            "dividend_yield": "dividendYield",
            "beta": "beta",
            "52_week_high": "fiftyTwoWeekHigh",
            "52_week_low": "fiftyTwoWeekLow",
            "50_day_avg": "fiftyDayAverage",
            "200_day_avg": "twoHundredDayAverage",
            "avg_volume": "averageVolume",
            "shares_outstanding": "sharesOutstanding"
        }

        yf_key = metric_map.get(metric_name)
        if not yf_key:
            raise ValueError(f"Unknown metric: {metric_name}")

        value = stock_data.get(yf_key)
        if value is None:
            raise ValueError(f"Metric not available: {metric_name}")

        # Determine unit
        if metric_name in ["market_cap", "shares_outstanding"]:
            unit = "count"
        elif metric_name in ["dividend_yield"]:
            unit = "percentage"
        elif metric_name in ["volume", "avg_volume"]:
            unit = "shares"
        else:
            unit = "USD"

        return {
            "value": value,
            "unit": unit,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "citation": {
                "source": "Yahoo Finance",
                "url": f"https://finance.yahoo.com/quote/{ticker}",
                "timestamp": datetime.now().isoformat()
            }
        }

    async def get_historical_data(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Dict:
        """
        Get historical price data

        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            Historical price data with OHLCV

        Example:
            history = await source.get_historical_data("AAPL", period="1mo", interval="1d")
        """
        stock = yf.Ticker(ticker)
        history = stock.history(period=period, interval=interval)

        if history.empty:
            raise ValueError(f"No historical data available for {ticker}")

        # Convert to dict format
        data = {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data": []
        }

        for date, row in history.iterrows():
            data["data"].append({
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            })

        return data

    async def get_company_info(self, ticker: str) -> Dict:
        """
        Get company information

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company information including name, sector, industry, etc.
        """
        stock_data = await self._get_stock_info(ticker)

        return {
            "ticker": ticker,
            "name": stock_data.get("longName", ticker),
            "sector": stock_data.get("sector"),
            "industry": stock_data.get("industry"),
            "description": stock_data.get("longBusinessSummary"),
            "website": stock_data.get("website"),
            "employees": stock_data.get("fullTimeEmployees"),
            "city": stock_data.get("city"),
            "state": stock_data.get("state"),
            "country": stock_data.get("country")
        }

    async def get_dividends(self, ticker: str) -> List[Dict]:
        """
        Get dividend history

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of dividend payments
        """
        stock = yf.Ticker(ticker)
        dividends = stock.dividends

        if dividends.empty:
            return []

        return [
            {
                "date": date.strftime("%Y-%m-%d"),
                "amount": float(amount)
            }
            for date, amount in dividends.items()
        ]

    async def get_splits(self, ticker: str) -> List[Dict]:
        """
        Get stock split history

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of stock splits
        """
        stock = yf.Ticker(ticker)
        splits = stock.splits

        if splits.empty:
            return []

        return [
            {
                "date": date.strftime("%Y-%m-%d"),
                "ratio": float(ratio)
            }
            for date, ratio in splits.items()
        ]

    async def _get_stock_info(self, ticker: str) -> Dict:
        """Get stock info with caching"""
        cache_key = f"{ticker}_info"

        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_data

        # Fetch fresh data
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Cache the result
            self._cache[cache_key] = (info, datetime.now())

            return info

        except Exception as e:
            raise ValueError(f"Failed to fetch data for {ticker}: {str(e)}")

    async def search_ticker(self, query: str) -> List[Dict]:
        """
        Search for ticker by company name

        Args:
            query: Company name or partial ticker

        Returns:
            List of matching tickers

        Note: Yahoo Finance doesn't have a search API, so this uses yfinance's
        Ticker.info to validate tickers. For production, consider using a
        dedicated ticker search service.
        """
        # This is a basic implementation
        # For production, use a proper search index or external service
        potential_ticker = query.upper()

        try:
            stock_data = await self._get_stock_info(potential_ticker)
            return [{
                "ticker": potential_ticker,
                "name": stock_data.get("longName"),
                "sector": stock_data.get("sector")
            }]

        except Exception:
            return []

    def calculate_returns(self, historical_data: Dict) -> Dict:
        """
        Calculate returns from historical data

        Args:
            historical_data: Historical price data from get_historical_data()

        Returns:
            Dictionary with various return calculations
        """
        if not historical_data.get("data"):
            raise ValueError("No historical data provided")

        prices = [day["close"] for day in historical_data["data"]]

        if len(prices) < 2:
            raise ValueError("Need at least 2 data points to calculate returns")

        # Simple return
        total_return = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Daily returns
        daily_returns = []
        for i in range(1, len(prices)):
            daily_return = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
            daily_returns.append(daily_return)

        # Calculate volatility (standard deviation of daily returns)
        import statistics
        volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0

        return {
            "total_return_pct": total_return,
            "daily_returns": daily_returns,
            "volatility": volatility,
            "start_price": prices[0],
            "end_price": prices[-1],
            "num_days": len(prices)
        }


# Convenience functions for direct use
async def get_current_price(ticker: str) -> float:
    """Quick helper to get current price"""
    source = YahooFinanceSource()
    data = await source.get_metric(ticker, "current_price")
    return data["value"]


async def get_market_cap(ticker: str) -> float:
    """Quick helper to get market cap"""
    source = YahooFinanceSource()
    data = await source.get_metric(ticker, "market_cap")
    return data["value"]
