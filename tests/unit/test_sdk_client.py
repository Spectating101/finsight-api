"""
Unit tests for FinSight Python SDK
Tests both synchronous and asynchronous clients with mocked HTTP responses
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
import os

# Add SDK to path
sdk_path = os.path.join(os.path.dirname(__file__), '../../sdk/python')
sys.path.insert(0, sdk_path)

from finsight.client import FinSightClient, AsyncFinSightClient
from finsight.models import Metric, Company, Citation, Subscription
from finsight.exceptions import (
    FinSightError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError
)


class TestFinSightClientInit:
    """Test client initialization"""

    def test_client_init_basic(self):
        """Test basic client initialization"""
        client = FinSightClient(api_key="test_key")

        assert client.api_key == "test_key"
        assert client.base_url == "https://api.finsight.com"
        assert client.timeout == 30
        assert "X-API-Key" in client.session.headers
        assert client.session.headers["X-API-Key"] == "test_key"

    def test_client_init_custom_base_url(self):
        """Test client with custom base URL"""
        client = FinSightClient(
            api_key="test_key",
            base_url="https://staging.finsight.com/"
        )

        # Should strip trailing slash
        assert client.base_url == "https://staging.finsight.com"

    def test_client_init_custom_timeout(self):
        """Test client with custom timeout"""
        client = FinSightClient(api_key="test_key", timeout=60)
        assert client.timeout == 60

    def test_client_context_manager(self):
        """Test client can be used as context manager"""
        with FinSightClient(api_key="test_key") as client:
            assert client.api_key == "test_key"

        # Session should be closed after context
        # (Can't easily test this without actual network calls)


class TestFinSightClientGetMetrics:
    """Test get_metrics method"""

    def setup_method(self):
        """Setup for each test"""
        self.client = FinSightClient(api_key="test_key")

    def test_get_metrics_single(self):
        """Test getting a single metric"""
        mock_response = {
            "metrics": [
                {
                    "name": "revenue",
                    "value": 394328000000.0,
                    "unit": "USD",
                    "date": "2024-09-30"
                }
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            metrics = self.client.get_metrics("AAPL", "revenue")

            assert len(metrics) == 1
            assert isinstance(metrics[0], Metric)
            assert metrics[0].name == "revenue"
            assert metrics[0].value == 394328000000.0

    def test_get_metrics_multiple(self):
        """Test getting multiple metrics"""
        mock_response = {
            "metrics": [
                {
                    "name": "revenue",
                    "value": 394328000000.0,
                    "unit": "USD",
                    "date": "2024-09-30"
                },
                {
                    "name": "net_income",
                    "value": 93736000000.0,
                    "unit": "USD",
                    "date": "2024-09-30"
                }
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            metrics = self.client.get_metrics("AAPL", ["revenue", "net_income"])

            assert len(metrics) == 2
            assert metrics[0].name == "revenue"
            assert metrics[1].name == "net_income"

    def test_get_metrics_with_period(self):
        """Test getting metrics with period filter"""
        mock_response = {"metrics": []}

        with patch.object(self.client, '_make_request', return_value=mock_response) as mock:
            self.client.get_metrics("AAPL", "revenue", period="2024-Q3")

            # Verify period was passed in params (kwargs)
            call_kwargs = mock.call_args.kwargs
            params = call_kwargs.get("params", {})
            assert params["period"] == "2024-Q3"

    def test_get_metrics_with_citation(self):
        """Test metrics with citation information"""
        mock_response = {
            "metrics": [
                {
                    "name": "revenue",
                    "value": 394328000000.0,
                    "unit": "USD",
                    "date": "2024-09-30",
                    "citation": {
                        "source": "SEC EDGAR",
                        "form": "10-Q",
                        "filing_date": "2024-11-01",
                        "url": "https://sec.gov/..."
                    }
                }
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            metrics = self.client.get_metrics("AAPL", "revenue")

            assert metrics[0].citation is not None
            assert isinstance(metrics[0].citation, Citation)
            assert metrics[0].citation.source == "SEC EDGAR"
            assert metrics[0].citation.form == "10-Q"


class TestFinSightClientCompanies:
    """Test company-related methods"""

    def setup_method(self):
        """Setup for each test"""
        self.client = FinSightClient(api_key="test_key")

    def test_search_companies(self):
        """Test searching for companies"""
        mock_response = {
            "companies": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "sector": "Technology",
                    "industry": "Consumer Electronics"
                },
                {
                    "ticker": "AAPLW",
                    "name": "Apple Inc. Warrants",
                    "sector": "Technology"
                }
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            companies = self.client.search_companies("Apple")

            assert len(companies) == 2
            assert isinstance(companies[0], Company)
            assert companies[0].ticker == "AAPL"
            assert companies[0].name == "Apple Inc."

    def test_search_companies_with_limit(self):
        """Test search with custom limit"""
        mock_response = {"companies": []}

        with patch.object(self.client, '_make_request', return_value=mock_response) as mock:
            self.client.search_companies("Tech", limit=5)

            # Verify limit was passed (kwargs)
            call_kwargs = mock.call_args.kwargs
            params = call_kwargs.get("params", {})
            assert params["limit"] == 5

    def test_get_company(self):
        """Test getting company details"""
        mock_response = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "description": "Apple designs, manufactures...",
            "website": "https://www.apple.com",
            "cik": "0000320193"
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            company = self.client.get_company("AAPL")

            assert isinstance(company, Company)
            assert company.ticker == "AAPL"
            assert company.name == "Apple Inc."
            assert company.cik == "0000320193"


class TestFinSightClientSubscription:
    """Test subscription-related methods"""

    def setup_method(self):
        """Setup for each test"""
        self.client = FinSightClient(api_key="test_key")

    def test_get_subscription(self):
        """Test getting subscription details"""
        mock_response = {
            "tier": "professional",
            "status": "active",
            "usage": 1250,
            "limit": 10000,
            "requests_remaining": 8750,
            "reset_date": "2024-12-01"
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            sub = self.client.get_subscription()

            assert isinstance(sub, Subscription)
            assert sub.tier == "professional"
            assert sub.usage == 1250
            assert sub.requests_remaining == 8750

    def test_get_pricing(self):
        """Test getting pricing information"""
        mock_response = {
            "tiers": {
                "free": {"price": 0, "requests": 100},
                "starter": {"price": 29, "requests": 1000},
                "professional": {"price": 99, "requests": 10000}
            }
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            pricing = self.client.get_pricing()

            assert "tiers" in pricing
            assert "free" in pricing["tiers"]
            assert pricing["tiers"]["starter"]["price"] == 29


class TestFinSightClientAPIKeys:
    """Test API key management methods"""

    def setup_method(self):
        """Setup for each test"""
        self.client = FinSightClient(api_key="test_key")

    def test_create_api_key(self):
        """Test creating an API key"""
        mock_response = {
            "api_key": "fsk_new_key_12345",
            "key_id": "key_123",
            "name": "Test Key",
            "prefix": "fsk_new_key"
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            key_info = self.client.create_api_key("Test Key")

            assert "api_key" in key_info
            assert key_info["name"] == "Test Key"

    def test_list_api_keys(self):
        """Test listing API keys"""
        mock_response = {
            "api_keys": [
                {"key_id": "key_1", "name": "Production", "prefix": "fsk_prod"},
                {"key_id": "key_2", "name": "Test", "prefix": "fsk_test"}
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            keys = self.client.list_api_keys()

            assert len(keys) == 2
            assert keys[0]["name"] == "Production"

    def test_revoke_api_key(self):
        """Test revoking an API key"""
        mock_response = {"message": "API key revoked successfully"}

        with patch.object(self.client, '_make_request', return_value=mock_response):
            result = self.client.revoke_api_key(123)

            assert "message" in result


class TestFinSightClientErrorHandling:
    """Test error handling in client"""

    def setup_method(self):
        """Setup for each test"""
        self.client = FinSightClient(api_key="test_key")

    def test_authentication_error(self):
        """Test 401 authentication error"""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(self.client.session, 'request', return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Invalid API key"):
                self.client.get_metrics("AAPL", "revenue")

    def test_rate_limit_error(self):
        """Test 429 rate limit error"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}

        with patch.object(self.client.session, 'request', return_value=mock_response):
            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                self.client.get_metrics("AAPL", "revenue")

    def test_validation_error(self):
        """Test 400 validation error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid ticker symbol"}

        with patch.object(self.client.session, 'request', return_value=mock_response):
            with pytest.raises(ValidationError, match="Invalid ticker symbol"):
                self.client.get_metrics("INVALID", "revenue")

    def test_not_found_error(self):
        """Test 404 not found error"""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(self.client.session, 'request', return_value=mock_response):
            with pytest.raises(NotFoundError, match="Resource not found"):
                self.client.get_company("NOTFOUND")

    def test_generic_api_error(self):
        """Test generic API error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        with patch.object(self.client.session, 'request', return_value=mock_response):
            with pytest.raises(FinSightError, match="API error: 500"):
                self.client.get_metrics("AAPL", "revenue")


