"""
Core scraping exception classes and error classifications.

This module defines the exception hierarchy for scraping operations,
including different error types and severity levels.
"""

from enum import Enum
from typing import Optional

try:
    from curl_cffi.requests import RequestsError as _CurlRequestsError
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False


class ErrorSeverity(Enum):
    """Error severity levels for scraping operations."""

    LOW = "low"  # Temporary issues, retry recommended
    MEDIUM = "medium"  # Data quality issues, continue with warnings
    HIGH = "high"  # Critical failures, stop processing
    FATAL = "fatal"  # System-level failures, escalate


class ScrapingError(Exception):
    """Base exception for scraping-related errors."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.severity = severity
        self.original_error = original_error


class NetworkError(ScrapingError):
    """Network-related scraping errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorSeverity.LOW, original_error)
        self.status_code = status_code


class DataError(ScrapingError):
    """Data parsing or validation errors."""

    def __init__(self, message: str, data_type: str = "unknown", original_error: Optional[Exception] = None):
        super().__init__(message, ErrorSeverity.MEDIUM, original_error)
        self.data_type = data_type


class UnknownClubError(ScrapingError):
    """Raised when trying to scrape an unregistered club domain"""

    def __init__(self, message: str, data_type: str = "unknown", original_error: Optional[Exception] = None):
        super().__init__(message, ErrorSeverity.MEDIUM, original_error)
        self.data_type = data_type


class RateLimitError(ScrapingError):
    """Rate limiting errors."""

    def __init__(self, message: str, retry_after: Optional[int] = None, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorSeverity.LOW, original_error)
        self.retry_after = retry_after


class CircuitBreakerOpenError(ScrapingError):
    """Raised when a circuit breaker is open, preventing HTTP calls to a downed provider.

    Severity is HIGH so ErrorHandler._should_retry() skips retries immediately.
    """

    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.HIGH)


class ErrorClassifier:
    """Classifies exceptions into scraping error types."""

    @staticmethod
    def classify_http_error(exception, response=None) -> ScrapingError:
        """Classify HTTP client errors."""
        if not HAS_CURL_CFFI:
            return NetworkError("HTTP error (curl_cffi not available)", None, exception)

        status_code = response.status_code if response else None

        # Check aiohttp exception types if available
        if hasattr(exception, '__class__') and hasattr(exception.__class__, '__module__'):
            class_name = exception.__class__.__name__
            if class_name == 'ClientTimeout':
                return NetworkError("Request timeout", status_code, exception)
            elif class_name == 'ClientConnectorError':
                return NetworkError("Connection failed", status_code, exception)

        if status_code:
            if status_code == 429:
                retry_after = None
                if response and "Retry-After" in response.headers:
                    try:
                        retry_after = int(response.headers["Retry-After"])
                    except ValueError:
                        pass
                return RateLimitError(f"Rate limited (HTTP {status_code})", retry_after, exception)

            if 400 <= status_code < 500:
                return NetworkError(f"Client error (HTTP {status_code})", status_code, exception)

            if 500 <= status_code < 600:
                return NetworkError(f"Server error (HTTP {status_code})", status_code, exception)

        return NetworkError("Unknown HTTP error", status_code, exception)

    @staticmethod
    def classify_data_error(exception: Exception, data_context: str = "unknown") -> DataError:
        """Classify data parsing errors."""
        if isinstance(exception, (ValueError, TypeError)):
            return DataError(f"Data parsing failed: {str(exception)}", data_context, exception)

        if isinstance(exception, KeyError):
            return DataError(f"Missing required field: {str(exception)}", data_context, exception)

        return DataError(f"Data processing error: {str(exception)}", data_context, exception)
