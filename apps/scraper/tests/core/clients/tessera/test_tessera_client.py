"""Unit tests for TesseraClient.refresh_session_id and _fetch_ticket_data.

After TASK-1653, both methods delegate to BaseApiClient / HttpClient helpers
so bot-block and empty-body responses benefit from the shared Playwright
fallback (A2) and Logger.error surfacing (A3).
"""

import pytest

from laughtrack.core.clients.tessera import client as tessera_module
from laughtrack.core.clients.tessera.client import TesseraClient
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http.client import HttpClient


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def silence_logging(monkeypatch):
    monkeypatch.setattr(tessera_module.TesseraClient, "log_warning", lambda *a, **k: None)
    monkeypatch.setattr(tessera_module.TesseraClient, "log_error", lambda *a, **k: None)
    monkeypatch.setattr(tessera_module.TesseraClient, "log_info", lambda *a, **k: None)


@pytest.fixture
def stub_base_init(monkeypatch):
    def _init(self, club, proxy_pool=None, rate_limiter=None):
        self.club = club
        self.headers = {"sessionid": "stale-token"}
        self.http_client = HttpClient()
        self.proxy_pool = None
        self.rate_limiter = None
    monkeypatch.setattr(BaseApiClient, "__init__", _init)


def _club() -> Club:
    return Club(
        id=9,
        name="Broadway Comedy Club",
        address="318 W 53rd St",
        website="https://broadwaycomedyclub.com",
        popularity=1,
        zip_code="10019",
        phone_number="212-000-0000",
        visible=True,
        scraping_sources=[
            ScrapingSource(platform="tessera", scraper_key="tessera", source_url="broadwaycomedyclub.com"),
        ],
    )


def _client() -> TesseraClient:
    return TesseraClient(
        _club(),
        base_domain="broadwaycomedyclub.com",
        api_base_url="https://api.tessera.example/products",
        origin_url="https://broadwaycomedyclub.com",
    )


# ---------------------------------------------------------------------------
# refresh_session_id
# ---------------------------------------------------------------------------


class TestRefreshSessionId:
    @pytest.mark.asyncio
    async def test_success_sets_sessionid_and_returns_true(self, monkeypatch, stub_base_init):
        client = _client()

        captured = {}

        async def fake_post_json(self, url, payload=None, headers=None, timeout=30, logger_context=None):
            captured["url"] = url
            captured["payload"] = payload
            captured["headers"] = headers
            return {"sessionId": "new-session-abc"}

        monkeypatch.setattr(BaseApiClient, "post_json", fake_post_json)

        result = await client.refresh_session_id()

        assert result is True
        assert client.headers["sessionid"] == "new-session-abc"
        assert captured["url"].endswith("/authorization/session")
        assert captured["payload"] is None
        assert captured["headers"] == {"Origin": "https://broadwaycomedyclub.com"}

    @pytest.mark.asyncio
    async def test_post_json_returns_none_yields_false(self, monkeypatch, stub_base_init):
        """Non-200 / empty body / bot-block — post_json returns None → False."""
        client = _client()

        async def fake_post_json(self, url, payload=None, headers=None, timeout=30, logger_context=None):
            return None

        monkeypatch.setattr(BaseApiClient, "post_json", fake_post_json)

        result = await client.refresh_session_id()

        assert result is False
        # sessionid header should not have been overwritten
        assert client.headers["sessionid"] == "stale-token"

    @pytest.mark.asyncio
    async def test_missing_session_id_field_yields_false(self, monkeypatch, stub_base_init):
        client = _client()

        async def fake_post_json(self, url, payload=None, headers=None, timeout=30, logger_context=None):
            return {"someOtherField": "x"}

        monkeypatch.setattr(BaseApiClient, "post_json", fake_post_json)

        result = await client.refresh_session_id()

        assert result is False
        assert client.headers["sessionid"] == "stale-token"


# ---------------------------------------------------------------------------
# _fetch_ticket_data
# ---------------------------------------------------------------------------


