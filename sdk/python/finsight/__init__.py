"""
FinSight API - Python SDK
Official Python client for FinSight Financial Data API
"""

__version__ = "1.0.0"

from .client import FinSightClient
from .exceptions import (
    FinSightError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError
)

__all__ = [
    "FinSightClient",
    "FinSightError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
]