class TestFinSightClientAvailableMetrics:
    """Test getting available metrics"""

    def setup_method(self):
        """Setup for each test"""
        self.client = FinSightClient(api_key="test_key")

    def test_get_available_metrics(self):
        """Test getting list of available metrics"""
        mock_response = {
            "metrics": [
                {"name": "revenue", "description": "Total revenue"},
                {"name": "net_income", "description": "Net income"},
                {"name": "eps", "description": "Earnings per share"}
            ]
        }

        with patch.object(self.client, '_make_request', return_value=mock_response):
            metrics = self.client.get_available_metrics()

            assert len(metrics) == 3
            assert metrics[0]["name"] == "revenue"


# Async Client Tests

class TestAsyncFinSightClientInit:
    """Test async client initialization"""

    def test_async_client_init(self):
        """Test async client initialization"""
        client = AsyncFinSightClient(api_key="test_key")

        assert client.api_key == "test_key"
        assert client.base_url == "https://api.finsight.com"
        assert client.session is None  # Not initialized until context manager


class TestAsyncFinSightClientGetMetrics:
    """Test async client get_metrics"""

    @pytest.mark.asyncio
    async def test_get_metrics_async(self):
        """Test getting metrics with async client"""
        mock_response = {
            "metrics": [
                {
                    "name": "revenue",
                    "value": 394328000000.0,
                    "unit": "USD",
                    "date": "2024-09-30"
                }
            ]
        }

        async with AsyncFinSightClient(api_key="test_key") as client:
            with patch.object(client, '_make_request', new_callable=AsyncMock, return_value=mock_response):
                metrics = await client.get_metrics("AAPL", "revenue")

                assert len(metrics) == 1
                assert metrics[0].name == "revenue"

    @pytest.mark.asyncio
    async def test_async_client_context_manager(self):
        """Test async client context manager"""
        async with AsyncFinSightClient(api_key="test_key") as client:
            assert client.session is not None
            assert "X-API-Key" in client.session.headers

        # Session should be closed after context

    @pytest.mark.asyncio
    async def test_async_client_without_context_manager(self):
        """Test async client raises error without context manager"""
        client = AsyncFinSightClient(api_key="test_key")

        with pytest.raises(FinSightError, match="Client not initialized"):
            await client.get_metrics("AAPL", "revenue")


