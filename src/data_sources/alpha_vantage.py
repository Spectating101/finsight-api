"""
Alpha Vantage Data Source
Provides fundamental data, technical indicators, and market data

Capabilities:
- Company fundamentals (income statement, balance sheet, cash flow)
- Market data and quotes
- Earnings data

Rate Limits:
- Free tier: 25 requests/day
- Premium: 75+ requests/minute
- Recommend caching heavily for free tier
"""

import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import (
    DataSourcePlugin,
    DataSourceType,
    DataSourceCapability,
    FinancialData
)


class AlphaVantageSource(DataSourcePlugin):
    """Alpha Vantage data source implementation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Alpha Vantage source

        Args:
            config: Configuration dict
                - api_key: Alpha Vantage API key (required)
                - cache_ttl: Cache time-to-live in seconds (default: 3600)
        """
        if config is None:
            config = {}

        super().__init__(config)

        self.api_key = config.get('api_key', 'demo')  # 'demo' key for testing
        self.base_url = "https://www.alphavantage.co/query"
        self.cache_ttl = config.get('cache_ttl', 3600)  # 1 hour default
        self._cache = {}

    def get_source_type(self) -> DataSourceType:
        """Return source type identifier"""
        return DataSourceType.ALPHA_VANTAGE

    def get_capabilities(self) -> List[DataSourceCapability]:
        """Return list of capabilities"""
        return [
            DataSourceCapability.FUNDAMENTALS,
            DataSourceCapability.MARKET_DATA,
            DataSourceCapability.EARNINGS
        ]

    def get_rate_limit(self) -> Optional[int]:
        """Alpha Vantage free tier: 25/day = ~1 per hour"""
        return 1  # Very conservative for free tier

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
            concepts: List of concepts (e.g., ["revenue", "net_income"])
            period: Optional period (uses most recent if not specified)

        Returns:
            List of FinancialData objects
        """
        results = []

        # Map concepts to Alpha Vantage data
        # For fundamentals, we need different API calls
        fundamental_concepts = {
            "revenue", "total_revenue", "gross_profit", "operating_income",
            "net_income", "ebitda", "eps"
        }

        market_concepts = {
            "current_price", "market_cap", "pe_ratio", "peg_ratio",
            "book_value", "dividend_yield"
        }

        # Get company overview (has many market metrics)
        if any(c in market_concepts for c in concepts):
            overview = await self._get_company_overview(ticker)

            concept_map = {
                "market_cap": ("MarketCapitalization", "USD"),
                "pe_ratio": ("PERatio", "ratio"),
                "peg_ratio": ("PEGRatio", "ratio"),
                "book_value": ("BookValue", "USD"),
                "dividend_yield": ("DividendYield", "percent"),
                "eps": ("EPS", "USD"),
                "revenue": ("RevenueTTM", "USD"),
                "profit_margin": ("ProfitMargin", "percent")
            }

            for concept in concepts:
                if concept in concept_map:
                    av_key, unit = concept_map[concept]
                    value = overview.get(av_key)

                    if value and value != "None":
                        try:
                            financial_data = FinancialData(
                                source=DataSourceType.ALPHA_VANTAGE,
                                ticker=ticker,
                                concept=concept,
                                value=float(value),
                                unit=unit,
                                period=overview.get("LatestQuarter", "ttm"),
                                period_type="instant",
                                citation={
                                    "source": "Alpha Vantage",
                                    "endpoint": "OVERVIEW",
                                    "url": f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}"
                                },
                                retrieved_at=datetime.now(),
                                confidence=0.90
                            )
                            results.append(financial_data)
                        except (ValueError, TypeError):
                            continue  # Skip invalid values

        return results

    async def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for companies

        Args:
            query: Search query (company name or ticker)

        Returns:
            List of company info dicts
        """
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query,
            "apikey": self.api_key
        }

        try:
            data = await self._make_request(params)
            matches = data.get("bestMatches", [])

            return [
                {
                    'ticker': match.get("1. symbol"),
                    'name': match.get("2. name"),
                    'type': match.get("3. type"),
                    'region': match.get("4. region"),
                    'currency': match.get("8. currency"),
                    'source': 'alpha_vantage'
                }
                for match in matches[:5]  # Top 5 results
            ]
        except Exception:
            return []

    async def health_check(self) -> bool:
        """
        Check if Alpha Vantage is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to fetch overview for a well-known ticker
            overview = await self._get_company_overview("AAPL")
            return 'Symbol' in overview
        except Exception:
            return False

    async def _get_company_overview(self, ticker: str) -> Dict[str, Any]:
        """Get company overview with key metrics"""
        cache_key = f"overview_{ticker}"

        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_data

        params = {
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": self.api_key
        }

        data = await self._make_request(params)

        # Cache the result
        self._cache[cache_key] = (data, datetime.now())

        return data

    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API request with caching and error handling

        Args:
            params: Query parameters

        Returns:
            Response data dictionary
        """
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

                return data

    async def get_income_statement(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Get income statement data (convenience method)

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of annual reports
        """
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": ticker,
            "apikey": self.api_key
        }

        data = await self._make_request(params)
        return data.get("annualReports", [])

    async def get_balance_sheet(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Get balance sheet data (convenience method)

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of annual reports
        """
        params = {
            "function": "BALANCE_SHEET",
            "symbol": ticker,
            "apikey": self.api_key
        }

        data = await self._make_request(params)
        return data.get("annualReports", [])

    async def get_cash_flow(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Get cash flow statement data (convenience method)

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of annual reports
        """
        params = {
            "function": "CASH_FLOW",
            "symbol": ticker,
            "apikey": self.api_key
        }

        data = await self._make_request(params)
        return data.get("annualReports", [])

    async def get_earnings(self, ticker: str) -> Dict[str, Any]:
        """
        Get earnings data (convenience method)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Earnings data dictionary
        """
        params = {
            "function": "EARNINGS",
            "symbol": ticker,
            "apikey": self.api_key
        }

        return await self._make_request(params)
