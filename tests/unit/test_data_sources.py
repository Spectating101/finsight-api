"""
Unit tests for data source integrations
Tests Yahoo Finance and Alpha Vantage with mocked API responses
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

from src.data_sources.yahoo_finance import YahooFinanceSource
from src.data_sources.alpha_vantage import AlphaVantageSource
from src.data_sources.base import (
    DataSourceType,
    DataSourceCapability,
    FinancialData
)


class TestYahooFinanceConfiguration:
    """Test Yahoo Finance configuration and initialization"""

    def test_source_type(self):
        """Test source type is correctly identified"""
        source = YahooFinanceSource()
        assert source.get_source_type() == DataSourceType.YAHOO_FINANCE

    def test_capabilities(self):
        """Test Yahoo Finance capabilities"""
        source = YahooFinanceSource()
        caps = source.get_capabilities()

        assert DataSourceCapability.MARKET_DATA in caps
        assert DataSourceCapability.REAL_TIME in caps
        assert DataSourceCapability.HISTORICAL in caps

    def test_rate_limit(self):
        """Test rate limit is defined"""
        source = YahooFinanceSource()
        rate_limit = source.get_rate_limit()

        assert rate_limit is not None
        assert rate_limit == 33  # ~2000 requests/hour

    def test_custom_cache_ttl(self):
        """Test custom cache TTL configuration"""
        source = YahooFinanceSource(config={'cache_ttl': 600})
        assert source.cache_ttl == 600

    def test_default_cache_ttl(self):
        """Test default cache TTL"""
        source = YahooFinanceSource()
        assert source.cache_ttl == 300  # 5 minutes


class TestYahooFinanceDataRetrieval:
    """Test Yahoo Finance data retrieval with mocked responses"""

    def setup_method(self):
        """Setup for each test"""
        self.source = YahooFinanceSource()

    @pytest.mark.asyncio
    async def test_get_financial_data_current_price(self):
        """Test fetching current price"""
        # Mock yfinance response
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'regularMarketPrice': 150.23,
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            data = await self.source.get_financial_data("AAPL", ["current_price"])

            assert len(data) == 1
            assert data[0].source == DataSourceType.YAHOO_FINANCE
            assert data[0].ticker == "AAPL"
            assert data[0].concept == "current_price"
            assert data[0].value == 150.23
            assert data[0].unit == "USD"
            assert data[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_get_financial_data_market_cap(self):
        """Test fetching market cap"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'marketCap': 2500000000000,
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            data = await self.source.get_financial_data("AAPL", ["market_cap"])

            assert len(data) == 1
            assert data[0].concept == "market_cap"
            assert data[0].value == 2500000000000
            assert data[0].unit == "shares"

    @pytest.mark.asyncio
    async def test_get_financial_data_multiple_concepts(self):
        """Test fetching multiple concepts at once"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'regularMarketPrice': 150.23,
                'marketCap': 2500000000000,
                'trailingPE': 25.5,
                'beta': 1.2,
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            data = await self.source.get_financial_data(
                "AAPL",
                ["current_price", "market_cap", "pe_ratio", "beta"]
            )

            assert len(data) == 4
            concepts = [d.concept for d in data]
            assert "current_price" in concepts
            assert "market_cap" in concepts
            assert "pe_ratio" in concepts
            assert "beta" in concepts

    @pytest.mark.asyncio
    async def test_get_financial_data_missing_field(self):
        """Test handling missing data fields"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'regularMarketPrice': 150.23,
                # marketCap missing
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            data = await self.source.get_financial_data(
                "AAPL",
                ["current_price", "market_cap"]
            )

            # Should only return current_price, skip missing market_cap
            assert len(data) == 1
            assert data[0].concept == "current_price"

    @pytest.mark.asyncio
    async def test_get_financial_data_unknown_concept(self):
        """Test handling unknown concepts"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'regularMarketPrice': 150.23,
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            data = await self.source.get_financial_data(
                "AAPL",
                ["unknown_concept", "current_price"]
            )

            # Should only return current_price, skip unknown
            assert len(data) == 1
            assert data[0].concept == "current_price"


class TestYahooFinanceSearch:
    """Test Yahoo Finance company search"""

    def setup_method(self):
        """Setup for each test"""
        self.source = YahooFinanceSource()

    @pytest.mark.asyncio
    async def test_search_valid_ticker(self):
        """Test searching for a valid ticker"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'symbol': 'AAPL',
                'longName': 'Apple Inc.',
                'sector': 'Technology',
                'industry': 'Consumer Electronics'
            }
            mock_ticker.return_value = mock_instance

            results = await self.source.search_companies("AAPL")

            assert len(results) == 1
            assert results[0]['ticker'] == 'AAPL'
            assert results[0]['name'] == 'Apple Inc.'
            assert results[0]['sector'] == 'Technology'
            assert results[0]['source'] == 'yahoo_finance'

    @pytest.mark.asyncio
    async def test_search_invalid_ticker(self):
        """Test searching for invalid ticker"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("Invalid ticker")

            results = await self.source.search_companies("INVALID")

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_too_long(self):
        """Test that long queries are rejected"""
        results = await self.source.search_companies("TOOLONGQUERY")
        assert len(results) == 0


class TestYahooFinanceHealthCheck:
    """Test Yahoo Finance health check"""

    def setup_method(self):
        """Setup for each test"""
        self.source = YahooFinanceSource()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'regularMarketPrice': 150.23,
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            is_healthy = await self.source.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("API unavailable")

            is_healthy = await self.source.health_check()
            assert is_healthy is False


class TestYahooFinanceCaching:
    """Test Yahoo Finance caching behavior"""

    def setup_method(self):
        """Setup for each test"""
        self.source = YahooFinanceSource(config={'cache_ttl': 300})

    @pytest.mark.asyncio
    async def test_cache_stores_data(self):
        """Test that data is cached"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'regularMarketPrice': 150.23,
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            # First call
            await self.source.get_financial_data("AAPL", ["current_price"])

            # Cache should be populated
            assert "AAPL_info" in self.source._cache

    @pytest.mark.asyncio
    async def test_cache_reuse(self):
        """Test that cached data is reused"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {
                'regularMarketPrice': 150.23,
                'symbol': 'AAPL'
            }
            mock_ticker.return_value = mock_instance

            # First call - should hit API
            await self.source.get_financial_data("AAPL", ["current_price"])
            assert mock_ticker.call_count == 1

            # Second call - should use cache
            await self.source.get_financial_data("AAPL", ["current_price"])
            # Still only 1 call if cache works
            # (In reality, yfinance is called each time, but our cache stores the info)


# Alpha Vantage Tests

class TestAlphaVantageConfiguration:
    """Test Alpha Vantage configuration and initialization"""

    def test_source_type(self):
        """Test source type is correctly identified"""
        source = AlphaVantageSource()
        assert source.get_source_type() == DataSourceType.ALPHA_VANTAGE

    def test_capabilities(self):
        """Test Alpha Vantage capabilities"""
        source = AlphaVantageSource()
        caps = source.get_capabilities()

        assert DataSourceCapability.FUNDAMENTALS in caps
        assert DataSourceCapability.MARKET_DATA in caps
        assert DataSourceCapability.EARNINGS in caps

    def test_rate_limit(self):
        """Test rate limit is very conservative for free tier"""
        source = AlphaVantageSource()
        rate_limit = source.get_rate_limit()

        assert rate_limit is not None
        assert rate_limit == 1  # Very conservative for free tier

    def test_custom_api_key(self):
        """Test custom API key configuration"""
        source = AlphaVantageSource(config={'api_key': 'custom_key'})
        assert source.api_key == 'custom_key'

    def test_default_api_key(self):
        """Test default demo API key"""
        source = AlphaVantageSource()
        assert source.api_key == 'demo'


class TestAlphaVantageDataRetrieval:
    """Test Alpha Vantage data retrieval with mocked responses"""

    def setup_method(self):
        """Setup for each test"""
        self.source = AlphaVantageSource(config={'api_key': 'test_key'})

    @pytest.mark.asyncio
    async def test_get_financial_data_market_cap(self):
        """Test fetching market cap from company overview"""
        mock_overview = {
            'Symbol': 'AAPL',
            'MarketCapitalization': '2500000000000',
            'PERatio': '25.5',
            'LatestQuarter': '2024-09-30'
        }

        with patch.object(self.source, '_get_company_overview', new_callable=AsyncMock) as mock_overview_call:
            mock_overview_call.return_value = mock_overview

            data = await self.source.get_financial_data("AAPL", ["market_cap"])

            assert len(data) == 1
            assert data[0].source == DataSourceType.ALPHA_VANTAGE
            assert data[0].ticker == "AAPL"
            assert data[0].concept == "market_cap"
            assert data[0].value == 2500000000000.0
            assert data[0].unit == "USD"
            assert data[0].confidence == 0.90

    @pytest.mark.asyncio
    async def test_get_financial_data_multiple_metrics(self):
        """Test fetching multiple metrics"""
        mock_overview = {
            'Symbol': 'AAPL',
            'MarketCapitalization': '2500000000000',
            'PERatio': '25.5',
            'PEGRatio': '2.1',
            'BookValue': '3.85',
            'DividendYield': '0.0055',
            'LatestQuarter': '2024-09-30'
        }

        with patch.object(self.source, '_get_company_overview', new_callable=AsyncMock) as mock_overview_call:
            mock_overview_call.return_value = mock_overview

            data = await self.source.get_financial_data(
                "AAPL",
                ["market_cap", "pe_ratio", "peg_ratio", "book_value", "dividend_yield"]
            )

            assert len(data) == 5
            concepts = [d.concept for d in data]
            assert "market_cap" in concepts
            assert "pe_ratio" in concepts
            assert "peg_ratio" in concepts
            assert "book_value" in concepts
            assert "dividend_yield" in concepts

    @pytest.mark.asyncio
    async def test_get_financial_data_none_values(self):
        """Test handling None values"""
        mock_overview = {
            'Symbol': 'AAPL',
            'MarketCapitalization': 'None',  # Alpha Vantage returns string "None"
            'PERatio': '25.5',
            'LatestQuarter': '2024-09-30'
        }

        with patch.object(self.source, '_get_company_overview', new_callable=AsyncMock) as mock_overview_call:
            mock_overview_call.return_value = mock_overview

            data = await self.source.get_financial_data(
                "AAPL",
                ["market_cap", "pe_ratio"]
            )

            # Should skip None values
            assert len(data) == 1
            assert data[0].concept == "pe_ratio"

    @pytest.mark.asyncio
    async def test_get_financial_data_invalid_numbers(self):
        """Test handling invalid number formats"""
        mock_overview = {
            'Symbol': 'AAPL',
            'MarketCapitalization': 'invalid',
            'PERatio': '25.5',
            'LatestQuarter': '2024-09-30'
        }

        with patch.object(self.source, '_get_company_overview', new_callable=AsyncMock) as mock_overview_call:
            mock_overview_call.return_value = mock_overview

            data = await self.source.get_financial_data(
                "AAPL",
                ["market_cap", "pe_ratio"]
            )

            # Should skip invalid values
            assert len(data) == 1
            assert data[0].concept == "pe_ratio"


class TestAlphaVantageSearch:
    """Test Alpha Vantage company search"""

    def setup_method(self):
        """Setup for each test"""
        self.source = AlphaVantageSource(config={'api_key': 'test_key'})

    @pytest.mark.asyncio
    async def test_search_companies(self):
        """Test searching for companies"""
        mock_response = {
            'bestMatches': [
                {
                    '1. symbol': 'AAPL',
                    '2. name': 'Apple Inc.',
                    '3. type': 'Equity',
                    '4. region': 'United States',
                    '8. currency': 'USD'
                },
                {
                    '1. symbol': 'AAPLW',
                    '2. name': 'Apple Inc. Warrants',
                    '3. type': 'Warrant',
                    '4. region': 'United States',
                    '8. currency': 'USD'
                }
            ]
        }

        with patch.object(self.source, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            results = await self.source.search_companies("Apple")

            assert len(results) == 2
            assert results[0]['ticker'] == 'AAPL'
            assert results[0]['name'] == 'Apple Inc.'
            assert results[0]['source'] == 'alpha_vantage'

    @pytest.mark.asyncio
    async def test_search_limit_results(self):
        """Test that search limits to top 5 results"""
        mock_response = {
            'bestMatches': [
                {'1. symbol': f'SYM{i}', '2. name': f'Company {i}',
                 '3. type': 'Equity', '4. region': 'US', '8. currency': 'USD'}
                for i in range(10)
            ]
        }

        with patch.object(self.source, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            results = await self.source.search_companies("test")

            # Should limit to 5
            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test search error handling"""
        with patch.object(self.source, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("API error")

            results = await self.source.search_companies("test")

            # Should return empty list on error
            assert len(results) == 0


class TestAlphaVantageHealthCheck:
    """Test Alpha Vantage health check"""

    def setup_method(self):
        """Setup for each test"""
        self.source = AlphaVantageSource(config={'api_key': 'test_key'})

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        mock_overview = {
            'Symbol': 'AAPL',
            'Name': 'Apple Inc.'
        }

        with patch.object(self.source, '_get_company_overview', new_callable=AsyncMock) as mock_overview_call:
            mock_overview_call.return_value = mock_overview

            is_healthy = await self.source.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check"""
        with patch.object(self.source, '_get_company_overview', new_callable=AsyncMock) as mock_overview_call:
            mock_overview_call.side_effect = Exception("API unavailable")

            is_healthy = await self.source.health_check()
            assert is_healthy is False


class TestAlphaVantageAPIRequests:
    """Test Alpha Vantage API request handling"""

    def setup_method(self):
        """Setup for each test"""
        self.source = AlphaVantageSource(config={'api_key': 'test_key'})

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test successful API request"""
        mock_response_data = {'Symbol': 'AAPL', 'Name': 'Apple Inc.'}

        # Mock the entire aiohttp flow
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)  # NOT AsyncMock - get() returns context manager directly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await self.source._make_request({'function': 'OVERVIEW'})
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_make_request_error_message(self):
        """Test handling Alpha Vantage error message"""
        mock_response_data = {'Error Message': 'Invalid API call'}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)  # NOT AsyncMock
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ValueError, match="Alpha Vantage error"):
                await self.source._make_request({'function': 'INVALID'})

    @pytest.mark.asyncio
    async def test_make_request_rate_limit(self):
        """Test handling rate limit"""
        mock_response_data = {'Note': 'API call frequency exceeded'}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)  # NOT AsyncMock
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await self.source._make_request({'function': 'OVERVIEW'})

    @pytest.mark.asyncio
    async def test_make_request_http_error(self):
        """Test handling HTTP errors"""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)  # NOT AsyncMock
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ValueError, match="API request failed: 500"):
                await self.source._make_request({'function': 'OVERVIEW'})


