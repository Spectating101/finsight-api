"""
Security Middleware for FinSight API
Request validation, size limits, and security headers
"""

import structlog
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
import re

logger = structlog.get_logger(__name__)

# Security constants
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
MAX_QUERY_PARAMS = 50
MAX_HEADER_SIZE = 8192  # 8KB
ALLOWED_CONTENT_TYPES = [
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data"
]


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware
    - Request size limits
    - Security headers
    - Content type validation
    - Query parameter limits
    """

    def __init__(
        self,
        app,
        max_request_size: int = MAX_REQUEST_SIZE,
        max_query_params: int = MAX_QUERY_PARAMS
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.max_query_params = max_query_params

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check request size (headers)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(
                        "Request too large",
                        size=size,
                        limit=self.max_request_size,
                        path=request.url.path
                    )
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "request_too_large",
                            "message": f"Request body too large. Maximum {self.max_request_size} bytes",
                            "max_size": self.max_request_size
                        }
                    )
            except ValueError:
                pass

        # Check query parameter count
        if len(request.query_params) > self.max_query_params:
            logger.warning(
                "Too many query parameters",
                count=len(request.query_params),
                limit=self.max_query_params,
                path=request.url.path
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "too_many_parameters",
                    "message": f"Too many query parameters. Maximum {self.max_query_params}"
                }
            )

        # Validate content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and not any(
                content_type.startswith(allowed) for allowed in ALLOWED_CONTENT_TYPES
            ):
                logger.warning(
                    "Invalid content type",
                    content_type=content_type,
                    path=request.url.path
                )
                raise HTTPException(
                    status_code=415,
                    detail={
                        "error": "unsupported_media_type",
                        "message": f"Content-Type '{content_type}' not supported",
                        "allowed_types": ALLOWED_CONTENT_TYPES
                    }
                )

        # Process request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]

        return response


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP Whitelisting middleware
    Checks allowed_ips from API key if configured
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get API key object from request state (set by auth middleware)
        api_key = getattr(request.state, "api_key", None)

        if api_key and api_key.allowed_ips:
            # Get client IP
            client_ip = request.client.host if request.client else None

            # Check X-Forwarded-For header (for proxies)
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()

            # Check if IP is allowed
            if client_ip and client_ip not in api_key.allowed_ips:
                logger.warning(
                    "IP not whitelisted",
                    client_ip=client_ip,
                    key_id=api_key.key_id,
                    allowed_ips=api_key.allowed_ips
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "ip_not_allowed",
                        "message": "Your IP address is not whitelisted for this API key",
                        "client_ip": client_ip
                    }
                )

        return await call_next(request)


def validate_ticker_symbol(ticker: str) -> str:
    """
    Validate and sanitize ticker symbol

    Args:
        ticker: Stock ticker symbol

    Returns:
        Sanitized ticker (uppercase, alphanumeric only)

    Raises:
        HTTPException: If ticker is invalid
    """
    if not ticker:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_ticker", "message": "Ticker symbol is required"}
        )

    # Remove whitespace and convert to uppercase
    ticker = ticker.strip().upper()

    # Validate format (alphanumeric, 1-5 characters, optional dot for classes)
    if not re.match(r"^[A-Z]{1,5}(?:\.[A-Z]{1,2})?$", ticker):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_ticker",
                "message": f"Invalid ticker symbol: {ticker}. Must be 1-5 uppercase letters, optionally followed by .XX for share class"
            }
        )

    return ticker


def validate_metric_name(metric: str) -> str:
    """
    Validate metric name

    Args:
        metric: Metric name (e.g., "revenue", "net_income")

    Returns:
        Sanitized metric name

    Raises:
        HTTPException: If metric is invalid
    """
    if not metric:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_metric", "message": "Metric name is required"}
        )

    # Lowercase, alphanumeric + underscores only
    metric = metric.strip().lower()

    if not re.match(r"^[a-z][a-z0-9_]{0,63}$", metric):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_metric",
                "message": f"Invalid metric name: {metric}. Must start with a letter, contain only lowercase letters, numbers, and underscores"
            }
        )

    return metric


def validate_date_range(start_date: str = None, end_date: str = None):
    """
    Validate date range parameters

    Args:
        start_date: Start date (YYYY-MM-DD or YYYY-Q1 format)
        end_date: End date (YYYY-MM-DD or YYYY-Q1 format)

    Raises:
        HTTPException: If dates are invalid
    """
    from datetime import datetime

    date_pattern = r"^\d{4}-(?:\d{2}-\d{2}|Q[1-4])$"

    if start_date:
        if not re.match(date_pattern, start_date):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_date",
                    "message": f"Invalid start_date format: {start_date}. Use YYYY-MM-DD or YYYY-Q1"
                }
            )

    if end_date:
        if not re.match(date_pattern, end_date):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_date",
                    "message": f"Invalid end_date format: {end_date}. Use YYYY-MM-DD or YYYY-Q1"
                }
            )

    # Validate chronological order (basic check)
    if start_date and end_date:
        try:
            # Simple year comparison
            start_year = int(start_date[:4])
            end_year = int(end_date[:4])

            if start_year > end_year:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_date_range",
                        "message": "start_date must be before or equal to end_date"
                    }
                )
        except (ValueError, IndexError):
            pass


def sanitize_string_input(value: str, max_length: int = 255, field_name: str = "input") -> str:
    """
    Sanitize string input

    Args:
        value: Input string
        max_length: Maximum allowed length
        field_name: Field name for error messages

    Returns:
        Sanitized string

    Raises:
        HTTPException: If input is invalid
    """
    if not value:
        return ""

    # Strip whitespace
    value = value.strip()

    # Check length
    if len(value) > max_length:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "input_too_long",
                "message": f"{field_name} exceeds maximum length of {max_length} characters"
            }
        )

    # Remove control characters
    value = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)

    return value


def validate_email(email: str) -> str:
    """
    Validate email address format

    Args:
        email: Email address

    Returns:
        Lowercase email

    Raises:
        HTTPException: If email is invalid
    """
    email = email.strip().lower()

    # Basic email regex (RFC 5322 simplified)
    pattern = r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"

    if not re.match(pattern, email):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_email", "message": f"Invalid email address: {email}"}
        )

    if len(email) > 254:  # RFC 5321
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_email", "message": "Email address too long"}
        )

    return email
