"""
Sports Drink scraper (New Orleans, LA).

Sports Drink (1042 Toledano St) is a hybrid café/comedy club that sells
tickets through OpenDate. All upcoming shows are listed on a single
server-rendered page with per_page parameter:

  https://app.opendate.io/v/sports-drink-1939?per_page=500

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url)              → fetch HTML, extract SportsDrinkEvents
  3. transformation_pipeline    → SportsDrinkEvent.to_show() → Show objects

Ticket prices (TASK-2839): the listing page renders no price strings, but each
card's detail page (event_url) embeds schema.org JSON-LD with offers.price.
get_data dispatches every distinct detail URL via asyncio.gather; the shared
rate limiter serializes app.opendate.io at its default 1 req/s, so the ~143
extra fetches add about 2.5 minutes to this venue's scrape — acceptable for a
nightly job, and memoization per run means a get_data retry refetches only
failures, never successes.
"""

import asyncio
from typing import Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.sports_drink import SportsDrinkEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor

from .data import SportsDrinkPageData
from .extractor import SportsDrinkExtractor
from .transformer import SportsDrinkEventTransformer


class SportsDrinkScraper(BaseScraper):
    """Scraper for Sports Drink (New Orleans) via OpenDate."""

    key = "sports_drink"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        # Detail-page price fetches memoized for the life of the run: each
        # distinct event_url is fetched at most once even across retries.
        self._detail_price_tasks: Dict[str, "asyncio.Task[Optional[float]]"] = {}
        self.transformation_pipeline.register_transformer(
            SportsDrinkEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[SportsDrinkPageData]:
        """
        Fetch the OpenDate listing page and extract all upcoming events.

        Args:
            url: The OpenDate venue listing URL (from club.scraping_url).

        Returns:
            SportsDrinkPageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = SportsDrinkExtractor.extract_events(html)
            if not events:
                self._warn_empty_extraction(url, html=html)
                return None

            await self._attach_detail_page_prices(events)

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return SportsDrinkPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None

    async def _attach_detail_page_prices(self, events: List[SportsDrinkEvent]) -> None:
        """Populate each event's price from its detail page's JSON-LD offers.

        Distinct detail URLs are fetched concurrently and memoized per run;
        events without an event_url keep price=None.
        """
        urls = list(dict.fromkeys(e.event_url for e in events if e.event_url))
        prices = await asyncio.gather(*(self._detail_page_price(u) for u in urls))
        price_by_url = dict(zip(urls, prices))
        for event in events:
            if event.event_url:
                event.price = price_by_url.get(event.event_url)

    def _detail_page_price(self, url: str) -> "asyncio.Task[Optional[float]]":
        task = self._detail_price_tasks.get(url)
        if task is None:
            task = asyncio.ensure_future(self._fetch_detail_page_price(url))
            self._detail_price_tasks[url] = task
        return task

    async def _fetch_detail_page_price(self, url: str) -> Optional[float]:
        """Fetch one detail page and parse its lowest JSON-LD offer price.

        Never raises: a missing price degrades the ticket to price-unknown
        (None) rather than dropping the listing. Failed fetches are evicted
        from the memo so a get_data retry can try the page again; a fetched
        page with no parseable offers stays cached — refetching would not help.
        """
        try:
            await self.rate_limiter.await_if_needed(url)
            html = await self.fetch_html(url)
        except Exception as e:
            self._detail_price_tasks.pop(url, None)
            Logger.warn(
                f"{self._log_prefix}: detail-page price fetch failed for {url}: {e}",
                self.logger_context,
            )
            return None
        if not html:
            self._detail_price_tasks.pop(url, None)
            return None
        try:
            return EventExtractor.extract_min_offer_price(html)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: detail-page price parse failed for {url}: {e}",
                self.logger_context,
            )
            return None
