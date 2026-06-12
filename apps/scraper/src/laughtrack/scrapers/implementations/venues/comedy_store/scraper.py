"""
The Comedy Store scraper implementation.

The Comedy Store (8433 W Sunset Blvd, West Hollywood, CA) lists shows on a
day-by-day HTML calendar at thecomedystore.com/calendar/YYYY-MM-DD.  Tickets
are sold through ShowClix (venue 30111).

Pipeline:
  1. collect_scraping_targets() → one URL per day for the next SCRAPE_WINDOW_DAYS days
  2. get_data(url)              → fetch daily calendar HTML → extract ComedyStoreEvents
  3. transformation_pipeline   → ComedyStoreEvent.to_show() → Show objects

Ticket prices (TASK-2841): the calendar pages render no price element, but the
ShowClix seated-event API the Gotham scraper already consumes in production
carries per-level prices. Ticket links are slug-style
(showclix.com/event/<slug>, served from events.leapevents.com since the Leap
migration), while the API takes a numeric id — the ticket page embeds it as
var EVENT = {"event_id":"<digits>", ...}. get_data resolves each distinct
slug page once (memoized per run, failure-evicting, capped concurrency) and
attaches ShowclixEventData.get_primary_price() to the event. Any failure in
the resolve→fetch chain degrades that show to the priceless fallback ticket.
"""

import asyncio
import re
from datetime import date, timedelta
from typing import Dict, List, Optional

from laughtrack.core.clients.showclix.client import ShowclixAPIClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_store import ComedyStoreEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyStorePageData
from .extractor import SHOWCLIX_EVENT_URL_RE, ComedyStoreEventExtractor
from .transformer import ComedyStoreEventTransformer

# Number of days ahead to scrape (inclusive of today)
_SCRAPE_WINDOW_DAYS = 60

# The ticket page embeds the numeric ShowClix id in an inline script:
#   var EVENT = {"event_id":"10341917","event":"..."}
_EVENT_ID_RE = re.compile(r'"event_id"\s*:\s*"(\d+)"')

# Cap on concurrent slug-page fetches — 60 day pages fetch concurrently and a
# busy week carries several shows per day, so an unbounded gather would burst
# hundreds of in-flight requests.
_SHOWCLIX_MAX_CONCURRENT_FETCHES = 10


class ComedyStoreScraper(BaseScraper):
    """Scraper for The Comedy Store (West Hollywood, CA)."""

    key = "comedy_store"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.showclix_client = ShowclixAPIClient(club)
        # Slug-page price resolutions memoized for the life of the run: the
        # same show page is never fetched twice, even across get_data retries.
        self._ticket_price_tasks: Dict[str, "asyncio.Task[Optional[float]]"] = {}
        self._price_semaphore = asyncio.Semaphore(_SHOWCLIX_MAX_CONCURRENT_FETCHES)
        self.transformation_pipeline.register_transformer(ComedyStoreEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Return one calendar URL per day for the next _SCRAPE_WINDOW_DAYS days."""
        today = date.today()
        base = self.club.scraping_url.rstrip("/")
        targets = [
            f"{base}/{(today + timedelta(days=i)).strftime('%Y-%m-%d')}"
            for i in range(_SCRAPE_WINDOW_DAYS)
        ]
        Logger.info(
            f"{self._log_prefix}: generated {len(targets)} daily calendar URLs "
            f"({today} – {today + timedelta(days=_SCRAPE_WINDOW_DAYS - 1)})",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[ComedyStorePageData]:
        """Fetch a single calendar day page and extract all show events."""
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(f"{self._log_prefix}: empty response from {url}", self.logger_context)
                return None

            events = ComedyStoreEventExtractor.extract_shows(html)
            if not events:
                # Days with no shows are normal — return None to skip silently
                return None

            await self._attach_showclix_prices(events)

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} show(s) from {url}",
                self.logger_context,
            )
            return ComedyStorePageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: error scraping {url}: {e}", self.logger_context)
            return None

    async def _attach_showclix_prices(self, events: List[ComedyStoreEvent]) -> None:
        """Populate each event's price from the ShowClix seated-event API.

        Only slug-style ticket pages are eligible; sold-out/free shows whose
        ticket_url fell back to the venue show page keep price=None.
        """
        # Same pattern the extractor uses to pick ticket anchors, so
        # extraction and enrichment can never disagree on eligibility.
        urls = list(dict.fromkeys(
            event.ticket_url
            for event in events
            if event.ticket_url and SHOWCLIX_EVENT_URL_RE.search(event.ticket_url)
        ))
        prices = await asyncio.gather(*(self._ticket_page_price(u) for u in urls))
        price_by_url = dict(zip(urls, prices))
        for event in events:
            if event.ticket_url in price_by_url:
                event.price = price_by_url[event.ticket_url]

    def _ticket_page_price(self, url: str) -> "asyncio.Task[Optional[float]]":
        task = self._ticket_price_tasks.get(url)
        if task is None:
            task = asyncio.ensure_future(self._resolve_and_fetch_price(url))
            self._ticket_price_tasks[url] = task
        return task

    async def _resolve_and_fetch_price(self, url: str) -> Optional[float]:
        """Resolve a slug-style ticket page to its numeric id and fetch the price.

        Never raises: any failure in the slug-page fetch, event-id resolution,
        or seated-API call degrades to price-unknown (None) — the show itself
        is never dropped. Failed page fetches are evicted from the memo so a
        get_data retry can try again; a fetched page without an embedded
        event_id (or an API miss) stays cached — refetching would not help.
        """
        try:
            async with self._price_semaphore:
                await self.rate_limiter.await_if_needed(url)
                html = await self.fetch_html(url)
        except Exception as e:
            self._ticket_price_tasks.pop(url, None)
            Logger.warn(
                f"{self._log_prefix}: ticket-page fetch failed for {url}: {e}",
                self.logger_context,
            )
            return None
        if not html:
            self._ticket_price_tasks.pop(url, None)
            return None

        match = _EVENT_ID_RE.search(html)
        if not match:
            Logger.warn(
                f"{self._log_prefix}: no embedded event_id on ticket page {url}",
                self.logger_context,
            )
            return None

        try:
            async with self._price_semaphore:
                event_data = await self.showclix_client.get_event_data(match.group(1))
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: seated-API fetch failed for event "
                f"{match.group(1)} ({url}): {e}",
                self.logger_context,
            )
            return None
        if not event_data:
            return None

        try:
            price = float(event_data.get_primary_price())
        except (TypeError, ValueError):
            return None
        # A 0.00 seated price level is a placeholder/comp tier, not proof the
        # show is free — keep price-unknown per the tickets-are-access-records
        # convention (TASK-2827).
        return price if price > 0 else None
