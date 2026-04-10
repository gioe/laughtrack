"""
Coral Gables Comedy Club scraper implementation.

Coral Gables Comedy Club (220 Water St, Saugatuck MI) is a seasonal Saturday-night
comedy venue inside the Coral Gables restaurant. Ticketing is handled via Square
Online (Weebly), with events exposed through the public storefront products API:

  GET https://cdn5.editmysite.com/app/store/api/v28/editor/users/{user_id}/sites/{site_id}/products
      ?product_type=event&visibilities[]=visible&per_page=50

The API returns all event-type products (upcoming and past); the extractor filters
to future dates only.

Pipeline:
  1. collect_scraping_targets() → [scraping_url] (base class default)
  2. get_data(url)              → fetches Square Online products API and parses
                                  CoralGablesComedyClubEvent objects
  3. transformation_pipeline    → CoralGablesComedyClubEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import CoralGablesComedyClubPageData
from .extractor import CoralGablesComedyClubEventExtractor
from .transformer import CoralGablesComedyClubEventTransformer


class CoralGablesComedyClubScraper(BaseScraper):
    """Scraper for Coral Gables Comedy Club (Saugatuck, MI) via Square Online API."""

    key = "coral_gables_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            CoralGablesComedyClubEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[CoralGablesComedyClubPageData]:
        """
        Fetch events from the Square Online products API.

        Args:
            url: The full Square Online products API URL (stored in scraping_url).

        Returns:
            CoralGablesComedyClubPageData containing upcoming events, or None.
        """
        try:
            data = await self.fetch_json(url)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: error fetching products API: {e}",
                self.logger_context,
            )
            return None

        if not data:
            Logger.info(
                f"{self._log_prefix}: no data returned from products API",
                self.logger_context,
            )
            return None

        events = CoralGablesComedyClubEventExtractor.parse_products(
            data, self.logger_context
        )

        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming events found",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: {len(events)} upcoming events",
            self.logger_context,
        )
        return CoralGablesComedyClubPageData(event_list=events)
