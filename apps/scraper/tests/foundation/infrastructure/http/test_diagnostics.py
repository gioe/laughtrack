"""Unit tests for ScrapeDiagnostics recording via the ContextVar side-channel.

Covers the four self-triage scenarios from TASK-1665:
    1. 5xx response → bot_block=False, http_status=503
    2. Cloudflare challenge → bot_block=True, signature='just a moment'
    3. 200 with empty event list → items_before_filter=0
    4. 200 with events but all filtered → items_before_filter>0, num_shows=0
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.infrastructure.http.diagnostics import (
    ScrapeDiagnostics,
    bind_diagnostics,
    reset_diagnostics,
)
from laughtrack.scrapers.base.base_scraper import BaseScraper


_NO_FALLBACK = patch(
    "laughtrack.foundation.infrastructure.http.client._get_js_browser",
    return_value=None,
)


def _make_response(status_code: int, text: str = "", json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=(json_data if json_data is not None else {}))
    return resp


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


class _NoOpScraper(BaseScraper):
    key = "test"

    async def get_data(self, target):
        return None


class TestScrapeDiagnosticsFetchHtml:
    @pytest.mark.asyncio
    async def test_5xx_records_http_status_without_bot_block(self):
        """Server error: http_status=503, bot_block stays False."""
        session = AsyncMock()
        session.get.return_value = _make_response(503)

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with _NO_FALLBACK:
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                    result = await HttpClient.fetch_html(session, "https://example.com/")
        finally:
            reset_diagnostics(token)

        assert result is None
        assert diagnostics.http_status == 503
        assert diagnostics.bot_block_detected is False
        assert diagnostics.bot_block_signature is None

    @pytest.mark.asyncio
    async def test_cloudflare_challenge_records_bot_block_signature(self):
        """Cloudflare 'just a moment' page: bot_block=True with matching signature."""
        cloudflare_html = "<html><title>Just a moment...</title></html>"
        session = AsyncMock()
        session.get.return_value = _make_response(200, text=cloudflare_html)

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with _NO_FALLBACK:
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    await HttpClient.fetch_html(session, "https://example.com/")
        finally:
            reset_diagnostics(token)

        assert diagnostics.http_status == 200
        assert diagnostics.bot_block_detected is True
        assert diagnostics.bot_block_signature == "just a moment"

    @pytest.mark.asyncio
    async def test_playwright_fallback_recorded_when_invoked(self):
        """Fallback attempted: playwright_fallback_used=True regardless of outcome."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = MagicMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>ok</html>")

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch(
                "laughtrack.foundation.infrastructure.http.client._get_js_browser",
                return_value=mock_browser,
            ):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                        await HttpClient.fetch_html(session, "https://example.com/")
        finally:
            reset_diagnostics(token)

        assert diagnostics.http_status == 403
        assert diagnostics.playwright_fallback_used is True

    @pytest.mark.asyncio
    async def test_no_recording_when_no_diagnostics_bound(self):
        """Ad-hoc HttpClient use outside a scrape must not raise."""
        session = AsyncMock()
        session.get.return_value = _make_response(503)

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                result = await HttpClient.fetch_html(session, "https://example.com/")

        assert result is None


class TestScrapeDiagnosticsFetchJson:
    @pytest.mark.asyncio
    async def test_non_200_records_http_status(self):
        """API path also records status for triage."""
        session = AsyncMock()
        session.get.return_value = _make_response(503, text="Service Unavailable")

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                result = await HttpClient.fetch_json(session, "https://example.com/api")
        finally:
            reset_diagnostics(token)

        assert result is None
        assert diagnostics.http_status == 503
        assert diagnostics.bot_block_detected is False

    @pytest.mark.asyncio
    async def test_200_json_response_records_status(self):
        """Successful API fetch still records http_status=200 for completeness."""
        session = AsyncMock()
        session.get.return_value = _make_response(200, text='{"ok":true}', json_data={"ok": True})

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            result = await HttpClient.fetch_json(session, "https://example.com/api")
        finally:
            reset_diagnostics(token)

        assert result == {"ok": True}
        assert diagnostics.http_status == 200

    @pytest.mark.asyncio
    async def test_cloudflare_html_challenge_on_json_path_records_bot_block(self):
        """WAF that returns a 403 HTML challenge to an API request surfaces as bot_block=True."""
        challenge_html = "<html><title>Just a moment...</title></html>"
        session = AsyncMock()
        session.get.return_value = _make_response(403, text=challenge_html)

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                result = await HttpClient.fetch_json(session, "https://example.com/api")
        finally:
            reset_diagnostics(token)

        assert result is None
        assert diagnostics.http_status == 403
        assert diagnostics.bot_block_detected is True
        assert diagnostics.bot_block_signature == "just a moment"


class TestItemsBeforeFilter:
    def test_empty_event_list_yields_zero_items(self):
        """200 response with empty array → items_before_filter stays 0."""
        scraper = _NoOpScraper(club=_make_club())
        raw_data = SimpleNamespace(event_list=[])

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            shows = scraper._transform_all_raw_data([(raw_data, "https://example.com/")])
        finally:
            reset_diagnostics(token)

        assert shows == []
        assert diagnostics.items_before_filter == 0

    def test_events_all_filtered_yields_positive_items_but_zero_shows(self):
        """200 with events but transform filters all → items_before_filter > 0, num_shows = 0."""
        scraper = _NoOpScraper(club=_make_club())
        raw_data = SimpleNamespace(event_list=[{"e": 1}, {"e": 2}, {"e": 3}])

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            # Simulate the pipeline filtering all events out (e.g. past dates, validation fails)
            with patch.object(scraper, "transform_data", return_value=[]):
                shows = scraper._transform_all_raw_data([(raw_data, "https://example.com/")])
        finally:
            reset_diagnostics(token)

        assert shows == []
        assert diagnostics.items_before_filter == 3
