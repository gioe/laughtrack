"""
Tests for ErrorHandler._should_retry — 4xx errors must not be retried.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from laughtrack.foundation.exceptions import DataError, NetworkError, RateLimitError

# ---------------------------------------------------------------------------
# Load error_handling.py directly via SourceFileLoader so we bypass the
# package __init__.py (which imports RateLimiter → gioe_libs, an optional dep
# not installed in this environment).
# ---------------------------------------------------------------------------
_SCRAPER_SRC = Path(__file__).parents[3] / "src"


def _load_module(dotted_name: str) -> ModuleType:
    path = _SCRAPER_SRC / dotted_name.replace(".", "/")
    if not path.suffix:
        path = path.with_suffix(".py")
    loader = importlib.machinery.SourceFileLoader(dotted_name, str(path))
    spec = importlib.util.spec_from_loader(dotted_name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(dotted_name, mod)
    loader.exec_module(mod)
    return mod


_error_handling = _load_module("laughtrack.utilities.infrastructure.error_handling")
ErrorHandler = _error_handling.ErrorHandler
RetryConfig = _error_handling.RetryConfig


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
