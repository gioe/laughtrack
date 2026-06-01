"""Unit tests for HttpClient.fetch_html and fetch_json."""

import asyncio
import concurrent.futures
import json as _json
import weakref
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import laughtrack.foundation.infrastructure.http.client as client_module
from laughtrack.foundation.infrastructure.http.client import HttpClient, _bot_block_reason


def _make_response(status_code: int, text: str = "", json_data=None):
    """Build a mock curl_cffi response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = _json.dumps(json_data) if json_data is not None and not text else text
    resp.json = MagicMock(return_value=json_data if json_data is not None else {})
    return resp


def _reset_browser_cache():
    client_module._js_browser = None
    client_module._js_browsers_by_loop = weakref.WeakKeyDictionary()
    # Also clear the per-process bot-block short-circuit cache so tests that
    # confirm Playwright bot-blocks don't leak into later tests on the same
    # hostname (most tests reuse "example.com").
    client_module._reset_bot_block_shortcircuit()


# ---------------------------------------------------------------------------
# fetch_html
# ---------------------------------------------------------------------------


_NO_FALLBACK = patch(
    "laughtrack.foundation.infrastructure.http.client._get_js_browser",
    return_value=None,
)


class TestFetchHtml:
    @pytest.mark.asyncio
    async def test_non_200_returns_none_and_logs_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response(404)

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                result = await HttpClient.fetch_html(session, "https://example.com/page")

        assert result is None
        mock_warn.assert_called_once()
        call_msg = mock_warn.call_args[0][0]
        assert "404" in call_msg

    @pytest.mark.asyncio
    async def test_200_returns_html_text(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="<html>hello</html>")

        with _NO_FALLBACK:
            result = await HttpClient.fetch_html(session, "https://example.com/page")

        assert result == "<html>hello</html>"

    @pytest.mark.asyncio
    async def test_network_exception_propagates_without_logging(self):
        session = AsyncMock()
        session.get.side_effect = ConnectionError("timeout")

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                with pytest.raises(ConnectionError):
                    await HttpClient.fetch_html(session, "https://example.com/page")

        mock_warn.assert_not_called()

    @pytest.mark.asyncio
    async def test_headers_forwarded_to_session_get(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="<html/>")
        custom_headers = {"X-Custom": "value", "Accept-Language": "en"}

        with _NO_FALLBACK:
            await HttpClient.fetch_html(session, "https://example.com/page", headers=custom_headers)

        session.get.assert_called_once()
        _, kwargs = session.get.call_args
        assert kwargs.get("headers") == custom_headers

    @pytest.mark.asyncio
    async def test_logger_context_passed_to_warn_on_non_200(self):
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        context = {"club": "test_club", "scraper": "test"}

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                await HttpClient.fetch_html(
                    session, "https://example.com/page", logger_context=context
                )

        mock_warn.assert_called_once()
        call_context = mock_warn.call_args[0][1]
        assert call_context == context

    @pytest.mark.asyncio
    async def test_200_empty_body_warn_matches_fetch_json(self):
        """200 + empty body in fetch_html warns exactly once with the 'empty body' phrasing.

        Pins the post-extraction symmetry: fetch_html used to be silent on
        empty-200 bodies, but since the shared _fetch_with_fallback helper
        owns the warn, both public methods now emit the same log. Asserting
        call count guards against a future refactor duplicating the warn
        (e.g. once in the helper, once in fetch_html).
        """
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="")

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                result = await HttpClient.fetch_html(session, "https://example.com/page")

        assert result is None
        mock_warn.assert_called_once()
        call_msg = mock_warn.call_args[0][0]
        assert "empty body" in call_msg


# ---------------------------------------------------------------------------
# _bot_block_reason
# ---------------------------------------------------------------------------


class TestBotBlockReason:
    def test_cloudflare_just_a_moment(self):
        html = "<html><title>Just a moment...</title></html>"
        assert _bot_block_reason(html) is not None

    def test_cloudflare_challenge_js(self):
        html = "<script>window._cf_chl_opt = {}</script>"
        assert _bot_block_reason(html) is not None

    def test_access_denied(self):
        html = "<html><title>Access Denied</title></html>"
        assert _bot_block_reason(html) is not None

    def test_access_denied_in_body_not_title_is_not_blocked(self):
        html = "<html><body>Access denied to the VIP lounge</body></html>"
        assert _bot_block_reason(html) is None

    def test_datadome(self):
        html = '<script src="https://js.datadome.co/tags.js"></script>'
        assert _bot_block_reason(html) is not None

    def test_enable_javascript_cookies(self):
        html = "<p>Enable JavaScript and cookies to continue</p>"
        assert _bot_block_reason(html) is not None

    def test_normal_html_returns_none(self):
        html = "<html><body><h1>Standup NY — Upcoming Shows</h1></body></html>"
        assert _bot_block_reason(html) is None

    def test_case_insensitive(self):
        html = "<title>JUST A MOMENT</title>"
        assert _bot_block_reason(html) is not None


# ---------------------------------------------------------------------------
# fetch_html — Playwright fallback
# ---------------------------------------------------------------------------


def _make_browser_mock(html: str = "<html>playwright-rendered</html>"):
    mock = AsyncMock()
    mock.fetch_html = AsyncMock(return_value=html)
    return mock


class TestFetchHtmlFallback:
    def setup_method(self):
        _reset_browser_cache()

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_none_response(self):
        """Non-200 → curl-cffi returns None → fallback fires."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = _make_browser_mock()

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            result = await HttpClient.fetch_html(session, "https://example.com/page")

        mock_browser.fetch_html.assert_called_once()
        assert result == "<html>playwright-rendered</html>"

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_empty_body(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="   ")
        mock_browser = _make_browser_mock()

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            result = await HttpClient.fetch_html(session, "https://example.com/page")

        mock_browser.fetch_html.assert_called_once()
        assert result == "<html>playwright-rendered</html>"

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_bot_block(self):
        bot_html = "<html><title>Just a moment...</title></html>"
        session = AsyncMock()
        session.get.return_value = _make_response(200, text=bot_html)
        mock_browser = _make_browser_mock()

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            result = await HttpClient.fetch_html(session, "https://example.com/page")

        mock_browser.fetch_html.assert_called_once()
        assert result == "<html>playwright-rendered</html>"

    @pytest.mark.asyncio
    async def test_no_fallback_for_good_html(self):
        good_html = "<html><body>Show listings here</body></html>"
        session = AsyncMock()
        session.get.return_value = _make_response(200, text=good_html)
        mock_browser = _make_browser_mock()

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            result = await HttpClient.fetch_html(session, "https://example.com/page")

        mock_browser.fetch_html.assert_not_called()
        assert result == good_html

    @pytest.mark.asyncio
    async def test_fallback_disabled_when_no_browser(self):
        """When _get_js_browser() returns None (env disabled), no fallback."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=None):
            result = await HttpClient.fetch_html(session, "https://example.com/page")

        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_returns_none_on_playwright_exception(self):
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(side_effect=RuntimeError("playwright crashed"))

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                result = await HttpClient.fetch_html(session, "https://example.com/page")

        assert result is None

    @pytest.mark.asyncio
    async def test_proxy_passed_to_playwright_fallback(self):
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = _make_browser_mock()

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            await HttpClient.fetch_html(
                session, "https://example.com/page", proxy_url="http://proxy:8080"
            )

        # The fallback receives the normalized URL, not the raw input
        from laughtrack.foundation.utilities.url import URLUtils
        expected_url = URLUtils.normalize_url("https://example.com/page")
        mock_browser.fetch_html.assert_called_once_with(
            expected_url, proxy_url="http://proxy:8080"
        )

    @pytest.mark.asyncio
    async def test_fallback_activation_logged(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="   ")
        mock_browser = _make_browser_mock()

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.info") as mock_info:
                await HttpClient.fetch_html(session, "https://example.com/page")

        mock_info.assert_called_once()
        log_msg = mock_info.call_args[0][0]
        assert "Playwright fallback" in log_msg
        assert "empty body" in log_msg


class TestBotBlockShortCircuit:
    """The per-process bot-block cache skips Playwright fallback on the
    second-and-later request to a host whose JS fallback already confirmed
    a bot-block. Eliminates the duplicate-Playwright-launch pattern seen in
    the 2026-05-31 nightly (Tixr/Etix retried each blocked URL twice within
    ~3s, burning ~12 Chromium launches × ~2-3s each = 30s of wall-clock)."""

    def setup_method(self):
        _reset_browser_cache()

    @pytest.mark.asyncio
    async def test_first_blocked_request_runs_playwright(self):
        """Cache is empty initially — first request to a host must invoke
        Playwright so we can confirm the host is actually bot-blocked."""
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="datadome challenge body")
        mock_browser = _make_browser_mock("<html>datadome challenge JS</html>")

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    await HttpClient.fetch_html(session, "https://blocked.example.com/a")

        mock_browser.fetch_html.assert_called_once()
        assert "blocked.example.com" in client_module._recent_bot_blocked_hosts

    @pytest.mark.asyncio
    async def test_second_blocked_request_skips_playwright(self):
        """After the first request confirms bot-block, a second request to
        the same host must NOT launch Playwright. This is the win."""
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="datadome challenge body")
        mock_browser = _make_browser_mock("<html>datadome challenge JS</html>")

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    await HttpClient.fetch_html(session, "https://blocked.example.com/a")
                    await HttpClient.fetch_html(session, "https://blocked.example.com/b")
                    await HttpClient.fetch_html(session, "https://blocked.example.com/c")

        # Playwright ran exactly once across three requests to the same host.
        mock_browser.fetch_html.assert_called_once()

    @pytest.mark.asyncio
    async def test_second_request_returns_curl_body_so_caller_still_sees_bot_block(self):
        """The short-circuit must return the curl response body (not None)
        so callers that re-check via _bot_block_reason still classify the
        request as bot-blocked rather than fetch-failed (preserves the
        bot_blocked / fetch_failed metric distinction in callers like
        update_club_enrichment)."""
        session = AsyncMock()
        # curl 200 with DataDome body — caller should classify as bot-block
        session.get.return_value = _make_response(200, text="datadome challenge body")
        mock_browser = _make_browser_mock("<html>datadome challenge JS</html>")

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    await HttpClient.fetch_html(session, "https://blocked.example.com/a")
                    result = await HttpClient.fetch_html(session, "https://blocked.example.com/b")

        assert _bot_block_reason(result) == "datadome"

    @pytest.mark.asyncio
    async def test_other_hosts_unaffected(self):
        """Caching one host as bot-blocked must not short-circuit other hosts."""
        session = AsyncMock()
        # Bot-block response for the first host, clean response for the second
        session.get.side_effect = [
            _make_response(403, text="datadome challenge body"),
            _make_response(200, text="<html>clean page</html>"),
        ]
        mock_browser = _make_browser_mock("<html>datadome challenge JS</html>")

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    await HttpClient.fetch_html(session, "https://blocked.example.com/a")
                    result = await HttpClient.fetch_html(session, "https://clean.example.com/a")

        assert result == "<html>clean page</html>"
        assert "blocked.example.com" in client_module._recent_bot_blocked_hosts
        assert "clean.example.com" not in client_module._recent_bot_blocked_hosts

    @pytest.mark.asyncio
    async def test_short_circuit_disabled_by_env_var(self, monkeypatch):
        """LAUGHTRACK_HTTP_BOT_BLOCK_SHORTCIRCUIT=0 disables the cache so
        every request hits Playwright. Escape hatch for debugging."""
        monkeypatch.setenv("LAUGHTRACK_HTTP_BOT_BLOCK_SHORTCIRCUIT", "0")
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="datadome challenge body")
        mock_browser = _make_browser_mock("<html>datadome challenge JS</html>")

        with patch("laughtrack.foundation.infrastructure.http.client._get_js_browser", return_value=mock_browser):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    await HttpClient.fetch_html(session, "https://blocked.example.com/a")
                    await HttpClient.fetch_html(session, "https://blocked.example.com/b")

        # Both requests must invoke Playwright because the env var disables the cache.
        assert mock_browser.fetch_html.call_count == 2


class TestPlaywrightBotBlockDiagnostic:
    """Playwright fallback that *itself* returns a bot-block page.

    Covers the gap called out in the TASK-1656 deferred finding: a WAF that
    blocks both curl-cffi and the headless browser would leave
    ``fetch_html`` returning challenge HTML and ``fetch_json`` returning None
    via the unparseable-body path, without any diagnostic distinguishing
    "persistent WAF" from "API returned unexpected HTML". The helper now
    records a ``playwright_<signature>`` on the bound ScrapeDiagnostics.
    """

    def setup_method(self):
        _reset_browser_cache()

    @pytest.mark.asyncio
    async def test_fetch_html_records_prefixed_signature_when_playwright_blocked(self):
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            ScrapeDiagnostics,
            bind_diagnostics,
            reset_diagnostics,
        )

        session = AsyncMock()
        session.get.return_value = _make_response(403)
        # Playwright returns its own Cloudflare challenge page
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(
            return_value="<html><title>Just a moment...</title></html>"
        )

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch(
                "laughtrack.foundation.infrastructure.http.client._get_js_browser",
                return_value=mock_browser,
            ):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                    with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                        await HttpClient.fetch_html(session, "https://example.com/page")
        finally:
            reset_diagnostics(token)

        assert diagnostics.bot_block_detected is True
        assert diagnostics.bot_block_signature == "playwright_just a moment"
        assert diagnostics.playwright_fallback_used is True
        assert diagnostics.bot_block_provider == "cloudflare"
        assert diagnostics.bot_block_type == "challenge"
        assert diagnostics.bot_block_source == "playwright_rendered_html"
        assert diagnostics.bot_block_stage == "playwright_fallback"

    @pytest.mark.asyncio
    async def test_fetch_json_records_prefixed_signature_when_playwright_blocked(self):
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            ScrapeDiagnostics,
            bind_diagnostics,
            reset_diagnostics,
        )

        session = AsyncMock()
        session.get.return_value = _make_response(403)
        # Playwright response is itself a DataDome challenge page — no JSON to parse
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(
            return_value='<html><body><script src="https://js.datadome.co/tags.js"></script></body></html>'
        )

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch(
                "laughtrack.foundation.infrastructure.http.client._get_js_browser",
                return_value=mock_browser,
            ):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                    with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                        result = await HttpClient.fetch_json(session, "https://example.com/api")
        finally:
            reset_diagnostics(token)

        assert result is None
        assert diagnostics.bot_block_detected is True
        assert diagnostics.bot_block_signature == "playwright_datadome"
        assert diagnostics.bot_block_provider == "datadome"
        assert diagnostics.bot_block_type == "interstitial"
        assert diagnostics.bot_block_source == "playwright_rendered_html"
        assert diagnostics.bot_block_stage == "playwright_fallback"

    @pytest.mark.asyncio
    async def test_no_prefixed_signature_when_playwright_returns_clean_content(self):
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            ScrapeDiagnostics,
            bind_diagnostics,
            reset_diagnostics,
        )

        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = _make_browser_mock("<html><body>real content</body></html>")

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch(
                "laughtrack.foundation.infrastructure.http.client._get_js_browser",
                return_value=mock_browser,
            ):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                    with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                        await HttpClient.fetch_html(session, "https://example.com/page")
        finally:
            reset_diagnostics(token)

        # curl-cffi saw a 403 (no body) so no signature was recorded there either —
        # Playwright rescued with clean HTML, so bot_block stays False.
        assert diagnostics.bot_block_detected is False
        assert diagnostics.bot_block_signature is None

    @pytest.mark.asyncio
    async def test_warn_logged_when_playwright_returns_bot_block(self):
        """On-call relies on greppable log output — pin the WARN phrasing."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(
            return_value="<html><title>Just a moment...</title></html>"
        )

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                    await HttpClient.fetch_html(session, "https://example.com/page")

        playwright_warns = [
            c for c in mock_warn.call_args_list
            if "Playwright fallback" in c.args[0] and "also returned a bot-block" in c.args[0]
        ]
        assert len(playwright_warns) == 1
        assert "just a moment" in playwright_warns[0].args[0]

    @pytest.mark.asyncio
    async def test_curl_cffi_signature_wins_when_playwright_also_blocked(self):
        """First-seen signature wins: curl-cffi's original bot block is preserved."""
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            ScrapeDiagnostics,
            bind_diagnostics,
            reset_diagnostics,
        )

        # curl-cffi returns 200 with a bot-block page (triggers fallback)
        session = AsyncMock()
        session.get.return_value = _make_response(
            200, text="<html><title>Just a moment...</title></html>"
        )
        # Playwright also returns a (different) bot-block signature
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(
            return_value='<html><body>Please <b>enable JavaScript and cookies to continue</b></body></html>'
        )

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            with patch(
                "laughtrack.foundation.infrastructure.http.client._get_js_browser",
                return_value=mock_browser,
            ):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                    with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                        await HttpClient.fetch_html(session, "https://example.com/page")
        finally:
            reset_diagnostics(token)

        assert diagnostics.bot_block_detected is True
        # curl-cffi's signature was recorded first — the playwright_ prefix does NOT overwrite it
        assert diagnostics.bot_block_signature == "just a moment"


