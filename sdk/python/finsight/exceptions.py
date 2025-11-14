"""
FinSight SDK Exceptions
Custom exception classes for error handling
"""


class FinSightError(Exception):
    """Base exception for all FinSight errors"""
    pass


class AuthenticationError(FinSightError):
    """Raised when API key is invalid or missing"""

    def __init__(self, message: str = "Authentication failed. Check your API key"):
        super().__init__(message)


class RateLimitError(FinSightError):
    """Raised when rate limit is exceeded"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message)
        self.retry_after = None  # Can be set by client

    @classmethod
    def with_retry_after(cls, retry_after: int):
        """Create error with retry-after time"""
        error = cls(f"Rate limit exceeded. Retry after {retry_after} seconds")
        error.retry_after = retry_after
        return error


class ValidationError(FinSightError):
    """Raised when request parameters are invalid"""

    def __init__(self, message: str = "Invalid request parameters"):
        super().__init__(message)


class NotFoundError(FinSightError):
    """Raised when requested resource is not found"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class QuotaExceededError(FinSightError):
    """Raised when monthly quota is exceeded"""

    def __init__(self, message: str = "Monthly quota exceeded. Upgrade your plan or wait for reset"):
        super().__init__(message)


class ServerError(FinSightError):
    """Raised when server encounters an error"""

    def __init__(self, message: str = "Server error occurred"):
        super().__init__(message)


class NetworkError(FinSightError):
    """Raised when network request fails"""

    def __init__(self, message: str = "Network request failed"):
        super().__init__(message)
