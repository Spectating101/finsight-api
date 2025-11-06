"""
FinSight API Exceptions
"""


class FinSightError(Exception):
    """Base exception for FinSight API errors"""

    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(FinSightError):
    """Raised when API key is invalid or missing"""
    pass


class RateLimitError(FinSightError):
    """Raised when rate limit is exceeded"""

    def __init__(self, message, status_code=None, response=None, reset_at=None):
        super().__init__(message, status_code, response)
        self.reset_at = reset_at


class NotFoundError(FinSightError):
    """Raised when resource is not found (e.g. ticker doesn't exist)"""
    pass


class ValidationError(FinSightError):
    """Raised when request validation fails"""
    pass


class ServerError(FinSightError):
    """Raised when server returns 5xx error"""
    pass
