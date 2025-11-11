"""
Sentry Configuration for FinSight API
Error tracking and performance monitoring
"""

import os
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = structlog.get_logger(__name__)


def init_sentry(environment: str = "production"):
    """
    Initialize Sentry error tracking

    Args:
        environment: Environment name (production, staging, development)
    """
    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        logger.warning("SENTRY_DSN not configured, skipping Sentry initialization")
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,

            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="url"),
                StarletteIntegration(transaction_style="url"),
                AsyncPGIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=None,  # Capture all logs
                    event_level="ERROR"  # Send errors to Sentry
                ),
            ],

            # Performance monitoring
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),  # 10% of transactions

            # Error sampling
            sample_rate=1.0,  # 100% of errors

            # Release tracking
            release=os.getenv("GIT_COMMIT", "unknown"),

            # Additional options
            max_breadcrumbs=50,
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send PII by default

            # Before send hook to filter sensitive data
            before_send=before_send_filter,

            # Performance profiles sampling
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        )

        logger.info(
            "Sentry initialized",
            environment=environment,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1
        )

    except Exception as e:
        logger.error("Failed to initialize Sentry", error=str(e))


def before_send_filter(event, hint):
    """
    Filter sensitive data before sending to Sentry

    Args:
        event: Sentry event dict
        hint: Additional context

    Returns:
        Modified event or None to drop the event
    """
    # Remove API keys from request data
    if "request" in event:
        if "headers" in event["request"]:
            headers = event["request"]["headers"]

            # Redact sensitive headers
            sensitive_headers = [
                "x-api-key",
                "authorization",
                "stripe-signature",
                "cookie",
                "set-cookie"
            ]

            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[REDACTED]"

        # Redact query parameters with sensitive names
        if "query_string" in event["request"]:
            query = event["request"]["query_string"]
            if query and ("api_key" in query or "token" in query):
                event["request"]["query_string"] = "[REDACTED]"

    # Remove sensitive data from breadcrumbs
    if "breadcrumbs" in event:
        for breadcrumb in event["breadcrumbs"]:
            if "message" in breadcrumb:
                # Redact anything that looks like an API key
                message = breadcrumb["message"]
                if "fsk_" in message:
                    breadcrumb["message"] = message.replace(
                        message[message.find("fsk_"):message.find("fsk_") + 36],
                        "[API_KEY_REDACTED]"
                    )

    return event


def set_user_context(user_id: str, tier: str, email: str = None):
    """
    Set user context for Sentry events

    Args:
        user_id: User ID
        tier: Pricing tier
        email: User email (optional, will be redacted if PII protection is on)
    """
    sentry_sdk.set_user({
        "id": user_id,
        "tier": tier,
        # Don't send email by default (PII)
    })


def set_request_context(endpoint: str, method: str, user_id: str = None):
    """
    Set request context for Sentry events

    Args:
        endpoint: API endpoint
        method: HTTP method
        user_id: User ID if authenticated
    """
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", endpoint)
        scope.set_tag("method", method)
        if user_id:
            scope.set_tag("user_id", user_id)


def capture_exception_with_context(
    exception: Exception,
    user_id: str = None,
    tier: str = None,
    endpoint: str = None,
    extra_context: dict = None
):
    """
    Capture exception with additional context

    Args:
        exception: Exception to capture
        user_id: User ID
        tier: Pricing tier
        endpoint: API endpoint
        extra_context: Additional context dict
    """
    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_tag("user_id", user_id)
        if tier:
            scope.set_tag("tier", tier)
        if endpoint:
            scope.set_tag("endpoint", endpoint)
        if extra_context:
            scope.set_context("extra", extra_context)

        sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: str = "info", **kwargs):
    """
    Capture a message in Sentry

    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in kwargs.items():
            scope.set_tag(key, str(value))

        sentry_sdk.capture_message(message, level=level)


def track_transaction(name: str, op: str = "function"):
    """
    Context manager to track a transaction

    Args:
        name: Transaction name
        op: Operation type

    Example:
        with track_transaction("fetch_sec_data", "api.call"):
            # ... code ...
    """
    return sentry_sdk.start_transaction(name=name, op=op)
