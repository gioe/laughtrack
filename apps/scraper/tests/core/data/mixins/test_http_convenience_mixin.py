"""Tests for HttpConvenienceMixin.fetch_json, fetch_html_bare, and fetch_json_list."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.data.mixins.http_convenience_mixin import HttpConvenienceMixin


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


class TestFetchJson:
    @pytest.mark.asyncio
    async def test_returns_none_and_warns_on_empty_body(self):
        """HTTP 200 with empty body returns None and logs a warning."""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
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
        mock_response.text = "   "
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        with patch(
            "laughtrack.core.data.mixins.http_convenience_mixin.Logger"
        ) as MockLogger:
            result = await mixin.fetch_json("https://example.com/api")

        assert result is None
        MockLogger.warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_parsed_json_on_valid_body(self):
        """HTTP 200 with valid JSON body returns parsed data."""
        mock_response = MagicMock()
        mock_response.text = '{"events": []}'
        mock_response.json.return_value = {"events": []}
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        mixin = _ConcreteMixin()
        mixin.get_session = AsyncMock(return_value=mock_session)

        result = await mixin.fetch_json("https://example.com/api")

        assert result == {"events": []}


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