# ---------------------------------------------------------------------------
# _get_js_browser — env-flag disable
# ---------------------------------------------------------------------------


class TestGetJsBrowser:
    def setup_method(self):
        _reset_browser_cache()

    def teardown_method(self):
        _reset_browser_cache()

    def test_returns_none_when_env_flag_disabled(self, monkeypatch):
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        result = client_module._get_js_browser()
        assert result is None

    def test_returns_none_when_playwright_not_installed(self, monkeypatch):
        """ImportError path: returns None, logs warn once, sets _BROWSER_UNAVAILABLE sentinel."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "1")
        _reset_browser_cache()

        def _raise_import(*args, **kwargs):
            raise ImportError("No module named 'playwright'")

        with patch(
            "laughtrack.foundation.infrastructure.http.client.PlaywrightBrowser",
            side_effect=_raise_import,
            create=True,
        ):
            with patch(
                "laughtrack.foundation.infrastructure.http.playwright_browser.PlaywrightBrowser",
                side_effect=_raise_import,
                create=True,
            ):
                # Patch the import inside _get_js_browser to raise ImportError
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name == "laughtrack.foundation.infrastructure.http.playwright_browser":
                        raise ImportError("No module named 'playwright'")
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=mock_import):
                    with patch(
                        "laughtrack.foundation.infrastructure.http.client.Logger.warn"
                    ) as mock_warn:
                        result = client_module._get_js_browser()

        assert result is None
        mock_warn.assert_called_once()
        # Sentinel is set — second call does not re-attempt import or re-warn
        with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn2:
            result2 = client_module._get_js_browser()
        assert result2 is None
        mock_warn2.assert_not_called()  # no repeated warning

    def test_creates_one_browser_per_worker_event_loop(self, monkeypatch):
        """Two worker loops must not share one PlaywrightBrowser instance.

        Regression for TASK-1691: scrape-all workers were all routing
        Playwright fallback through one process-global browser, so the second
        Etix/Tixr fallback could reuse a browser whose internal lock belonged
        to another worker loop and fail with ``... bound to a different event
        loop``.
        """

        class FakeLoopBoundBrowser:
            def __init__(self):
                self.launch_loop = None

            async def fetch_html(self, url: str, proxy_url=None) -> str:  # noqa: ANN001
                loop = asyncio.get_running_loop()
                if self.launch_loop is None:
                    self.launch_loop = loop
                elif self.launch_loop is not loop:
                    raise RuntimeError(
                        "<asyncio.locks.Lock object at 0x1234 [locked, waiters:4]> "
                        "is bound to a different event loop"
                    )
                return f"<html>{url}</html>"

            async def close(self) -> None:
                return None

        class FakeSession:
            async def get(self, *args, **kwargs):  # noqa: ANN002, ANN003
                return _make_response(403)

        created = []

        def _factory():
            browser = FakeLoopBoundBrowser()
            created.append(browser)
            return browser

        async def _worker(url: str) -> str:
            return await HttpClient.fetch_html(FakeSession(), url)

        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "1")
        _reset_browser_cache()

        with patch(
            "laughtrack.foundation.infrastructure.http.playwright_browser.PlaywrightBrowser",
            side_effect=_factory,
        ):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(asyncio.run, _worker("https://example.com/one")),
                    executor.submit(asyncio.run, _worker("https://example.com/two")),
                ]
                results = [future.result() for future in futures]

        assert results == [
            "<html>https://example.com/one</html>",
            "<html>https://example.com/two</html>",
        ]
        assert len(created) == 2


# ---------------------------------------------------------------------------
# close_js_browser
# ---------------------------------------------------------------------------


class TestCloseJsBrowser:
    def setup_method(self):
        _reset_browser_cache()

    def teardown_method(self):
        _reset_browser_cache()

    @pytest.mark.asyncio
    async def test_returns_early_when_browser_is_none(self):
        """close_js_browser() is a no-op when no browser has been created."""
        client_module._js_browser = None
        from laughtrack.foundation.infrastructure.http.client import close_js_browser
        await close_js_browser()  # must not raise
        assert client_module._js_browser is None

    @pytest.mark.asyncio
    async def test_returns_early_when_browser_unavailable(self):
        """close_js_browser() is a no-op when Playwright is unavailable."""
        client_module._js_browser = client_module._BROWSER_UNAVAILABLE
        from laughtrack.foundation.infrastructure.http.client import close_js_browser
        await close_js_browser()
        assert client_module._js_browser is client_module._BROWSER_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_closes_browser_and_clears_singleton(self):
        """close_js_browser() calls browser.close() and sets _js_browser to None."""
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        client_module._js_browser = mock_browser

        from laughtrack.foundation.infrastructure.http.client import close_js_browser
        await close_js_browser()

        mock_browser.close.assert_awaited_once()
        assert client_module._js_browser is None

    @pytest.mark.asyncio
    async def test_double_call_is_noop(self):
        """Calling close_js_browser() twice only closes the browser once."""
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        client_module._js_browser = mock_browser

        from laughtrack.foundation.infrastructure.http.client import close_js_browser
        await close_js_browser()
        await close_js_browser()  # second call: _js_browser is None, early return

        mock_browser.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_closes_loop_cached_browsers_and_clears_cache(self):
        mock_browser_one = MagicMock()
        mock_browser_one.close = AsyncMock()
        mock_browser_two = MagicMock()
        mock_browser_two.close = AsyncMock()

        loop_one = asyncio.get_running_loop()
        loop_two = asyncio.new_event_loop()
        client_module._js_browsers_by_loop = weakref.WeakKeyDictionary(
            {
                loop_one: mock_browser_one,
                loop_two: mock_browser_two,
            }
        )

        from laughtrack.foundation.infrastructure.http.client import close_js_browser
        await close_js_browser()

        mock_browser_one.close.assert_awaited_once()
        mock_browser_two.close.assert_awaited_once()
        assert len(client_module._js_browsers_by_loop) == 0
        loop_two.close()

    @pytest.mark.asyncio
    async def test_swallows_cross_loop_runtime_error(self):
        """close_js_browser() must not propagate ``bound to a different event loop``.

        Regression for TASK-1668 / 90-minute GHA timeout: when a worker
        thread's ``asyncio.run()`` loop created the Playwright singleton,
        the main loop calling ``close_js_browser()`` used to propagate the
        cross-loop RuntimeError up through ``_scrape_clubs_concurrently``'s
        finally block, which propagated into ``scrape_shows.main()`` and
        triggered ``sys.exit(1)`` — after which atexit handlers hung until
        the 90-minute GHA job timeout fired.  The close path now catches
        this RuntimeError so nightly teardown is resilient even if the
        PlaywrightBrowser.close() short-circuit misses an edge case.
        """
        runtime_exc = RuntimeError(
            "<asyncio.locks.Lock object at 0x1234 [locked]> "
            "is bound to a different event loop"
        )
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock(side_effect=runtime_exc)
        client_module._js_browser = mock_browser

        from laughtrack.foundation.infrastructure.http.client import close_js_browser

        with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
            # Must not raise — would crash scrape_shows orchestrator otherwise.
            await close_js_browser()

        mock_browser.close.assert_awaited_once()
        assert client_module._js_browser is None
        # Operator visibility: one WARN with the original exception's message
        # embedded so the cross-loop signature is still searchable in logs.
        mock_warn.assert_called_once()
        assert str(runtime_exc) in mock_warn.call_args[0][0]

    @pytest.mark.asyncio
    async def test_reraises_non_cross_loop_runtime_error(self):
        """Non-cross-loop RuntimeErrors from browser.close() must propagate.

        The cross-loop swallow is intentionally narrow so genuine Playwright
        transport failures (node subprocess crashes, torn-down pipes, etc.)
        remain visible to callers and nightly triage — only the known
        ``bound to a different event loop`` signature is absorbed.
        """
        transport_exc = RuntimeError("Playwright node transport closed")
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock(side_effect=transport_exc)
        client_module._js_browser = mock_browser

        from laughtrack.foundation.infrastructure.http.client import close_js_browser

        with pytest.raises(RuntimeError, match="Playwright node transport closed"):
            await close_js_browser()

        mock_browser.close.assert_awaited_once()
        # Singleton is still cleared so retries don't re-use the dead browser.
        assert client_module._js_browser is None


# ---------------------------------------------------------------------------
# fetch_json
# ---------------------------------------------------------------------------


class TestFetchJson:
    @pytest.mark.asyncio
    async def test_non_200_returns_none_and_logs_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response(500)

        with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None
        mock_warn.assert_called_once()
        call_msg = mock_warn.call_args[0][0]
        assert "500" in call_msg

    @pytest.mark.asyncio
    async def test_200_returns_json_data(self):
        session = AsyncMock()
        payload = {"events": [{"id": 1}]}
        session.get.return_value = _make_response(200, json_data=payload)

        result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result == payload

    @pytest.mark.asyncio
    async def test_network_exception_propagates_without_logging(self):
        session = AsyncMock()
        session.get.side_effect = OSError("connection refused")

        with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
            with pytest.raises(OSError):
                await HttpClient.fetch_json(session, "https://example.com/api")

        mock_warn.assert_not_called()

    @pytest.mark.asyncio
    async def test_headers_forwarded_to_session_get(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, json_data={"ok": True})
        custom_headers = {"Authorization": "Bearer token", "X-Request-ID": "abc"}

        await HttpClient.fetch_json(session, "https://example.com/api", headers=custom_headers)

        session.get.assert_called_once()
        _, kwargs = session.get.call_args
        assert kwargs.get("headers") == custom_headers

    @pytest.mark.asyncio
    async def test_logger_context_passed_to_warn_on_non_200(self):
        session = AsyncMock()
        session.get.return_value = _make_response(503)
        context = {"club": "test_club", "endpoint": "/api/shows"}

        with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
            await HttpClient.fetch_json(session, "https://example.com/api", logger_context=context)

        mock_warn.assert_called_once()
        call_context = mock_warn.call_args[0][1]
        assert call_context == context

    @pytest.mark.asyncio
    async def test_200_empty_body_returns_none_and_logs_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="")

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None
        mock_warn.assert_called_once()
        call_msg = mock_warn.call_args[0][0]
        assert "empty body" in call_msg

    @pytest.mark.asyncio
    async def test_200_whitespace_only_body_returns_none_and_logs_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="   \n  ")

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None
        mock_warn.assert_called_once()
        call_msg = mock_warn.call_args[0][0]
        assert "empty body" in call_msg

    @pytest.mark.asyncio
    async def test_200_empty_body_passes_logger_context_to_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="")
        context = {"club": "test_club", "endpoint": "/api/shows"}

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                await HttpClient.fetch_json(session, "https://example.com/api", logger_context=context)

        mock_warn.assert_called_once()
        call_context = mock_warn.call_args[0][1]
        assert call_context == context


# ---------------------------------------------------------------------------
# fetch_json — Playwright fallback
# ---------------------------------------------------------------------------


def _make_json_browser_mock(payload):
    """Build a mock PlaywrightBrowser whose fetch_html returns Chrome-wrapped JSON."""
    import json as _json_lib
    wrapped = f"<html><body><pre>{_json_lib.dumps(payload)}</pre></body></html>"
    mock = AsyncMock()
    mock.fetch_html = AsyncMock(return_value=wrapped)
    return mock


class TestFetchJsonFallback:
    def setup_method(self):
        client_module._js_browser = None

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_403(self):
        """403 response → curl-cffi returns non-200 → Playwright fallback fires."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        payload = {"events": [{"id": 42}]}
        mock_browser = _make_json_browser_mock(payload)

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        mock_browser.fetch_html.assert_called_once()
        assert result == payload

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_empty_body(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="   ")
        payload = {"ok": True}
        mock_browser = _make_json_browser_mock(payload)

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        mock_browser.fetch_html.assert_called_once()
        assert result == payload

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_bot_block(self):
        bot_html = "<html><title>Just a moment...</title></html>"
        session = AsyncMock()
        session.get.return_value = _make_response(200, text=bot_html)
        payload = {"events": []}
        mock_browser = _make_json_browser_mock(payload)

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        mock_browser.fetch_html.assert_called_once()
        assert result == payload

    @pytest.mark.asyncio
    async def test_no_fallback_for_good_json(self):
        session = AsyncMock()
        payload = {"events": [{"id": 1}]}
        session.get.return_value = _make_response(200, json_data=payload)
        mock_browser = _make_json_browser_mock({"should": "not be reached"})

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        mock_browser.fetch_html.assert_not_called()
        assert result == payload

    @pytest.mark.asyncio
    async def test_fallback_skipped_on_5xx(self):
        """500-class responses skip the fallback (server can't be rescued by a browser)."""
        session = AsyncMock()
        session.get.return_value = _make_response(502)
        mock_browser = _make_json_browser_mock({"never": "reached"})

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                result = await HttpClient.fetch_json(session, "https://example.com/api")

        mock_browser.fetch_html.assert_not_called()
        assert result is None
        # The HTTP-status warn is the only signal on-call sees for 5xx —
        # assert it so a refactor can't silently drop it.
        mock_warn.assert_called_once()
        assert "502" in mock_warn.call_args[0][0]

    @pytest.mark.asyncio
    async def test_fallback_disabled_when_env_flag_is_zero(self, monkeypatch):
        """PLAYWRIGHT_FALLBACK=0 disables the fallback symmetrically with fetch_html."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client_module._js_browser = None
        session = AsyncMock()
        session.get.return_value = _make_response(403)

        result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_returns_none_on_playwright_exception(self):
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(side_effect=RuntimeError("playwright crashed"))

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None
        # Ensure the exception message reaches the log so operators can debug.
        fallback_warns = [c for c in mock_warn.call_args_list if "Playwright fallback failed" in c.args[0]]
        assert len(fallback_warns) == 1
        assert "playwright crashed" in fallback_warns[0].args[0]

    @pytest.mark.asyncio
    async def test_fallback_returns_none_on_unparseable_body(self):
        """Rendered HTML without a <pre> block and no raw JSON → None."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(
            return_value="<html><body>Not JSON at all</body></html>"
        )

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None
        # The 'could not parse JSON' phrasing is what on-call greps for; pin it.
        parse_warns = [c for c in mock_warn.call_args_list if "could not parse JSON" in c.args[0]]
        assert len(parse_warns) == 1

    @pytest.mark.asyncio
    async def test_fallback_parses_raw_json_body(self):
        """Browser returned raw JSON (no <pre> wrapping) — still parses."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        payload = {"foo": "bar"}
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(return_value='{"foo": "bar"}')

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result == payload

    @pytest.mark.asyncio
    async def test_fallback_unescapes_html_entities_in_pre_block(self):
        """Chrome HTML-escapes special chars in the JSON viewer — unescape before parsing."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        # Chrome wraps and escapes: >, <, & become &gt;, &lt;, &amp;
        rendered = '<html><body><pre>{"note": "a &amp; b &lt; c"}</pre></body></html>'
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(return_value=rendered)

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result == {"note": "a & b < c"}

    @pytest.mark.asyncio
    async def test_proxy_passed_to_playwright_fallback(self):
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = _make_json_browser_mock({"ok": True})

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            await HttpClient.fetch_json(
                session, "https://example.com/api", proxy_url="http://proxy:8080"
            )

        from laughtrack.foundation.utilities.url import URLUtils
        expected_url = URLUtils.normalize_url("https://example.com/api")
        mock_browser.fetch_html.assert_called_once_with(
            expected_url, proxy_url="http://proxy:8080"
        )

    @pytest.mark.asyncio
    async def test_fallback_activation_logged(self):
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = _make_json_browser_mock({"ok": True})

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.info") as mock_info:
                await HttpClient.fetch_json(session, "https://example.com/api")

        mock_info.assert_called_once()
        log_msg = mock_info.call_args[0][0]
        assert "Playwright fallback" in log_msg
        assert "403" in log_msg


