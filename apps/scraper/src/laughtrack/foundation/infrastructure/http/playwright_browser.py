"""Playwright-based headless browser for JS-rendered pages.

PlaywrightBrowser is the concrete implementation of the JSBrowser port.
It is used exclusively as the automatic fallback inside HttpClient.fetch_html
when curl-cffi returns an empty body or a known bot-block response.

Playwright is *lazy-imported* — the package is only loaded at the moment the
first fallback is triggered, so scrapers that never encounter a bot-block page
pay zero import overhead.

The Chromium process is launched once on first use and reused across all
subsequent fetch_html calls.  Call ``await browser.close()`` to shut it down
explicitly; an ``atexit`` handler provides a best-effort shutdown on process exit.

Atexit cleanup and asyncio event loop safety
--------------------------------------------
Playwright browser and context objects are bound to the event loop on which they
were created.  When ``atexit`` fires *during* ``asyncio.run()`` shutdown (i.e.
while the original loop is still running but tearing down), calling
``asyncio.new_event_loop().run_until_complete(browser.close())`` runs
``close()`` on a *different* loop.  Playwright's internal transport may reject
this, leaving the Chromium process alive after the scraper exits.

``_atexit_close`` avoids this by inspecting the loop that was current when the
browser was first launched (``_launch_loop``):

* **Loop still running** — schedules ``close()`` on the original loop via
  ``asyncio.run_coroutine_threadsafe`` and blocks until it completes.  This
  path is taken when atexit fires during ``asyncio.run()`` shutdown.
* **Loop not running / never set** — drops references without calling
  ``close()`` on a fresh loop.  ``_browser_lock`` and Playwright's internal
  futures remain bound to the dead launch loop, so driving ``close()`` through
  a new loop would either raise ``RuntimeError('... bound to a different event
  loop')`` or hang.  The Chromium subprocess is reaped by the OS at Python
  process exit — acceptable for the scraper's short-lived CLI invocations.

Callers should prefer ``await browser.close()`` for deterministic shutdown.
The atexit handler is a last-resort safety net only.
"""

import asyncio
import atexit
import concurrent.futures
import logging
import weakref
from typing import Optional
from urllib.parse import urlparse

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils

# ---------------------------------------------------------------------------
# Stealth script injected before every page navigation
# ---------------------------------------------------------------------------

# Runs as a bare script block (not wrapped in a function), so statements
# execute immediately in the page's context before any other script runs.
_STEALTH_SCRIPT = """
// Remove the webdriver automation marker
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
});

// Spoof plugin list — empty plugins is a clear automation signal
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const fakePlugins = [
            { name: 'Chrome PDF Plugin' },
            { name: 'Chrome PDF Viewer' },
            { name: 'Native Client' },
        ];
        fakePlugins.length = 3;
        return fakePlugins;
    },
    configurable: true,
});

// Realistic language list
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true,
});

// Canvas fingerprint noise — add imperceptible jitter to getImageData output
(function () {
    const orig = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function () {
        const imgData = orig.apply(this, arguments);
        for (let i = 0; i < imgData.data.length; i += 100) {
            imgData.data[i] = (imgData.data[i] + (Math.random() > 0.5 ? 1 : 0)) & 0xff;
        }
        return imgData;
    };
})();
"""

# Realistic Chrome 124 macOS user-agent to match the curl-cffi impersonation
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Per-step shutdown timeout in close(): the outer close_js_browser() in the
# scraping service grants 30s overall; bounding each step at 10s leaves
# headroom and prevents a single hung step from triggering the outer warning.
_CLOSE_STEP_TIMEOUT = 10

# Chromium launch flags. --disable-blink-features=AutomationControlled removes
# the ``navigator.webdriver`` flag at the Blink layer (not just via the stealth
# init script). AWS WAF's passive JS challenge inspects this flag before
# signing its mp_verify payload; without the launch flag the signed payload is
# rejected and the WAF escalates to an interactive CAPTCHA, leaving Playwright
# stuck on the challenge page. Applies to all contexts — Cloudflare's "Just a
# moment" challenge is unaffected by this flag.
_LAUNCH_ARGS: tuple[str, ...] = (
    "--disable-blink-features=AutomationControlled",
)

# Markers present in AWS WAF passive JS challenge pages. When the initial
# ``page.goto(..., wait_until='domcontentloaded')`` resolves, the challenge
# script is still executing — the rendered HTML contains these globals but not
# the real content. fetch_html waits briefly for the challenge to complete
# (cookie set, JS reload) before returning.
_AWS_WAF_MARKERS: tuple[str, ...] = (
    "awsWafCookieDomainList",
    "gokuProps",
)

