"""
Comedy Works South scraper implementation.

Comedy Works South (5345 Landmark Pl, Greenwood Village CO) shares the same
comedyworks.com Rails ticketing platform as Comedy Works Downtown. The site
lists shows for both locations; this scraper filters for South only.

Pipeline:
  1. collect_scraping_targets() -> unique comedian slugs from /events?south=1
  2. get_data(slug)             -> fetch /comedians/{slug}, extract showtimes
  3. transformation_pipeline    -> ComedyWorksDowntownEvent.to_show() -> Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import ComedyWorksSouthPageData
from .extractor import ComedyWorksSouthExtractor
from .transformer import ComedyWorksSouthTransformer

_BASE_URL = "https://www.comedyworks.com"


class ComedyWorksSouthScraper(BaseScraper):
    """
    Scraper for Comedy Works South (Greenwood Village, CO).

    Two-phase scrape:
    1. Fetch /events?south=1 to discover unique comedian slugs
    2. For each slug, fetch /comedians/{slug} to extract all South showtimes
       with full pricing and sold-out status
    """

    key = "comedy_works_south"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyWorksSouthTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Fetch the South events list page and return unique comedian slugs.

        Each slug becomes a target processed by get_data().
        """
        events_url = f"{_BASE_URL}/events?south=1"

        try:
            html = await self.fetch_html(events_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events page: {e}",
                self.logger_context,
            )
            return []

        if not html:
            Logger.info(
                f"{self._log_prefix}: empty response from events page",
                self.logger_context,
            )
            return []

        slugs = ComedyWorksSouthExtractor.extract_comedian_slugs(html)

        Logger.info(
            f"{self._log_prefix}: found {len(slugs)} unique comedian slugs",
            self.logger_context,
        )
        return slugs

    async def get_data(self, target: ScrapingTarget) -> Optional[ComedyWorksSouthPageData]:
        """
        Fetch a comedian detail page and extract South showtimes.

        Args:
            target: Comedian slug (e.g. "craig-conant")

        Returns:
            ComedyWorksSouthPageData with the event, or None if no showtimes found
        """
        slug = str(target)
        detail_url = f"{_BASE_URL}/comedians/{slug}"

        try:
            html = await self.fetch_html(detail_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {detail_url}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.info(
                f"{self._log_prefix}: empty response from {detail_url}",
                self.logger_context,
            )
            return None

        events = ComedyWorksSouthExtractor.extract_events_from_detail(html, slug)

        if not events:
            Logger.info(
                f"{self._log_prefix}: no South showtimes for {slug}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: {events[0].name}: {len(events)} showtimes",
            self.logger_context,
        )
        return ComedyWorksSouthPageData(event_list=events)
