"""
Foundation exceptions with no domain dependencies.

These exception classes use only standard library and third-party dependencies,
making them reusable across different domains.
"""

from .scraping_errors import (
    CircuitBreakerOpenError,
    DataError,
    ErrorClassifier,
    ErrorSeverity,
    NetworkError,
    RateLimitError,
    ScrapingError,
    UnknownClubError,
)

__all__ = [
    "CircuitBreakerOpenError",
    "DataError",
    "ErrorClassifier",
    "ErrorSeverity",
    "NetworkError",
    "RateLimitError",
    "ScrapingError",
    "UnknownClubError",
]
