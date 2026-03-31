"""
Tests for ErrorClassifier.classify_http_error — exception.response fallback path.

Covers the bug from TASK-833 where response=None but exception.response has a
status_code, causing the scraper to treat a 404 as an unknown error and retry 4 times.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Load error_handling.py directly via SourceFileLoader so we bypass the
# package __init__.py (which imports RateLimiter → gioe_libs, an optional dep
# not installed in this environment).
# ---------------------------------------------------------------------------
_SCRAPER_SRC = Path(__file__).parents[3] / "src"


def _load_module(dotted_name: str) -> ModuleType:
    """Load a module by dotted name directly from source, bypassing __init__ files."""
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

from laughtrack.foundation.exceptions import NetworkError, RateLimitError
from laughtrack.foundation.exceptions.scraping_errors import ErrorClassifier


class TestClassifyHttpErrorExceptionResponseFallback:
    """ErrorClassifier.classify_http_error extracts status_code from exception.response."""

    def test_404_extracted_from_exception_response_when_response_arg_is_none(self):
        """The response= arg is None, but exception.response.status_code is 404."""
        mock_exc = MagicMock()
        mock_exc.response.status_code = 404

        error = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(error, NetworkError)
        assert error.status_code == 404

    def test_400_extracted_from_exception_response(self):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 400

        error = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(error, NetworkError)
        assert error.status_code == 400

    def test_403_extracted_from_exception_response(self):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 403

        error = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(error, NetworkError)
        assert error.status_code == 403

    def test_500_extracted_from_exception_response(self):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 500

        error = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(error, NetworkError)
        assert error.status_code == 500

    def test_429_extracted_from_exception_response_returns_rate_limit_error(self):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 429
        mock_exc.response.headers = {}

        error = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(error, RateLimitError)

    def test_exception_with_no_response_attribute_returns_unknown_network_error(self):
        """When exception has no .response attribute at all, status_code is None."""
        mock_exc = MagicMock(spec=[])  # no attributes

        error = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(error, NetworkError)
        assert error.status_code is None

    def test_exception_response_none_returns_unknown_network_error(self):
        """When exception.response is None (not just absent), status_code is None."""
        mock_exc = MagicMock()
        mock_exc.response = None

        error = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(error, NetworkError)
        assert error.status_code is None


class TestClassifyHttpError4xxClassification:
    """4xx errors are classified as NetworkError with the correct status_code."""

    def test_400_is_network_error_with_status_code(self):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 400

        error = ErrorClassifier.classify_http_error(mock_exc)

        assert isinstance(error, NetworkError)
        assert error.status_code == 400

    def test_404_is_network_error_with_status_code(self):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 404

        error = ErrorClassifier.classify_http_error(mock_exc)

        assert isinstance(error, NetworkError)
        assert error.status_code == 404

    def test_4xx_message_includes_status_code(self):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 404

        error = ErrorClassifier.classify_http_error(mock_exc)

        assert "404" in str(error)


class TestShouldRetry4xxFromClassifier:
    """_should_retry returns False for NetworkErrors with 4xx status produced by ErrorClassifier."""

    @pytest.fixture
    def handler(self):
        return ErrorHandler(RetryConfig(max_attempts=3))

    def test_404_from_exception_response_not_retried(self, handler):
        """Full path: exception.response fallback → NetworkError(404) → no retry."""
        mock_exc = MagicMock()
        mock_exc.response.status_code = 404

        classified = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert isinstance(classified, NetworkError)
        assert classified.status_code == 404
        assert handler._should_retry(classified, attempt=1) is False

    def test_403_from_exception_response_not_retried(self, handler):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 403

        classified = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert handler._should_retry(classified, attempt=1) is False

    def test_400_from_exception_response_not_retried(self, handler):
        mock_exc = MagicMock()
        mock_exc.response.status_code = 400

        classified = ErrorClassifier.classify_http_error(mock_exc, response=None)

        assert handler._should_retry(classified, attempt=1) is False
