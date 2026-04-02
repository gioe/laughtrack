"""Unit tests: BaseScraper._fetch_html_with_js() — Playwright singleton helper."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_club() -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="",
        website="https://example.com",
        scraping_url="https://example.com/events",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )


class _ConcreteScraper(BaseScraper):
    key = "test"

    async def get_data(self, target):
        return None


_MODULE = "laughtrack.foundation.infrastructure.http.client"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFetchHtmlWithJs:
    @pytest.mark.asyncio
    async def test_returns_none_when_browser_unavailable(self):
        """When _get_js_browser() returns None, the method returns None."""
        scraper = _ConcreteScraper(club=_make_club())

        with patch(f"{_MODULE}._get_js_browser", return_value=None):
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_html_on_success(self):
        """When the browser fetches HTML successfully, the method returns it."""
        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>events</html>")

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser):
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result == "<html>events</html>"
        mock_browser.fetch_html.assert_called_once_with("https://example.com/events")

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        """When browser.fetch_html raises, the method catches it and returns None."""
        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(side_effect=RuntimeError("Chromium crash"))

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser):
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """When browser.fetch_html times out, the method logs a warning and returns None."""
        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser):
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result is None