# Maximum time to wait for the AWS WAF passive challenge to resolve after
# the initial DOMContentLoaded. 8s comfortably covers the typical 1-3s
# challenge + reload path; on timeout, fetch_html returns whatever HTML is
# present and the caller's bot-block detector handles the rest.
_WAF_CHALLENGE_WAIT_MS = 8_000


def _parse_proxy(proxy_url: str) -> dict:
    """Convert a proxy URL string to Playwright's proxy dict format.

    Playwright expects ``{"server": "http://host:port", "username": ..., "password": ...}``.
    """
    try:
        parsed = urlparse(proxy_url)
        server = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            server = f"{server}:{parsed.port}"
        proxy_dict: dict = {"server": server}
        if parsed.username:
            proxy_dict["username"] = parsed.username
        if parsed.password:
            proxy_dict["password"] = parsed.password
        return proxy_dict
    except Exception:
        return {"server": proxy_url}


class _QuietShutdownFilter(logging.Filter):
    """Drop benign 'Event loop is closed' noise from the asyncio logger.

    The scraper runs each club inside a worker thread that owns its own
    ``asyncio.run()`` loop, while the shared ``PlaywrightBrowser`` singleton
    outlives that worker and is closed later on the main loop.  Playwright's
    internal connection futures remain bound to the (now-closed) worker loop,
    and the cancellation cascade scheduled during main-loop teardown calls
    ``future.cancel()`` on those closed loops — raising
    ``RuntimeError('Event loop is closed')``.

    The default asyncio exception handler logs these at ERROR level via
    ``logging.getLogger('asyncio')``, producing cosmetic noise that drowns out
    real failures in shared logs.  A logging filter is used here (rather than
    ``loop.set_exception_handler``) because the error surfaces on whichever
    loop runs the callback — which is not necessarily the loop the browser was
    launched on — making a per-loop handler unreliable.
    """

    _PATTERN = "Event loop is closed"

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        # Narrow match: asyncio's default exception handler emits records with
        # the message prefix "Exception in callback" when a callback raises.
        # Requiring a RuntimeError whose str() contains the pattern avoids
        # silencing unrelated future asyncio log calls that happen to mention
        # "Event loop is closed" (e.g. debug lines about loop state).
        exc_info = record.exc_info
        if (
            exc_info
            and exc_info[0] is RuntimeError
            and exc_info[1] is not None
            and self._PATTERN in str(exc_info[1])
        ):
            return False
        # Fallback: some asyncio callsites pass the error via the formatted
        # message string without exc_info (e.g. "Task exception was never
        # retrieved").  Require the "Exception in callback" prefix so unrelated
        # log lines aren't dropped.
        msg = record.getMessage()
        if self._PATTERN in msg and "Exception in callback" in msg:
            return False
        return True


_quiet_filter_installed = False


def _install_quiet_shutdown_filter() -> None:
    """Attach the quiet-shutdown filter to the asyncio logger exactly once."""
    global _quiet_filter_installed
    if _quiet_filter_installed:
        return
    logging.getLogger("asyncio").addFilter(_QuietShutdownFilter())
    _quiet_filter_installed = True


def _atexit_close(browser_ref: "weakref.ref[PlaywrightBrowser]") -> None:
    """Best-effort synchronous shutdown of the Playwright browser on process exit.

    Schedules ``close()`` on the original event loop when it is still running
    (e.g., during ``asyncio.run()`` teardown), so Playwright objects are closed
    on the same loop that created them.  When the launch loop is no longer
    running (or was never set) drops references without calling ``close()`` —
    driving ``close()`` through a fresh loop would hit the same cross-loop
    Lock error the main ``close()`` path now short-circuits, and Chromium is
    reaped by the OS when the process exits shortly after.
    """
    browser = browser_ref()
    if browser is None:
        return
    try:
        launch_loop = browser._launch_loop
        if launch_loop is not None and launch_loop.is_running():
            # The original loop is still running (shutdown phase of asyncio.run()).
            # Submit close() onto that loop from this thread and block until done.
            future = asyncio.run_coroutine_threadsafe(browser.close(), launch_loop)
            try:
                # close() acquires _browser_lock; if an active fetch_html holds
                # it, we may block here until the fetch completes.  The 10-second
                # timeout prevents an indefinite hang — prefer explicit
                # ``await browser.close()`` before the loop exits.
                future.result(timeout=10)
            except concurrent.futures.TimeoutError:
                pass
        else:
            # Original loop is done.  A fresh loop cannot await browser.close()
            # because _browser_lock and Playwright's internal futures are still
            # bound to the dead launch_loop — acquiring the lock would raise
            # (or hang).  close() also short-circuits on loop mismatch now, so
            # driving it through a new loop is pointless.  Drop references and
            # let the OS reap Chromium at process exit.
            browser._browser = None
            browser._pw_cm = None
            browser._pw = None
    except Exception:
        pass


