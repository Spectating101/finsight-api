"""
Rate-Limited SEC API Utilities
Adds FinSight's production-grade rate limiting to FinRobot's SEC utilities
Prevents IP bans from SEC EDGAR (10 requests/second limit)
"""

import asyncio
import time
from typing import Optional
from functools import wraps
import structlog

logger = structlog.get_logger(__name__)


class SECRateLimiter:
    """
    Rate limiter for SEC EDGAR API

    SEC allows 10 requests per second maximum.
    This implementation ensures compliance to prevent IP bans.

    Adapted from FinSight's production SEC EDGAR source.
    """

    def __init__(self, requests_per_second: int = 10):
        """
        Initialize rate limiter

        Args:
            requests_per_second: Maximum requests per second (default 10 for SEC)
        """
        self._requests_per_second = requests_per_second
        self._min_request_interval = 1.0 / requests_per_second
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        """Wait if necessary to comply with rate limit"""
        async with self._lock:
            now = time.time()
            time_since_last = now - self._last_request_time

            if time_since_last < self._min_request_interval:
                wait_time = self._min_request_interval - time_since_last
                logger.debug(
                    "SEC rate limit: waiting",
                    wait_time_ms=int(wait_time * 1000),
                    requests_per_second=self._requests_per_second
                )
                await asyncio.sleep(wait_time)

            self._last_request_time = time.time()

    def wait_sync(self):
        """Synchronous wait for rate limit (for non-async code)"""
        now = time.time()
        time_since_last = now - self._last_request_time

        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            logger.debug(
                "SEC rate limit: waiting (sync)",
                wait_time_ms=int(wait_time * 1000),
                requests_per_second=self._requests_per_second
            )
            time.sleep(wait_time)

        self._last_request_time = time.time()


# Global rate limiter instance
_sec_rate_limiter = SECRateLimiter(requests_per_second=10)


def rate_limited(func):
    """
    Decorator to add rate limiting to async SEC API calls

    Usage:
        @rate_limited
        async def fetch_sec_data(...):
            # Your SEC API call here
            pass
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        await _sec_rate_limiter.wait()
        return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        _sec_rate_limiter.wait_sync()
        return func(*args, **kwargs)

    # Return appropriate wrapper based on whether function is async
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def get_rate_limiter() -> SECRateLimiter:
    """Get the global SEC rate limiter instance"""
    return _sec_rate_limiter


# Example usage with existing sec_utils:
"""
from finrobot.data_source.sec_utils_rate_limited import rate_limited

# Wrap existing SEC API calls with rate limiting:

@rate_limited
def get_10k_metadata_safe(ticker, start_date, end_date):
    from finrobot.data_source.sec_utils import SECUtils
    return SECUtils.get_10k_metadata(ticker, start_date, end_date)

@rate_limited
def download_10k_filing_safe(ticker, start_date, end_date, save_folder):
    from finrobot.data_source.sec_utils import SECUtils
    return SECUtils.download_10k_filing(ticker, start_date, end_date, save_folder)

# Usage:
metadata = get_10k_metadata_safe("AAPL", "2023-01-01", "2023-12-31")
# Rate limiting automatically applied!
"""

# Integration guide for FinRobot codebase:
"""
INTEGRATION STEPS:
==================

1. Import this module in your SEC-related code:
   from finrobot.data_source.sec_utils_rate_limited import rate_limited, SECRateLimiter

2. Wrap SEC API calls with @rate_limited decorator:

   Before:
   response = query_api.get_filings(query)

   After:
   @rate_limited
   async def get_filings_safe(query):
       return query_api.get_filings(query)

   response = await get_filings_safe(query)

3. For batch operations on multiple tickers:

   # Bad (no rate limiting, will get IP banned):
   for ticker in tickers:
       data = SECUtils.get_10k_metadata(ticker, start, end)

   # Good (respects rate limits):
   @rate_limited
   async def get_metadata_safe(ticker, start, end):
       return SECUtils.get_10k_metadata(ticker, start, end)

   for ticker in tickers:
       data = await get_metadata_safe(ticker, start, end)
       # Automatically waits 100ms between requests

4. For existing synchronous code:

   from finrobot.data_source.sec_utils_rate_limited import get_rate_limiter

   rate_limiter = get_rate_limiter()

   for ticker in tickers:
       rate_limiter.wait_sync()  # Wait before each request
       data = SECUtils.get_10k_metadata(ticker, start, end)

BENEFITS:
=========
- Prevents SEC IP bans (SEC enforces 10 req/sec strictly)
- Production-ready rate limiting from FinSight
- Easy to integrate with existing code
- Supports both async and sync patterns
- Automatic backoff and timing
- Logging for debugging

NOTES:
======
- SEC's rate limit is 10 requests per second
- This implementation uses 100ms between requests (10/sec)
- Rate limiting is applied per-process (uses global instance)
- For distributed systems, consider Redis-based rate limiting
"""
