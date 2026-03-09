"""Unit tests for HttpClient.fetch_html and fetch_json."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.foundation.infrastructure.http.client import HttpClient


def _make_response(status_code: int, text: str = "", json_data=None):
    """Build a mock curl_cffi response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=json_data if json_data is not None else {})
    return resp


# ---------------------------------------------------------------------------
# fetch_html
# ---------------------------------------------------------------------------


class TestFetchHtml:
    @pytest.mark.asyncio
    async def test_non_200_returns_none_and_logs_warn(self):
        session = AsyncMock()
        session.get.return_value = _make_response(404)

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

        result = await HttpClient.fetch_html(session, "https://example.com/page")

        assert result == "<html>hello</html>"

    @pytest.mark.asyncio
    async def test_network_exception_propagates_without_logging(self):
        session = AsyncMock()
        session.get.side_effect = ConnectionError("timeout")

        with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
            with pytest.raises(ConnectionError):
                await HttpClient.fetch_html(session, "https://example.com/page")

        mock_warn.assert_not_called()

    @pytest.mark.asyncio
    async def test_headers_forwarded_to_session_get(self):
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="<html/>")
        custom_headers = {"X-Custom": "value", "Accept-Language": "en"}

        await HttpClient.fetch_html(session, "https://example.com/page", headers=custom_headers)

        session.get.assert_called_once()
        _, kwargs = session.get.call_args
        assert kwargs.get("headers") == custom_headers

    @pytest.mark.asyncio
    async def test_logger_context_passed_to_warn_on_non_200(self):
        session = AsyncMock()
        session.get.return_value = _make_response(403)
        context = {"club": "test_club", "scraper": "test"}

        with patch("laughtrack.foundation.infrastructure.http.client.Logger.warn") as mock_warn:
            await HttpClient.fetch_html(session, "https://example.com/page", logger_context=context)

        mock_warn.assert_called_once()
        call_context = mock_warn.call_args[0][1]
        assert call_context == context


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
