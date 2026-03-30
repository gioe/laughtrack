"""
Ninkashi venue scraper.

Venues that use Ninkashi as their ticketing platform expose events via the
unauthenticated public API:
  GET https://api.ninkashi.com/public_access/events/find_by_url_site
      ?url_site=<subdomain>&page=1&per_page=100

The 'url_site' parameter (e.g. 'tickets.cttcomedy.com') is stored in
club.scraping_url.

Currently used by: Cheaper Than Therapy (San Francisco, CA).
A new Ninkashi venue can be onboarded with only a DB row — no Python changes.
"""

from typing import List, Optional

from laughtrack.core.clients.ninkashi.client import NinkashiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import NinkashiPageData
from .extractor import NinkashiExtractor
from .transformer import NinkashiEventTransformer


class NinkashiScraper(BaseScraper):
    """
    Generic Ninkashi scraper — reads club.scraping_url for the url_site value.

    Fetches all upcoming events in a single paginated pass.
    """

    key = "ninkashi"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(NinkashiEventTransformer(club))
        self.ninkashi_client = NinkashiClient(club, proxy_pool=self.proxy_pool)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the url_site stored in club.scraping_url."""
        return [self.club.scraping_url] if self.club.scraping_url else []

    async def get_data(self, url_site: str) -> Optional[NinkashiPageData]:
        """Fetch events from the Ninkashi API for the given url_site."""
        try:
            events = await self.ninkashi_client.fetch_events(url_site)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events returned for {url_site}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: fetched {len(events)} events for {url_site}",
                self.logger_context,
            )
            return NinkashiExtractor.to_page_data(events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events for {url_site}: {e}",
                self.logger_context,
            )
            return None