# ---------------------------------------------------------------------------
# _parse_json_from_rendered_html
# ---------------------------------------------------------------------------


class TestParseJsonFromRenderedHtml:
    def test_raw_json_body(self):
        from laughtrack.foundation.infrastructure.http.client import _parse_json_from_rendered_html
        assert _parse_json_from_rendered_html('{"a": 1}') == {"a": 1}

    def test_raw_json_array_body(self):
        from laughtrack.foundation.infrastructure.http.client import _parse_json_from_rendered_html
        assert _parse_json_from_rendered_html("[1, 2, 3]") == [1, 2, 3]

    def test_pre_wrapped_json(self):
        from laughtrack.foundation.infrastructure.http.client import _parse_json_from_rendered_html
        rendered = '<html><body><pre>{"x": "y"}</pre></body></html>'
        assert _parse_json_from_rendered_html(rendered) == {"x": "y"}

    def test_pre_wrapped_json_with_attributes(self):
        from laughtrack.foundation.infrastructure.http.client import _parse_json_from_rendered_html
        rendered = '<html><body><pre style="word-wrap: break-word;">{"x": 1}</pre></body></html>'
        assert _parse_json_from_rendered_html(rendered) == {"x": 1}

    def test_html_entities_unescaped(self):
        from laughtrack.foundation.infrastructure.http.client import _parse_json_from_rendered_html
        rendered = "<pre>{&quot;k&quot;: &quot;v&quot;}</pre>"
        assert _parse_json_from_rendered_html(rendered) == {"k": "v"}

    def test_returns_none_for_non_json(self):
        from laughtrack.foundation.infrastructure.http.client import _parse_json_from_rendered_html
        assert _parse_json_from_rendered_html("<html><body>plain page</body></html>") is None

    def test_returns_none_for_invalid_json_in_pre(self):
        from laughtrack.foundation.infrastructure.http.client import _parse_json_from_rendered_html
        assert _parse_json_from_rendered_html("<pre>not { valid json</pre>") is None


