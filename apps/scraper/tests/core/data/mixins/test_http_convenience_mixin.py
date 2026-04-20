"""Tests for HttpConvenienceMixin.fetch_html, fetch_json, fetch_html_bare, fetch_json_list, and post_json."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.data.mixins.http_convenience_mixin import (
    HttpConvenienceMixin,
    _parse_json_from_rendered,
)


# ---------------------------------------------------------------------------
# Minimal concrete implementation
# ---------------------------------------------------------------------------


class _ConcreteMixin(HttpConvenienceMixin):
    def __init__(self, error_handler=None):
        self._club = MagicMock(timeout=30, scraping_url="https://example.com/events")
        self.rate_limiter = None
        self.error_handler = error_handler
        super().__init__()

    @property
    def club(self):
        return self._club


# ---------------------------------------------------------------------------
# fetch_json — empty-body guard
# ---------------------------------------------------------------------------


_NO_JS_FALLBACK = patch(
    "laughtrack.core.data.mixins.http_convenience_mixin._get_js_browser",
    return_value=None,
)


class TestFetchJson:
    @pytest.mark.asyncio
    async def test_returns_none_and_warns_on_empty_body(self):
        """HTTP 200 with empty body returns None and logs a warning."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with _NO_JS_FALLBACK, patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.Logger"
        ) as MockLogger:
            result = await mixin.fetch_json("https://example.com/api")

        assert result is None
        MockLogger.warn.assert_called_once()
        warning_msg = MockLogger.warn.call_args[0][0]
        assert "empty body" in warning_msg

    @pytest.mark.asyncio
    async def test_returns_none_and_warns_on_whitespace_body(self):
        """HTTP 200 with whitespace-only body is treated as empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "   "

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with _NO_JS_FALLBACK, patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.Logger"
        ) as MockLogger:
            result = await mixin.fetch_json("https://example.com/api")

        assert result is None
        MockLogger.warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_parsed_json_on_valid_body(self):
        """HTTP 200 with valid JSON body returns parsed data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"events": []}'
        mock_response.json.return_value = {"events": []}

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with _NO_JS_FALLBACK:
            result = await mixin.fetch_json("https://example.com/api")

        assert result == {"events": []}

    @pytest.mark.asyncio
    async def test_fallback_recovers_json_on_403(self):
        """HTTP 403 triggers Playwright fallback and the rendered JSON is parsed."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = ""

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        rendered = '<html><body><pre>{"events": [{"id": 1}]}</pre></body></html>'
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(return_value=rendered)

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin._get_js_browser",
            return_value=mock_browser,
        ):
            result = await mixin.fetch_json("https://example.com/api")

        mock_browser.fetch_html.assert_called_once()
        assert result == {"events": [{"id": 1}]}

    @pytest.mark.asyncio
    async def test_fallback_recovers_json_on_bot_block(self):
        """HTTP 200 with Cloudflare bot-block body triggers Playwright fallback."""
        bot_html = "<html><title>Just a moment...</title></html>"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = bot_html

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        rendered = '<html><body><pre>{"ok": true}</pre></body></html>'
        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(return_value=rendered)

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin._get_js_browser",
            return_value=mock_browser,
        ):
            result = await mixin.fetch_json("https://example.com/api")

        mock_browser.fetch_html.assert_called_once()
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_raises_on_403_when_fallback_disabled(self):
        """HTTP 403 with PLAYWRIGHT_FALLBACK disabled raises via raise_for_status.

        This preserves the pre-TASK-1649 contract so ErrorHandler.execute_with_retry
        can classify the error into NetworkError for the retry layer.
        """
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = ""
        mock_response.raise_for_status.side_effect = RuntimeError("403 Forbidden")

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with _NO_JS_FALLBACK, pytest.raises(RuntimeError, match="403"):
            await mixin.fetch_json("https://example.com/api")

    @pytest.mark.asyncio
    async def test_raises_on_5xx_without_attempting_playwright(self):
        """HTTP 5xx raises immediately without spinning up the headless browser.

        Server errors cannot be rescued by a client-side browser; attempting
        Playwright wastes 1-3s per retry. Verify raise_for_status fires and
        the browser is never consulted.
        """
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = ""
        mock_response.raise_for_status.side_effect = RuntimeError("503 Service Unavailable")

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>should_not_be_called</html>")

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin._get_js_browser",
            return_value=mock_browser,
        ), pytest.raises(RuntimeError, match="503"):
            await mixin.fetch_json("https://example.com/api")

        mock_browser.fetch_html.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_html_bare — no application headers sent
# ---------------------------------------------------------------------------


class TestFetchHtmlBare:
    @pytest.mark.asyncio
    async def test_returns_response_text(self):
        mock_response = MagicMock()
        mock_response.text = "<html>bare</html>"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mixin = _ConcreteMixin()
        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.AsyncSession",
            return_value=mock_session,
        ):
            result = await mixin.fetch_html_bare("https://example.com/calendar")

        assert result == "<html>bare</html>"

    @pytest.mark.asyncio
    async def test_no_headers_kwarg_passed_to_get(self):
        """AsyncSession.get() must be called with no extra kwargs (no headers)."""
        mock_response = MagicMock()
        mock_response.text = "<html/>"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mixin = _ConcreteMixin()
        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.AsyncSession",
            return_value=mock_session,
        ):
            await mixin.fetch_html_bare("https://example.com/page")

        # get() must be called with ONLY the URL — no headers= kwarg
        call_kwargs = mock_session.get.call_args.kwargs
        assert "headers" not in call_kwargs

    @pytest.mark.asyncio
    async def test_asyncsession_constructed_with_impersonate_only(self):
        """AsyncSession must be constructed with `impersonate` only — no `headers=` kwarg."""
        mock_response = MagicMock()
        mock_response.text = "<html/>"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mixin = _ConcreteMixin()
        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.AsyncSession",
            return_value=mock_session,
        ) as MockSession:
            await mixin.fetch_html_bare("https://example.com/page")

        _, kwargs = MockSession.call_args
        assert "impersonate" in kwargs
        assert "headers" not in kwargs

    @pytest.mark.asyncio
    async def test_uses_error_handler_when_present(self):
        """When error_handler is set, execute_with_retry should be called."""
        mock_handler = MagicMock()
        mock_handler.execute_with_retry = AsyncMock(return_value="<html>retried</html>")

        mixin = _ConcreteMixin(error_handler=mock_handler)
        result = await mixin.fetch_html_bare("https://example.com/page")

        mock_handler.execute_with_retry.assert_called_once()
        assert result == "<html>retried</html>"

    @pytest.mark.asyncio
    async def test_no_error_handler_executes_directly(self):
        """When no error_handler, the fetch should complete without retry."""
        mock_response = MagicMock()
        mock_response.text = "<html>direct</html>"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mixin = _ConcreteMixin(error_handler=None)
        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.AsyncSession",
            return_value=mock_session,
        ):
            result = await mixin.fetch_html_bare("https://example.com/page")

        assert result == "<html>direct</html>"


# ---------------------------------------------------------------------------
# fetch_json_list — narrow wrapper around fetch_json
# ---------------------------------------------------------------------------


class TestFetchJsonList:
    @pytest.mark.asyncio
    async def test_returns_list_on_list_response(self):
        """When fetch_json returns a list, fetch_json_list returns it as-is."""
        expected = [{"id": 1}, {"id": 2}]
        mixin = _ConcreteMixin()
        mixin.fetch_json = AsyncMock(return_value=expected)

        result = await mixin.fetch_json_list("https://example.com/api")

        assert result == expected

    @pytest.mark.asyncio
    async def test_returns_none_on_dict_response(self):
        """When fetch_json returns a dict, fetch_json_list returns None and logs a warning."""
        mixin = _ConcreteMixin()
        mixin.fetch_json = AsyncMock(return_value={"events": []})

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.Logger"
        ) as MockLogger:
            result = await mixin.fetch_json_list("https://example.com/api")

        assert result is None
        MockLogger.warn.assert_called_once()
        warning_msg = MockLogger.warn.call_args[0][0]
        assert "expected list" in warning_msg
        assert "dict" in warning_msg

    @pytest.mark.asyncio
    async def test_returns_none_when_fetch_json_returns_none(self):
        """When fetch_json returns None (e.g. error_handler returning None), result is None."""
        mixin = _ConcreteMixin()
        mixin.fetch_json = AsyncMock(return_value=None)

        with patch("laughtrack.core.data.mixins.http_convenience_mixin.Logger"):
            result = await mixin.fetch_json_list("https://example.com/api")

        assert result is None


# ---------------------------------------------------------------------------
# post_json — empty-body guard
# ---------------------------------------------------------------------------


class TestPostJson:
    @pytest.mark.asyncio
    async def test_returns_none_and_warns_on_empty_body(self):
        """HTTP 200 with empty body returns None and logs a warning."""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.Logger"
        ) as MockLogger:
            result = await mixin.post_json("https://example.com/api", {"key": "val"})

        assert result is None
        MockLogger.warn.assert_called_once()
        warning_msg = MockLogger.warn.call_args[0][0]
        assert "empty body" in warning_msg

    @pytest.mark.asyncio
    async def test_returns_none_and_warns_on_whitespace_body(self):
        """HTTP 200 with whitespace-only body is treated as empty."""
        mock_response = MagicMock()
        mock_response.text = "   "
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.Logger"
        ) as MockLogger:
            result = await mixin.post_json("https://example.com/api", {"key": "val"})

        assert result is None
        MockLogger.warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_parsed_json_on_valid_body(self):
        """HTTP 200 with valid JSON body returns parsed data."""
        mock_response = MagicMock()
        mock_response.text = '{"token": "abc"}'
        mock_response.json.return_value = {"token": "abc"}
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        result = await mixin.post_json("https://example.com/api", {"key": "val"})

        assert result == {"token": "abc"}


# ---------------------------------------------------------------------------
# fetch_html — delegates to HttpClient.fetch_html (Playwright fallback parity)
# ---------------------------------------------------------------------------


class TestFetchHtml:
    @pytest.mark.asyncio
    async def test_delegates_to_http_client_fetch_html(self):
        """fetch_html routes through HttpClient.fetch_html with the owned session."""
        mock_session = AsyncMock()
        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.HttpClient.fetch_html",
            new_callable=AsyncMock,
            return_value="<html>ok</html>",
        ) as mock_fetch:
            result = await mixin.fetch_html("https://example.com/page")

        assert result == "<html>ok</html>"
        mock_fetch.assert_awaited_once()
        call_args = mock_fetch.await_args
        # Positional args: (session, url)
        assert call_args.args[0] is mock_session
        assert call_args.args[1] == "https://example.com/page"

    @pytest.mark.asyncio
    async def test_forwards_headers_and_timeout_kwargs(self):
        """Caller kwargs (headers, timeout) propagate through to HttpClient.fetch_html."""
        mock_session = AsyncMock()
        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.HttpClient.fetch_html",
            new_callable=AsyncMock,
            return_value="<html/>",
        ) as mock_fetch:
            await mixin.fetch_html(
                "https://example.com/page",
                headers={"X-Custom": "v"},
                timeout=45,
            )

        kwargs = mock_fetch.await_args.kwargs
        assert kwargs.get("headers") == {"X-Custom": "v"}
        assert kwargs.get("timeout") == 45

    @pytest.mark.asyncio
    async def test_fallback_recovers_html_on_403(self):
        """HTTP 403 at the session layer triggers HttpClient's Playwright fallback."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = ""

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>rescued</html>")

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ):
            result = await mixin.fetch_html("https://example.com/page")

        assert result == "<html>rescued</html>"
        mock_browser.fetch_html.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_error_handler_when_present(self):
        """execute_with_retry wraps the delegated fetch and the wrapped closure works.

        Assert both: (1) the handler was called, and (2) invoking the wrapped
        closure drives the real HttpClient.fetch_html delegation path — this
        catches regressions where the closure is silently broken (wrong
        kwargs, session not forwarded, etc.).
        """
        captured_closure = {}

        async def capture_and_run(fn, _name):
            captured_closure["fn"] = fn
            return await fn()

        mock_handler = MagicMock()
        mock_handler.execute_with_retry = AsyncMock(side_effect=capture_and_run)

        mock_session = AsyncMock()
        mixin = _ConcreteMixin(error_handler=mock_handler)
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.HttpClient.fetch_html",
            new_callable=AsyncMock,
            return_value="<html>ok</html>",
        ) as mock_fetch:
            result = await mixin.fetch_html("https://example.com/page")

        mock_handler.execute_with_retry.assert_called_once()
        assert "fn" in captured_closure
        # The wrapped closure executed and drove the real delegation
        mock_fetch.assert_awaited_once()
        assert mock_fetch.await_args.args[0] is mock_session
        assert result == "<html>ok</html>"

    @pytest.mark.asyncio
    async def test_raises_on_non_2xx_when_fallback_disabled(self):
        """403 with no rescue raises — preserves retry-layer NetworkError contract."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = ""
        mock_response.raise_for_status.side_effect = RuntimeError("403 Forbidden")

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=None,
        ), pytest.raises(RuntimeError, match="403"):
            await mixin.fetch_html("https://example.com/page")

    @pytest.mark.asyncio
    async def test_5xx_short_circuits_without_playwright(self):
        """5xx raises immediately without invoking the headless browser."""
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.text = ""
        mock_response.raise_for_status.side_effect = RuntimeError("502 Bad Gateway")

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mock_browser = AsyncMock()
        mock_browser.fetch_html = AsyncMock(return_value="<html>nope</html>")

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.foundation.infrastructure.http.client._get_js_browser",
            return_value=mock_browser,
        ), pytest.raises(RuntimeError, match="502"):
            await mixin.fetch_html("https://example.com/page")

        mock_browser.fetch_html.assert_not_called()


# ---------------------------------------------------------------------------
# _parse_json_from_rendered — Playwright-rescued JSON extraction
# ---------------------------------------------------------------------------


class TestParseJsonFromRendered:
    def test_extracts_json_from_pre_tag(self):
        html = '<html><body><pre>{"k": 1}</pre></body></html>'
        assert _parse_json_from_rendered(html) == {"k": 1}

    def test_extracts_json_from_pre_with_attributes(self):
        html = '<html><body><pre style="color:red">{"k": 2}</pre></body></html>'
        assert _parse_json_from_rendered(html) == {"k": 2}

    def test_unescapes_html_entities_in_pre(self):
        """Chromium encodes quotes in the JSON viewer — they must round-trip."""
        html = '<pre>{&quot;k&quot;: &quot;v&quot;}</pre>'
        assert _parse_json_from_rendered(html) == {"k": "v"}

    def test_parses_raw_json_when_no_pre_tag(self):
        assert _parse_json_from_rendered('{"k": 3}') == {"k": 3}

    def test_returns_none_on_unparseable(self):
        assert _parse_json_from_rendered("<html>not json</html>") is None

    def test_returns_none_on_empty(self):
        assert _parse_json_from_rendered("") is None
        assert _parse_json_from_rendered(None) is None
