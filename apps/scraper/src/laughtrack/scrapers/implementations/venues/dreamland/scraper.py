"""Nantucket Dreamland (Nantucket, MA) Live Comedy scraper.

The venue runs a dedicated "Dreamland Comedy" series plus the Nantucket Comedy
Festival. Its comedy is published under a comedy-only WordPress taxonomy archive
(/event-type/live-comedy) as static HTML cards — no schema.org Event JSON-LD and
no events REST endpoint — so this venue-specific parser reads the archive HTML.
Because the archive is already comedy-only, no comedy_filter is applied.

  source_url (club.scraping_url): https://www.nantucketdreamland.org/event-type/live-comedy
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import DreamlandPageData
from .extractor import DreamlandExtractor
from .transformer import DreamlandEventTransformer

_DEFAULT_SOURCE_URL = "https://www.nantucketdreamland.org/event-type/live-comedy"


class DreamlandScraper(BaseScraper):
    """Static-HTML scraper for Nantucket Dreamland's Live Comedy archive."""

    key = "dreamland"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(DreamlandEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        return [self.club.scraping_url or _DEFAULT_SOURCE_URL]

    async def get_data(self, url: str) -> Optional[DreamlandPageData]:
        html = await self.fetch_html(url)
        if not html:
            self._warn_empty_extraction(url, subject="html", payload=html)
            return None

        events = DreamlandExtractor.extract_events(html, tz=self.club.timezone or "America/New_York")
        if not events:
            self._warn_empty_extraction(url, payload=html)
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} comedy event(s) from {url}",
            self.logger_context,
        )
        return DreamlandPageData(event_list=events)
