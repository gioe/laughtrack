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
"""

import asyncio
import atexit
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


def _atexit_close(browser_ref: "weakref.ref[PlaywrightBrowser]") -> None:
    """Best-effort synchronous shutdown of the Playwright browser on process exit."""
    browser = browser_ref()
    if browser is None or browser._browser is None:
        return
    try:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(browser.close())
        finally:
            loop.close()
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
        # Serializes browser launch, the entire fetch_html body, and close() to
        # prevent TOCTOU races between active fetches and concurrent close() calls.
        # fetch_html calls are therefore serialized; concurrent callers queue up.
        self._browser_lock = asyncio.Lock()

        # Register best-effort cleanup on process exit
        atexit.register(_atexit_close, weakref.ref(self))

    async def _launch_if_needed_locked(self) -> None:
        """Launch Chromium if it is not already running.

        MUST be called with ``_browser_lock`` already held by the caller.
        """
        if self._browser is not None:
            return

        # Lazy import — keeps playwright out of the import graph unless needed
        from playwright.async_api import async_playwright  # noqa: PLC0415

        self._pw_cm = async_playwright()
        self._pw = await self._pw_cm.__aenter__()
        self._browser = await self._pw.chromium.launch(headless=True)

    async def close(self) -> None:
        """Close the persistent Chromium browser and the Playwright context.

        Safe to call multiple times; subsequent calls are no-ops.
        """
        async with self._browser_lock:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            if self._pw_cm is not None:
                await self._pw_cm.__aexit__(None, None, None)
                self._pw_cm = None
                self._pw = None

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
                Logger.debug(
                    f"[PlaywrightBrowser] Fetched {normalized_url} ({len(html)} chars)",
                    {},
                )
                return html
            finally:
                if context is not None:
                    await context.close()
