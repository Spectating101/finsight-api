"""
Redis Caching Layer for FinSight API
Caches expensive operations like SEC data fetches
"""

import json
import hashlib
import structlog
from typing import Any, Optional, Callable
from datetime import timedelta
from functools import wraps
import redis.asyncio as redis

logger = structlog.get_logger(__name__)


class RedisCache:
    """Redis-based caching with automatic serialization"""

    def __init__(self, redis_client: redis.Redis, prefix: str = "finsight"):
        self.redis = redis_client
        self.prefix = prefix

    def _make_key(self, *parts) -> str:
        """
        Create cache key from parts

        Args:
            *parts: Key components

        Returns:
            Formatted cache key
        """
        key_parts = [str(part) for part in parts]
        return f"{self.prefix}:{':'.join(key_parts)}"

    def _make_hash_key(self, data: dict) -> str:
        """
        Create hash-based cache key from dict

        Args:
            data: Data to hash

        Returns:
            Hash-based cache key
        """
        # Sort dict for consistent hashing
        sorted_data = json.dumps(data, sort_keys=True)
        hash_value = hashlib.sha256(sorted_data.encode()).hexdigest()[:16]
        return f"{self.prefix}:hash:{hash_value}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value)
            await self.redis.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern

        Args:
            pattern: Key pattern (e.g., "finsight:metrics:*")

        Returns:
            Number of keys deleted
        """
        try:
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )

                if keys:
                    deleted += await self.redis.delete(*keys)

                if cursor == 0:
                    break

            logger.info("Cache invalidated", pattern=pattern, deleted=deleted)
            return deleted

        except Exception as e:
            logger.error("Cache invalidation failed", pattern=pattern, error=str(e))
            return 0

    async def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.warning("Cache TTL check failed", key=key, error=str(e))
            return -2


def cached(
    ttl: int = 3600,
    key_prefix: str = "cache",
    cache_instance: Optional[RedisCache] = None
):
    """
    Decorator to cache function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        cache_instance: RedisCache instance to use

    Example:
        @cached(ttl=1800, key_prefix="metrics")
        async def get_financial_data(ticker: str, metric: str):
            # ... expensive operation ...
            return data
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip caching if no cache instance
            if not cache_instance:
                return await func(*args, **kwargs)

            # Create cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]

            # Add positional args
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))

            # Add keyword args
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    key_parts.append(f"{k}={v}")

            cache_key = cache_instance._make_key(*key_parts)

            # Try to get from cache
            cached_value = await cache_instance.get(cache_key)
            if cached_value is not None:
                logger.debug("Cache hit", key=cache_key, function=func.__name__)
                return cached_value

            # Execute function
            logger.debug("Cache miss", key=cache_key, function=func.__name__)
            result = await func(*args, **kwargs)

            # Store in cache
            await cache_instance.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator


# Cache TTL constants
TTL_1_MINUTE = 60
TTL_5_MINUTES = 300
TTL_15_MINUTES = 900
TTL_30_MINUTES = 1800
TTL_1_HOUR = 3600
TTL_6_HOURS = 21600
TTL_12_HOURS = 43200
TTL_24_HOURS = 86400
TTL_1_WEEK = 604800


class CacheKeys:
    """Standard cache key prefixes"""

    # Financial data (changes quarterly)
    FINANCIAL_METRICS = "metrics"
    COMPANY_INFO = "company"
    SEC_FILINGS = "sec"

    # User data (changes frequently)
    USER_PROFILE = "user"
    API_KEY = "apikey"

    # Static data (rarely changes)
    TICKER_CIK_MAP = "ticker_cik"
    AVAILABLE_METRICS = "available_metrics"

    @staticmethod
    def financial_data(ticker: str, metric: str, period: str = None) -> str:
        """Generate key for financial data"""
        parts = ["metrics", ticker.upper(), metric]
        if period:
            parts.append(period)
        return ":".join(parts)

    @staticmethod
    def company_info(ticker: str) -> str:
        """Generate key for company info"""
        return f"company:{ticker.upper()}"

    @staticmethod
    def ticker_to_cik(ticker: str) -> str:
        """Generate key for ticker-to-CIK mapping"""
        return f"ticker_cik:{ticker.upper()}"
