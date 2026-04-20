"""Unit tests for HttpClient.fetch_html and fetch_json."""

import json as _json
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
        # Reset the module-level singleton between tests
        client_module._js_browser = None

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


# ---------------------------------------------------------------------------
# _get_js_browser — env-flag disable
# ---------------------------------------------------------------------------


class TestGetJsBrowser:
    def setup_method(self):
        client_module._js_browser = None

    def teardown_method(self):
        # Restore sentinel state so other tests aren't affected
        client_module._js_browser = None

    def test_returns_none_when_env_flag_disabled(self, monkeypatch):
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        result = client_module._get_js_browser()
        assert result is None

    def test_returns_none_when_playwright_not_installed(self, monkeypatch):
        """ImportError path: returns None, logs warn once, sets _BROWSER_UNAVAILABLE sentinel."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "1")
        client_module._js_browser = None

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


# ---------------------------------------------------------------------------
# close_js_browser
# ---------------------------------------------------------------------------


class TestCloseJsBrowser:
    def setup_method(self):
        client_module._js_browser = None

    def teardown_method(self):
        client_module._js_browser = None

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
            result = await HttpClient.fetch_json(session, "https://example.com/api")

        mock_browser.fetch_html.assert_not_called()
        assert result is None

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
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None

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
            with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn"):
                result = await HttpClient.fetch_json(session, "https://example.com/api")

        assert result is None

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