class TestAsyncFinSightClientCompanies:
    """Test async client company methods"""

    @pytest.mark.asyncio
    async def test_search_companies_async(self):
        """Test async company search"""
        mock_response = {
            "companies": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "sector": "Technology"
                }
            ]
        }

        async with AsyncFinSightClient(api_key="test_key") as client:
            with patch.object(client, '_make_request', new_callable=AsyncMock, return_value=mock_response):
                companies = await client.search_companies("Apple")

                assert len(companies) == 1
                assert companies[0].ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_get_company_async(self):
        """Test async get company"""
        mock_response = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology"
        }

        async with AsyncFinSightClient(api_key="test_key") as client:
            with patch.object(client, '_make_request', new_callable=AsyncMock, return_value=mock_response):
                company = await client.get_company("AAPL")

                assert company.ticker == "AAPL"


class TestAsyncFinSightClientErrorHandling:
    """Test async client error handling"""

    @pytest.mark.asyncio
    async def test_async_authentication_error(self):
        """Test async client authentication error"""
        # Create mock response
        mock_response = AsyncMock()
        mock_response.status = 401

        # Create mock session
        mock_session = AsyncMock()
        mock_session.request = AsyncMock(return_value=mock_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        async with AsyncFinSightClient(api_key="test_key") as client:
            client.session.request = Mock(return_value=mock_response)

            with pytest.raises(AuthenticationError):
                await client.get_metrics("AAPL", "revenue")

    @pytest.mark.asyncio
    async def test_async_rate_limit_error(self):
        """Test async client rate limit error"""
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}

        async with AsyncFinSightClient(api_key="test_key") as client:
            with patch.object(client.session, 'request') as mock_request:
                mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(RateLimitError):
                    await client.get_metrics("AAPL", "revenue")


# Integration-style tests

class TestSDKModels:
    """Test SDK data models"""

    def test_metric_str_representation(self):
        """Test Metric string representation"""
        metric = Metric(
            name="revenue",
            value=1000000000.0,
            unit="USD",
            date="2024-09-30"
        )

        str_repr = str(metric)
        assert "revenue" in str_repr
        assert "1,000,000,000.00" in str_repr

    def test_citation_from_dict(self):
        """Test creating Citation from dict"""
        data = {
            "source": "SEC EDGAR",
            "form": "10-Q",
            "filing_date": "2024-11-01",
            "url": "https://sec.gov/..."
        }

        citation = Citation.from_dict(data)
        assert citation.source == "SEC EDGAR"
        assert citation.form == "10-Q"

    def test_company_str_representation(self):
        """Test Company string representation"""
        company = Company(
            ticker="AAPL",
            name="Apple Inc."
        )

        str_repr = str(company)
        assert "AAPL" in str_repr
        assert "Apple Inc." in str_repr
