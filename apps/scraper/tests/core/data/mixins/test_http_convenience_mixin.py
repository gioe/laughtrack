"""Tests for HttpConvenienceMixin.fetch_html_bare."""

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
