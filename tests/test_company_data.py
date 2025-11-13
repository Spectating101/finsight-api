"""
Tests for FinSight API - Company Data Endpoints
Tests for high-value endpoints: ratios, overview, and batch
Adapted from FinRobot's testing discipline
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from src.api.company_data import (
    get_financial_ratios,
    get_company_overview,
    get_batch_companies,
    fetch_company_fundamentals
)
from src.models.user import User, APIKey, PricingTier
from src.utils.financial_calculations import FinancialCalculator


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
def mock_api_key():
    """Create a mock API key"""
    return APIKey(
        key_id="key_test123",
        user_id="usr_test123",
        key_prefix="fsk_12345678",
        name="Test Key",
        is_active=True,
        is_test_mode=False,
        total_calls=100,
        calls_this_month=50,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_fundamentals():
    """Create mock company fundamentals data"""
    return {
        "revenue": 394328000000.0,
        "netIncome": 96995000000.0,
        "totalAssets": 352755000000.0,
        "currentAssets": 143566000000.0,
        "currentLiabilities": 145308000000.0,
        "shareholdersEquity": 62146000000.0,
        "totalDebt": 111088000000.0,
        "cashAndEquivalents": 29965000000.0,
        "costOfRevenue": 214137000000.0,
        "grossProfit": 180191000000.0,
        "operatingIncome": 114301000000.0,
        "sharesDiluted": 15728700000.0,
        "sharesBasic": 15634200000.0,
        "as_of_date": "2023-09-30"
    }


@pytest.fixture
def mock_data_source_result():
    """Create mock data source result"""
    results = []

    fundamentals = {
        "revenue": 394328000000.0,
        "netIncome": 96995000000.0,
        "totalAssets": 352755000000.0,
        "currentAssets": 143566000000.0,
        "currentLiabilities": 145308000000.0,
        "shareholdersEquity": 62146000000.0,
        "totalDebt": 111088000000.0,
        "cashAndEquivalents": 29965000000.0,
        "costOfRevenue": 214137000000.0,
        "grossProfit": 180191000000.0,
        "operatingIncome": 114301000000.0,
        "sharesDiluted": 15728700000.0,
        "sharesBasic": 15634200000.0
    }

    for concept, value in fundamentals.items():
        result = Mock()
        result.ticker = "AAPL"
        result.concept = concept
        result.value = value
        result.unit = "USD"
        result.period = "2023-09-30"
        result.citation = {"form": "10-K"}
        result.source = Mock()
        result.source.value = "SEC EDGAR"
        results.append(result)

    return results


class TestFetchCompanyFundamentals:
    """Test the fundamental data fetching utility"""

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_success(self, mock_data_source_result):
        """Test successful fundamental data fetch"""

        mock_source = AsyncMock()
        mock_source.get_financial_data.return_value = mock_data_source_result

        with patch('src.api.company_data.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_source]

            fundamentals = await fetch_company_fundamentals("AAPL")

            assert fundamentals is not None
            assert "revenue" in fundamentals
            assert "netIncome" in fundamentals
            assert "totalAssets" in fundamentals
            assert "as_of_date" in fundamentals
            assert fundamentals["as_of_date"] == "2023-09-30"

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_no_sources(self):
        """Test handling when no data sources available"""

        with patch('src.api.company_data.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = []

            fundamentals = await fetch_company_fundamentals("AAPL")

            assert fundamentals is None

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_no_results(self):
        """Test handling when data source returns no results"""

        mock_source = AsyncMock()
        mock_source.get_financial_data.return_value = None

        with patch('src.api.company_data.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_source]

            fundamentals = await fetch_company_fundamentals("INVALID")

            assert fundamentals is None

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_exception(self):
        """Test handling of exceptions during fetch"""

        mock_source = AsyncMock()
        mock_source.get_financial_data.side_effect = Exception("API error")

        with patch('src.api.company_data.get_registry') as mock_registry:
            mock_registry.return_value.get_by_capability.return_value = [mock_source]

            fundamentals = await fetch_company_fundamentals("AAPL")

            # Should return None on exception
            assert fundamentals is None


class TestFinancialRatiosEndpoint:
    """Test the financial ratios endpoint"""

    @pytest.mark.asyncio
    async def test_get_ratios_success(self, mock_user, mock_api_key, mock_fundamentals):
        """Test successful ratio calculation"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = mock_fundamentals.copy()

            response = await get_financial_ratios(
                ticker="AAPL",
                auth=(mock_user, mock_api_key)
            )

            assert response.ticker == "AAPL"
            assert response.as_of_date == "2023-09-30"
            assert response.source == "SEC EDGAR"

            # Verify key ratios are calculated
            ratios = response.ratios
            assert "profit_margin" in ratios
            assert "roe" in ratios
            assert "current_ratio" in ratios
            assert "debt_to_equity" in ratios

            # Verify ratio values are reasonable
            assert ratios["profit_margin"] is not None
            assert 0 <= ratios["profit_margin"] <= 1  # Profit margin should be between 0-100%

    @pytest.mark.asyncio
    async def test_get_ratios_ticker_validation(self, mock_user, mock_api_key):
        """Test ticker validation in ratios endpoint"""

        with pytest.raises(HTTPException) as exc:
            await get_financial_ratios(
                ticker="INVALID_TICKER_TOO_LONG",
                auth=(mock_user, mock_api_key)
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_ratios_no_data(self, mock_user, mock_api_key):
        """Test handling when no data is found"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = None

            with pytest.raises(HTTPException) as exc:
                await get_financial_ratios(
                    ticker="INVALID",
                    auth=(mock_user, mock_api_key)
                )

            assert exc.value.status_code == 404
            assert "No data found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_ratios_case_insensitive(self, mock_user, mock_api_key, mock_fundamentals):
        """Test that ticker is case-insensitive"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = mock_fundamentals.copy()

            response = await get_financial_ratios(
                ticker="aapl",  # lowercase
                auth=(mock_user, mock_api_key)
            )

            # Should be normalized to uppercase
            assert response.ticker == "AAPL"


class TestCompanyOverviewEndpoint:
    """Test the company overview endpoint"""

    @pytest.mark.asyncio
    async def test_get_overview_success(self, mock_user, mock_api_key, mock_fundamentals):
        """Test successful company overview retrieval"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = mock_fundamentals.copy()

            response = await get_company_overview(
                ticker="AAPL",
                auth=(mock_user, mock_api_key)
            )

            assert response.ticker == "AAPL"
            assert response.as_of_date == "2023-09-30"

            # Verify all three data sections are present
            assert response.fundamentals is not None
            assert response.ratios is not None
            assert response.per_share_metrics is not None

            # Verify fundamentals
            assert "revenue" in response.fundamentals
            assert "netIncome" in response.fundamentals

            # Verify ratios
            assert "profit_margin" in response.ratios
            assert "roe" in response.ratios

            # Verify per-share metrics
            assert "eps_diluted" in response.per_share_metrics
            assert "book_value_per_share" in response.per_share_metrics

    @pytest.mark.asyncio
    async def test_overview_data_consistency(self, mock_user, mock_api_key, mock_fundamentals):
        """Test that all data in overview comes from same period"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = mock_fundamentals.copy()

            response = await get_company_overview(
                ticker="AAPL",
                auth=(mock_user, mock_api_key)
            )

            # All data should be from same date
            assert response.as_of_date == "2023-09-30"

            # Fundamentals should not include as_of_date key (removed in processing)
            assert "as_of_date" not in response.fundamentals

    @pytest.mark.asyncio
    async def test_overview_no_data(self, mock_user, mock_api_key):
        """Test overview endpoint when no data found"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = None

            with pytest.raises(HTTPException) as exc:
                await get_company_overview(
                    ticker="INVALID",
                    auth=(mock_user, mock_api_key)
                )

            assert exc.value.status_code == 404


class TestBatchCompaniesEndpoint:
    """Test the batch companies endpoint"""

    @pytest.mark.asyncio
    async def test_batch_companies_success(self, mock_user, mock_api_key, mock_fundamentals):
        """Test successful batch retrieval"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            # Return fundamentals for all tickers
            mock_fetch.return_value = mock_fundamentals.copy()

            response = await get_batch_companies(
                tickers="AAPL,GOOGL,MSFT",
                include_ratios=True,
                auth=(mock_user, mock_api_key)
            )

            assert response.requested == 3
            assert response.successful == 3
            assert response.failed == 0
            assert len(response.companies) == 3

            # Check first company
            company = response.companies[0]
            assert company.ticker == "AAPL"
            assert company.fundamentals is not None
            assert company.ratios is not None
            assert company.error is None

    @pytest.mark.asyncio
    async def test_batch_without_ratios(self, mock_user, mock_api_key, mock_fundamentals):
        """Test batch retrieval without ratios"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = mock_fundamentals.copy()

            response = await get_batch_companies(
                tickers="AAPL,GOOGL",
                include_ratios=False,
                auth=(mock_user, mock_api_key)
            )

            # Should not include ratios
            for company in response.companies:
                assert company.fundamentals is not None
                assert company.ratios is None

    @pytest.mark.asyncio
    async def test_batch_max_limit(self, mock_user, mock_api_key):
        """Test that batch is limited to 20 companies"""

        # Try to request 21 companies
        tickers = ",".join([f"TICK{i}" for i in range(21)])

        with pytest.raises(HTTPException) as exc:
            await get_batch_companies(
                tickers=tickers,
                include_ratios=True,
                auth=(mock_user, mock_api_key)
            )

        assert exc.value.status_code == 400
        assert "Too many tickers" in str(exc.value.detail)
        assert "max 20" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_batch_partial_success(self, mock_user, mock_api_key, mock_fundamentals):
        """Test batch where some tickers succeed and some fail"""

        async def mock_fetch(ticker):
            if ticker == "INVALID":
                return None
            return mock_fundamentals.copy()

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch_func:
            mock_fetch_func.side_effect = mock_fetch

            response = await get_batch_companies(
                tickers="AAPL,INVALID,GOOGL",
                include_ratios=True,
                auth=(mock_user, mock_api_key)
            )

            assert response.requested == 3
            assert response.successful == 2
            assert response.failed == 1

            # Find the failed ticker
            invalid_company = next(c for c in response.companies if c.ticker == "INVALID")
            assert invalid_company.error == "No data found"
            assert invalid_company.fundamentals is None

    @pytest.mark.asyncio
    async def test_batch_ticker_normalization(self, mock_user, mock_api_key, mock_fundamentals):
        """Test that tickers are normalized (uppercase, trimmed)"""

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch:
            mock_fetch.return_value = mock_fundamentals.copy()

            # Use lowercase with spaces
            response = await get_batch_companies(
                tickers=" aapl , googl , msft ",
                include_ratios=True,
                auth=(mock_user, mock_api_key)
            )

            # Should be normalized to uppercase
            assert response.companies[0].ticker == "AAPL"
            assert response.companies[1].ticker == "GOOGL"
            assert response.companies[2].ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_batch_invalid_ticker(self, mock_user, mock_api_key):
        """Test batch with invalid ticker format"""

        with pytest.raises(HTTPException) as exc:
            await get_batch_companies(
                tickers="AAPL,INVALID_TICKER_TOO_LONG",
                include_ratios=True,
                auth=(mock_user, mock_api_key)
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_batch_exception_handling(self, mock_user, mock_api_key, mock_fundamentals):
        """Test that exceptions for individual tickers don't break entire batch"""

        async def mock_fetch(ticker):
            if ticker == "ERROR":
                raise Exception("Data source error")
            return mock_fundamentals.copy()

        with patch('src.api.company_data.fetch_company_fundamentals') as mock_fetch_func:
            mock_fetch_func.side_effect = mock_fetch

            response = await get_batch_companies(
                tickers="AAPL,ERROR,GOOGL",
                include_ratios=True,
                auth=(mock_user, mock_api_key)
            )

            # Should still succeed for valid tickers
            assert response.successful == 2
            assert response.failed == 1

            # Error ticker should have error message
            error_company = next(c for c in response.companies if c.ticker == "ERROR")
            assert error_company.error is not None


class TestFinancialCalculations:
    """Test financial calculation accuracy"""

    def test_ratio_calculation_accuracy(self):
        """Test that calculated ratios are mathematically accurate"""

        fundamentals = {
            "revenue": 100000000.0,
            "netIncome": 20000000.0,
            "totalAssets": 500000000.0,
            "shareholdersEquity": 200000000.0,
            "currentAssets": 150000000.0,
            "currentLiabilities": 100000000.0,
            "totalDebt": 150000000.0,
        }

        calculator = FinancialCalculator()
        ratios = calculator.calculate_ratios(fundamentals)

        # Test profit margin: net income / revenue
        expected_profit_margin = 20000000.0 / 100000000.0
        assert abs(ratios["profit_margin"] - expected_profit_margin) < 0.001

        # Test ROE: net income / equity
        expected_roe = 20000000.0 / 200000000.0
        assert abs(ratios["roe"] - expected_roe) < 0.001

        # Test current ratio: current assets / current liabilities
        expected_current_ratio = 150000000.0 / 100000000.0
        assert abs(ratios["current_ratio"] - expected_current_ratio) < 0.001

        # Test debt to equity: total debt / equity
        expected_debt_to_equity = 150000000.0 / 200000000.0
        assert abs(ratios["debt_to_equity"] - expected_debt_to_equity) < 0.001

    def test_ratio_calculation_missing_data(self):
        """Test ratio calculation with missing data"""

        # Minimal fundamentals
        fundamentals = {
            "revenue": 100000000.0,
            "netIncome": 20000000.0,
        }

        calculator = FinancialCalculator()
        ratios = calculator.calculate_ratios(fundamentals)

        # Should calculate what it can
        assert ratios["profit_margin"] is not None

        # Should return None for ratios that can't be calculated
        assert ratios["current_ratio"] is None
        assert ratios["debt_to_equity"] is None

    def test_per_share_calculation(self):
        """Test per-share metric calculations"""

        fundamentals = {
            "netIncome": 20000000.0,
            "revenue": 100000000.0,
            "shareholdersEquity": 200000000.0,
            "sharesDiluted": 10000000.0,
        }

        calculator = FinancialCalculator()
        per_share = calculator.calculate_per_share_metrics(fundamentals)

        # Test EPS: net income / shares
        expected_eps = 20000000.0 / 10000000.0
        assert abs(per_share["eps_diluted"] - expected_eps) < 0.001

        # Test book value per share: equity / shares
        expected_book_value = 200000000.0 / 10000000.0
        assert abs(per_share["book_value_per_share"] - expected_book_value) < 0.001

        # Test revenue per share: revenue / shares
        expected_revenue_per_share = 100000000.0 / 10000000.0
        assert abs(per_share["revenue_per_share"] - expected_revenue_per_share) < 0.001


class TestAuthenticationRequirements:
    """Test that endpoints require proper authentication"""

    @pytest.mark.asyncio
    async def test_ratios_requires_auth(self):
        """Test that ratios endpoint requires authentication"""

        # Create mock request without user
        mock_request = Mock()
        mock_request.state.user = None
        mock_request.state.api_key = None

        from src.api.company_data import get_current_user_from_request

        with pytest.raises(HTTPException) as exc:
            await get_current_user_from_request(mock_request)

        assert exc.value.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
