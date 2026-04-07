"""Flappers Comedy Club scraper.

The Flappers calendar is server-rendered PHP at:
  https://www.flapperscomedy.com/site/calendar_test_2025.php?month=N&year=YYYY

Each page contains <form> elements with <button class="event-btn">
holding show titles, times, rooms, and event IDs.

Pipeline:
  1. collect_scraping_targets() -> monthly calendar URLs (current + next 2 months)
  2. get_data(url)              -> fetch HTML -> extract FlappersEvent objects
  3. transformation_pipeline    -> FlappersEvent.to_show() -> Show objects
"""

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
            return FlappersPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error scraping {url}: {e}",
                self.logger_context,
            )
            return None