# ---------------------------------------------------------------------------
# allow_empty_body — per-call opt-out for empty-body fallback
# ---------------------------------------------------------------------------


class TestAllowEmptyBody:
    """HTTP-200 + empty body → return None immediately when opted in.

    Tessera's stale-event signal is HTTP 200 with an empty body: the
    browser replay returns empty too, so every stale event paid ~1–3 s
    of Chromium launch for no recovery (TASK-1672 deferred finding from
    TASK-1649). ``allow_empty_body=True`` short-circuits before the WARN
    and before ``_get_js_browser`` is touched. Non-200 and 200+bot-block
    branches are unaffected and still trigger the fallback.
    """

    def setup_method(self):
        client_module._js_browser = None

    @pytest.mark.asyncio
    async def test_fetch_json_empty_body_skips_fallback_when_opted_in(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="")
        mock_browser = _make_browser_mock()

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(
                session, "https://api.tessera.example/products/123",
                allow_empty_body=True,
            )

        assert result is None
        mock_browser.fetch_html.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_json_whitespace_only_body_skips_fallback_when_opted_in(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="   \n  ")
        mock_browser = _make_browser_mock()

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_json(
                session, "https://api.tessera.example/products/123",
                allow_empty_body=True,
            )

        assert result is None
        mock_browser.fetch_html.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_html_empty_body_skips_fallback_when_opted_in(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="")
        mock_browser = _make_browser_mock()

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await HttpClient.fetch_html(
                session, "https://example.com/page",
                allow_empty_body=True,
            )

        assert result is None
        mock_browser.fetch_html.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_json_empty_body_suppresses_warn_when_opted_in(self):
        """Callers that opt in own their own stale-event logging — no duplicate WARN from the helper."""
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="")

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=_make_browser_mock(),
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                await HttpClient.fetch_json(
                    session, "https://api.tessera.example/products/123",
                    allow_empty_body=True,
                )

        mock_warn.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_200_still_triggers_fallback_when_allow_empty_body_true(self):
        """``allow_empty_body`` must NOT widen to non-200: a 403 still needs the browser rescue."""
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        mock_browser = _make_browser_mock('<html><body><pre>{"ok": true}</pre></body></html>')

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    result = await HttpClient.fetch_json(
                        session, "https://api.tessera.example/products/123",
                        allow_empty_body=True,
                    )

        mock_browser.fetch_html.assert_called_once()
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_200_bot_block_still_triggers_fallback_when_allow_empty_body_true(self):
        """200 with a bot-block signature must still fall back — ``allow_empty_body`` is empty-only."""
        session = AsyncMock()
        session.get.return_value = _make_response(
            200, text="<html><title>Just a moment...</title></html>"
        )
        mock_browser = _make_browser_mock('<html><body><pre>{"ok": true}</pre></body></html>')

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    result = await HttpClient.fetch_json(
                        session, "https://example.com/api",
                        allow_empty_body=True,
                    )

        mock_browser.fetch_html.assert_called_once()
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_default_behavior_unchanged_when_flag_omitted(self):
        """Regression guard: without ``allow_empty_body``, empty body still WARNs and falls back."""
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="")
        mock_browser = _make_browser_mock()

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                with patch("laughtrack.foundation.infrastructure.http.client.Logger.info"):
                    await HttpClient.fetch_json(session, "https://example.com/api")

        mock_browser.fetch_html.assert_called_once()
        assert any("empty body" in c.args[0] for c in mock_warn.call_args_list)


