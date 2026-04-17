"""
JetBook (Bubble.io) platform scraper.

JetBook is a hosted ticketing platform for improv/comedy venues, built on
Bubble.io. Each venue is rendered as an iframe at
``https://jetbook.co/o_iframe/<venue-slug>`` which lazy-loads event rows
via ``/elasticsearch/msearch`` POST requests.

Challenge
---------
Bubble.io encrypts the POST request bodies (opaque ``{"z": "..."}``
payloads), so the msearch endpoint cannot be replayed directly from
Python. However, the RESPONSE bodies are plaintext JSON — they contain
the full event records (``_source.name_text``, ``parsedate_start_date``,
``Slug``, visibility flags, etc.).

Pipeline
--------
1. Launch a headless Chromium browser via Playwright.
2. Navigate to ``club.scraping_url`` (the JetBook iframe URL) and wait
   for ``networkidle`` so the initial batch of msearch requests completes.
3. Scroll to the bottom of the page and click the "Show more" button
   iteratively (via ``evaluate()`` — the standard Playwright click times
   out against Bubble's non-standard button implementation) to trigger
   further msearch requests until no more results are loaded.
4. Collect all captured msearch response bodies.
5. Hand them to ``JetBookExtractor.parse_msearch_responses`` which
   filters visibly-bookable upcoming events and returns JetBookEvent
   objects.

Per-event ticket URL: ``https://jetbook.co/e/<slug>``
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import JetBookPageData
from .extractor import JetBookExtractor
from .transformer import JetBookEventTransformer

_PAGE_LOAD_TIMEOUT_MS = 60_000
_NETWORK_IDLE_TIMEOUT_MS = 15_000
_POST_SCROLL_WAIT_MS = 800
_POST_SHOW_MORE_WAIT_MS = 2500
_MAX_SHOW_MORE_CLICKS = 40

# Total runtime budget for a single _capture_msearch_responses() call.
# Covers page load + the "Show more" click loop + trailing networkidle.
# Worst-case theoretical cost (~132s click loop + 60s page load + 15s idle)
# exceeds this; the wait_for cap prevents a hung Bubble page from pinning
# Chromium for minutes during nightly runs.
_CAPTURE_TOTAL_BUDGET_S = 180


class JetBookScraper(BaseScraper):
    """Generic scraper for venues hosted on the JetBook (Bubble.io) platform."""

    key = "jetbook"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            JetBookEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[JetBookPageData]:
        """Render the JetBook iframe and extract upcoming events.

        Args:
            url: JetBook iframe URL (``club.scraping_url``).

        Returns:
            JetBookPageData with extracted events, or None on failure.
        """
        try:
            response_bodies = await asyncio.wait_for(
                self._capture_msearch_responses(url),
                timeout=_CAPTURE_TOTAL_BUDGET_S,
            )
        except asyncio.TimeoutError:
            Logger.warn(
                f"{self._log_prefix}: Playwright capture exceeded "
                f"{_CAPTURE_TOTAL_BUDGET_S}s budget for {url}",
                self.logger_context,
            )
            return None
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Playwright capture failed for {url}: {e}",
                self.logger_context,
            )
            return None

        if not response_bodies:
            Logger.warn(
                f"{self._log_prefix}: no msearch responses captured at {url}",
                self.logger_context,
            )
            return None

        events = JetBookExtractor.parse_msearch_responses(response_bodies)
        if not events:
            Logger.info(
                f"{self._log_prefix}: no bookable upcoming events found at {url}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} events from "
            f"{len(response_bodies)} msearch response(s)",
            self.logger_context,
        )
        return JetBookPageData(event_list=events)

    async def _capture_msearch_responses(self, url: str) -> List[str]:
        """Drive a headless browser through the iframe and collect msearch responses.

        Uses ``playwright.async_api`` directly rather than the shared
        ``PlaywrightBrowser`` singleton because we need to attach a
        ``response`` event listener before navigation — the shared helper
        only returns the final HTML.
        """
        from playwright.async_api import async_playwright  # lazy import

        bodies: List[str] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                page = await context.new_page()

                async def _on_response(response) -> None:
                    # Tight suffix match — avoids matching unrelated paths
                    # that happen to contain both substrings.
                    if (
                        response.url.endswith("/elasticsearch/msearch")
                        and response.status == 200
                    ):
                        try:
                            bodies.append(await response.text())
                        except Exception:
                            # Response may be closed before we can read it.
                            pass

                page.on("response", _on_response)

                try:
                    await page.goto(
                        url,
                        wait_until="networkidle",
                        timeout=_PAGE_LOAD_TIMEOUT_MS,
                    )
                except Exception as e:
                    Logger.warn(
                        f"{self._log_prefix}: initial navigation to {url} failed: {e}",
                        self.logger_context,
                    )

                # Scroll + click "Show more" until no more results load.
                clicks = 0
                for _ in range(_MAX_SHOW_MORE_CLICKS):
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(_POST_SCROLL_WAIT_MS)

                    # Standard Playwright .click() times out against Bubble's
                    # button (the element is "not visible" per Playwright's
                    # visibility checks). Dispatch via evaluate() instead.
                    # Scope the selector to actual interactive elements so a
                    # parent div whose innerText happens to equal "Show more"
                    # never becomes the click target.
                    clicked = await page.evaluate(
                        """
                        () => {
                            const candidates = Array.from(
                                document.querySelectorAll('button, a, [role="button"]')
                            ).filter(el => {
                                const t = (el.innerText || '').trim().toLowerCase();
                                return t === 'show more' && el.offsetParent !== null;
                            });
                            if (candidates.length === 0) return false;
                            candidates[0].scrollIntoView();
                            candidates[0].click();
                            return true;
                        }
                        """
                    )
                    if not clicked:
                        break
                    clicks += 1
                    await page.wait_for_timeout(_POST_SHOW_MORE_WAIT_MS)

                if clicks >= _MAX_SHOW_MORE_CLICKS:
                    # Pagination cap hit — events past this point are silently
                    # dropped. Surface to the scraper team so they can raise
                    # the cap for high-volume venues.
                    Logger.warn(
                        f"{self._log_prefix}: hit _MAX_SHOW_MORE_CLICKS="
                        f"{_MAX_SHOW_MORE_CLICKS} at {url}; additional events "
                        "may have been dropped",
                        self.logger_context,
                    )

                try:
                    await page.wait_for_load_state(
                        "networkidle", timeout=_NETWORK_IDLE_TIMEOUT_MS
                    )
                except Exception:
                    # Networkidle timeout is non-fatal — keep whatever we
                    # collected so far.
                    pass
            finally:
                await browser.close()

        return bodies
