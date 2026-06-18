"""
Ventura Improv Company scraper (club 8884) — bespoke /shows parser.

venturaimprov.com/shows is a hand-maintained WordPress page whose "Coming Up"
GenerateBlocks block lists one upcoming show at a time (no JSON-LD, no tribe
API). This scraper fetches that page and parses the block. Tickets are sold
off-site via NAMBA Arts (Tickera/WooCommerce); the per-show ticket URL points
at the nambaarts.com event page.

Pipeline:
  1. collect_scraping_targets() → [scraping_url]  (the /shows page; default)
  2. get_data(url)              → fetch + parse the 'Coming Up' block
  3. transformation_pipeline   → VenturaImprovEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import VenturaImprovPageData
from .extractor import VenturaImprovExtractor
from .transformer import VenturaImprovTransformer


class VenturaImprovScraper(BaseScraper):
    """Scraper for Ventura Improv Company via the hand-maintained /shows page."""

    key = "ventura_improv"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(VenturaImprovTransformer(club))

    async def get_data(self, url: str) -> Optional[VenturaImprovPageData]:
        """Fetch the /shows page and extract the upcoming show(s).

        Args:
            url: The venue's /shows URL (from scraping_sources.source_url).

        Returns:
            VenturaImprovPageData with upcoming shows, or None.
        """
        try:
            html = await self.fetch_html(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to fetch Ventura Improv /shows: {e}", self.logger_context)
            return None

        events = VenturaImprovExtractor.extract_shows(html or "", self.logger_context)
        if not events:
            self._warn_empty_extraction(url, html=html)
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} upcoming show(s)",
            self.logger_context,
        )
        return VenturaImprovPageData(event_list=events)
