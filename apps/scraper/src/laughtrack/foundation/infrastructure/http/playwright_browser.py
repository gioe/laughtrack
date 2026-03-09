"""Playwright-based headless browser for JS-rendered pages.

PlaywrightBrowser is the concrete implementation of the JSBrowser port.
It is used exclusively as the automatic fallback inside HttpClient.fetch_html
when curl-cffi returns an empty body or a known bot-block response.

Playwright is *lazy-imported* — the package is only loaded at the moment the
first fallback is triggered, so scrapers that never encounter a bot-block page
pay zero import overhead.
"""

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


class PlaywrightBrowser:
    """Playwright headless browser for fetching JS-rendered pages.

    Applies stealth patches on every page context to reduce bot-detection
    false positives:
    - Removes ``navigator.webdriver``
    - Spoofs ``navigator.plugins`` and ``navigator.languages``
    - Adds imperceptible canvas fingerprint noise

    Usage::

        browser = PlaywrightBrowser()
        html = await browser.fetch_html("https://example.com/events")
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

    async def fetch_html(self, url: str, proxy_url: Optional[str] = None) -> str:
        """Fetch fully-rendered HTML from *url* using a Playwright browser.

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
        # Lazy import — keeps playwright out of the import graph unless needed
        from playwright.async_api import async_playwright  # noqa: PLC0415

        normalized_url = URLUtils.normalize_url(url)
        proxy_dict = _parse_proxy(proxy_url) if proxy_url else None

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = None
            try:
                context = await browser.new_context(
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
                await browser.close()
