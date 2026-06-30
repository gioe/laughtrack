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
   for the first ``/elasticsearch/msearch`` response so the initial batch
   has started.
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
from laughtrack.core.entities.event.jetbook import JetBookEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import JetBookPageData
from .extractor import JetBookExtractor
from .transformer import JetBookEventTransformer

_PAGE_LOAD_TIMEOUT_MS = 60_000
_INITIAL_MSEARCH_TIMEOUT_MS = 15_000
_TRAILING_MSEARCH_TIMEOUT_MS = 15_000
_POST_SCROLL_WAIT_MS = 800
_POST_SHOW_MORE_WAIT_MS = 2500
_POST_SHOW_MORE_MISS_WAIT_MS = 1000
_MAX_SHOW_MORE_CLICKS = 40
_MAX_SHOW_MORE_MISSES = 8
_MAX_LISTING_CAPTURE_ATTEMPTS = 3
_LISTING_RETRY_MIN_RESPONSE_BODIES = 4
_LISTING_RETRY_EVENT_THRESHOLD = 30
_DETAIL_PRICE_PAGE_POOL_SIZE = 4
_DETAIL_PRICE_MAX_EVENTS = 24
_DETAIL_PAGE_LOAD_TIMEOUT_MS = 60_000
_DETAIL_MGET_TIMEOUT_MS = 8_000
_DETAIL_BLOCKED_RESOURCE_TYPES = {"font", "image", "media"}

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
        self.transformation_pipeline.register_transformer(JetBookEventTransformer(club))

    async def get_data(self, url: str) -> Optional[JetBookPageData]:
        """Render the JetBook iframe and extract upcoming events.

        Args:
            url: JetBook iframe URL (``club.scraping_url``).

        Returns:
            JetBookPageData with extracted events, or None on failure.
        """
        return await self._get_data_within_budget(url)

    async def _get_data_within_budget(self, url: str) -> Optional[JetBookPageData]:
        started_at = asyncio.get_running_loop().time()
        response_bodies: list[str] = []
        events: list[JetBookEvent] = []
        for attempt in range(_MAX_LISTING_CAPTURE_ATTEMPTS):
            remaining_budget_s = _CAPTURE_TOTAL_BUDGET_S - (asyncio.get_running_loop().time() - started_at)
            if remaining_budget_s <= 0:
                break

            try:
                candidate_bodies = await asyncio.wait_for(
                    self._capture_msearch_responses(url),
                    timeout=remaining_budget_s,
                )
            except asyncio.TimeoutError:
                Logger.warn(
                    f"{self._log_prefix}: Playwright capture exceeded {_CAPTURE_TOTAL_BUDGET_S}s budget for {url}",
                    self.logger_context,
                )
                if attempt + 1 >= _MAX_LISTING_CAPTURE_ATTEMPTS:
                    break
                continue
            except Exception as e:
                Logger.error(
                    f"{self._log_prefix}: Playwright capture failed for {url}: {e}",
                    self.logger_context,
                )
                if attempt + 1 >= _MAX_LISTING_CAPTURE_ATTEMPTS:
                    break
                continue

            candidate_events = JetBookExtractor.parse_msearch_responses(candidate_bodies)
            if len(candidate_events) > len(events):
                response_bodies = candidate_bodies
                events = candidate_events

            should_retry_empty_capture = attempt + 1 < _MAX_LISTING_CAPTURE_ATTEMPTS and not candidate_bodies
            should_retry_partial_listing = (
                attempt + 1 < _MAX_LISTING_CAPTURE_ATTEMPTS
                and len(candidate_bodies) >= _LISTING_RETRY_MIN_RESPONSE_BODIES
                and 0 < len(candidate_events) < _LISTING_RETRY_EVENT_THRESHOLD
            )
            if not (should_retry_empty_capture or should_retry_partial_listing):
                break

            if should_retry_empty_capture:
                Logger.warn(
                    f"{self._log_prefix}: JetBook listing capture returned no msearch responses at {url}; retrying",
                    self.logger_context,
                )
            else:
                Logger.warn(
                    f"{self._log_prefix}: JetBook listing capture returned only {len(candidate_events)} events "
                    f"from {len(candidate_bodies)} msearch response(s) at {url}; retrying",
                    self.logger_context,
                )

        if not response_bodies:
            Logger.warn(
                f"{self._log_prefix}: no msearch responses captured at {url}",
                self.logger_context,
            )
            return None

        if not events:
            Logger.info(
                f"{self._log_prefix}: no bookable upcoming events found at {url}",
                self.logger_context,
            )
            return None

        remaining_budget_s = _CAPTURE_TOTAL_BUDGET_S - (asyncio.get_running_loop().time() - started_at)
        if remaining_budget_s <= 0:
            Logger.warn(
                f"{self._log_prefix}: no JetBook detail-price budget remains for {url}; "
                "returning price-less listing events",
                self.logger_context,
            )
        else:
            try:
                detail_price_events = events[:_DETAIL_PRICE_MAX_EVENTS]
                if len(detail_price_events) < len(events):
                    Logger.warn(
                        f"{self._log_prefix}: limiting JetBook detail-price capture to "
                        f"{len(detail_price_events)} of {len(events)} events for {url}; "
                        "remaining events will use price-less fallback tickets",
                        self.logger_context,
                    )
                await asyncio.wait_for(
                    self._attach_detail_ticket_prices(detail_price_events),
                    timeout=remaining_budget_s,
                )
            except asyncio.TimeoutError:
                Logger.warn(
                    f"{self._log_prefix}: JetBook detail-price capture exceeded remaining "
                    f"{remaining_budget_s:.1f}s budget for {url}; returning price-less fallback tickets where needed",
                    self.logger_context,
                )
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: JetBook detail-price capture failed for {url}: {e}; "
                    "returning price-less fallback tickets where needed",
                    self.logger_context,
                )

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} events from " f"{len(response_bodies)} msearch response(s)",
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
                loop = asyncio.get_running_loop()
                first_msearch_seen = loop.create_future()

                async def _on_response(response) -> None:
                    # Tight suffix match — avoids matching unrelated paths
                    # that happen to contain both substrings.
                    if response.url.endswith("/elasticsearch/msearch") and response.status == 200:
                        try:
                            bodies.append(await response.text())
                        except Exception:
                            # Response may be closed before we can read it.
                            pass
                        if not first_msearch_seen.done():
                            first_msearch_seen.set_result(None)

                page.on("response", _on_response)

                try:
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=_PAGE_LOAD_TIMEOUT_MS,
                    )
                    try:
                        await asyncio.wait_for(first_msearch_seen, timeout=_INITIAL_MSEARCH_TIMEOUT_MS / 1000)
                    except Exception:
                        pass
                except Exception as e:
                    Logger.warn(
                        f"{self._log_prefix}: initial navigation to {url} failed: {e}",
                        self.logger_context,
                    )

                # Scroll + click "Show more" until no more results load.
                clicks = 0
                misses = 0
                for _ in range(_MAX_SHOW_MORE_CLICKS):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(_POST_SCROLL_WAIT_MS)

                    # Standard Playwright .click() times out against Bubble's
                    # button (the element is "not visible" per Playwright's
                    # visibility checks). Dispatch via evaluate() instead.
                    # Scope the selector to actual interactive elements so a
                    # parent div whose innerText happens to equal "Show more"
                    # never becomes the click target.
                    clicked = await page.evaluate("""
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
                        """)
                    if not clicked:
                        misses += 1
                        if misses >= _MAX_SHOW_MORE_MISSES:
                            break
                        await page.wait_for_timeout(_POST_SHOW_MORE_MISS_WAIT_MS)
                        continue
                    misses = 0
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
                    await asyncio.wait_for(first_msearch_seen, timeout=_TRAILING_MSEARCH_TIMEOUT_MS / 1000)
                except Exception:
                    # A trailing wait timeout is non-fatal — keep whatever we
                    # collected so far.
                    pass
            finally:
                await browser.close()

        return bodies

    async def _attach_detail_ticket_prices(self, events: list[JetBookEvent]) -> None:
        """Populate event.price from each event detail page using a bounded pool.

        Note: unlike the curl-cffi price-enrichment scrapers (comedy_mothership,
        delirious, DetailPagePriceMixin) which opt out of the Playwright fallback
        via skip_js_fallback, JetBook MUST drive a real headless browser here.
        Bubble.io renders the ticket page client-side and the price only appears
        in a runtime ``/elasticsearch/mget`` XHR captured from a live page — there
        is no server-rendered payload a plain fetch could read. The browser is the
        primary fetch mechanism, not a fallback, so skip_js_fallback does not apply
        (TASK-3544 audit).
        """
        if not events:
            return

        semaphore = asyncio.Semaphore(_DETAIL_PRICE_PAGE_POOL_SIZE)
        fetcher = type(self)._fetch_detail_ticket_price
        if fetcher is not JetBookScraper._fetch_detail_ticket_price:

            async def enrich_without_browser_pool(event: JetBookEvent) -> None:
                async with semaphore:
                    try:
                        event.price = await self._fetch_detail_ticket_price(event)
                    except Exception as e:
                        Logger.warn(
                            f"{self._log_prefix}: JetBook detail-price fetch failed for {event.slug}: {e}",
                            self.logger_context,
                        )

            await asyncio.gather(*(enrich_without_browser_pool(event) for event in events))
            return

        from playwright.async_api import async_playwright  # lazy import

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                self._detail_price_context = context

                async def enrich(event: JetBookEvent) -> None:
                    async with semaphore:
                        try:
                            event.price = await self._fetch_detail_ticket_price(event)
                        except Exception as e:
                            Logger.warn(
                                f"{self._log_prefix}: JetBook detail-price fetch failed for {event.slug}: {e}",
                                self.logger_context,
                            )

                await asyncio.gather(*(enrich(event) for event in events))
            finally:
                if hasattr(self, "_detail_price_context"):
                    delattr(self, "_detail_price_context")
                await browser.close()

    async def _fetch_detail_ticket_price(self, event: JetBookEvent) -> Optional[float]:
        context = getattr(self, "_detail_price_context", None)
        if context is not None:
            return await self._fetch_detail_ticket_price_with_context(event, context)

        from playwright.async_api import async_playwright  # lazy import

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                return await self._fetch_detail_ticket_price_with_context(event, context)
            finally:
                await browser.close()

    async def _fetch_detail_ticket_price_with_context(self, event: JetBookEvent, context) -> Optional[float]:
        ticket_url = JetBookExtractor.build_ticket_url(event.slug)
        if not ticket_url:
            return None

        bodies: list[str] = []
        page = await context.new_page()
        loop = asyncio.get_running_loop()
        price_seen = loop.create_future()
        try:
            async def _route_request(route) -> None:
                request = route.request
                if request.resource_type in _DETAIL_BLOCKED_RESOURCE_TYPES:
                    await route.abort()
                    return
                await route.continue_()

            async def _on_response(response) -> None:
                if response.url.endswith("/elasticsearch/mget") and response.status == 200:
                    try:
                        body = await response.text()
                        bodies.append(body)
                    except Exception:
                        pass
                    else:
                        price = JetBookExtractor.parse_mget_ticket_price([body])
                        if price is not None and not price_seen.done():
                            price_seen.set_result(price)

            await page.route("**/*", _route_request)
            page.on("response", _on_response)
            try:
                await page.goto(
                    ticket_url,
                    wait_until="domcontentloaded",
                    timeout=_DETAIL_PAGE_LOAD_TIMEOUT_MS,
                )
                try:
                    return await asyncio.wait_for(price_seen, timeout=_DETAIL_MGET_TIMEOUT_MS / 1000)
                except (asyncio.TimeoutError, Exception):
                    pass
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: JetBook detail navigation failed for " f"{ticket_url}: {e}",
                    self.logger_context,
                )
                return None
        finally:
            await page.close()

        return JetBookExtractor.parse_mget_ticket_price(bodies)
