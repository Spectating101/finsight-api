"""
Unit tests for SEC EDGAR data source
Tests financial data retrieval, parsing, and citation generation
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from src.data_sources.sec_edgar import SECEdgarSource


class TestSECEdgarInitialization:
    """Test SEC EDGAR data source initialization"""

    def test_initialize_with_defaults(self):
        """Test initializing with default configuration"""
        source = SECEdgarSource()

        assert source.name == "SEC EDGAR"
        assert source.base_url == "https://www.sec.gov"
        assert source.cache_enabled is True

    def test_initialize_with_custom_config(self):
        """Test initializing with custom configuration"""
        source = SECEdgarSource(
            cache_ttl=7200,
            rate_limit_delay=0.5
        )

        assert source.cache_ttl == 7200
        assert source.rate_limit_delay == 0.5


class TestCompanyIdentification:
    """Test company CIK lookup and identification"""

    @pytest.mark.asyncio
    async def test_get_cik_by_ticker(self):
        """Test getting CIK number from ticker"""
        source = SECEdgarSource()

        with patch.object(source, '_fetch_cik_mapping') as mock_fetch:
            mock_fetch.return_value = {"AAPL": "0000320193"}

            cik = await source.get_cik("AAPL")

            assert cik == "0000320193"

    @pytest.mark.asyncio
    async def test_get_cik_invalid_ticker(self):
        """Test getting CIK for invalid ticker"""
        source = SECEdgarSource()

        with patch.object(source, '_fetch_cik_mapping') as mock_fetch:
            mock_fetch.return_value = {}

            with pytest.raises(ValueError, match="Ticker not found"):
                await source.get_cik("INVALID")

    @pytest.mark.asyncio
    async def test_cik_caching(self):
        """Test that CIK lookups are cached"""
        source = SECEdgarSource()

        with patch.object(source, '_fetch_cik_mapping') as mock_fetch:
            mock_fetch.return_value = {"AAPL": "0000320193"}

            # First call
            cik1 = await source.get_cik("AAPL")

            # Second call should use cache
            cik2 = await source.get_cik("AAPL")

            # Should only fetch once
            assert mock_fetch.call_count == 1
            assert cik1 == cik2


class TestFinancialDataRetrieval:
    """Test retrieving financial data from filings"""

    @pytest.mark.asyncio
    async def test_get_revenue(self):
        """Test retrieving revenue metric"""
        source = SECEdgarSource()

        mock_filing_data = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"val": 394328000000, "end": "2022-09-30", "form": "10-K"}
                            ]
                        }
                    }
                }
            }
        }

        with patch.object(source, '_fetch_company_facts') as mock_fetch:
            mock_fetch.return_value = mock_filing_data

            revenue = await source.get_metric("AAPL", "revenue")

            assert revenue["value"] == 394328000000
            assert revenue["date"] == "2022-09-30"
            assert revenue["form"] == "10-K"
            assert revenue["unit"] == "USD"

    @pytest.mark.asyncio
    async def test_get_net_income(self):
        """Test retrieving net income metric"""
        source = SECEdgarSource()

        mock_filing_data = {
            "facts": {
                "us-gaap": {
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"val": 99803000000, "end": "2022-09-30", "form": "10-K"}
                            ]
                        }
                    }
                }
            }
        }

        with patch.object(source, '_fetch_company_facts') as mock_fetch:
            mock_fetch.return_value = mock_filing_data

            net_income = await source.get_metric("AAPL", "net_income")

            assert net_income["value"] == 99803000000
            assert net_income["form"] == "10-K"

    @pytest.mark.asyncio
    async def test_get_multiple_metrics(self):
        """Test retrieving multiple metrics at once"""
        source = SECEdgarSource()

        metrics = ["revenue", "net_income", "total_assets"]

        with patch.object(source, 'get_metric') as mock_get:
            mock_get.side_effect = [
                {"value": 394328000000, "date": "2022-09-30"},
                {"value": 99803000000, "date": "2022-09-30"},
                {"value": 352755000000, "date": "2022-09-30"}
            ]

            results = await source.get_metrics("AAPL", metrics)

            assert len(results) == 3
            assert results["revenue"]["value"] == 394328000000
            assert results["net_income"]["value"] == 99803000000
            assert results["total_assets"]["value"] == 352755000000

    @pytest.mark.asyncio
    async def test_metric_not_found(self):
        """Test handling when metric is not available"""
        source = SECEdgarSource()

        mock_filing_data = {"facts": {"us-gaap": {}}}

        with patch.object(source, '_fetch_company_facts') as mock_fetch:
            mock_fetch.return_value = mock_filing_data

            with pytest.raises(KeyError, match="Metric not found"):
                await source.get_metric("AAPL", "nonexistent_metric")


class TestCitationGeneration:
    """Test generating proper citations for data"""

    def test_generate_filing_citation(self):
        """Test generating citation for a filing"""
        source = SECEdgarSource()

        citation = source.generate_citation(
            ticker="AAPL",
            form="10-K",
            filing_date="2022-09-30",
            metric_name="revenue"
        )

        assert "AAPL" in citation
        assert "10-K" in citation
        assert "2022-09-30" in citation
        assert "https://www.sec.gov" in citation

    def test_citation_includes_direct_link(self):
        """Test that citation includes direct link to filing"""
        source = SECEdgarSource()

        citation = source.generate_citation(
            ticker="AAPL",
            form="10-K",
            filing_date="2022-09-30",
            accession_number="0000320193-22-000108"
        )

        # Should include accession number in URL
        assert "0000320193-22-000108" in citation

    def test_citation_format_consistent(self):
        """Test that citation format is consistent"""
        source = SECEdgarSource()

        citation1 = source.generate_citation("AAPL", "10-K", "2022-09-30")
        citation2 = source.generate_citation("MSFT", "10-Q", "2023-03-31")

        # Both should follow same pattern
        assert citation1.startswith("Source:")
        assert citation2.startswith("Source:")


class TestDataParsing:
    """Test parsing of SEC filing data"""

    def test_parse_xbrl_data(self):
        """Test parsing XBRL formatted data"""
        source = SECEdgarSource()

        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "label": "Total Assets",
                        "units": {
                            "USD": [
                                {"val": 352755000000, "end": "2022-09-30", "form": "10-K"},
                                {"val": 351002000000, "end": "2022-06-30", "form": "10-Q"}
                            ]
                        }
                    }
                }
            }
        }

        parsed = source.parse_xbrl(xbrl_data, metric_name="Assets")

        # Should return most recent value
        assert parsed["value"] == 352755000000
        assert parsed["date"] == "2022-09-30"

    def test_parse_multiple_time_periods(self):
        """Test parsing data across multiple time periods"""
        source = SECEdgarSource()

        xbrl_data = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"val": 394328000000, "end": "2022-09-30", "form": "10-K"},
                                {"val": 365817000000, "end": "2021-09-30", "form": "10-K"},
                                {"val": 274515000000, "end": "2020-09-30", "form": "10-K"}
                            ]
                        }
                    }
                }
            }
        }

        time_series = source.parse_time_series(xbrl_data, metric_name="Revenues", periods=3)

        assert len(time_series) == 3
        assert time_series[0]["value"] == 394328000000  # Most recent
        assert time_series[2]["value"] == 274515000000  # Oldest

    def test_handle_missing_data(self):
        """Test handling missing or incomplete data"""
        source = SECEdgarSource()

        incomplete_data = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            # Missing USD unit
                        }
                    }
                }
            }
        }

        with pytest.raises(ValueError, match="No data available"):
            source.parse_xbrl(incomplete_data, metric_name="Revenues")


class TestRateLimiting:
    """Test SEC API rate limiting compliance"""

    @pytest.mark.asyncio
    async def test_respects_rate_limit(self):
        """Test that requests respect SEC rate limits (10 req/sec)"""
        source = SECEdgarSource(rate_limit_delay=0.1)

        start_time = datetime.now()

        # Make 5 requests
        with patch.object(source, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"facts": {}}

            for _ in range(5):
                await source.get_metric("AAPL", "revenue")

        elapsed = (datetime.now() - start_time).total_seconds()

        # Should take at least 0.4 seconds (4 delays of 0.1s each)
        assert elapsed >= 0.4

    @pytest.mark.asyncio
    async def test_user_agent_header(self):
        """Test that SEC-required User-Agent header is set"""
        source = SECEdgarSource(user_agent="MyApp admin@example.com")

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value={})

            await source._make_request("https://www.sec.gov/test")

            # Verify User-Agent header was set
            call_args = mock_get.call_args
            assert "User-Agent" in call_args[1]["headers"]


class TestCaching:
    """Test caching of SEC data"""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test that cached data is returned on subsequent requests"""
        source = SECEdgarSource(cache_enabled=True)

        with patch.object(source, '_fetch_company_facts') as mock_fetch:
            mock_fetch.return_value = {"facts": {"test": "data"}}

            # First request
            await source.get_metric("AAPL", "revenue")

            # Second request should use cache
            await source.get_metric("AAPL", "revenue")

            # Should only fetch once
            assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that cache expires after TTL"""
        source = SECEdgarSource(cache_enabled=True, cache_ttl=1)

        with patch.object(source, '_fetch_company_facts') as mock_fetch:
            mock_fetch.return_value = {"facts": {"test": "data"}}

            # First request
            await source.get_metric("AAPL", "revenue")

            # Wait for cache to expire
            import asyncio
            await asyncio.sleep(1.5)

            # Second request should fetch again
            await source.get_metric("AAPL", "revenue")

            # Should fetch twice
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test that caching can be disabled"""
        source = SECEdgarSource(cache_enabled=False)

        with patch.object(source, '_fetch_company_facts') as mock_fetch:
            mock_fetch.return_value = {"facts": {"test": "data"}}

            # Multiple requests
            await source.get_metric("AAPL", "revenue")
            await source.get_metric("AAPL", "revenue")

            # Should fetch every time
            assert mock_fetch.call_count == 2


class TestErrorHandling:
    """Test error handling and retries"""

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self):
        """Test that network errors trigger retries"""
        source = SECEdgarSource(max_retries=3)

        with patch.object(source, '_make_request') as mock_request:
            # Fail twice, then succeed
            mock_request.side_effect = [
                Exception("Network error"),
                Exception("Network error"),
                {"facts": {"test": "data"}}
            ]

            result = await source.get_metric("AAPL", "revenue")

            # Should have retried and eventually succeeded
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries is respected"""
        source = SECEdgarSource(max_retries=2)

        with patch.object(source, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                await source.get_metric("AAPL", "revenue")

            # Should have tried 3 times (initial + 2 retries)
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_handle_404_gracefully(self):
        """Test handling 404 responses"""
        source = SECEdgarSource()

        with patch.object(source, '_make_request') as mock_request:
            mock_request.side_effect = Exception("404 Not Found")

            with pytest.raises(ValueError, match="Company or metric not found"):
                await source.get_metric("INVALID", "revenue")


# Note: Adjust tests based on actual SECEdgarSource implementation
# Some methods may need to be implemented or renamed
