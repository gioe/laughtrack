"""Brew HaHa Comedy at River scraper (Wethersfield, CT).

Comedy Craft Beer (comedycraftbeer.com) runs shows at multiple venues.
The /calendar page embeds JSON-LD for all venues. This scraper fetches
the calendar and filters to events at the River venue only.
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import BrewHaHaRiverPageData
from .extractor import BrewHaHaRiverExtractor
from .transformer import BrewHaHaRiverTransformer


class BrewHaHaRiverScraper(BaseScraper):
    """Scraper for Brew HaHa Comedy at River via Comedy Craft Beer JSON-LD."""

    key = "brew_haha_river"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            BrewHaHaRiverTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[BrewHaHaRiverPageData]:
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(f"{self._log_prefix}: empty response for {url}")
                return None

            events = BrewHaHaRiverExtractor.extract_events(html)
            if not events:
                Logger.info(f"{self._log_prefix}: no River events found on {url}")
                return None

            Logger.info(f"{self._log_prefix}: extracted {len(events)} River events from {url}")
            return BrewHaHaRiverPageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: error fetching {url}: {e}")
            return None
