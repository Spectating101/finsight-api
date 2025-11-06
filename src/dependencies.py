"""
Shared dependencies and utilities for API endpoints
"""

import redis.asyncio as redis
from typing import Optional

# Global references (set by main.py at startup)
_redis_client: Optional[redis.Redis] = None


def set_redis_client(client: redis.Redis):
    """Set the global Redis client reference"""
    global _redis_client
    _redis_client = client


def get_redis_client() -> Optional[redis.Redis]:
    """Get the global Redis client"""
    return _redis_client
