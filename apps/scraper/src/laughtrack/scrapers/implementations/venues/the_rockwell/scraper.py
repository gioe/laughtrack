"""
The Rockwell scraper implementation.

The Rockwell (255 Elm St, Somerville, MA) uses The Events Calendar WordPress
plugin, which exposes a REST API at:
  /wp-json/tribe/events/v1/events

Pipeline:
  1. collect_scraping_targets() → returns [scraping_url] (default base behaviour)
  2. get_data(url)              → fetches all API pages, extracts RockwellEvents
  3. transformation_pipeline    → RockwellEvent.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import RockwellPageData
from .extractor import RockwellEventExtractor
from .transformer import RockwellEventTransformer

_PER_PAGE = 50


class TheRockwellScraper(BaseScraper):
    """Scraper for The Rockwell (Somerville, MA) via Tribe Events REST API."""

    key = "the_rockwell"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(RockwellEventTransformer(club))

    async def get_data(self, url: str) -> Optional[RockwellPageData]:
        """
        Fetch all pages from The Rockwell Tribe Events API.

        Args:
            url: The Tribe Events API base URL (from club.scraping_url)

        Returns:
            RockwellPageData containing all RockwellEvent objects, or None
        """
        try:
            all_events = []
            page = 1
            while True:
                api_url = f"{url}?per_page={_PER_PAGE}&status=publish&page={page}"
                response = await self.fetch_json(api_url)
                if not response:
                    break

                events = RockwellEventExtractor.extract_events(response)
                all_events.extend(events)

                total_pages = RockwellEventExtractor.get_total_pages(response)
                Logger.debug(
                    f"TheRockwellScraper: page {page}/{total_pages}, "
                    f"{len(events)} events",
                    self.logger_context,
                )
                if page >= total_pages:
                    break
                page += 1

            if not all_events:
                Logger.info(f"TheRockwellScraper: no events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"TheRockwellScraper: extracted {len(all_events)} events total",
                self.logger_context,
            )
            return RockwellPageData(event_list=all_events)

        except Exception as e:
            Logger.error(f"TheRockwellScraper: error fetching events: {e}", self.logger_context)
            return None
