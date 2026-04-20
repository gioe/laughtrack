"""
Unit tests for SquadUpScraper._fetch_events_page.

Verifies that the bare AsyncSession + Chrome impersonation path delegates to
HttpClient.fetch_json (TASK-1654 / B3) so Cloudflare 403 responses trigger
the shared Playwright fallback, while preserving the DataDome/Cloudflare-
friendly behaviour of sending headers=None (curl_cffi's built-in
impersonation fingerprint only — no application-level headers).
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.squadup import scraper as squadup_module
from laughtrack.scrapers.implementations.api.squadup.scraper import SquadUpScraper


def _club() -> Club:
    return Club(
        id=42,
        name="Test SquadUp Venue",
        address="123 Main St",
        website="https://example.com",
        scraping_url="https://example.com",
        popularity=0,
        zip_code="90001",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
        squadup_user_id="7408591",
    )


class _FakeSession:
    """Async context manager that forwards to subclasses' ``get``."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None, proxies=None, **kwargs):
        raise NotImplementedError("subclass must override get()")


@pytest.mark.asyncio
async def test_200_returns_parsed_json(monkeypatch):
    """HTTP 200 + well-formed JSON body returns the parsed dict unchanged."""
    monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")

    payload = {
        "events": [{"id": 1, "title": "Open Mic"}],
        "meta": {"paging": {"total_pages": 1}},
    }

    class FakeResponse:
        status_code = 200
        text = '{"events": [{"id": 1, "title": "Open Mic"}], "meta": {"paging": {"total_pages": 1}}}'

        def json(self):
            return payload

    class Session(_FakeSession):
        async def get(self, url, headers=None, proxies=None, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(squadup_module, "AsyncSession", Session)

    scraper = SquadUpScraper(_club())
    result = await scraper._fetch_events_page(user_id="7408591", page=1)

    assert result == payload


@pytest.mark.asyncio
async def test_non_200_returns_none_when_fallback_disabled(monkeypatch):
    """Non-200 without a Playwright rescue returns None."""
    monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")

    class FakeResponse:
        status_code = 404
        text = "Not Found"

        def json(self):  # pragma: no cover - should not be reached
            raise AssertionError("json() should not be called on non-200")

    class Session(_FakeSession):
        async def get(self, url, headers=None, proxies=None, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(squadup_module, "AsyncSession", Session)

    scraper = SquadUpScraper(_club())
    result = await scraper._fetch_events_page(user_id="7408591", page=1)

    assert result is None


@pytest.mark.asyncio
async def test_exception_returns_none(monkeypatch):
    """Network-layer exceptions are caught and logged, returning None."""
    monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")

    class Session(_FakeSession):
        async def get(self, url, headers=None, proxies=None, **kwargs):
            raise ConnectionError("network down")

    monkeypatch.setattr(squadup_module, "AsyncSession", Session)

    scraper = SquadUpScraper(_club())
    result = await scraper._fetch_events_page(user_id="7408591", page=1)

    assert result is None


@pytest.mark.asyncio
async def test_cloudflare_403_triggers_playwright_fallback(monkeypatch):
    """A Cloudflare 403 is rescued via the Playwright fallback (TASK-1654 / B3)."""
    monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)

    captured_headers: dict = {}

    class FakeResponse:
        status_code = 403
        text = "<html><body>Just a moment...</body></html>"

    class Session(_FakeSession):
        async def get(self, url, headers=None, proxies=None, **kwargs):
            captured_headers["value"] = headers
            return FakeResponse()

    monkeypatch.setattr(squadup_module, "AsyncSession", Session)

    rescued_payload = {
        "events": [{"id": 7, "title": "Rescued By Playwright"}],
        "meta": {"paging": {"total_pages": 1}},
    }

    class FakeBrowser:
        async def fetch_html(self, url, proxy_url=None):
            # Chromium wraps JSON endpoints in <pre>; HttpClient.fetch_json
            # strips and parses it.
            import json as _json
            return f"<html><body><pre>{_json.dumps(rescued_payload)}</pre></body></html>"

    monkeypatch.setattr(
        "laughtrack.foundation.infrastructure.http.client._get_js_browser",
        lambda: FakeBrowser(),
    )

    scraper = SquadUpScraper(_club())
    result = await scraper._fetch_events_page(user_id="7408591", page=1)

    assert result == rescued_payload
    # Preserve the DataDome-friendly contract: no application-level headers on
    # the curl_cffi request — only the Chrome impersonation fingerprint.
    assert captured_headers["value"] is None
