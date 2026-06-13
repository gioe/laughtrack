"""Unit tests: BaseScraper._fetch_html_with_js() — Playwright singleton helper."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.base.base_scraper import BaseScraper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_club() -> Club:
    _c = Club(id=1, name='Test Club', address='', website='https://example.com', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://example.com/events', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


class _ConcreteScraper(BaseScraper):
    key = "test"

    async def get_data(self, target):
        return None


_MODULE = "laughtrack.foundation.infrastructure.http.client"

# Neutralize the scrapers-table allowlist lookup: resolve_proxy_url calls
# scraper_proxy_registry.proxy_enabled_keys(), which opens a DB connection
# and re-runs load_dotenv (see test_tixr_client.py for the full story).
_NO_KEY_PROXY = patch(f"{_MODULE}.HttpClient.resolve_proxy_url", return_value=None)


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

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), _NO_KEY_PROXY:
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result == "<html>events</html>"
        mock_browser.fetch_html.assert_called_once_with(
            "https://example.com/events", proxy_url=None
        )

    @pytest.mark.asyncio
    async def test_key_allowlisted_proxy_is_threaded_to_browser(self):
        """A scraper whose key is allowlisted in the scrapers table routes
        the Playwright fetch through the residential proxy."""
        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>events</html>")

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), \
                patch(
                    f"{_MODULE}.HttpClient.resolve_proxy_url",
                    return_value="http://user:pass@proxy.example:7000",
                ):
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result == "<html>events</html>"
        mock_browser.fetch_html.assert_called_once_with(
            "https://example.com/events",
            proxy_url="http://user:pass@proxy.example:7000",
        )

    @pytest.mark.asyncio
    async def test_source_metadata_flag_enables_proxy(self, monkeypatch):
        """TASK-2845: a use_residential_proxy metadata flag on the scraping
        source routes this venue through the proxy even when the scraper key
        (shared by many venues, e.g. json_ld) is not allowlisted."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", "http://user:pass@proxy.example:7000")
        club = _make_club()
        club.active_scraping_source = ScrapingSource(
            id=1,
            club_id=club.id,
            platform="custom",
            scraper_key="json_ld",
            source_url="https://example.com/events",
            external_id=None,
            metadata={"use_residential_proxy": True},
        )
        club.scraping_sources = [club.active_scraping_source]
        scraper = _ConcreteScraper(club=club)
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>events</html>")

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), _NO_KEY_PROXY:
            await scraper._fetch_html_with_js("https://example.com/events")

        mock_browser.fetch_html.assert_called_once_with(
            "https://example.com/events",
            proxy_url="http://user:pass@proxy.example:7000",
        )

    @pytest.mark.asyncio
    async def test_no_flag_and_no_allowlist_means_direct(self, monkeypatch):
        """Without the metadata flag or a key allowlist entry, the fetch goes
        out direct even when RESIDENTIAL_PROXY_URL is configured."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", "http://user:pass@proxy.example:7000")
        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>events</html>")

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), _NO_KEY_PROXY:
            await scraper._fetch_html_with_js("https://example.com/events")

        mock_browser.fetch_html.assert_called_once_with(
            "https://example.com/events", proxy_url=None
        )

    @pytest.mark.asyncio
    async def test_rendered_challenge_html_records_bot_block(self):
        """TASK-2845: a rendered page that is still a WAF challenge records a
        bot-block signature on the bound diagnostics — before this, a fully
        blocked force_js_rendering venue persisted bot_block_detected=false
        and read as a legitimately empty calendar (West River incident)."""
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            ScrapeDiagnostics,
            bind_diagnostics,
            reset_diagnostics,
        )

        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(
            return_value="<html><title>Just a moment...</title></html>"
        )

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), _NO_KEY_PROXY:
                await scraper._fetch_html_with_js("https://example.com/events")
        finally:
            reset_diagnostics(token)

        assert diagnostics.playwright_fallback_used is True
        assert diagnostics.bot_block_detected is True
        assert diagnostics.bot_block_signature == "playwright_just a moment"
        assert diagnostics.bot_block_source == "playwright_rendered_html"

    @pytest.mark.asyncio
    async def test_rendered_real_html_records_no_bot_block(self):
        """A successful render marks playwright use but no bot block."""
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            ScrapeDiagnostics,
            bind_diagnostics,
            reset_diagnostics,
        )

        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>real events</html>")

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), _NO_KEY_PROXY:
                await scraper._fetch_html_with_js("https://example.com/events")
        finally:
            reset_diagnostics(token)

        assert diagnostics.playwright_fallback_used is True
        assert diagnostics.bot_block_detected is False

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        """When browser.fetch_html raises, the method catches it and returns None."""
        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(side_effect=RuntimeError("Chromium crash"))

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), _NO_KEY_PROXY:
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """When browser.fetch_html times out, the method logs a warning and returns None."""
        scraper = _ConcreteScraper(club=_make_club())
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch(f"{_MODULE}._get_js_browser", return_value=mock_browser), _NO_KEY_PROXY:
            result = await scraper._fetch_html_with_js("https://example.com/events")

        assert result is None
