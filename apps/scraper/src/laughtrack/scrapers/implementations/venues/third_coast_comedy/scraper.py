"""
Vivenu scraper implementation.

Vivenu (vivenu.com) is a ticketing platform used by venues that sell tickets
through a custom subdomain (e.g. tickets.thirdcoastcomedy.club). Event data
is embedded in the seller page HTML as __NEXT_DATA__ JSON — no authenticated
API access is needed.

The club.scraping_url must point to the Vivenu seller page root, e.g.:
  https://tickets.thirdcoastcomedy.club/

The scraper fetches the page using bare curl_cffi Chrome impersonation
(no application headers) to avoid bot-detection challenges.

Currently used by: Third Coast Comedy Club (Nashville, TN).
A second Vivenu venue can be onboarded with only a DB row — no Python changes.
"""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import VivenuPageData
from .extractor import VivenuExtractor
from .transformer import VivenuEventTransformer


class VivenuScraper(BaseScraper):
    """
    Generic Vivenu seller-page scraper — reads club.scraping_url for the page URL.

    Fetches upcoming events from the Vivenu SSR page (__NEXT_DATA__ JSON).
    Only events with a start timestamp in the future are returned.
    """

    key = "vivenu"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(VivenuEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the Vivenu seller page URL from club.scraping_url."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[VivenuPageData]:
        """
        Fetch the Vivenu seller page and return extracted VivenuEvents.

        Uses fetch_html_bare (no application headers) to avoid Cloudflare
        bot-detection on the Next.js seller page.

        Args:
            url: The Vivenu seller page URL (from collect_scraping_targets).

        Returns:
            VivenuPageData containing upcoming events, or None if none found.
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            html = await self.fetch_html_bare(url)
            if not html:
                Logger.info(f"{self.__class__.__name__} [{self._club.name}]: no response from {url}", self.logger_context)
                return None

            parsed = urlparse(url)
            ticket_base_url = f"{parsed.scheme}://{parsed.netloc}"

            events = VivenuExtractor.extract_events(html, ticket_base_url)

            if not events:
                Logger.info(f"{self.__class__.__name__} [{self._club.name}]: no upcoming events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"{self.__class__.__name__} [{self._club.name}]: extracted {len(events)} upcoming events from {url}",
                self.logger_context,
            )
            return VivenuPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self.__class__.__name__} [{self._club.name}]: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None
