"""
The Comedy Clubhouse scraper (Chicago, IL).

The Comedy Clubhouse (1462 N Ashland Ave, Wicker Park) sells tickets through
TicketSource.  All upcoming shows are listed on a single server-rendered page:

  https://www.ticketsource.com/thecomedyclubhouse

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url)              → fetch HTML, extract ComedyClubhouseEvents
  3. transformation_pipeline    → ComedyClubhouseEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyClubhousePageData
from .extractor import ComedyClubhouseExtractor
from .transformer import ComedyClubhouseEventTransformer


class ComedyClubhouseScraper(BaseScraper):
    """Scraper for The Comedy Clubhouse (Wicker Park, Chicago) via TicketSource."""

    key = "comedy_clubhouse"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyClubhouseEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[ComedyClubhousePageData]:
        """
        Fetch the TicketSource listing page and extract all upcoming events.

        Args:
            url: The TicketSource venue listing URL (from club.scraping_url).

        Returns:
            ComedyClubhousePageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = ComedyClubhouseExtractor.extract_events(html)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ComedyClubhousePageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
