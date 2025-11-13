"""
Tests for FinSight API - Financial Metrics Endpoints
Adapted from FinRobot's testing discipline
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from src.api.metrics import get_metrics, list_available_metrics
from src.models.user import User, PricingTier
from src.data_sources import DataSourceCapability


@pytest.fixture
def mock_user():
    """Create a mock authenticated user"""
    return User(
        user_id="usr_test123",
        email="test@example.com",
        email_verified=True,
        tier=PricingTier.FREE,
        status="active",
        api_calls_this_month=50,
        api_calls_limit=100,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_request(mock_user):
    """Create a mock FastAPI request with authenticated user"""
    request = Mock()
    request.state.user = mock_user
    request.state.api_key = Mock()
    return request


@pytest.fixture
def mock_data_source():
    """Create a mock data source"""
    source = AsyncMock()

    # Mock successful data response
    mock_result = Mock()
    mock_result.ticker = "AAPL"
    mock_result.concept = "revenue"
    mock_result.value = 394328000000.0
    mock_result.unit = "USD"
    mock_result.period = "2023-Q4"
    mock_result.citation = {
        "form": "10-K",
        "accessionNumber": "0000320193-23-000077",
        "filingDate": "2023-11-03"
    }
    mock_result.source = Mock()
    mock_result.source.value = "SEC EDGAR"

    source.get_financial_data.return_value = [mock_result]

    return source


class TestMetricsEndpoint:
    """Test the main metrics endpoint"""

    @pytest.mark.asyncio
    async def test_get_metrics_success(self, mock_user, mock_data_source):
        """Test successful metrics retrieval"""

        with patch('src.api.metrics.get_registry') as mock_registry:
            # Setup mock registry
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            # Call endpoint
            response = await get_metrics(
                ticker="AAPL",
                metrics="revenue",
                period="2023-Q4",
                user=mock_user
            )

            # Verify response
            assert len(response) == 1
            assert response[0].ticker == "AAPL"
            assert response[0].metric == "revenue"
            assert response[0].value == 394328000000.0
            assert response[0].unit == "USD"
            assert response[0].period == "2023-Q4"
            assert response[0].source == "SEC EDGAR"

            # Verify data source was called correctly
            mock_data_source.get_financial_data.assert_called_once_with(
                ticker="AAPL",
                concepts=["revenue"],
                period="2023-Q4"
            )

    @pytest.mark.asyncio
    async def test_get_multiple_metrics(self, mock_user, mock_data_source):
        """Test retrieving multiple metrics at once"""

        # Mock multiple results
        mock_results = []
        for concept in ["revenue", "netIncome", "totalAssets"]:
            result = Mock()
            result.ticker = "AAPL"
            result.concept = concept
            result.value = 1000000.0
            result.unit = "USD"
            result.period = "2023-Q4"
            result.citation = {}
            result.source = Mock()
            result.source.value = "SEC EDGAR"
            mock_results.append(result)

        mock_data_source.get_financial_data.return_value = mock_results

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            response = await get_metrics(
                ticker="AAPL",
                metrics="revenue,netIncome,totalAssets",
                period=None,
                user=mock_user
            )

            assert len(response) == 3
            assert response[0].metric == "revenue"
            assert response[1].metric == "netIncome"
            assert response[2].metric == "totalAssets"

    @pytest.mark.asyncio
    async def test_get_metrics_ticker_validation(self, mock_user):
        """Test that invalid tickers are rejected"""

        with patch('src.api.metrics.get_registry'):
            # Test invalid ticker format
            with pytest.raises(HTTPException) as exc:
                await get_metrics(
                    ticker="INVALID_TICKER_TOO_LONG",
                    metrics="revenue",
                    period=None,
                    user=mock_user
                )

            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_metrics_too_many_metrics(self, mock_user):
        """Test that requesting too many metrics is rejected"""

        with patch('src.api.metrics.get_registry'):
            # Request 21 metrics (max is 20)
            metrics = ",".join([f"metric{i}" for i in range(21)])

            with pytest.raises(HTTPException) as exc:
                await get_metrics(
                    ticker="AAPL",
                    metrics=metrics,
                    period=None,
                    user=mock_user
                )

            assert exc.value.status_code == 400
            assert "Too many metrics" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_metrics_no_data_found(self, mock_user, mock_data_source):
        """Test handling when no data is found for ticker"""

        mock_data_source.get_financial_data.return_value = None

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            with pytest.raises(HTTPException) as exc:
                await get_metrics(
                    ticker="INVALID",
                    metrics="revenue",
                    period=None,
                    user=mock_user
                )

            assert exc.value.status_code == 404
            assert "No data found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_metrics_no_data_sources(self, mock_user):
        """Test handling when no data sources are available"""

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = []

            with pytest.raises(HTTPException) as exc:
                await get_metrics(
                    ticker="AAPL",
                    metrics="revenue",
                    period=None,
                    user=mock_user
                )

            assert exc.value.status_code == 503
            assert "No data sources available" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_metrics_with_period_filter(self, mock_user, mock_data_source):
        """Test metrics retrieval with specific period filter"""

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            response = await get_metrics(
                ticker="AAPL",
                metrics="revenue",
                period="ttm",
                user=mock_user
            )

            # Verify period was passed to data source
            mock_data_source.get_financial_data.assert_called_once()
            call_args = mock_data_source.get_financial_data.call_args
            assert call_args[1]['period'] == "ttm"


class TestAvailableMetricsEndpoint:
    """Test the available metrics endpoint"""

    @pytest.mark.asyncio
    async def test_list_available_metrics(self, mock_user):
        """Test listing available metrics"""

        response = await list_available_metrics(user=mock_user)

        # Verify response structure
        assert "metrics" in response
        assert "periods" in response

        # Verify metrics list
        metrics = response["metrics"]
        assert len(metrics) > 0

        # Check required fields in each metric
        for metric in metrics:
            assert "name" in metric
            assert "description" in metric
            assert "unit" in metric

        # Check for key metrics
        metric_names = [m["name"] for m in metrics]
        assert "revenue" in metric_names
        assert "netIncome" in metric_names
        assert "totalAssets" in metric_names

        # Verify periods list
        periods = response["periods"]
        assert len(periods) > 0
        assert any("ttm" in p.lower() for p in periods)


class TestMetricsValidation:
    """Test input validation for metrics"""

    @pytest.mark.asyncio
    async def test_ticker_case_normalization(self, mock_user, mock_data_source):
        """Test that ticker is normalized to uppercase"""

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            # Use lowercase ticker
            await get_metrics(
                ticker="aapl",
                metrics="revenue",
                period=None,
                user=mock_user
            )

            # Verify it was normalized to uppercase
            call_args = mock_data_source.get_financial_data.call_args
            assert call_args[1]['ticker'] == "AAPL"

    @pytest.mark.asyncio
    async def test_metrics_whitespace_trimming(self, mock_user, mock_data_source):
        """Test that whitespace in metrics is trimmed"""

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            # Use metrics with whitespace
            await get_metrics(
                ticker="AAPL",
                metrics=" revenue , netIncome , totalAssets ",
                period=None,
                user=mock_user
            )

            # Verify whitespace was trimmed
            call_args = mock_data_source.get_financial_data.call_args
            concepts = call_args[1]['concepts']
            assert concepts == ["revenue", "netIncome", "totalAssets"]


class TestMetricsErrorHandling:
    """Test error handling in metrics endpoints"""

    @pytest.mark.asyncio
    async def test_data_source_exception(self, mock_user, mock_data_source):
        """Test handling of data source exceptions"""

        # Mock data source raising exception
        mock_data_source.get_financial_data.side_effect = Exception("Database connection failed")

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            with pytest.raises(HTTPException) as exc:
                await get_metrics(
                    ticker="AAPL",
                    metrics="revenue",
                    period=None,
                    user=mock_user
                )

            assert exc.value.status_code == 500
            assert "Failed to fetch financial metrics" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_metric_name(self, mock_user):
        """Test handling of invalid metric names"""

        with patch('src.api.metrics.get_registry'):
            # Use invalid characters in metric name
            with pytest.raises(HTTPException) as exc:
                await get_metrics(
                    ticker="AAPL",
                    metrics="revenue; DROP TABLE users;",
                    period=None,
                    user=mock_user
                )

            assert exc.value.status_code == 400


class TestMetricsPerformance:
    """Test performance characteristics of metrics endpoints"""

    @pytest.mark.asyncio
    async def test_concurrent_metric_requests(self, mock_user, mock_data_source):
        """Test that multiple metrics can be requested efficiently"""

        # Mock data source with realistic delay
        async def mock_fetch(*args, **kwargs):
            # Simulate I/O delay
            import asyncio
            await asyncio.sleep(0.01)
            return [Mock(
                ticker="AAPL",
                concept="revenue",
                value=1000000.0,
                unit="USD",
                period="2023-Q4",
                citation={},
                source=Mock(value="SEC EDGAR")
            )]

        mock_data_source.get_financial_data = mock_fetch

        with patch('src.api.metrics.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_data_source]

            import time
            start = time.time()

            response = await get_metrics(
                ticker="AAPL",
                metrics="revenue",
                period=None,
                user=mock_user
            )

            elapsed = time.time() - start

            # Should complete quickly (< 1 second for single request)
            assert elapsed < 1.0
            assert len(response) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
