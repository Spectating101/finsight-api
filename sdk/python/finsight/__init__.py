"""
FinSight Python SDK
Official Python client for the FinSight Financial Data API

Installation:
    pip install finsight

Usage:
    from finsight import FinSightClient

    client = FinSightClient(api_key="your_api_key_here")

    # Get financial metrics
    metrics = client.get_metrics("AAPL", ["revenue", "net_income"])

    # Search companies
    companies = client.search_companies("tesla")

    # Get company details
    company = client.get_company("TSLA")
"""

from .client import FinSightClient, AsyncFinSightClient
from .exceptions import (
    FinSightError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError
)
from .models import Metric, Company, Citation

__version__ = "1.0.0"
__all__ = [
    "FinSightClient",
    "AsyncFinSightClient",
    "FinSightError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "NotFoundError",
    "Metric",
    "Company",
    "Citation"
]
