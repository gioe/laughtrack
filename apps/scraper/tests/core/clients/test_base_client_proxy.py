"""Integration tests verifying BaseApiClient proxy wiring.

Confirms that get_proxy(), report_success(), and report_failure() are
called at the right points — including the non-200 (None-return) case that
was previously a silent false-success bug.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http import scraper_proxy_registry
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool


PROXY_URL = "http://proxy-host:8080"
RESIDENTIAL_PROXY_URL = "http://residential.example:8080"
ALLOWLISTED_KEY = "tixr"


@pytest.fixture
def stub_registry():
    """Pin the registry so key-driven routing tests don't hit Postgres.

    Mirrors the fixture in tests/foundation/infrastructure/http/test_client_proxy.py.
    Not autouse — only the key-driven routing tests at the bottom need it; the
    legacy ProxyPool tests above must continue running without registry stubs.
    """
    scraper_proxy_registry.reset_cache()
    with patch.object(
        scraper_proxy_registry,
        "proxy_enabled_keys",
        return_value=frozenset({ALLOWLISTED_KEY}),
    ):
        yield
    scraper_proxy_registry.reset_cache()


_NO_FALLBACK = patch(
    "laughtrack.foundation.infrastructure.http.client._get_js_browser",
    return_value=None,
)


def _make_club() -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="123 St",
        website="https://example.com",
        popularity=1,
        zip_code="00000",
        phone_number="000-000-0000",
        visible=True,
        scraping_sources=[
            ScrapingSource(platform="custom", scraper_key="custom", source_url="example.com"),
        ],
    )


class ConcreteClient(BaseApiClient):
    """Minimal concrete subclass for testing."""

    def _initialize_headers(self):
        return {}


def _make_pool(proxy_url: str = PROXY_URL) -> ProxyPool:
    pool = MagicMock(spec=ProxyPool)
    pool.get_proxy.return_value = proxy_url
    return pool


def _make_session_cm(status_code: int = 200, text: str = "<html/>", json_data=None):
    """Return an AsyncSession context-manager mock."""
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json = MagicMock(return_value=json_data or {"ok": True})

    session = AsyncMock()
    session.get.return_value = response
    session.post.return_value = response

    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = False
    return cm, session


# ---------------------------------------------------------------------------
# fetch_json
# ---------------------------------------------------------------------------


class TestFetchJsonProxyWiring:
    @pytest.mark.asyncio
    async def test_get_proxy_called_once_per_request(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            await client.fetch_json("https://example.com/api")

        pool.get_proxy.assert_called_once()

    @pytest.mark.asyncio
    async def test_report_success_on_200_response(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            await client.fetch_json("https://example.com/api")

        pool.report_success.assert_called_once_with(PROXY_URL)
        pool.report_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_failure_on_non200_response(self):
        """Non-200 returns None from HttpClient — must call report_failure, not report_success."""
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(status_code=503)

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.fetch_json("https://example.com/api")

        assert result is None
        pool.report_failure.assert_called_once_with(PROXY_URL)
        pool.report_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_failure_on_network_exception(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)

        cm = AsyncMock()
        cm.__aenter__.side_effect = ConnectionError("timeout")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.fetch_json("https://example.com/api")

        assert result is None
        pool.report_failure.assert_called_once_with(PROXY_URL)

    @pytest.mark.asyncio
    async def test_no_pool_no_proxy_calls(self):
        """When proxy_pool is None the pool methods are never invoked."""
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(200, json_data={"ok": True})

        # Should not raise and should return data normally
        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.fetch_json("https://example.com/api")

        assert result == {"ok": True}


# ---------------------------------------------------------------------------
# fetch_html
# ---------------------------------------------------------------------------


class TestFetchHtmlProxyWiring:
    @pytest.mark.asyncio
    async def test_report_success_on_200_response(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(200, text="<html>ok</html>")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            await client.fetch_html("https://example.com/page")

        pool.report_success.assert_called_once_with(PROXY_URL)
        pool.report_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_failure_on_non200_response(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(status_code=404)

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm), \
             patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=None):
            result = await client.fetch_html("https://example.com/page")

        assert result is None
        pool.report_failure.assert_called_once_with(PROXY_URL)


# ---------------------------------------------------------------------------
# post_json — empty-body guard
# ---------------------------------------------------------------------------


class TestPostJsonEmptyBody:
    @pytest.mark.asyncio
    async def test_200_empty_body_returns_none_and_logs_error(self):
        """HTTP 200 with empty body returns None and logs an error."""
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(200, text="")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_json("https://example.com/api", {"key": "val"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "empty body" in error_msg

    @pytest.mark.asyncio
    async def test_200_whitespace_only_body_returns_none_and_logs_error(self):
        """HTTP 200 with whitespace-only body is treated as empty."""
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(200, text="   \n  ")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_json("https://example.com/api", {"key": "val"})

        assert result is None
        MockLogger.error.assert_called()

    @pytest.mark.asyncio
    async def test_200_valid_body_returns_parsed_json(self):
        """HTTP 200 with valid JSON body returns parsed data."""
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(200, text='{"token": "abc"}', json_data={"token": "abc"})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.post_json("https://example.com/api", {"key": "val"})

        assert result == {"token": "abc"}


# ---------------------------------------------------------------------------
# post_json — bot-block detection
# ---------------------------------------------------------------------------


class TestPostJsonBotBlock:
    @pytest.mark.asyncio
    async def test_non200_with_datadome_body_logs_error_with_signature(self):
        """HTTP 403 with a DataDome challenge body logs the signature at error level."""
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(
            status_code=403,
            text="<html><body>datadome challenge page</body></html>",
        )

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_json("https://example.com/api", {"key": "val"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "datadome" in error_msg.lower()
        assert "bot-block" in error_msg.lower()
        pool.report_failure.assert_called_once_with(PROXY_URL)

    @pytest.mark.asyncio
    async def test_non200_without_bot_block_logs_plain_error(self):
        """HTTP 500 without a bot-block signature logs an error without the signature label."""
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(status_code=500, text="internal server error")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_json("https://example.com/api", {"key": "val"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "500" in error_msg
        assert "bot-block" not in error_msg.lower()

    @pytest.mark.asyncio
    async def test_200_with_cloudflare_interstitial_returns_none_and_logs_error(self):
        """HTTP 200 + Cloudflare 'Just a moment' body is treated as a bot-block."""
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(
            status_code=200,
            text="<html><title>Just a moment...</title></html>",
        )

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_json("https://example.com/api", {"key": "val"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "bot-block" in error_msg.lower()
        pool.report_failure.assert_called_once_with(PROXY_URL)


# ---------------------------------------------------------------------------
# post_form — empty-body + bot-block detection
# ---------------------------------------------------------------------------


class TestPostFormBotBlock:
    @pytest.mark.asyncio
    async def test_non200_with_datadome_body_logs_error_with_signature(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(
            status_code=403,
            text="<html><body>datadome challenge page</body></html>",
        )

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_form("https://example.com/api", {"k": "v"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "datadome" in error_msg.lower()
        pool.report_failure.assert_called_once_with(PROXY_URL)

    @pytest.mark.asyncio
    async def test_non200_without_bot_block_logs_plain_error(self):
        """HTTP 500 without a bot-block signature logs an error without the signature label."""
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(status_code=500, text="internal server error")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_form("https://example.com/api", {"k": "v"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "500" in error_msg
        assert "form" in error_msg.lower()
        assert "bot-block" not in error_msg.lower()

    @pytest.mark.asyncio
    async def test_200_empty_body_logs_error(self):
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(status_code=200, text="")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_form("https://example.com/api", {"k": "v"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "empty body" in error_msg

    @pytest.mark.asyncio
    async def test_200_with_cloudflare_interstitial_returns_none_and_logs_error(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(
            status_code=200,
            text="<html>Just a moment please…</html>",
        )

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with patch("laughtrack.core.clients.base.Logger") as MockLogger:
                result = await client.post_form("https://example.com/api", {"k": "v"})

        assert result is None
        MockLogger.error.assert_called()
        error_msg = MockLogger.error.call_args[0][0]
        assert "bot-block" in error_msg.lower()
        pool.report_failure.assert_called_once_with(PROXY_URL)

    @pytest.mark.asyncio
    async def test_200_valid_body_returns_text(self):
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(status_code=200, text="OK")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.post_form("https://example.com/api", {"k": "v"})

        assert result == "OK"


# ---------------------------------------------------------------------------
# fetch_json_list — allow_empty_body forwarding (TASK-1677)
# ---------------------------------------------------------------------------


class TestFetchJsonListAllowEmptyBody:
    @pytest.mark.asyncio
    async def test_allow_empty_body_forwarded_to_fetch_json(self):
        """``fetch_json_list`` must forward ``allow_empty_body`` to ``fetch_json``
        so array endpoints that use empty body as a stale-data signal can opt in."""
        client = ConcreteClient(_make_club())
        with patch.object(ConcreteClient, "fetch_json", new=AsyncMock(return_value=[])) as mock_fetch_json:
            await client.fetch_json_list("https://example.com/api", allow_empty_body=True)

        assert mock_fetch_json.await_count == 1
        assert mock_fetch_json.await_args.kwargs["allow_empty_body"] is True

    @pytest.mark.asyncio
    async def test_allow_empty_body_defaults_to_false(self):
        """Default ``allow_empty_body=False`` preserves the pre-refactor behavior."""
        client = ConcreteClient(_make_club())
        with patch.object(ConcreteClient, "fetch_json", new=AsyncMock(return_value=[])) as mock_fetch_json:
            await client.fetch_json_list("https://example.com/api")

        assert mock_fetch_json.await_count == 1
        assert mock_fetch_json.await_args.kwargs["allow_empty_body"] is False


# ---------------------------------------------------------------------------
# _report_proxy_outcome helper (TASK-1678)
# ---------------------------------------------------------------------------


class TestReportProxyOutcomeHelper:
    """Direct coverage for the shared proxy-accounting helper."""

    def test_success_routes_to_report_success(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        client._report_proxy_outcome(PROXY_URL, success=True)
        pool.report_success.assert_called_once_with(PROXY_URL)
        pool.report_failure.assert_not_called()

    def test_failure_routes_to_report_failure(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        client._report_proxy_outcome(PROXY_URL, success=False)
        pool.report_failure.assert_called_once_with(PROXY_URL)
        pool.report_success.assert_not_called()

    def test_noop_when_proxy_url_is_none(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        client._report_proxy_outcome(None, success=True)
        client._report_proxy_outcome(None, success=False)
        pool.report_success.assert_not_called()
        pool.report_failure.assert_not_called()

    def test_noop_when_proxy_pool_is_none(self):
        client = ConcreteClient(_make_club(), proxy_pool=None)
        # Must not raise even though there is no pool to report to.
        client._report_proxy_outcome(PROXY_URL, success=True)
        client._report_proxy_outcome(PROXY_URL, success=False)


# ---------------------------------------------------------------------------
# Key-driven residential-proxy routing (TASK-1935)
#
# These tests verify the BaseApiClient.key ClassVar is forwarded into
# HttpClient.fetch_html and HttpClient.fetch_json as scraper_key, so
# allowlisted clients (TixrClient: key="tixr") pick up RESIDENTIAL_PROXY_URL
# automatically. They use a session-mock that captures the proxies kwarg
# rather than asserting on log calls — the fetch_html/fetch_json proxy
# WARN behavior is covered exhaustively in test_client_proxy.py.
# ---------------------------------------------------------------------------


class AllowlistedClient(BaseApiClient):
    """Subclass that opts into residential proxy via key ClassVar."""

    key = ALLOWLISTED_KEY

    def _initialize_headers(self):
        return {}


class UnkeyedClient(BaseApiClient):
    """Subclass without a key — must NOT route through residential proxy."""

    def _initialize_headers(self):
        return {}


class TestKeyDrivenResidentialProxyRouting:
    @pytest.mark.asyncio
    async def test_fetch_json_routes_allowlisted_key_through_residential_proxy(
        self, stub_registry, monkeypatch
    ):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", RESIDENTIAL_PROXY_URL)
        client = AllowlistedClient(_make_club())
        cm, session = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with _NO_FALLBACK:
                await client.fetch_json("https://example.com/api")

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") == {
            "http": RESIDENTIAL_PROXY_URL,
            "https": RESIDENTIAL_PROXY_URL,
        }

    @pytest.mark.asyncio
    async def test_fetch_html_routes_allowlisted_key_through_residential_proxy(
        self, stub_registry, monkeypatch
    ):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", RESIDENTIAL_PROXY_URL)
        client = AllowlistedClient(_make_club())
        cm, session = _make_session_cm(200, text="<html>ok</html>")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with _NO_FALLBACK:
                await client.fetch_html("https://example.com/page")

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") == {
            "http": RESIDENTIAL_PROXY_URL,
            "https": RESIDENTIAL_PROXY_URL,
        }

    @pytest.mark.asyncio
    async def test_unkeyed_client_does_not_route_through_residential_proxy(
        self, stub_registry, monkeypatch
    ):
        """Subclass with no key forwards scraper_key=None — bypass stays silent."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", RESIDENTIAL_PROXY_URL)
        client = UnkeyedClient(_make_club())
        cm, session = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with _NO_FALLBACK:
                await client.fetch_json("https://example.com/api")

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") is None

    @pytest.mark.asyncio
    async def test_proxy_pool_url_wins_over_residential_resolution(
        self, stub_registry, monkeypatch
    ):
        """A proxy_pool-supplied URL must take precedence over the auto-resolver.

        This protects the TixrClient inline path: if a caller explicitly threads
        a ProxyPool through, those proxies are honored instead of being silently
        replaced by RESIDENTIAL_PROXY_URL.
        """
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", RESIDENTIAL_PROXY_URL)
        pool = _make_pool(PROXY_URL)
        client = AllowlistedClient(_make_club(), proxy_pool=pool)
        cm, session = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with _NO_FALLBACK:
                await client.fetch_json("https://example.com/api")

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") == {"http": PROXY_URL, "https": PROXY_URL}

    @pytest.mark.asyncio
    async def test_no_residential_proxy_when_env_unset(
        self, stub_registry, monkeypatch
    ):
        monkeypatch.delenv("RESIDENTIAL_PROXY_URL", raising=False)
        client = AllowlistedClient(_make_club())
        cm, session = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            with _NO_FALLBACK:
                await client.fetch_json("https://example.com/api")

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") is None
