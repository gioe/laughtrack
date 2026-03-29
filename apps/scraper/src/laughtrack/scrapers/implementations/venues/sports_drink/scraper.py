"""
Sports Drink scraper (New Orleans, LA).

Sports Drink (1042 Toledano St) is a hybrid café/comedy club that sells
tickets through OpenDate. All upcoming shows are listed on a single
server-rendered page with per_page parameter:

  https://app.opendate.io/v/sports-drink-1939?per_page=500

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url)              → fetch HTML, extract SportsDrinkEvents
  3. transformation_pipeline    → SportsDrinkEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import SportsDrinkPageData
from .extractor import SportsDrinkExtractor
from .transformer import SportsDrinkEventTransformer


class SportsDrinkScraper(BaseScraper):
    """Scraper for Sports Drink (New Orleans) via OpenDate."""

    key = "sports_drink"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            SportsDrinkEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[SportsDrinkPageData]:
        """
        Fetch the OpenDate listing page and extract all upcoming events.

        Args:
            url: The OpenDate venue listing URL (from club.scraping_url).

        Returns:
            SportsDrinkPageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"SportsDrinkScraper: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = SportsDrinkExtractor.extract_events(html)
            if not events:
                Logger.info(
                    f"SportsDrinkScraper: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"SportsDrinkScraper: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return SportsDrinkPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"SportsDrinkScraper: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