class TestFetchTicketData:
    @pytest.mark.asyncio
    async def test_success_returns_parsed_response(self, monkeypatch, stub_base_init):
        client = _client()

        captured = {}

        async def fake_fetch_json(self, url, headers=None, timeout=30, logger_context=None, allow_empty_body=False):
            captured["url"] = url
            captured["headers"] = headers
            captured["allow_empty_body"] = allow_empty_body
            return {"campaigns": [], "seatingChartUrl": None}

        monkeypatch.setattr(BaseApiClient, "fetch_json", fake_fetch_json)

        result = await client._fetch_ticket_data("EVT-123")

        assert result is not None
        assert captured["url"] == "https://api.tessera.example/products/EVT-123"
        # sessionid header is threaded through so the API can authenticate the request
        assert captured["headers"] is client.headers
        assert "sessionid" in captured["headers"]
        # TASK-1672: Tessera opts into empty-body-is-OK so stale events
        # don't pay the Chromium launch for a response the browser can't rescue.
        assert captured["allow_empty_body"] is True

    @pytest.mark.asyncio
    async def test_none_from_fetch_json_returns_none(self, monkeypatch, stub_base_init):
        """fetch_json already handles empty-body / 403 / bot-block via HttpClient; Tessera just re-labels."""
        client = _client()

        async def fake_fetch_json(self, url, headers=None, timeout=30, logger_context=None, allow_empty_body=False):
            return None

        monkeypatch.setattr(BaseApiClient, "fetch_json", fake_fetch_json)

        result = await client._fetch_ticket_data("EVT-999")
        assert result is None

    @pytest.mark.asyncio
    async def test_non_dict_response_returns_none(self, monkeypatch, stub_base_init):
        client = _client()

        async def fake_fetch_json(self, url, headers=None, timeout=30, logger_context=None, allow_empty_body=False):
            return ["unexpected", "array"]

        monkeypatch.setattr(BaseApiClient, "fetch_json", fake_fetch_json)

        result = await client._fetch_ticket_data("EVT-000")
        assert result is None


# ---------------------------------------------------------------------------
# End-to-end: bot-block → Playwright fallback path
#
# Verifies the actual delegation chain Tessera now depends on — AsyncSession
# returns a 403 + DataDome body, HttpClient.fetch_json kicks off the Playwright
# fallback, and the rescued JSON flows back to TesseraClient. Without this
# test, a future rename of a BaseApiClient / HttpClient kwarg would silently
# skip the fallback and the stubbed unit tests above would still pass.
# ---------------------------------------------------------------------------


class _EndToEndFakeSession:
    """AsyncSession stub that returns a canned response for a single GET."""

    def __init__(self, impersonate=None, timeout=None):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url, headers=None, proxies=None, **kwargs):
        class _Resp:
            status_code = 403
            text = "<html><body>datadome challenge page</body></html>"
        return _Resp()


class TestFetchTicketDataEndToEnd:
    @pytest.mark.asyncio
    async def test_datadome_403_reaches_playwright_fallback(self, monkeypatch, stub_base_init):
        """A DataDome 403 on the Tessera GET path triggers the shared Playwright fallback."""
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        client = _client()

        # Replace AsyncSession in the BaseApiClient module so fetch_json opens our fake session.
        from laughtrack.core.clients import base as base_mod
        monkeypatch.setattr(base_mod, "AsyncSession", _EndToEndFakeSession)

        # Stub the Playwright browser to return rescued JSON wrapped in <pre>
        # (Chromium's default JSON-viewer shape — HttpClient._parse_json_from_rendered_html
        # handles the extraction).
        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                return '<html><body><pre>{"campaigns": [], "seatingChartUrl": null}</pre></body></html>'

        monkeypatch.setattr(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        result = await client._fetch_ticket_data("EVT-999")

        assert result is not None
        # Parsed TesseraAPIResponse with empty campaigns list from the rescued JSON
        assert list(result.campaigns or []) == []


# ---------------------------------------------------------------------------
# End-to-end: stale-event (HTTP 200 + empty body) skips Playwright
# ---------------------------------------------------------------------------


class _EmptyBodySession:
    """AsyncSession stub that returns a 200 + empty body (Tessera stale event)."""

    def __init__(self, impersonate=None, timeout=None):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url, headers=None, proxies=None, **kwargs):
        class _Resp:
            status_code = 200
            text = ""

            def json(self):
                raise ValueError("empty body not JSON")
        return _Resp()


class TestFetchTicketDataStaleEventSkipsFallback:
    """TASK-1672: HTTP 200 + empty body must NOT trigger the Playwright fallback.

    Previously every stale event on Broadway Comedy Club paid ~1–3 s of
    Chromium launch via ``_fetch_with_fallback``'s empty-body branch.
    The browser replay returns empty too, so the launch was pure overhead.
    ``_fetch_ticket_data`` now passes ``allow_empty_body=True``; the
    short-circuit is exercised end-to-end below.
    """

    @pytest.mark.asyncio
    async def test_empty_body_does_not_launch_browser(self, monkeypatch, stub_base_init):
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        client = _client()

        from laughtrack.core.clients import base as base_mod
        monkeypatch.setattr(base_mod, "AsyncSession", _EmptyBodySession)

        browser_launch_count = {"n": 0}

        def _tracking_get_js_browser():
            browser_launch_count["n"] += 1

            class _ShouldNotBeCalled:
                async def fetch_html(self, url, proxy_url=None):
                    raise AssertionError(
                        "Playwright fallback must not run on Tessera stale-event empty body"
                    )
            return _ShouldNotBeCalled()

        monkeypatch.setattr(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            _tracking_get_js_browser,
        )

        result = await client._fetch_ticket_data("EVT-STALE")

        assert result is None
        # The fallback branch never ran — _get_js_browser was not touched at all.
        assert browser_launch_count["n"] == 0
