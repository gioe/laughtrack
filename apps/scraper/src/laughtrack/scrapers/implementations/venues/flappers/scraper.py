"""Flappers Comedy Club scraper.

The Flappers calendar is server-rendered PHP at:
  https://www.flapperscomedy.com/site/calendar_test_2025.php?month=N&year=YYYY

Each page contains <form> elements with <button class="event-btn">
holding show titles, times, rooms, and event IDs.

Pipeline:
  1. collect_scraping_targets() -> monthly calendar URLs (current + next 2 months)
  2. get_data(url)              -> fetch calendar HTML -> extract FlappersEvent objects
                                   -> fetch each show detail page for tickets + lineup
  3. transformation_pipeline    -> FlappersEvent.to_show() -> Show objects
"""

import asyncio
from datetime import date
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import FlappersPageData
from .extractor import FlappersEventExtractor
from .transformer import FlappersEventTransformer

_SCRAPE_WINDOW_MONTHS = 3
_DETAIL_CONCURRENCY = 5
_DETAIL_BASE_URL = "https://www.flapperscomedy.com/site/shows.php?event_id="


class FlappersComediClubScraper(BaseScraper):
    """Scraper for Flappers Comedy Club via server-rendered PHP calendar."""

    key = "flappers"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            FlappersEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        today = date.today()
        base = self.club.scraping_url.rstrip("/")
        targets = []
        for i in range(_SCRAPE_WINDOW_MONTHS):
            d = today + relativedelta(months=i)
            targets.append(f"{base}?month={d.month}&year={d.year}")

        Logger.info(
            f"{self._log_prefix}: generated {len(targets)} monthly calendar URLs",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[FlappersPageData]:
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response from {url}",
                    self.logger_context,
                )
                return None

            tz = self.club.timezone or "America/Los_Angeles"
            events = FlappersEventExtractor.extract_shows(html, url=url, timezone=tz)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no shows found in {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} show(s) from {url}",
                self.logger_context,
            )

            # Enrich events with detail page data (tickets, lineup, description)
            await self._enrich_events(events)

            return FlappersPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error scraping {url}: {e}",
                self.logger_context,
            )
            return None

    async def _enrich_events(self, events: list) -> None:
        """Fetch show detail pages concurrently and enrich events with ticket/lineup data."""
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)

        async def fetch_detail(event):
            async with sem:
                detail_url = f"{_DETAIL_BASE_URL}{event.event_id}"
                try:
                    html = await self.fetch_html(detail_url)
                    if not html:
                        return
                    details = FlappersEventExtractor.extract_show_details(html)
                    if not details:
                        return
                    if details.ticket_tiers:
                        event.ticket_tiers = details.ticket_tiers
                    if details.lineup_names:
                        event.lineup_names = details.lineup_names
                    if details.description:
                        event.description = details.description
                except Exception as e:
                    Logger.warn(
                        f"{self._log_prefix}: failed to fetch detail for event {event.event_id}: {e}",
                        self.logger_context,
                    )

        await asyncio.gather(*(fetch_detail(ev) for ev in events))

        enriched = sum(1 for ev in events if ev.ticket_tiers)
        Logger.info(
            f"{self._log_prefix}: enriched {enriched}/{len(events)} events with detail page data",
            self.logger_context,
        )
