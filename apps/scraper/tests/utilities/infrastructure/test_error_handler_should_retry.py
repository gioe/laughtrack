"""
Tests for ErrorHandler._should_retry — 4xx errors must not be retried.
"""

import pytest

from laughtrack.foundation.exceptions import DataError, NetworkError, RateLimitError
from laughtrack.utilities.infrastructure.error_handling import ErrorHandler, RetryConfig


@pytest.fixture
def handler():
    return ErrorHandler(RetryConfig(max_attempts=3))


class TestShouldRetry4xx:
    def test_400_not_retried(self, handler):
        err = NetworkError("Client error (HTTP 400)", status_code=400)
        assert handler._should_retry(err, attempt=1) is False

    def test_403_not_retried(self, handler):
        err = NetworkError("Client error (HTTP 403)", status_code=403)
        assert handler._should_retry(err, attempt=1) is False

    def test_404_not_retried(self, handler):
        err = NetworkError("Client error (HTTP 404)", status_code=404)
        assert handler._should_retry(err, attempt=1) is False

    def test_422_not_retried(self, handler):
        err = NetworkError("Client error (HTTP 422)", status_code=422)
        assert handler._should_retry(err, attempt=1) is False

    def test_499_not_retried(self, handler):
        err = NetworkError("Client error (HTTP 499)", status_code=499)
        assert handler._should_retry(err, attempt=1) is False


class TestShouldRetry429:
    def test_rate_limit_error_retried(self, handler):
        """429 is RateLimitError, not NetworkError — must still retry."""
        err = RateLimitError("Rate limited (HTTP 429)", retry_after=5)
        assert handler._should_retry(err, attempt=1) is True


class TestShouldRetry5xx:
    def test_500_retried(self, handler):
        err = NetworkError("Server error (HTTP 500)", status_code=500)
        assert handler._should_retry(err, attempt=1) is True

    def test_503_retried(self, handler):
        err = NetworkError("Server error (HTTP 503)", status_code=503)
        assert handler._should_retry(err, attempt=1) is True


class TestShouldRetryNetworkLevelErrors:
    def test_timeout_retried(self, handler):
        """NetworkError with no status code (timeout/connection refused) retries."""
        err = NetworkError("Request timeout", status_code=None)
        assert handler._should_retry(err, attempt=1) is True

    def test_connection_refused_retried(self, handler):
        err = NetworkError("Connection failed", status_code=None)
        assert handler._should_retry(err, attempt=1) is True


class TestShouldRetryMaxAttempts:
    def test_no_retry_at_max_attempts(self, handler):
        err = NetworkError("Server error (HTTP 500)", status_code=500)
        # attempt == max_attempts → False regardless
        assert handler._should_retry(err, attempt=3) is False

    def test_4xx_still_false_at_attempt_1(self, handler):
        err = NetworkError("Client error (HTTP 404)", status_code=404)
        assert handler._should_retry(err, attempt=1) is False
