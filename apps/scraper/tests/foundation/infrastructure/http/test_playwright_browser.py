"""Unit tests for PlaywrightBrowser."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.foundation.infrastructure.http.playwright_browser import (
    PlaywrightBrowser,
    _parse_proxy,
)


# ---------------------------------------------------------------------------
# _parse_proxy
# ---------------------------------------------------------------------------


class TestParseProxy:
    def test_basic_url(self):
        result = _parse_proxy("http://host:8080")
        assert result == {"server": "http://host:8080"}

    def test_url_with_credentials(self):
        result = _parse_proxy("http://user:pass@proxy.example.com:3128")
        assert result["server"] == "http://proxy.example.com:3128"
        assert result["username"] == "user"
        assert result["password"] == "pass"

    def test_url_without_port(self):
        result = _parse_proxy("http://proxy.example.com")
        assert result["server"] == "http://proxy.example.com"
        assert "username" not in result
        assert "password" not in result


# ---------------------------------------------------------------------------
# PlaywrightBrowser.fetch_html
# ---------------------------------------------------------------------------


def _make_pw_mocks():
    """Build a mock playwright async context chain.

    Returns (mock_pw_module, mock_browser, mock_page) where:
    - mock_pw_module.async_playwright() is the async context manager
    - async_playwright().__aenter__() returns mock_pw (the pw object)
    - mock_pw.chromium.launch() returns mock_browser
    - mock_browser.new_context().new_page() returns mock_page
    """
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html>rendered</html>")
    mock_page.add_init_script = AsyncMock()
    mock_page.goto = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    # The pw object returned by `async with async_playwright() as pw:`
    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium

    # async_playwright() returns a context manager whose __aenter__ yields mock_pw
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_pw_module = MagicMock()
    mock_pw_module.async_playwright = MagicMock(return_value=mock_cm)

    return mock_pw_module, mock_browser, mock_page


def _patch_playwright(mock_pw_module):
    """Context manager that injects mock_pw_module into sys.modules."""
    return patch.dict(
        sys.modules,
        {
            "playwright": MagicMock(),
            "playwright.async_api": mock_pw_module,
        },
    )


class TestPlaywrightBrowser:
    @pytest.mark.asyncio
    async def test_returns_rendered_html(self):
        mock_pw_module, _, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            result = await browser.fetch_html("https://example.com")

        assert result == "<html>rendered</html>"

    @pytest.mark.asyncio
    async def test_stealth_script_injected(self):
        mock_pw_module, _, mock_page = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

        mock_page.add_init_script.assert_called_once()
        script = mock_page.add_init_script.call_args[0][0]
        assert "webdriver" in script

    @pytest.mark.asyncio
    async def test_proxy_applied_to_context(self):
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com", proxy_url="http://proxy:8080")

        _, kwargs = mock_browser.new_context.call_args
        assert kwargs.get("proxy") == {"server": "http://proxy:8080"}

    @pytest.mark.asyncio
    async def test_no_proxy_when_not_provided(self):
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

        _, kwargs = mock_browser.new_context.call_args
        assert kwargs.get("proxy") is None

    @pytest.mark.asyncio
    async def test_browser_closed_after_fetch(self):
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_closed_even_on_exception(self):
        mock_pw_module, mock_browser, mock_page = _make_pw_mocks()
        mock_page.goto.side_effect = RuntimeError("navigation failed")

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            with pytest.raises(RuntimeError):
                await browser.fetch_html("https://example.com")

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_goto_uses_domcontentloaded(self):
        mock_pw_module, _, mock_page = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

        _, kwargs = mock_page.goto.call_args
        assert kwargs.get("wait_until") == "domcontentloaded"

    @pytest.mark.asyncio
    async def test_context_closed_after_fetch(self):
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

        # new_context() returns mock_browser.new_context.return_value (the context mock)
        context_mock = mock_browser.new_context.return_value
        context_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_closed_even_on_exception(self):
        mock_pw_module, mock_browser, mock_page = _make_pw_mocks()
        mock_page.goto.side_effect = RuntimeError("navigation failed")

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            with pytest.raises(RuntimeError):
                await browser.fetch_html("https://example.com")

        context_mock = mock_browser.new_context.return_value
        context_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_proxy_with_credentials_parsed(self):
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html(
                "https://example.com", proxy_url="http://user:secret@proxy:3128"
            )

        _, kwargs = mock_browser.new_context.call_args
        proxy = kwargs.get("proxy")
        assert proxy["server"] == "http://proxy:3128"
        assert proxy["username"] == "user"
        assert proxy["password"] == "secret"
