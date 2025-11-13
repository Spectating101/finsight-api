"""
Yahoo Finance Data Source Plugin
Provides real-time market data, company info, and financial statements
Integrated from FinRobot's yfinance_utils with FinSight's plugin architecture
"""

import structlog
import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.data_sources.base import (
    DataSourcePlugin,
    DataSourceType,
    DataSourceCapability,
    FinancialData
)

logger = structlog.get_logger(__name__)


class YahooFinanceSource(DataSourcePlugin):
    """
    Yahoo Finance data source plugin

    Provides:
    - Real-time stock prices
    - Company information (sector, industry, market cap)
    - Historical market data
    - Financial statements (income, balance sheet, cash flow)
    - Dividends and splits
    - Analyst recommendations

    Rate Limits: None (free tier has no enforced limits)
    Cost: Free
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Yahoo Finance source

        Args:
            config: Configuration dict (no API key needed for yfinance)
        """
        super().__init__(config)
        self._cache = {}  # Simple in-memory cache for ticker objects

    def get_source_type(self) -> DataSourceType:
        """Return Yahoo Finance source type"""
        return DataSourceType.YAHOO_FINANCE

    def get_capabilities(self) -> List[DataSourceCapability]:
        """Return capabilities provided by Yahoo Finance"""
        return [
            DataSourceCapability.MARKET_DATA,
            DataSourceCapability.REAL_TIME,
            DataSourceCapability.HISTORICAL,
            DataSourceCapability.FUNDAMENTALS,
            DataSourceCapability.NEWS,
        ]

    def _get_ticker(self, ticker: str) -> yf.Ticker:
        """
        Get yfinance Ticker object with caching

        Args:
            ticker: Ticker symbol

        Returns:
            yf.Ticker object
        """
        ticker = ticker.upper()
        if ticker not in self._cache:
            self._cache[ticker] = yf.Ticker(ticker)
        return self._cache[ticker]

    async def get_financial_data(
        self,
        ticker: str,
        concepts: List[str],
        period: Optional[str] = None
    ) -> List[FinancialData]:
        """
        Fetch financial data from Yahoo Finance

        Supported concepts:
        - Market data: currentPrice, marketCap, previousClose, dayHigh, dayLow, volume
        - Fundamentals: totalRevenue, netIncome, totalAssets, totalDebt,
                       shareholderEquity, freeCashflow, operatingIncome
        - Per-share: earningsPerShare, dividendYield, peRatio, pbRatio

        Args:
            ticker: Company ticker symbol
            concepts: List of financial concepts
            period: Optional period filter (not used for Yahoo Finance info)

        Returns:
            List of FinancialData objects
        """
        try:
            ticker_obj = self._get_ticker(ticker)
            info = ticker_obj.info

            if not info or "symbol" not in info:
                logger.warning("No data found for ticker", ticker=ticker)
                return []

            results = []
            retrieved_at = datetime.utcnow()

            # Map of concept names to Yahoo Finance info keys
            concept_mapping = {
                # Market data (real-time)
                "currentPrice": "currentPrice",
                "marketCap": "marketCap",
                "previousClose": "previousClose",
                "dayHigh": "dayHigh",
                "dayLow": "dayLow",
                "volume": "volume",
                "averageVolume": "averageVolume",

                # Company fundamentals (latest available)
                "totalRevenue": "totalRevenue",
                "revenue": "totalRevenue",
                "netIncome": "netIncome",
                "totalAssets": "totalAssets",
                "totalDebt": "totalDebt",
                "totalLiabilities": "totalLiab",
                "shareholderEquity": "totalStockholderEquity",
                "shareholdersEquity": "totalStockholderEquity",
                "freeCashflow": "freeCashflow",
                "operatingIncome": "operatingIncome",
                "ebitda": "ebitda",
                "grossProfit": "grossProfits",

                # Per-share metrics
                "earningsPerShare": "trailingEps",
                "eps": "trailingEps",
                "dividendYield": "dividendYield",
                "bookValue": "bookValue",

                # Valuation ratios
                "peRatio": "trailingPE",
                "priceToBook": "priceToBook",
                "pbRatio": "priceToBook",
                "priceToSales": "priceToSalesTrailing12Months",

                # Shares outstanding
                "sharesOutstanding": "sharesOutstanding",
            }

            for concept in concepts:
                yf_key = concept_mapping.get(concept)

                if not yf_key:
                    logger.debug("Concept not supported by Yahoo Finance", concept=concept)
                    continue

                value = info.get(yf_key)

                if value is None:
                    logger.debug("No data for concept", ticker=ticker, concept=concept)
                    continue

                # Determine unit and period
                if concept in ["dividendYield", "peRatio", "priceToBook", "priceToSales", "pbRatio"]:
                    unit = "ratio"
                elif concept in ["volume", "averageVolume", "sharesOutstanding"]:
                    unit = "shares"
                elif concept in ["currentPrice", "dayHigh", "dayLow", "previousClose", "bookValue"]:
                    unit = "USD_per_share"
                else:
                    unit = "USD"

                # Determine period type
                if concept in ["currentPrice", "marketCap", "dayHigh", "dayLow", "volume", "totalAssets", "totalDebt"]:
                    period_type = "instant"
                else:
                    period_type = "duration"

                # Get fiscal period info if available
                fiscal_period = "ttm"  # Most Yahoo Finance data is trailing twelve months
                if "financialCurrency" in info:
                    fiscal_period = "latest"

                results.append(FinancialData(
                    source=DataSourceType.YAHOO_FINANCE,
                    ticker=ticker.upper(),
                    concept=concept,
                    value=float(value),
                    unit=unit,
                    period=fiscal_period,
                    period_type=period_type,
                    citation={
                        "source": "Yahoo Finance",
                        "ticker": ticker.upper(),
                        "retrieved_at": retrieved_at.isoformat(),
                        "info_keys": [yf_key],
                        "url": f"https://finance.yahoo.com/quote/{ticker.upper()}"
                    },
                    retrieved_at=retrieved_at,
                    confidence=0.95  # Yahoo Finance is generally reliable
                ))

            logger.info(
                "Yahoo Finance data fetched",
                ticker=ticker,
                concepts_requested=len(concepts),
                concepts_found=len(results)
            )

            return results

        except Exception as e:
            logger.error(
                "Failed to fetch Yahoo Finance data",
                ticker=ticker,
                error=str(e)
            )
            return []

    async def get_stock_price(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get stock price data (current or historical)

        Args:
            ticker: Ticker symbol
            start_date: Optional start date (YYYY-MM-DD) for historical data
            end_date: Optional end date (YYYY-MM-DD) for historical data

        Returns:
            Dict with price data
        """
        try:
            ticker_obj = self._get_ticker(ticker)

            if start_date and end_date:
                # Historical data
                hist = ticker_obj.history(start=start_date, end=end_date)
                return {
                    "ticker": ticker.upper(),
                    "data_type": "historical",
                    "start_date": start_date,
                    "end_date": end_date,
                    "prices": hist.to_dict('records') if not hist.empty else []
                }
            else:
                # Current price
                info = ticker_obj.info
                return {
                    "ticker": ticker.upper(),
                    "data_type": "current",
                    "price": info.get("currentPrice"),
                    "previous_close": info.get("previousClose"),
                    "day_high": info.get("dayHigh"),
                    "day_low": info.get("dayLow"),
                    "volume": info.get("volume"),
                    "market_cap": info.get("marketCap"),
                    "currency": info.get("currency", "USD")
                }

        except Exception as e:
            logger.error("Failed to get stock price", ticker=ticker, error=str(e))
            return {}

    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get company information

        Args:
            ticker: Ticker symbol

        Returns:
            Dict with company info
        """
        try:
            ticker_obj = self._get_ticker(ticker)
            info = ticker_obj.info

            return {
                "ticker": ticker.upper(),
                "company_name": info.get("shortName", info.get("longName")),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary"),
                "employees": info.get("fullTimeEmployees"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency", "USD")
            }

        except Exception as e:
            logger.error("Failed to get company info", ticker=ticker, error=str(e))
            return {}

    async def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for companies by name or ticker

        Note: Yahoo Finance doesn't have a search API, so this tries to match ticker directly

        Args:
            query: Search query (ticker symbol)

        Returns:
            List of company info dicts
        """
        try:
            # Try to fetch company info for the query as a ticker
            ticker_obj = self._get_ticker(query)
            info = ticker_obj.info

            if "symbol" in info:
                return [{
                    "ticker": info.get("symbol"),
                    "name": info.get("shortName", info.get("longName")),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "market_cap": info.get("marketCap")
                }]

            return []

        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            return []

    async def health_check(self) -> bool:
        """
        Check if Yahoo Finance is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to fetch data for a well-known ticker
            ticker_obj = self._get_ticker("AAPL")
            info = ticker_obj.info

            # If we can get basic info, the source is healthy
            return "symbol" in info and info["symbol"] == "AAPL"

        except Exception as e:
            logger.error("Yahoo Finance health check failed", error=str(e))
            return False

    def get_rate_limit(self) -> Optional[int]:
        """
        Yahoo Finance has no enforced rate limit for free tier

        Returns:
            None (no rate limit)
        """
        return None

    def get_cost_per_call(self) -> Optional[float]:
        """
        Yahoo Finance is free

        Returns:
            0.0 (free)
        """
        return 0.0
