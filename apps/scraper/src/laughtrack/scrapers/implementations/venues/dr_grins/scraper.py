"""
Dr. Grins Comedy Club scraper (Grand Rapids, MI).

Dr. Grins sells tickets through Etix.  The venue page at
https://www.etix.com/ticket/v/35455/drgrins-comedy-club-at-the-bob
lists upcoming shows across multiple paginated pages (20 per page).

Pipeline:
  1. collect_scraping_targets() — build paginated Etix URLs.
  2. get_data(url)              — fetch page and extract events.
  3. transformation_pipeline    — DrGrinsEvent.to_show() -> Show.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import DrGrinsPageData
from .extractor import DrGrinsExtractor
from .transformer import DrGrinsEventTransformer

_ETIX_VENUE_URL = (
    "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue"
    "?venue_id={venue_id}&orderBy=1&pageNumber={page}"
)
_MAX_PAGES = 10


class DrGrinsScraper(BaseScraper):
    """Scraper for Dr. Grins Comedy Club (Grand Rapids, MI)."""

    key = "dr_grins"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            DrGrinsEventTransformer(club)
        )
        self._venue_id = self._extract_venue_id()

    def _extract_venue_id(self) -> str:
        """Extract the Etix venue ID from scraping_url or fall back to default."""
        url = self.club.scraping_url or ""
        # Try to extract venue_id from URL param or path
        import re
        m = re.search(r"venue_id=(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/v/(\d+)/", url)
        if m:
            return m.group(1)
        return "35455"

    async def collect_scraping_targets(self) -> List[str]:
        """
        Build paginated Etix URLs.

        Fetches page 1 first to discover the total page count, then
        returns URLs for all pages.
        """
        page1_url = _ETIX_VENUE_URL.format(venue_id=self._venue_id, page=1)
        html = await self.fetch_html(page1_url)
        if not html:
            return [page1_url]

        max_page = min(DrGrinsExtractor.extract_max_page(html), _MAX_PAGES)
        urls = [page1_url]
        for page in range(2, max_page + 1):
            urls.append(
                _ETIX_VENUE_URL.format(venue_id=self._venue_id, page=page)
            )

        Logger.info(
            f"{self._log_prefix}: discovered {max_page} page(s) of events",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[DrGrinsPageData]:
        """Fetch a single page and extract event cards."""
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = DrGrinsExtractor.extract_events(html)
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
            return DrGrinsPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
