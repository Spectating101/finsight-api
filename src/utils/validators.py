"""
Input Validation and Sanitization Utilities
Production-grade validation to prevent injection attacks and data corruption
"""

import re
from typing import Optional
from pydantic import validator, Field, HttpUrl
from pydantic import BaseModel as PydanticBaseModel


class ValidationRules:
    """Centralized validation rules"""

    # String length limits
    MAX_COMPANY_NAME_LENGTH = 255
    MAX_API_KEY_NAME_LENGTH = 100
    MAX_WEBSITE_LENGTH = 255
    MAX_TICKER_LENGTH = 10
    MIN_TICKER_LENGTH = 1
    MAX_CONCEPT_LENGTH = 50

    # Regex patterns
    TICKER_PATTERN = re.compile(r'^[A-Z0-9\.\-]{1,10}$')
    SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-\_\.\,\&\(\)]+$')
    API_KEY_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-\_\.]{1,100}$')

    # Dangerous patterns to detect
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)',
        r'(--|\/\*|\*\/|;)',
        r'(\bOR\b.*=.*)',
        r'(\bAND\b.*=.*)',
        r'(\'|\"|`)',
    ]

    XSS_PATTERNS = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
    ]

    @classmethod
    def is_safe_string(cls, value: str) -> bool:
        """Check if string contains only safe characters"""
        if not value:
            return True
        return bool(cls.SAFE_STRING_PATTERN.match(value))

    @classmethod
    def has_sql_injection(cls, value: str) -> bool:
        """Detect potential SQL injection attempts"""
        if not value:
            return False
        value_upper = value.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False

    @classmethod
    def has_xss_attempt(cls, value: str) -> bool:
        """Detect potential XSS attempts"""
        if not value:
            return False
        value_lower = value.lower()
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False

    @classmethod
    def sanitize_string(cls, value: str, max_length: int) -> str:
        """Sanitize and trim string"""
        if not value:
            return value

        # Remove leading/trailing whitespace
        value = value.strip()

        # Enforce length limit
        if len(value) > max_length:
            value = value[:max_length]

        return value


def validate_company_name(value: Optional[str]) -> Optional[str]:
    """Validate company name"""
    if not value:
        return value

    # Sanitize
    value = ValidationRules.sanitize_string(value, ValidationRules.MAX_COMPANY_NAME_LENGTH)

    # Check length
    if len(value) > ValidationRules.MAX_COMPANY_NAME_LENGTH:
        raise ValueError(f"Company name too long (max {ValidationRules.MAX_COMPANY_NAME_LENGTH} chars)")

    # Check for injection attempts
    if ValidationRules.has_sql_injection(value):
        raise ValueError("Company name contains invalid characters")

    if ValidationRules.has_xss_attempt(value):
        raise ValueError("Company name contains invalid characters")

    return value


def validate_api_key_name(value: str) -> str:
    """Validate API key name"""
    if not value:
        raise ValueError("API key name is required")

    # Sanitize
    value = ValidationRules.sanitize_string(value, ValidationRules.MAX_API_KEY_NAME_LENGTH)

    # Check length
    if len(value) > ValidationRules.MAX_API_KEY_NAME_LENGTH:
        raise ValueError(f"API key name too long (max {ValidationRules.MAX_API_KEY_NAME_LENGTH} chars)")

    # Check pattern
    if not ValidationRules.API_KEY_NAME_PATTERN.match(value):
        raise ValueError("API key name contains invalid characters (use only letters, numbers, spaces, hyphens, underscores, dots)")

    return value


def validate_ticker(value: str) -> str:
    """Validate stock ticker symbol"""
    if not value:
        raise ValueError("Ticker is required")

    # Convert to uppercase
    value = value.upper().strip()

    # Check length
    if len(value) < ValidationRules.MIN_TICKER_LENGTH:
        raise ValueError(f"Ticker too short (min {ValidationRules.MIN_TICKER_LENGTH} char)")

    if len(value) > ValidationRules.MAX_TICKER_LENGTH:
        raise ValueError(f"Ticker too long (max {ValidationRules.MAX_TICKER_LENGTH} chars)")

    # Check pattern (letters, numbers, dots, hyphens only)
    if not ValidationRules.TICKER_PATTERN.match(value):
        raise ValueError("Ticker contains invalid characters (use only letters, numbers, dots, hyphens)")

    return value


def validate_concept(value: str) -> str:
    """Validate financial concept/metric name"""
    if not value:
        raise ValueError("Concept is required")

    # Sanitize
    value = value.strip().lower()

    # Check length
    if len(value) > ValidationRules.MAX_CONCEPT_LENGTH:
        raise ValueError(f"Concept name too long (max {ValidationRules.MAX_CONCEPT_LENGTH} chars)")

    # Only allow alphanumeric and underscores (snake_case)
    if not re.match(r'^[a-z0-9_]+$', value):
        raise ValueError("Concept name must be alphanumeric with underscores only")

    return value


def validate_website_url(value: Optional[str]) -> Optional[str]:
    """Validate website URL"""
    if not value:
        return value

    # Trim and check length
    value = value.strip()

    if len(value) > ValidationRules.MAX_WEBSITE_LENGTH:
        raise ValueError(f"Website URL too long (max {ValidationRules.MAX_WEBSITE_LENGTH} chars)")

    # Check for XSS
    if ValidationRules.has_xss_attempt(value):
        raise ValueError("Website URL contains invalid characters")

    # Basic URL validation (Pydantic HttpUrl is too strict for some cases)
    if not value.startswith(('http://', 'https://')):
        value = f"https://{value}"

    return value


class ValidatedBaseModel(PydanticBaseModel):
    """Base model with common validation"""

    class Config:
        str_strip_whitespace = True  # Auto-strip whitespace
        min_anystr_length = 0  # Allow empty strings where Optional
        max_anystr_length = 10000  # Global max to prevent DoS
        validate_assignment = True  # Validate on assignment
