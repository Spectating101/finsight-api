"""
FinSight API Client
Main client for interacting with the FinSight API
"""

import requests
import aiohttp
from typing import List, Dict, Optional, Union
from urllib.parse import urlencode

from .models import Metric, Company, Citation, Subscription
from .exceptions import (
    FinSightError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError
)


class FinSightClient:
    """
    Synchronous client for FinSight API

    Example:
        client = FinSightClient(api_key="your_api_key")
        metrics = client.get_metrics("AAPL", ["revenue", "net_income"])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.finsight.com",
        timeout: int = 30
    ):
        """
        Initialize FinSight client

        Args:
            api_key: Your FinSight API key
            base_url: API base URL (default: production)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "User-Agent": "finsight-python/1.0.0"
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict:
        """Make HTTP request and handle errors"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout
            )

            # Handle error responses
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            elif response.status_code == 400:
                error_detail = response.json().get("detail", "Validation error")
                raise ValidationError(error_detail)
            elif response.status_code == 404:
                raise NotFoundError("Resource not found")
            elif response.status_code >= 400:
                raise FinSightError(f"API error: {response.status_code} - {response.text}")

            return response.json()

        except requests.RequestException as e:
            raise FinSightError(f"Request failed: {str(e)}")

    def get_metrics(
        self,
        ticker: str,
        metrics: Union[str, List[str]],
        period: Optional[str] = None
    ) -> List[Metric]:
        """
        Get financial metrics for a company

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            metrics: Metric name(s) to retrieve
            period: Optional time period filter

        Returns:
            List of Metric objects

        Example:
            metrics = client.get_metrics("AAPL", ["revenue", "net_income"])
            for metric in metrics:
                print(f"{metric.name}: {metric.value} ({metric.date})")
        """
        if isinstance(metrics, list):
            metrics_str = ",".join(metrics)
        else:
            metrics_str = metrics

        params = {"ticker": ticker, "metrics": metrics_str}
        if period:
            params["period"] = period

        data = self._make_request("GET", "/api/v1/metrics", params=params)

        return [Metric.from_dict(m) for m in data.get("metrics", [])]

    def get_available_metrics(self) -> List[Dict]:
        """
        Get list of all available metrics

        Returns:
            List of available metric definitions

        Example:
            metrics = client.get_available_metrics()
            for m in metrics:
                print(f"{m['name']}: {m['description']}")
        """
        data = self._make_request("GET", "/api/v1/metrics/available")
        return data.get("metrics", [])

    def search_companies(self, query: str, limit: int = 10) -> List[Company]:
        """
        Search for companies by name or ticker

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of Company objects

        Example:
            companies = client.search_companies("apple")
            for company in companies:
                print(f"{company.ticker}: {company.name}")
        """
        params = {"q": query, "limit": limit}
        data = self._make_request("GET", "/api/v1/companies/search", params=params)

        return [Company.from_dict(c) for c in data.get("companies", [])]

    def get_company(self, ticker: str) -> Company:
        """
        Get detailed information about a company

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company object

        Example:
            company = client.get_company("AAPL")
            print(f"{company.name} - {company.sector}")
        """
        data = self._make_request("GET", f"/api/v1/companies/{ticker}")
        return Company.from_dict(data)

    def get_subscription(self) -> Subscription:
        """
        Get current subscription details

        Returns:
            Subscription object

        Example:
            sub = client.get_subscription()
            print(f"Tier: {sub.tier}, Usage: {sub.usage}/{sub.limit}")
        """
        data = self._make_request("GET", "/api/v1/subscription")
        return Subscription.from_dict(data)

    def get_pricing(self) -> Dict:
        """
        Get pricing information for all tiers

        Returns:
            Dictionary of pricing tiers

        Example:
            pricing = client.get_pricing()
            for tier, details in pricing['tiers'].items():
                print(f"{tier}: {details['price']}")
        """
        return self._make_request("GET", "/api/v1/pricing")

    def create_api_key(self, name: Optional[str] = None) -> Dict:
        """
        Create a new API key

        Args:
            name: Optional name for the key

        Returns:
            API key details (WARNING: key is only shown once!)

        Example:
            key_info = client.create_api_key("Production Key")
            print(f"New API key: {key_info['api_key']}")
            # SAVE THIS KEY - it won't be shown again!
        """
        json_data = {"name": name} if name else {}
        return self._make_request("POST", "/api/v1/auth/keys", json_data=json_data)

    def list_api_keys(self) -> List[Dict]:
        """
        List all API keys for current user

        Returns:
            List of API key metadata (no actual keys)

        Example:
            keys = client.list_api_keys()
            for key in keys:
                print(f"{key['name']}: {key['prefix']}... (created {key['created_at']})")
        """
        data = self._make_request("GET", "/api/v1/auth/keys")
        return data.get("api_keys", [])

    def revoke_api_key(self, key_id: int) -> Dict:
        """
        Revoke an API key

        Args:
            key_id: ID of the key to revoke

        Returns:
            Confirmation message

        Example:
            result = client.revoke_api_key(123)
            print(result['message'])
        """
        return self._make_request("DELETE", f"/api/v1/auth/keys/{key_id}")

    def close(self):
        """Close the HTTP session"""
        self.session.close()

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()


class AsyncFinSightClient:
    """
    Asynchronous client for FinSight API

    Example:
        async with AsyncFinSightClient(api_key="your_key") as client:
            metrics = await client.get_metrics("AAPL", ["revenue"])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.finsight.com",
        timeout: int = 30
    ):
        """
        Initialize async FinSight client

        Args:
            api_key: Your FinSight API key
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                "X-API-Key": self.api_key,
                "User-Agent": "finsight-python/1.0.0"
            },
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict:
        """Make async HTTP request"""
        if not self.session:
            raise FinSightError("Client not initialized. Use 'async with' context manager")

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            ) as response:
                # Handle errors
                if response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
                elif response.status == 400:
                    error_data = await response.json()
                    raise ValidationError(error_data.get("detail", "Validation error"))
                elif response.status == 404:
                    raise NotFoundError("Resource not found")
                elif response.status >= 400:
                    text = await response.text()
                    raise FinSightError(f"API error: {response.status} - {text}")

                return await response.json()

        except aiohttp.ClientError as e:
            raise FinSightError(f"Request failed: {str(e)}")

    async def get_metrics(
        self,
        ticker: str,
        metrics: Union[str, List[str]],
        period: Optional[str] = None
    ) -> List[Metric]:
        """Get financial metrics (async)"""
        if isinstance(metrics, list):
            metrics_str = ",".join(metrics)
        else:
            metrics_str = metrics

        params = {"ticker": ticker, "metrics": metrics_str}
        if period:
            params["period"] = period

        data = await self._make_request("GET", "/api/v1/metrics", params=params)
        return [Metric.from_dict(m) for m in data.get("metrics", [])]

    async def search_companies(self, query: str, limit: int = 10) -> List[Company]:
        """Search companies (async)"""
        params = {"q": query, "limit": limit}
        data = await self._make_request("GET", "/api/v1/companies/search", params=params)
        return [Company.from_dict(c) for c in data.get("companies", [])]

    async def get_company(self, ticker: str) -> Company:
        """Get company details (async)"""
        data = await self._make_request("GET", f"/api/v1/companies/{ticker}")
        return Company.from_dict(data)

    async def get_subscription(self) -> Subscription:
        """Get subscription details (async)"""
        data = await self._make_request("GET", "/api/v1/subscription")
        return Subscription.from_dict(data)