# ---------------------------------------------------------------------------
# Cross-host redirect WARN (TASK-2562)
# ---------------------------------------------------------------------------


def _make_response_with_url(
    status_code: int,
    text: str = "",
    final_url: str = "https://example.com/page",
):
    """Build a mock curl_cffi response with an explicit ``.url`` so the
    cross-host redirect detector has a concrete final URL to inspect."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.url = final_url
    resp.json = MagicMock(return_value={})
    return resp


class TestCrossHostRedirectWarn:
    """A response whose final URL host differs from the requested host must
    emit exactly one WARN per (original_host, final_host) tuple per scrape
    run. Same-host redirects (trailing slash, http->https on same host) must
    not warn at all."""

    def setup_method(self):
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            ScrapeDiagnostics,
            bind_diagnostics,
        )

        client_module._reset_cross_host_redirect_dedup()
        # Bind a fresh diagnostics container so per-scrape dedup is exercised
        # the same way it is in production. teardown_method resets it.
        self._diag = ScrapeDiagnostics()
        self._token = bind_diagnostics(self._diag)

    def teardown_method(self):
        from laughtrack.foundation.infrastructure.http.diagnostics import (
            reset_diagnostics,
        )

        reset_diagnostics(self._token)

    @pytest.mark.asyncio
    async def test_cross_host_302_emits_exactly_one_warn(self):
        session = AsyncMock()
        # curl-cffi follows the redirect transparently; the response object's
        # .url reflects the final URL after the 302.
        session.get.return_value = _make_response_with_url(
            200, text="<html/>", final_url="https://www.example.com/page",
        )

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                await HttpClient.fetch_html(session, "https://example.com/page")

        cross_host_warns = [
            c for c in mock_warn.call_args_list
            if "Cross-host redirect" in c.args[0]
        ]
        assert len(cross_host_warns) == 1
        msg = cross_host_warns[0].args[0]
        assert "example.com" in msg
        assert "www.example.com" in msg
        assert "scraping_sources.source_url" in msg

    @pytest.mark.asyncio
    async def test_same_host_path_rewrite_does_not_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response_with_url(
            200, text="<html/>", final_url="https://example.com/page/",
        )

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                await HttpClient.fetch_html(session, "https://example.com/page")

        assert not any(
            "Cross-host redirect" in c.args[0] for c in mock_warn.call_args_list
        )

    @pytest.mark.asyncio
    async def test_same_host_scheme_upgrade_does_not_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response_with_url(
            200, text="<html/>", final_url="https://example.com/page",
        )

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                await HttpClient.fetch_html(session, "http://example.com/page")

        assert not any(
            "Cross-host redirect" in c.args[0] for c in mock_warn.call_args_list
        )

    @pytest.mark.asyncio
    async def test_repeated_cross_host_redirect_is_debounced(self):
        """A 315-fetch fan-out to the same uncanonical host must emit one
        WARN, not 315 — the TASK-2559 OTH log-flood scenario."""
        session = AsyncMock()
        session.get.return_value = _make_response_with_url(
            200, text="<html/>", final_url="https://www.example.com/page",
        )

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                for _ in range(5):
                    await HttpClient.fetch_html(session, "https://example.com/page")

        cross_host_warns = [
            c for c in mock_warn.call_args_list
            if "Cross-host redirect" in c.args[0]
        ]
        assert len(cross_host_warns) == 1
        assert self._diag.cross_host_redirects_warned == {("example.com", "www.example.com")}

    @pytest.mark.asyncio
    async def test_distinct_cross_host_pairs_each_emit_one_warn(self):
        session = AsyncMock()

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                session.get.return_value = _make_response_with_url(
                    200, text="<html/>", final_url="https://www.example.com/a",
                )
                await HttpClient.fetch_html(session, "https://example.com/a")
                session.get.return_value = _make_response_with_url(
                    200, text="<html/>", final_url="https://www.other.com/b",
                )
                await HttpClient.fetch_html(session, "https://other.com/b")

        cross_host_warns = [
            c for c in mock_warn.call_args_list
            if "Cross-host redirect" in c.args[0]
        ]
        assert len(cross_host_warns) == 2

    @pytest.mark.asyncio
    async def test_club_id_from_logger_context_appears_in_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response_with_url(
            200, text="<html/>", final_url="https://www.example.com/page",
        )

        with _NO_FALLBACK:
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
                await HttpClient.fetch_html(
                    session,
                    "https://example.com/page",
                    logger_context={"club_id": 1234},
                )

        cross_host_warns = [
            c for c in mock_warn.call_args_list
            if "Cross-host redirect" in c.args[0]
        ]
        assert len(cross_host_warns) == 1
        assert "club_id=1234" in cross_host_warns[0].args[0]
