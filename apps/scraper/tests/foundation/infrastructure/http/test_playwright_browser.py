"""Unit tests for PlaywrightBrowser."""

import asyncio
import concurrent.futures
import logging
import sys
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.foundation.infrastructure.http import playwright_browser as _pb_mod
from laughtrack.foundation.infrastructure.http.playwright_browser import (
    PlaywrightBrowser,
    _QuietShutdownFilter,
    _install_quiet_shutdown_filter,
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
        """Two fetch_html calls must not start two Chromium processes.

        Under the current implementation fetch_html holds _browser_lock for its
        entire body, so the two gather tasks are serialized rather than truly
        concurrent.  The important invariant verified here is that Chromium is
        launched exactly once regardless of the order/serialization.
        """
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
    async def test_launch_loop_stored_on_first_fetch(self):
        """_launch_loop is set to the running event loop on the first fetch."""
        mock_pw_module, _, _ = _make_pw_mocks()
        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            assert browser._launch_loop is None
            await browser.fetch_html("https://example.com")

        assert browser._launch_loop is asyncio.get_running_loop()

    def test_atexit_close_uses_run_coroutine_threadsafe_when_loop_running(self):
        """_atexit_close uses run_coroutine_threadsafe when the original loop is still running."""
        import weakref
        from laughtrack.foundation.infrastructure.http.playwright_browser import _atexit_close

        close_coro = MagicMock()

        # Use a plain object so we can set arbitrary attributes freely
        class FakeBrowser:
            _browser = MagicMock()
            _launch_loop = MagicMock()
            def close(self):  # noqa: ANN201
                return close_coro

        fake = FakeBrowser()
        fake._launch_loop.is_running.return_value = True

        mock_future = MagicMock()
        mock_future.result = MagicMock(return_value=None)

        with patch(
            "asyncio.run_coroutine_threadsafe",
            return_value=mock_future,
        ) as mock_rcts:
            ref = weakref.ref(fake)
            _atexit_close(ref)

        mock_rcts.assert_called_once_with(close_coro, fake._launch_loop)
        mock_future.result.assert_called_once_with(timeout=10)

    def test_atexit_close_uses_new_loop_when_original_loop_not_running(self):
        """_atexit_close falls back to a new event loop when the original loop is stopped."""
        import weakref
        from laughtrack.foundation.infrastructure.http.playwright_browser import _atexit_close

        mock_browser_obj = MagicMock()
        mock_browser_obj._browser = MagicMock()

        mock_loop = MagicMock()
        mock_loop.is_running.return_value = False
        mock_browser_obj._launch_loop = mock_loop

        close_coro = MagicMock()
        mock_browser_obj.close = MagicMock(return_value=close_coro)

        new_loop = MagicMock()
        wait_for_sentinel = MagicMock()
        # Use new= to force MagicMock instead of AsyncMock (asyncio.wait_for is async,
        # so patch() would auto-create AsyncMock whose call returns a coroutine, not the sentinel)
        mock_wf = MagicMock(return_value=wait_for_sentinel)

        with (
            patch("asyncio.new_event_loop", return_value=new_loop) as mock_nel,
            patch("asyncio.wait_for", new=mock_wf),
            patch("asyncio.run_coroutine_threadsafe") as mock_rcts,
        ):
            ref = weakref.ref(mock_browser_obj)
            _atexit_close(ref)

        mock_nel.assert_called_once()
        mock_wf.assert_called_once_with(close_coro, timeout=10)
        new_loop.run_until_complete.assert_called_once_with(wait_for_sentinel)
        new_loop.close.assert_called_once()
        mock_rcts.assert_not_called()

    def test_atexit_close_uses_new_loop_when_launch_loop_is_none(self):
        """_atexit_close falls back to a new loop when _launch_loop was never set."""
        import weakref
        from laughtrack.foundation.infrastructure.http.playwright_browser import _atexit_close

        mock_browser_obj = MagicMock()
        mock_browser_obj._browser = MagicMock()
        mock_browser_obj._launch_loop = None

        close_coro = MagicMock()
        mock_browser_obj.close = MagicMock(return_value=close_coro)

        new_loop = MagicMock()
        wait_for_sentinel = MagicMock()
        mock_wf = MagicMock(return_value=wait_for_sentinel)

        with (
            patch("asyncio.new_event_loop", return_value=new_loop),
            patch("asyncio.wait_for", new=mock_wf),
            patch("asyncio.run_coroutine_threadsafe") as mock_rcts,
        ):
            ref = weakref.ref(mock_browser_obj)
            _atexit_close(ref)

        mock_wf.assert_called_once_with(close_coro, timeout=10)
        new_loop.run_until_complete.assert_called_once_with(wait_for_sentinel)
        mock_rcts.assert_not_called()

    def test_atexit_close_calls_close_when_browser_is_none_but_pw_cm_is_set(self):
        """_atexit_close still calls close() when _browser is None but _pw_cm is set.

        This is the partial-launch scenario: async_playwright().__aenter__() succeeded
        but chromium.launch() failed, leaving _pw_cm non-None and _browser None.
        The old guard 'if browser is None or browser._browser is None: return' would
        have skipped close(), leaking the _pw_cm resource.
        """
        import weakref
        from laughtrack.foundation.infrastructure.http.playwright_browser import _atexit_close

        mock_browser_obj = MagicMock()
        mock_browser_obj._browser = None          # launch failed / not yet launched
        mock_browser_obj._pw_cm = MagicMock()     # context manager was entered
        mock_browser_obj._launch_loop = None

        close_coro = MagicMock()
        mock_browser_obj.close = MagicMock(return_value=close_coro)

        new_loop = MagicMock()
        wait_for_sentinel = MagicMock()
        mock_wf = MagicMock(return_value=wait_for_sentinel)

        with (
            patch("asyncio.new_event_loop", return_value=new_loop),
            patch("asyncio.wait_for", new=mock_wf),
            patch("asyncio.run_coroutine_threadsafe") as mock_rcts,
        ):
            ref = weakref.ref(mock_browser_obj)
            _atexit_close(ref)

        # close() must be called so _pw_cm.__aexit__ has a chance to run
        mock_browser_obj.close.assert_called_once()
        mock_wf.assert_called_once_with(close_coro, timeout=10)
        new_loop.run_until_complete.assert_called_once_with(wait_for_sentinel)
        mock_rcts.assert_not_called()

    def test_atexit_close_else_branch_tolerates_timeout(self):
        """_atexit_close else branch does not hang when close() exceeds 10s timeout."""
        import weakref
        from laughtrack.foundation.infrastructure.http.playwright_browser import _atexit_close

        mock_browser_obj = MagicMock()
        mock_browser_obj._browser = MagicMock()
        mock_browser_obj._launch_loop = MagicMock()
        mock_browser_obj._launch_loop.is_running.return_value = False

        close_coro = MagicMock()
        mock_browser_obj.close = MagicMock(return_value=close_coro)

        new_loop = MagicMock()
        new_loop.run_until_complete.side_effect = asyncio.TimeoutError()

        with (
            patch("asyncio.new_event_loop", return_value=new_loop),
            patch("asyncio.run_coroutine_threadsafe") as mock_rcts,
        ):
            ref = weakref.ref(mock_browser_obj)
            _atexit_close(ref)  # must not raise

        new_loop.close.assert_called_once()  # finally block always runs
        mock_rcts.assert_not_called()

    def test_atexit_close_does_not_raise_when_future_times_out(self):
        """_atexit_close silently absorbs a TimeoutError from future.result()."""
        import weakref
        from laughtrack.foundation.infrastructure.http.playwright_browser import _atexit_close

        close_coro = MagicMock()

        class FakeBrowser:
            _browser = MagicMock()
            _launch_loop = MagicMock()
            def close(self):  # noqa: ANN201
                return close_coro

        fake = FakeBrowser()
        fake._launch_loop.is_running.return_value = True

        mock_future = MagicMock()
        mock_future.result.side_effect = concurrent.futures.TimeoutError()

        with patch("asyncio.run_coroutine_threadsafe", return_value=mock_future):
            ref = weakref.ref(fake)
            _atexit_close(ref)  # must not raise

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

    @pytest.mark.asyncio
    async def test_fetch_after_close_relaunches_browser(self):
        """fetch_html called after close() must re-launch the browser without raising.

        close() sets self._browser = None; a subsequent fetch_html should
        re-enter _launch_if_needed_locked and create a fresh Chromium process.
        """
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        mock_pw_chromium = mock_pw_module.async_playwright.return_value.__aenter__.return_value.chromium

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com/first")
            await browser.close()
            assert browser._browser is None
            # Second fetch after close() should succeed and re-launch.
            result = await browser.fetch_html("https://example.com/second")

        assert result == "<html>rendered</html>"
        # Chromium launched twice: once before close(), once after.
        assert mock_pw_chromium.launch.call_count == 2


# ---------------------------------------------------------------------------
# _QuietShutdownFilter — silences benign Playwright shutdown noise
# ---------------------------------------------------------------------------


def _make_record(msg: str, exc: Optional[Exception] = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="asyncio",
        level=logging.ERROR,
        pathname=__file__,
        lineno=0,
        msg=msg,
        args=(),
        exc_info=(type(exc), exc, None) if exc is not None else None,
    )
    return record


class TestQuietShutdownFilter:
    def test_drops_record_with_matching_message(self):
        f = _QuietShutdownFilter()
        record = _make_record("Exception in callback: Event loop is closed")
        assert f.filter(record) is False

    def test_drops_record_with_matching_exc_info(self):
        f = _QuietShutdownFilter()
        record = _make_record("Exception in callback", RuntimeError("Event loop is closed"))
        assert f.filter(record) is False

    def test_keeps_unrelated_record(self):
        f = _QuietShutdownFilter()
        record = _make_record("Task was destroyed but it is pending")
        assert f.filter(record) is True

    def test_keeps_unrelated_exception(self):
        f = _QuietShutdownFilter()
        record = _make_record("Exception in callback", ValueError("something else"))
        assert f.filter(record) is True

    def test_keeps_message_mentioning_pattern_without_callback_prefix(self):
        """A debug/info line that mentions the phrase but is not a callback error must pass."""
        f = _QuietShutdownFilter()
        record = _make_record("Loop state: Event loop is closed after drain")
        assert f.filter(record) is True

    def test_keeps_non_runtime_error_with_matching_string(self):
        """Filter requires exc type to be RuntimeError exactly."""
        f = _QuietShutdownFilter()
        record = _make_record("Exception in callback", ValueError("Event loop is closed"))
        assert f.filter(record) is True


class TestInstallQuietShutdownFilter:
    def setup_method(self):
        # Reset global install flag and strip any prior instance from the logger
        # so each test starts from a clean slate.
        _pb_mod._quiet_filter_installed = False
        logger = logging.getLogger("asyncio")
        for filt in list(logger.filters):
            if isinstance(filt, _QuietShutdownFilter):
                logger.removeFilter(filt)

    def teardown_method(self):
        logger = logging.getLogger("asyncio")
        for filt in list(logger.filters):
            if isinstance(filt, _QuietShutdownFilter):
                logger.removeFilter(filt)
        _pb_mod._quiet_filter_installed = False

    def test_install_adds_filter_to_asyncio_logger(self):
        _install_quiet_shutdown_filter()
        filters = logging.getLogger("asyncio").filters
        assert any(isinstance(f, _QuietShutdownFilter) for f in filters)

    def test_install_is_idempotent(self):
        _install_quiet_shutdown_filter()
        _install_quiet_shutdown_filter()
        _install_quiet_shutdown_filter()
        filters = logging.getLogger("asyncio").filters
        count = sum(1 for f in filters if isinstance(f, _QuietShutdownFilter))
        assert count == 1

    def test_constructing_browser_installs_filter(self):
        PlaywrightBrowser()
        filters = logging.getLogger("asyncio").filters
        assert any(isinstance(f, _QuietShutdownFilter) for f in filters)


# ---------------------------------------------------------------------------
# close() — loop mismatch detection
# ---------------------------------------------------------------------------


class TestCloseLoopMismatch:
    @pytest.mark.asyncio
    async def test_close_clears_state_without_awaiting_when_launch_loop_closed(self):
        """If _launch_loop is closed, close() clears state without awaiting browser.close()."""
        mock_pw_module, mock_browser, _ = _make_pw_mocks()

        # Replace the mocks' close with an AsyncMock that would hang forever
        # if awaited — proving we skipped the graceful path.
        async def hang(*_a, **_kw):
            await asyncio.sleep(60)

        mock_browser.close = AsyncMock(side_effect=hang)
        mock_cm = mock_pw_module.async_playwright.return_value
        mock_cm.__aexit__ = AsyncMock(side_effect=hang)

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

            # Simulate the worker-thread scenario: launch_loop points at a
            # now-closed loop that is NOT the current running loop.
            dead_loop = asyncio.new_event_loop()
            dead_loop.close()
            browser._launch_loop = dead_loop

            # Should return quickly (no hang) and clear state.
            await asyncio.wait_for(browser.close(), timeout=1)

        assert browser._browser is None
        assert browser._pw_cm is None
        assert browser._pw is None
        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_clears_state_when_launch_loop_is_different_running_loop(self):
        """If _launch_loop is a different (still-alive) loop, also skip graceful close."""
        mock_pw_module, mock_browser, _ = _make_pw_mocks()

        async def hang(*_a, **_kw):
            await asyncio.sleep(60)

        mock_browser.close = AsyncMock(side_effect=hang)

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")

            other_loop = asyncio.new_event_loop()
            try:
                browser._launch_loop = other_loop
                await asyncio.wait_for(browser.close(), timeout=1)
            finally:
                other_loop.close()

        assert browser._browser is None
        mock_browser.close.assert_not_called()


# ---------------------------------------------------------------------------
# close() shutdown-step timeouts
# ---------------------------------------------------------------------------


class TestCloseStepTimeouts:
    @pytest.mark.asyncio
    async def test_close_clears_state_when_browser_close_times_out(self):
        """A hung browser.close() must not leave _browser set or block forever."""
        mock_pw_module, mock_browser, _ = _make_pw_mocks()

        async def hang(*_a, **_kw):
            await asyncio.sleep(60)  # would exceed _CLOSE_STEP_TIMEOUT (10s)

        mock_browser.close = AsyncMock(side_effect=hang)

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")
            # Patch the constant down to keep the test quick
            with patch(
                "laughtrack.foundation.infrastructure.http.playwright_browser._CLOSE_STEP_TIMEOUT",
                0.05,
            ):
                await browser.close()

        # Even though browser.close() timed out, the state is cleared and
        # close() returned without raising.
        assert browser._browser is None
        assert browser._pw_cm is None

    @pytest.mark.asyncio
    async def test_close_clears_state_when_pw_aexit_times_out(self):
        """A hung playwright shutdown still results in cleared state."""
        mock_pw_module, mock_browser, _ = _make_pw_mocks()
        mock_cm = mock_pw_module.async_playwright.return_value

        async def hang(*_a, **_kw):
            await asyncio.sleep(60)

        mock_cm.__aexit__ = AsyncMock(side_effect=hang)

        with _patch_playwright(mock_pw_module):
            browser = PlaywrightBrowser()
            await browser.fetch_html("https://example.com")
            with patch(
                "laughtrack.foundation.infrastructure.http.playwright_browser._CLOSE_STEP_TIMEOUT",
                0.05,
            ):
                await browser.close()

        assert browser._browser is None
        assert browser._pw_cm is None
        assert browser._pw is None
