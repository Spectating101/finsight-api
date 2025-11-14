"""
Yahoo Finance Data Source
Provides real-time stock prices, historical data, and market statistics

Capabilities:
- Real-time stock quotes
- Historical price data
- Market statistics (P/E, Beta, Market Cap, etc.)
- Company information

Rate Limits:
- 2,000 requests/hour
- Recommend caching for production use
"""

import yfinance as yf
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base import (
    DataSourcePlugin,
    DataSourceType,
    DataSourceCapability,
    FinancialData
)


class YahooFinanceSource(DataSourcePlugin):
    """Yahoo Finance data source implementation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Yahoo Finance source

        Args:
            config: Optional configuration dict
                - cache_ttl: Cache time-to-live in seconds (default: 300)
        """
        if config is None:
            config = {}

        super().__init__(config)

        self.cache_ttl = config.get('cache_ttl', 300)  # 5 minutes default
        self._cache = {}

    def get_source_type(self) -> DataSourceType:
        """Return source type identifier"""
        return DataSourceType.YAHOO_FINANCE

    def get_capabilities(self) -> List[DataSourceCapability]:
        """Return list of capabilities"""
        return [
            DataSourceCapability.MARKET_DATA,
            DataSourceCapability.REAL_TIME,
            DataSourceCapability.HISTORICAL
        ]

    def get_rate_limit(self) -> Optional[int]:
        """Yahoo Finance rate limit: ~2000 requests/hour = ~33/minute"""
        return 33

    async def get_financial_data(
        self,
        ticker: str,
        concepts: List[str],
        period: Optional[str] = None
    ) -> List[FinancialData]:
        """
        Fetch financial data for given ticker and concepts

        Args:
            ticker: Stock ticker symbol
            concepts: List of concepts (e.g., ["current_price", "market_cap"])
            period: Optional period (not used for Yahoo, always current)

        Returns:
            List of FinancialData objects
        """
        results = []
        stock_data = await self._get_stock_info(ticker)

        # Map concepts to Yahoo Finance fields
        concept_map = {
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

        for concept in concepts:
            yf_field = concept_map.get(concept)
            if not yf_field:
                continue  # Skip unknown concepts

            value = stock_data.get(yf_field)
            if value is None:
                continue  # Skip missing data

            # Determine unit
            if concept in ["market_cap", "shares_outstanding"]:
                unit = "shares"
            elif concept in ["dividend_yield"]:
                unit = "percent"
            elif concept in ["volume", "avg_volume"]:
                unit = "count"
            else:
                unit = "USD"

            # Create FinancialData object
            financial_data = FinancialData(
                source=DataSourceType.YAHOO_FINANCE,
                ticker=ticker,
                concept=concept,
                value=float(value),
                unit=unit,
                period="current",  # Yahoo Finance is always current
                period_type="instant",
                citation={
                    "source": "Yahoo Finance",
                    "url": f"https://finance.yahoo.com/quote/{ticker}",
                    "timestamp": datetime.now().isoformat()
                },
                retrieved_at=datetime.now(),
                confidence=0.95  # Yahoo Finance is generally reliable
            )

            results.append(financial_data)

        return results

    async def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for companies (limited in Yahoo Finance)

        Args:
            query: Search query (ticker symbol)

        Returns:
            List of company info dicts

        Note: Yahoo Finance doesn't have a search API, so we just
        try to fetch info for the ticker if it looks like one
        """
        # Basic validation - if it looks like a ticker, try it
        if not query or len(query) > 5:
            return []

        ticker = query.upper()

        try:
            stock_data = await self._get_stock_info(ticker)

            return [{
                'ticker': ticker,
                'name': stock_data.get('longName', ticker),
                'sector': stock_data.get('sector'),
                'industry': stock_data.get('industry'),
                'source': 'yahoo_finance'
            }]
        except Exception:
            return []

    async def health_check(self) -> bool:
        """
        Check if Yahoo Finance is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to fetch data for a well-known ticker
            stock_data = await self._get_stock_info("AAPL")
            return 'regularMarketPrice' in stock_data
        except Exception:
            return False

    async def _get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get stock info with caching

        Args:
            ticker: Stock ticker symbol

        Returns:
            Stock info dictionary
        """
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

    async def get_historical_data(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data (convenience method)

        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            Historical price data with OHLCV
        """
        stock = yf.Ticker(ticker)
        history = stock.history(period=period, interval=interval)

        if history.empty:
            raise ValueError(f"No historical data available for {ticker}")

        # Convert to list of dicts
        data = []
        for date, row in history.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            })

        return data

    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get company information (convenience method)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company information dictionary
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
