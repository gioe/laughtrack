"""
The Comedy & Magic Club scraper.

The Comedy & Magic Club (1018 Hermosa Ave, Hermosa Beach, CA) lists its
upcoming shows via a paginated WordPress page powered by the rhp-events
plugin.  Tickets are sold through eTix.

Pipeline:
  1. collect_scraping_targets() — fetch the first listing page to discover
     the total number of pages; return all page URLs.
  2. get_data(url)              — fetch one listing page and extract events.
  3. transformation_pipeline   — ComedyMagicClubEvent.to_show() → Show.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyMagicClubPageData
from .extractor import ComedyMagicClubExtractor
from .transformer import ComedyMagicClubEventTransformer


class ComedyMagicClubScraper(BaseScraper):
    """Scraper for The Comedy & Magic Club (Hermosa Beach, CA)."""

    key = "comedy_magic_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyMagicClubEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """
        Return the single events listing page URL.

        The Comedy & Magic Club's rhp-events plugin serves the same 40
        upcoming shows on every pagination URL (/events/page/2/ etc.),
        so there is no benefit in fetching more than the base page.
        """
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[ComedyMagicClubPageData]:
        """
        Fetch one listing page and extract all event cards.

        Args:
            url: A listing page URL returned by collect_scraping_targets().

        Returns:
            ComedyMagicClubPageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(URLUtils.normalize_url(url))
            if not html:
                Logger.warn(
                    f"ComedyMagicClubScraper: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = ComedyMagicClubExtractor.extract_events(html)
            if not events:
                Logger.info(
                    f"ComedyMagicClubScraper: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"ComedyMagicClubScraper: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ComedyMagicClubPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"ComedyMagicClubScraper: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
