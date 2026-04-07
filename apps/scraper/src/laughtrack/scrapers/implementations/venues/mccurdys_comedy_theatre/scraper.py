"""
McCurdy's Comedy Theatre scraper.

McCurdy's Comedy Theatre (1923 Ringling Blvd, Sarasota, FL) lists shows
on a custom ColdFusion-powered website.  The listing page at /shows/
displays a grid of upcoming shows; each links to a detail page at
/shows/show.cfm?shoID=<id> that lists individual performance dates, times,
and Etix ticket links.

Pipeline:
  1. collect_scraping_targets() — fetch the listing page; collect unique
     detail page URLs from the show card onclick handlers.
  2. get_data(url) — fetch one detail page and extract all performance
     date/time/ticket entries.
  3. transformation_pipeline — McCurdysEvent.to_show() → Show objects.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import McCurdysPageData
from .extractor import McCurdysExtractor
from .transformer import McCurdysEventTransformer


class McCurdysComedyTheatreScraper(BaseScraper):
    """Scraper for McCurdy's Comedy Theatre (Sarasota, FL)."""

    key = "mccurdys_comedy_theatre"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            McCurdysEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Fetch the listing page and return detail page URLs."""
        listing_url = URLUtils.normalize_url(self.club.scraping_url)
        html = await self.fetch_html(listing_url)
        if not html:
            Logger.warn(
                f"{self._log_prefix}: empty response for listing page {listing_url}",
                self.logger_context,
            )
            return []

        targets = McCurdysExtractor.extract_detail_page_urls(html, listing_url)
        Logger.info(
            f"{self._log_prefix}: discovered {len(targets)} show detail pages",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[McCurdysPageData]:
        """Fetch one detail page and extract all performances."""
        try:
            html = await self.fetch_html(URLUtils.normalize_url(url))
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = McCurdysExtractor.extract_events(html)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} performances from {url}",
                self.logger_context,
            )
            return McCurdysPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
