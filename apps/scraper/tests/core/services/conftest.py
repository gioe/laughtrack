"""Shared fixtures for core/services tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_close_js_browser():
    """Prevent _scrape_clubs_concurrently's finally block from trying to close a
    stale PlaywrightBrowser singleton left behind by prior tests.

    Tests in this directory exercise ScrapingService metrics and wiring — they
    never launch a real browser, so close_js_browser should be a no-op."""
    with patch(
        "laughtrack.foundation.infrastructure.http.client.close_js_browser",
        new_callable=AsyncMock,
    ):
        yield
