#!/usr/bin/env python3
"""
Production Environment Validation Script
Checks that all required configuration and services are ready
"""

import os
import sys
import asyncio
import asyncpg
import redis.asyncio as redis
from typing import List, Tuple
import stripe
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class ValidationResult:
    def __init__(self):
        self.checks: List[Tuple[str, bool, str]] = []
        self.warnings: List[str] = []

    def add_check(self, name: str, passed: bool, message: str = ""):
        self.checks.append((name, passed, message))

    def add_warning(self, message: str):
        self.warnings.append(message)

    def print_summary(self):
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}Production Validation Summary{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        passed = sum(1 for _, p, _ in self.checks if p)
        failed = len(self.checks) - passed

        for name, passed_check, message in self.checks:
            status = f"{GREEN}✓ PASS{RESET}" if passed_check else f"{RED}✗ FAIL{RESET}"
            print(f"{status} | {name}")
            if message:
                print(f"       {message}")

        if self.warnings:
            print(f"\n{YELLOW}Warnings:{RESET}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"Total: {passed} passed, {failed} failed")

        if failed == 0:
            print(f"{GREEN}✓ All checks passed! Ready for production.{RESET}")
            return 0
        else:
            print(f"{RED}✗ Some checks failed. Fix issues before deploying.{RESET}")
            return 1


async def check_database_connection(result: ValidationResult):
    """Check PostgreSQL database connection"""
    try:
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            result.add_check("Database URL", False, "DATABASE_URL not set")
            return

        # Try to connect
        conn = await asyncpg.connect(database_url, timeout=5)

        # Check database version
        version = await conn.fetchval("SELECT version()")

        # Check if tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)

        table_names = [t["tablename"] for t in tables]
        required_tables = ["users", "api_keys", "usage_records", "subscription_history"]
        missing_tables = [t for t in required_tables if t not in table_names]

        await conn.close()

        if missing_tables:
            result.add_check(
                "Database Schema",
                False,
                f"Missing tables: {', '.join(missing_tables)}"
            )
        else:
            result.add_check("Database Connection", True, f"PostgreSQL connected, {len(table_names)} tables found")

    except Exception as e:
        result.add_check("Database Connection", False, f"Error: {str(e)}")


async def check_redis_connection(result: ValidationResult):
    """Check Redis connection"""
    try:
        redis_url = os.getenv("REDIS_URL")

        if not redis_url:
            result.add_check("Redis URL", False, "REDIS_URL not set")
            return

        # Try to connect
        client = await redis.from_url(
            redis_url,
            decode_responses=True,
            ssl_cert_reqs="none",
            socket_timeout=5
        )

        # Test ping
        await client.ping()

        # Get info
        info = await client.info("server")

        await client.close()

        result.add_check(
            "Redis Connection",
            True,
            f"Redis {info.get('redis_version', 'unknown')} connected"
        )

    except Exception as e:
        result.add_check("Redis Connection", False, f"Error: {str(e)}")


def check_stripe_configuration(result: ValidationResult):
    """Check Stripe API configuration"""
    try:
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        if not stripe_key:
            result.add_check("Stripe Secret Key", False, "STRIPE_SECRET_KEY not set")
            return

        if not webhook_secret:
            result.add_warning("STRIPE_WEBHOOK_SECRET not set (webhooks won't work)")

        # Check if it's a test key in production
        environment = os.getenv("ENVIRONMENT", "production")
        if environment == "production" and stripe_key.startswith("sk_test_"):
            result.add_warning("Using Stripe TEST key in PRODUCTION environment!")

        # Try to make an API call
        stripe.api_key = stripe_key
        account = stripe.Account.retrieve()

        result.add_check(
            "Stripe Configuration",
            True,
            f"Connected to Stripe account: {account.get('business_profile', {}).get('name', account.id)}"
        )

        # Check if price IDs are configured
        from src.models.user import STRIPE_PRICE_IDS
        placeholder_prices = [
            price_id for price_id in STRIPE_PRICE_IDS.values()
            if "xxx" in price_id
        ]

        if placeholder_prices:
            result.add_warning(
                f"Stripe price IDs contain placeholders: {len(placeholder_prices)} need configuration"
            )

    except Exception as e:
        result.add_check("Stripe Configuration", False, f"Error: {str(e)}")


def check_environment_variables(result: ValidationResult):
    """Check required environment variables"""
    required_vars = {
        "DATABASE_URL": "PostgreSQL database connection string",
        "REDIS_URL": "Redis connection string",
        "STRIPE_SECRET_KEY": "Stripe API secret key",
        "SEC_USER_AGENT": "SEC EDGAR API user agent",
    }

    optional_vars = {
        "SENTRY_DSN": "Error tracking with Sentry",
        "GROQ_API_KEY": "AI synthesis with Groq",
        "ALPHA_VANTAGE_API_KEY": "Real-time market data",
        "STRIPE_WEBHOOK_SECRET": "Stripe webhook verification",
    }

    missing_required = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_required.append(f"{var} ({description})")

    if missing_required:
        result.add_check(
            "Required Environment Variables",
            False,
            f"Missing: {', '.join(missing_required)}"
        )
    else:
        result.add_check(
            "Required Environment Variables",
            True,
            f"All {len(required_vars)} required variables set"
        )

    # Check optional vars
    missing_optional = [
        var for var in optional_vars.keys()
        if not os.getenv(var)
    ]

    if missing_optional:
        result.add_warning(
            f"Optional variables not set: {', '.join(missing_optional)}"
        )


def check_security_configuration(result: ValidationResult):
    """Check security settings"""
    environment = os.getenv("ENVIRONMENT", "production")
    debug = os.getenv("DEBUG", "false").lower()

    # Check if DEBUG is disabled in production
    if environment == "production" and debug == "true":
        result.add_check(
            "Debug Mode",
            False,
            "DEBUG=true in production environment!"
        )
    else:
        result.add_check("Debug Mode", True, f"DEBUG={debug} for {environment}")

    # Check ALLOWED_ORIGINS
    origins = os.getenv("ALLOWED_ORIGINS", "*")
    if origins == "*" and environment == "production":
        result.add_warning("ALLOWED_ORIGINS=* (allows all origins, not recommended for production)")

    # Check if JWT secret is set
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        result.add_warning("JWT_SECRET_KEY not set")
    elif jwt_secret == "generate_random_secret_here":
        result.add_check("JWT Secret", False, "Using default JWT_SECRET_KEY (INSECURE!)")
    else:
        result.add_check("JWT Secret", True, "Custom JWT_SECRET_KEY configured")


def check_monitoring_configuration(result: ValidationResult):
    """Check monitoring and logging setup"""
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        result.add_warning("Sentry not configured (no error tracking)")
    else:
        result.add_check("Sentry Configuration", True, "Sentry DSN configured")

    log_level = os.getenv("LOG_LEVEL", "INFO")
    result.add_check("Log Level", True, f"LOG_LEVEL={log_level}")


def check_data_sources(result: ValidationResult):
    """Check data source configuration"""
    sec_agent = os.getenv("SEC_USER_AGENT")

    if not sec_agent or "contact@" not in sec_agent:
        result.add_check(
            "SEC User Agent",
            False,
            "SEC_USER_AGENT must include valid contact email (required by SEC)"
        )
    else:
        result.add_check("SEC User Agent", True, f"Configured: {sec_agent}")

    # Check optional data sources
    optional_sources = {
        "ALPHA_VANTAGE_API_KEY": "Alpha Vantage",
        "GROQ_API_KEY": "Groq AI",
    }

    configured_sources = [
        name for key, name in optional_sources.items()
        if os.getenv(key)
    ]

    if configured_sources:
        result.add_check(
            "Optional Data Sources",
            True,
            f"Configured: {', '.join(configured_sources)}"
        )


async def main():
    """Run all validation checks"""
    print(f"{BLUE}Starting production environment validation...{RESET}\n")

    result = ValidationResult()

    # Run checks
    print("Checking environment variables...")
    check_environment_variables(result)

    print("Checking security configuration...")
    check_security_configuration(result)

    print("Checking database connection...")
    await check_database_connection(result)

    print("Checking Redis connection...")
    await check_redis_connection(result)

    print("Checking Stripe configuration...")
    check_stripe_configuration(result)

    print("Checking data sources...")
    check_data_sources(result)

    print("Checking monitoring configuration...")
    check_monitoring_configuration(result)

    # Print summary
    result.print_summary()

    return result.checks


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Validation cancelled{RESET}")
        sys.exit(1)
