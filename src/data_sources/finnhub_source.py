"""
Finnhub Data Source Plugin
Provides company news, profiles, and market data
Integrated from FinRobot's finnhub_utils with FinSight's plugin architecture
"""

import structlog
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp

from src.data_sources.base import (
    DataSourcePlugin,
    DataSourceType,
    DataSourceCapability,
    FinancialData
)

logger = structlog.get_logger(__name__)


class FinnhubSource(DataSourcePlugin):
    """
    Finnhub data source plugin

    Provides:
    - Company news and press releases
    - Company profiles (sector, industry, description)
    - Market data and fundamentals
    - Insider transactions
    - Stock recommendations

    Rate Limits: 60 calls/minute (free tier), 30 calls/second (premium)
    Cost: Free tier available, premium tiers for higher limits
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Finnhub source

        Args:
            config: Configuration dict with api_key
        """
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            logger.warning("Finnhub API key not configured")

        self.base_url = "https://finnhub.io/api/v1"
        self._session: Optional[aiohttp.ClientSession] = None

    def get_source_type(self) -> DataSourceType:
        """Return Finnhub source type"""
        return DataSourceType.CUSTOM  # Will add FINNHUB to enum later

    def get_capabilities(self) -> List[DataSourceCapability]:
        """Return capabilities provided by Finnhub"""
        return [
            DataSourceCapability.NEWS,
            DataSourceCapability.MARKET_DATA,
            DataSourceCapability.FUNDAMENTALS,
            DataSourceCapability.INSIDER_TRADING,
        ]

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make request to Finnhub API

        Args:
            endpoint: API endpoint (e.g., "/stock/profile2")
            params: Query parameters

        Returns:
            Response data dict
        """
        if not self.api_key:
            raise ValueError("Finnhub API key not configured")

        session = await self._get_session()

        params = params or {}
        params["token"] = self.api_key

        url = f"{self.base_url}{endpoint}"

        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error("Finnhub API request failed", endpoint=endpoint, error=str(e))
            raise

    async def get_company_news(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_news: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get company news

        Args:
            ticker: Ticker symbol
            start_date: Start date (YYYY-MM-DD), defaults to 7 days ago
            end_date: End date (YYYY-MM-DD), defaults to today
            max_news: Maximum number of news items to return

        Returns:
            List of news items
        """
        try:
            # Default to last 7 days
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            news = await self._make_request(
                "/company-news",
                params={
                    "symbol": ticker.upper(),
                    "from": start_date,
                    "to": end_date
                }
            )

            if not news:
                return []

            # Limit to max_news items
            news = news[:max_news]

            # Format news items
            formatted_news = []
            for item in news:
                formatted_news.append({
                    "date": datetime.fromtimestamp(item["datetime"]).isoformat(),
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "image": item.get("image", ""),
                    "category": item.get("category", ""),
                    "related": item.get("related", "")
                })

            logger.info(
                "Finnhub news fetched",
                ticker=ticker,
                news_count=len(formatted_news)
            )

            return formatted_news

        except Exception as e:
            logger.error("Failed to fetch company news", ticker=ticker, error=str(e))
            return []

    async def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """
        Get company profile

        Args:
            ticker: Ticker symbol

        Returns:
            Dict with company profile information
        """
        try:
            profile = await self._make_request(
                "/stock/profile2",
                params={"symbol": ticker.upper()}
            )

            if not profile:
                return {}

            return {
                "ticker": profile.get("ticker"),
                "company_name": profile.get("name"),
                "country": profile.get("country"),
                "currency": profile.get("currency"),
                "exchange": profile.get("exchange"),
                "ipo_date": profile.get("ipo"),
                "market_cap": profile.get("marketCapitalization"),
                "shares_outstanding": profile.get("shareOutstanding"),
                "industry": profile.get("finnhubIndustry"),
                "logo": profile.get("logo"),
                "website": profile.get("weburl"),
                "phone": profile.get("phone")
            }

        except Exception as e:
            logger.error("Failed to get company profile", ticker=ticker, error=str(e))
            return {}

    async def get_financial_data(
        self,
        ticker: str,
        concepts: List[str],
        period: Optional[str] = None
    ) -> List[FinancialData]:
        """
        Fetch financial data from Finnhub

        Note: Finnhub's financial data is limited compared to SEC EDGAR.
        This primarily provides market data and basic fundamentals.

        Args:
            ticker: Company ticker symbol
            concepts: List of financial concepts
            period: Optional period filter

        Returns:
            List of FinancialData objects
        """
        try:
            # Get basic financials from Finnhub
            financials = await self._make_request(
                "/stock/metric",
                params={
                    "symbol": ticker.upper(),
                    "metric": "all"
                }
            )

            if not financials or "metric" not in financials:
                return []

            metrics = financials["metric"]
            results = []
            retrieved_at = datetime.utcnow()

            # Map common concepts to Finnhub metrics
            concept_mapping = {
                "marketCap": "marketCapitalization",
                "peRatio": "peNormalizedAnnual",
                "pbRatio": "pbAnnual",
                "epsAnnual": "epsAnnual",
                "dividendYield": "currentDividendYieldTTM",
                "beta": "beta",
                "week52High": "52WeekHigh",
                "week52Low": "52WeekLow",
            }

            for concept in concepts:
                finnhub_key = concept_mapping.get(concept)
                if not finnhub_key:
                    continue

                value = metrics.get(finnhub_key)
                if value is None:
                    continue

                results.append(FinancialData(
                    source=self.get_source_type(),
                    ticker=ticker.upper(),
                    concept=concept,
                    value=float(value),
                    unit="ratio" if concept in ["peRatio", "pbRatio", "dividendYield", "beta"] else "USD",
                    period="ttm",
                    period_type="duration",
                    citation={
                        "source": "Finnhub",
                        "ticker": ticker.upper(),
                        "retrieved_at": retrieved_at.isoformat(),
                        "url": f"https://finnhub.io/quote/{ticker.upper()}"
                    },
                    retrieved_at=retrieved_at,
                    confidence=0.90
                ))

            return results

        except Exception as e:
            logger.error("Failed to fetch Finnhub data", ticker=ticker, error=str(e))
            return []

    async def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for companies by name or ticker

        Args:
            query: Search query

        Returns:
            List of company info dicts
        """
        try:
            results = await self._make_request(
                "/search",
                params={"q": query}
            )

            if not results or "result" not in results:
                return []

            companies = []
            for item in results["result"][:10]:  # Limit to 10 results
                companies.append({
                    "ticker": item.get("symbol"),
                    "name": item.get("description"),
                    "type": item.get("type"),
                    "exchange": item.get("displaySymbol")
                })

            return companies

        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            return []

    async def health_check(self) -> bool:
        """
        Check if Finnhub is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.api_key:
                return False

            # Try to get company profile for a well-known ticker
            profile = await self.get_company_profile("AAPL")
            return profile.get("ticker") == "AAPL"

        except Exception as e:
            logger.error("Finnhub health check failed", error=str(e))
            return False

    def get_rate_limit(self) -> Optional[int]:
        """
        Finnhub rate limit: 60 calls/minute (free tier)

        Returns:
            60 calls per minute
        """
        return 60

    def get_cost_per_call(self) -> Optional[float]:
        """
        Finnhub has free tier

        Returns:
            0.0 for free tier
        """
        return 0.0

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
