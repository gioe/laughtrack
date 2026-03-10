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
    async def test_browser_not_closed_after_fetch(self):
        """Chromium process stays alive after a single fetch (reuse across calls)."""
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_browser_not_closed_on_page_exception(self):
        """Chromium process stays alive even when page navigation raises."""
        mock_pw_module, mock_browser, mock_page = _make_pw_mocks()
        mock_page.goto.side_effect = RuntimeError("navigation failed")

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            with pytest.raises(RuntimeError):
                await browser.fetch_html("https://example.com")

        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_fetch_launches_browser_only_once(self):
        """Two concurrent fetch_html calls must not start two Chromium processes."""
        import asyncio as _asyncio
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        mock_pw_chromium = mock_pw_module.async_playwright.return_value.__aenter__.return_value.chromium

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await _asyncio.gather(
                browser.fetch_html("https://example.com/a"),
                browser.fetch_html("https://example.com/b"),
            )

        mock_pw_chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_launched_once_across_multiple_fetches(self):
        """Chromium is launched exactly once regardless of how many pages are fetched.

        This verifies the per-call latency improvement: the old implementation
        called chromium.launch() on every fetch_html invocation; the new
        implementation calls it only on the first call.
        """
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        # Each new_context call returns the same mock_context, which is fine for the test
        mock_pw_chromium = mock_pw_module.async_playwright.return_value.__aenter__.return_value.chromium

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com/page1")
            await browser.fetch_html("https://example.com/page2")
            await browser.fetch_html("https://example.com/page3")

        mock_pw_chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_close_stops_browser(self):
        """await browser.close() closes the Chromium process and Playwright context."""
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        mock_cm = mock_pw_module.async_playwright.return_value

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")
            await browser.close()

        mock_browser.close.assert_called_once()
        mock_cm.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_explicit_close_is_idempotent(self):
        """Calling close() multiple times does not raise."""
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")
            await browser.close()
            await browser.close()  # second call is a no-op

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

    def test_atexit_handler_registered(self):
        """atexit.register is called with _atexit_close when a PlaywrightBrowser is instantiated."""
        import weakref
        from laughtrack.foundation.infrastructure.http.playwright_browser import _atexit_close

        with patch("atexit.register") as mock_register:
            browser = PlaywrightBrowser()

        mock_register.assert_called_once()
        args = mock_register.call_args[0]
        assert args[0] is _atexit_close
        assert isinstance(args[1], weakref.ref)
        assert args[1]() is browser

    @pytest.mark.asyncio
    async def test_concurrent_close_and_fetch_does_not_raise(self):
        """close() called concurrently with fetch_html() must not raise AttributeError.

        fetch_html holds _browser_lock for its entire body, so close() cannot
        clear self._browser between _launch_if_needed_locked() and new_context()
        (the TOCTOU window).  Instead, close() waits until the fetch completes
        before tearing down the browser.
        """
        import asyncio as _asyncio
        mock_pw_module, mock_browser, _ = _make_pw_mocks()

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            # Neither coroutine should raise — gather propagates exceptions by default.
            await _asyncio.gather(
                browser.fetch_html("https://example.com"),
                browser.close(),
            )

        # fetch_html always goes first in gather order; close() runs after and
        # clears the browser state.
        assert browser._browser is None
        assert browser._pw_cm is None
        assert browser._pw is None

    @pytest.mark.asyncio
    async def test_close_waits_for_active_fetch_before_clearing_browser(self):
        """close() must not clear self._browser while fetch_html is using it.

        Uses asyncio events to force the race: close() is triggered mid-fetch
        (after _launch_if_needed_locked but before new_context returns).
        With the lock held throughout fetch_html, close() is blocked until the
        fetch completes — no AttributeError must be raised.
        """
        import asyncio as _asyncio
        mock_pw_module, mock_browser, _ = _make_pw_mocks()

        fetch_entered_lock = _asyncio.Event()

        async def slow_new_context(*args, **kwargs):
            # Signal that we are inside the lock (browser in use), then yield so
            # the close() task can attempt to acquire the lock (it should block).
            fetch_entered_lock.set()
            await _asyncio.sleep(0)
            return mock_browser.new_context.return_value

        mock_browser.new_context.side_effect = slow_new_context

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()

            async def deferred_close():
                # Wait until fetch_html has entered the critical section, then
                # try to close.  With the fix, close() blocks until the fetch
                # releases the lock — no AttributeError is raised.
                await fetch_entered_lock.wait()
                await browser.close()

            result, _ = await _asyncio.gather(
                browser.fetch_html("https://example.com"),
                deferred_close(),
            )

        assert result == "<html>rendered</html>"
        assert browser._browser is None  # close() ran after fetch completed