class PlaywrightBrowser:
    """Playwright headless browser for fetching JS-rendered pages.

    Chromium is launched once on the first ``fetch_html`` call and reused for
    all subsequent calls.  This avoids the 1–3 s per-call launch penalty when
    multiple bot-blocked pages need to be fetched in the same scraping run.

    A fresh browser *context* (and page) is created for every ``fetch_html``
    call so that cookies and state do not leak between requests.

    Applies stealth patches on every page context to reduce bot-detection
    false positives:
    - Removes ``navigator.webdriver``
    - Spoofs ``navigator.plugins`` and ``navigator.languages``
    - Adds imperceptible canvas fingerprint noise

    Usage::

        browser = PlaywrightBrowser()
        html = await browser.fetch_html("https://example.com/events")
        # … more fetches reuse the same Chromium process …
        await browser.close()
    """

    def __init__(
        self,
        viewport_width: int = 1280,
        viewport_height: int = 800,
        locale: str = "en-US",
        timeout_ms: int = 30_000,
    ) -> None:
        self._viewport = {"width": viewport_width, "height": viewport_height}
        self._locale = locale
        self._timeout_ms = timeout_ms

        # Lazy browser state — populated by _launch_if_needed_locked()
        self._pw_cm: Optional[object] = None   # async_playwright() context manager
        self._pw: Optional[object] = None      # Playwright object (pw in `async with ... as pw`)
        self._browser: Optional[object] = None # Browser instance
        # Event loop on which Chromium was launched; used by _atexit_close to
        # schedule close() on the correct loop (see module docstring).
        self._launch_loop: Optional[asyncio.AbstractEventLoop] = None
        # Serializes browser launch, the entire fetch_html body, and close() to
        # prevent TOCTOU races between active fetches and concurrent close() calls.
        # fetch_html calls are therefore serialized; concurrent callers queue up.
        self._browser_lock = asyncio.Lock()

        # Install the logging filter once at construction so the noise is
        # silenced regardless of which loop eventually raises it.
        _install_quiet_shutdown_filter()

        # Register best-effort cleanup on process exit
        atexit.register(_atexit_close, weakref.ref(self))

    async def _launch_if_needed_locked(self) -> None:
        """Launch Chromium if it is not already running.

        MUST be called with ``_browser_lock`` already held by the caller.
        """
        if self._browser is not None:
            return

        # Record the running loop before any await so _atexit_close can close
        # Playwright objects on the same loop they were created on.
        loop = asyncio.get_running_loop()
        self._launch_loop = loop

        # Lazy import — keeps playwright out of the import graph unless needed
        from playwright.async_api import async_playwright  # noqa: PLC0415

        self._pw_cm = async_playwright()
        self._pw = await self._pw_cm.__aenter__()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=list(_LAUNCH_ARGS),
        )

    async def close(self) -> None:
        """Close the persistent Chromium browser and the Playwright context.

        Safe to call multiple times; subsequent calls are no-ops.

        If the current running loop differs from the loop the browser was
        launched on — which happens when a worker thread's ``asyncio.run()``
        creates the browser and the main loop later calls ``close_js_browser``
        — the Playwright internals *and* ``_browser_lock`` are bound to the
        (possibly closed) launch loop.  Acquiring the lock from a different
        loop raises ``RuntimeError('... bound to a different event loop')``
        immediately, so the loop-mismatch check must run **before**
        ``async with self._browser_lock``.  When mismatched we drop the
        references without touching the lock and return.  The Chromium
        subprocess is then reaped by the OS at Python process exit;
        ``_atexit_close`` cannot rescue it because the launch loop is
        already closed (and awaiting its futures from a new loop would
        itself hang).  This trade-off is acceptable for the scraper's
        short-lived CLI invocations, where the process terminates shortly
        after this path is taken.

        Each shutdown step is bounded by an internal timeout so that one
        hung step (e.g. an unresponsive Node subprocess) cannot exhaust the
        outer ``close_js_browser`` budget — keeping the scraper teardown
        deterministic even when Playwright misbehaves.
        """
        if self._browser is None and self._pw_cm is None:
            return

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        launch_loop = self._launch_loop
        loop_mismatch = (
            launch_loop is not None
            and (launch_loop is not current_loop or launch_loop.is_closed())
        )

        if loop_mismatch:
            # Playwright's connection futures and _browser_lock are both
            # bound to launch_loop.  Acquiring the lock from a different
            # loop raises RuntimeError; awaiting Playwright cross-loop
            # would deadlock.  Drop references without touching the lock
            # so scrape_shows' close_js_browser() can return cleanly.
            self._browser = None
            self._pw_cm = None
            self._pw = None
            return

        async with self._browser_lock:
            if self._browser is None and self._pw_cm is None:
                return

            if self._browser is not None:
                try:
                    await asyncio.wait_for(self._browser.close(), timeout=_CLOSE_STEP_TIMEOUT)
                except asyncio.TimeoutError:
                    Logger.warn(
                        f"PlaywrightBrowser.close: browser.close() timed out after {_CLOSE_STEP_TIMEOUT}s"
                    )
                finally:
                    self._browser = None
            if self._pw_cm is not None:
                try:
                    await asyncio.wait_for(
                        self._pw_cm.__aexit__(None, None, None),
                        timeout=_CLOSE_STEP_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    Logger.warn(
                        f"PlaywrightBrowser.close: playwright shutdown timed out after {_CLOSE_STEP_TIMEOUT}s"
                    )
                finally:
                    self._pw_cm = None
                    self._pw = None

    @staticmethod
    async def _wait_for_waf_challenge(page: object, html: str) -> str:
        """Wait for an AWS WAF passive JS challenge to resolve, then return the final HTML.

        Polls the live DOM for the absence of the challenge's inline globals
        (``awsWafCookieDomainList`` / ``gokuProps``). These are set on
        ``window`` by the challenge markup and disappear once the challenge
        reloads the page into the real content. Falls back to returning the
        original challenge HTML on timeout — ``HttpClient._bot_block_reason``
        and caller-level error handling will surface the unresolved block.
        """
        try:
            await page.wait_for_function(
                "() => !window.awsWafCookieDomainList && !window.gokuProps",
                timeout=_WAF_CHALLENGE_WAIT_MS,
            )
        except Exception:
            # Any exception (TimeoutError, navigation racing the script) —
            # return current HTML; bot-block detection handles the rest.
            return html
        return await page.content()

    async def fetch_html(self, url: str, proxy_url: Optional[str] = None) -> str:
        """Fetch fully-rendered HTML from *url* using the persistent Playwright browser.

        The Chromium process is started on the first call and reused for all
        subsequent calls.  A new browser context is created per call to ensure
        cookie/state isolation between requests, then closed when done.

        Args:
            url: Page URL to navigate to (will be scheme-normalized).
            proxy_url: Optional proxy URL applied to the browser context
                       (e.g. "http://user:pass@host:port").

        Returns:
            Rendered HTML string after DOMContentLoaded.

        Raises:
            ImportError: When playwright is not installed.
            Exception: Any Playwright navigation error.
        """
        normalized_url = URLUtils.normalize_url(url)
        proxy_dict = _parse_proxy(proxy_url) if proxy_url else None

        # Hold the lock across the entire fetch to prevent a concurrent close()
        # from setting self._browser = None between _ensure_browser() and
        # new_context() (TOCTOU race).  close() acquires the same lock, so it
        # will wait until this fetch completes before tearing down the browser.
        async with self._browser_lock:
            await self._launch_if_needed_locked()

            context = None
            try:
                context = await self._browser.new_context(
                    viewport=self._viewport,
                    locale=self._locale,
                    java_script_enabled=True,
                    proxy=proxy_dict,
                    user_agent=_USER_AGENT,
                )
                page = await context.new_page()
                # Apply stealth patches before any navigation
                await page.add_init_script(_STEALTH_SCRIPT)
                await page.goto(
                    normalized_url,
                    wait_until="domcontentloaded",
                    timeout=self._timeout_ms,
                )
                html = await page.content()
                if any(marker in html for marker in _AWS_WAF_MARKERS):
                    html = await self._wait_for_waf_challenge(page, html)
                Logger.debug(
                    f"[PlaywrightBrowser] Fetched {normalized_url} ({len(html)} chars)",
                    {},
                )
                return html
            finally:
                if context is not None:
                    await context.close()
