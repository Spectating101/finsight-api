"""
FinSight API Client
Official Python client for interacting with FinSight API
"""

import requests
from typing import List, Dict, Any, Optional
from .exceptions import (
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError,
    ServerError,
    FinSightError
)


class FinSightClient:
    """
    FinSight API Client

    Usage:
        >>> from finsight import FinSightClient
        >>> client = FinSightClient(api_key="fsk_xxxxxxxxxxxx")
        >>> ratios = client.get_ratios("AAPL")
        >>> print(ratios['pe_ratio'])
    """

    def __init__(self, api_key: str, base_url: str = "https://api.finsight.io/api/v1"):
        """
        Initialize FinSight API client

        Args:
            api_key: Your FinSight API key
            base_url: Base URL for API (default: production)
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "User-Agent": "finsight-python/1.0.0"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g. "/company/AAPL/ratios")
            **kwargs: Additional arguments for requests library

        Returns:
            JSON response as dictionary

        Raises:
            AuthenticationError: Invalid API key
            RateLimitError: Rate limit exceeded
            NotFoundError: Resource not found
            ValidationError: Invalid request
            ServerError: Server error (5xx)
            FinSightError: Other API errors
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)

            # Handle different status codes
            if response.status_code == 200:
                return response.json()

            elif response.status_code == 401:
                raise AuthenticationError(
                    "Invalid API key",
                    status_code=401,
                    response=response
                )

            elif response.status_code == 429:
                reset_at = response.headers.get('X-RateLimit-Reset')
                raise RateLimitError(
                    "Rate limit exceeded",
                    status_code=429,
                    response=response,
                    reset_at=reset_at
                )

            elif response.status_code == 404:
                error_data = response.json()
                raise NotFoundError(
                    error_data.get('detail', 'Resource not found'),
                    status_code=404,
                    response=response
                )

            elif response.status_code == 400:
                error_data = response.json()
                raise ValidationError(
                    error_data.get('detail', 'Invalid request'),
                    status_code=400,
                    response=response
                )

            elif response.status_code >= 500:
                raise ServerError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response=response
                )

            else:
                raise FinSightError(
                    f"Unexpected error: {response.status_code}",
                    status_code=response.status_code,
                    response=response
                )

        except requests.exceptions.RequestException as e:
            raise FinSightError(f"Network error: {str(e)}")

    # ==========================================
    # Company Data Methods
    # ==========================================

    def get_ratios(self, ticker: str) -> Dict[str, Any]:
        """
        Get pre-calculated financial ratios for a company

        Args:
            ticker: Stock ticker symbol (e.g. "AAPL")

        Returns:
            Dictionary with ratios:
            {
                "ticker": "AAPL",
                "ratios": {
                    "pe_ratio": 28.5,
                    "roe": 0.147,
                    "debt_to_equity": 1.8,
                    ...
                },
                "as_of_date": "2024-09-30"
            }

        Example:
            >>> ratios = client.get_ratios("AAPL")
            >>> print(f"P/E Ratio: {ratios['ratios']['pe_ratio']}")
        """
        return self._request("GET", f"/company/{ticker.upper()}/ratios")

    def get_overview(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive company overview (fundamentals + ratios + per-share)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with complete company data:
            {
                "ticker": "AAPL",
                "fundamentals": {...},
                "ratios": {...},
                "per_share_metrics": {...}
            }

        Example:
            >>> data = client.get_overview("TSLA")
            >>> print(data['fundamentals']['revenue'])
            >>> print(data['ratios']['pe_ratio'])
        """
        return self._request("GET", f"/company/{ticker.upper()}/overview")

    def get_batch(
        self,
        tickers: List[str],
        include_ratios: bool = True
    ) -> Dict[str, Any]:
        """
        Get data for multiple companies in one request

        Args:
            tickers: List of ticker symbols (max 20)
            include_ratios: Include calculated ratios (default: True)

        Returns:
            Dictionary with companies array:
            {
                "companies": [
                    {"ticker": "AAPL", "fundamentals": {...}, "ratios": {...}},
                    {"ticker": "GOOGL", "fundamentals": {...}, "ratios": {...}}
                ],
                "requested": 2,
                "successful": 2,
                "failed": 0
            }

        Example:
            >>> data = client.get_batch(["AAPL", "GOOGL", "MSFT"])
            >>> for company in data['companies']:
            ...     print(f"{company['ticker']}: P/E = {company['ratios']['pe_ratio']}")
        """
        if len(tickers) > 20:
            raise ValidationError("Maximum 20 tickers per batch request")

        params = {
            "tickers": ",".join([t.upper() for t in tickers]),
            "include_ratios": str(include_ratios).lower()
        }

        return self._request("GET", "/batch/companies", params=params)

    def get_metrics(
        self,
        ticker: str,
        metrics: List[str],
        period: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get specific financial metrics for a company

        Args:
            ticker: Stock ticker symbol
            metrics: List of metrics to fetch (e.g. ["revenue", "netIncome"])
            period: Optional period filter (e.g. "2024-Q3")

        Returns:
            List of metric objects with values and citations

        Example:
            >>> metrics = client.get_metrics("AAPL", ["revenue", "netIncome"])
            >>> for metric in metrics:
            ...     print(f"{metric['metric']}: ${metric['value']:,.0f}")
        """
        params = {
            "ticker": ticker.upper(),
            "metrics": ",".join(metrics)
        }

        if period:
            params["period"] = period

        return self._request("GET", "/metrics", params=params)

    def search_companies(self, query: str) -> Dict[str, Any]:
        """
        Search for companies by name or ticker

        Args:
            query: Search query (company name or ticker)

        Returns:
            Dictionary with search results:
            {
                "query": "apple",
                "results": [
                    {"ticker": "AAPL", "name": "Apple Inc.", "cik": "0000320193"}
                ],
                "count": 1
            }

        Example:
            >>> results = client.search_companies("apple")
            >>> print(results['results'][0]['ticker'])  # AAPL
        """
        return self._request("GET", "/companies/search", params={"q": query})

    # ==========================================
    # Subscription Methods
    # ==========================================

    def get_subscription(self) -> Dict[str, Any]:
        """
        Get current subscription status and usage

        Returns:
            Dictionary with subscription details:
            {
                "tier": "starter",
                "status": "active",
                "api_calls_this_month": 1247,
                "api_calls_limit": 5000,
                "billing_period_start": "2024-11-01",
                "billing_period_end": "2024-12-01"
            }

        Example:
            >>> sub = client.get_subscription()
            >>> remaining = sub['api_calls_limit'] - sub['api_calls_this_month']
            >>> print(f"Calls remaining: {remaining}")
        """
        return self._request("GET", "/billing/subscription")

    # ==========================================
    # Convenience Methods
    # ==========================================

    def get_pe_ratio(self, ticker: str) -> Optional[float]:
        """Get P/E ratio for a company"""
        ratios = self.get_ratios(ticker)
        return ratios['ratios'].get('pe_ratio')

    def get_debt_to_equity(self, ticker: str) -> Optional[float]:
        """Get debt-to-equity ratio for a company"""
        ratios = self.get_ratios(ticker)
        return ratios['ratios'].get('debt_to_equity')

    def get_roe(self, ticker: str) -> Optional[float]:
        """Get ROE (Return on Equity) for a company"""
        ratios = self.get_ratios(ticker)
        return ratios['ratios'].get('roe')

    def get_profit_margin(self, ticker: str) -> Optional[float]:
        """Get profit margin for a company"""
        ratios = self.get_ratios(ticker)
        return ratios['ratios'].get('profit_margin')

    def screen_stocks(
        self,
        tickers: List[str],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Screen stocks based on financial criteria

        Args:
            tickers: List of tickers to screen
            filters: Dictionary of filters, e.g.:
                {
                    "pe_ratio": {"max": 25},
                    "debt_to_equity": {"max": 1.0},
                    "roe": {"min": 0.10}
                }

        Returns:
            List of companies that match criteria

        Example:
            >>> tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
            >>> filters = {
            ...     "pe_ratio": {"max": 30},
            ...     "debt_to_equity": {"max": 1.5}
            ... }
            >>> matches = client.screen_stocks(tickers, filters)
            >>> for company in matches:
            ...     print(company['ticker'])
        """
        batch = self.get_batch(tickers, include_ratios=True)

        matches = []
        for company in batch['companies']:
            if not company.get('ratios'):
                continue

            meets_criteria = True

            for metric, criteria in filters.items():
                value = company['ratios'].get(metric)

                if value is None:
                    meets_criteria = False
                    break

                if 'min' in criteria and value < criteria['min']:
                    meets_criteria = False
                    break

                if 'max' in criteria and value > criteria['max']:
                    meets_criteria = False
                    break

            if meets_criteria:
                matches.append(company)

        return matches

    def __repr__(self):
        return f"<FinSightClient base_url='{self.base_url}'>"