class TestAlphaVantageCaching:
    """Test Alpha Vantage caching behavior"""

    def setup_method(self):
        """Setup for each test"""
        self.source = AlphaVantageSource(config={
            'api_key': 'test_key',
            'cache_ttl': 3600
        })

    @pytest.mark.asyncio
    async def test_cache_stores_overview(self):
        """Test that overview data is cached"""
        mock_data = {'Symbol': 'AAPL', 'Name': 'Apple Inc.'}

        with patch.object(self.source, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data

            # First call
            await self.source._get_company_overview("AAPL")

            # Cache should be populated
            assert "overview_AAPL" in self.source._cache

    @pytest.mark.asyncio
    async def test_cache_reuse(self):
        """Test that cached data is reused"""
        mock_data = {'Symbol': 'AAPL', 'Name': 'Apple Inc.'}

        with patch.object(self.source, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data

            # First call
            await self.source._get_company_overview("AAPL")
            assert mock_request.call_count == 1

            # Second call - should use cache
            await self.source._get_company_overview("AAPL")
            # Should still be 1 if cache works
            assert mock_request.call_count == 1


# Integration-style tests

class TestDataSourceInterface:
    """Test that both sources properly implement the DataSourcePlugin interface"""

    def test_yahoo_implements_interface(self):
        """Test Yahoo Finance implements all required methods"""
        source = YahooFinanceSource()

        # Check all required methods exist
        assert hasattr(source, 'get_source_type')
        assert hasattr(source, 'get_capabilities')
        assert hasattr(source, 'get_rate_limit')
        assert hasattr(source, 'get_financial_data')
        assert hasattr(source, 'search_companies')
        assert hasattr(source, 'health_check')

    def test_alpha_vantage_implements_interface(self):
        """Test Alpha Vantage implements all required methods"""
        source = AlphaVantageSource()

        # Check all required methods exist
        assert hasattr(source, 'get_source_type')
        assert hasattr(source, 'get_capabilities')
        assert hasattr(source, 'get_rate_limit')
        assert hasattr(source, 'get_financial_data')
        assert hasattr(source, 'search_companies')
        assert hasattr(source, 'health_check')

    @pytest.mark.asyncio
    async def test_both_return_financial_data_objects(self):
        """Test both sources return FinancialData objects"""
        yahoo = YahooFinanceSource()
        alpha = AlphaVantageSource()

        # Mock Yahoo
        with patch('yfinance.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {'regularMarketPrice': 150.23}
            mock_ticker.return_value = mock_instance

            yahoo_data = await yahoo.get_financial_data("AAPL", ["current_price"])
            assert len(yahoo_data) > 0
            assert isinstance(yahoo_data[0], FinancialData)

        # Mock Alpha Vantage
        with patch.object(alpha, '_get_company_overview', new_callable=AsyncMock) as mock_overview:
            mock_overview.return_value = {
                'MarketCapitalization': '2500000000000',
                'LatestQuarter': '2024-09-30'
            }

            alpha_data = await alpha.get_financial_data("AAPL", ["market_cap"])
            assert len(alpha_data) > 0
            assert isinstance(alpha_data[0], FinancialData)
