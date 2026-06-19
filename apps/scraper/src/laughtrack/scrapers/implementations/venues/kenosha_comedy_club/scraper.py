"""Kenosha Comedy Club scraper.

The venue's domain redirects to Happenings Magazine, where Kenosha Comedy Club
shows are maintained as WordPress posts in category 506. The Events Calendar
REST API is present on the site but currently empty for these shows, so this
scraper reads the WordPress posts endpoint directly.
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import KenoshaComedyClubPageData
from .extractor import KenoshaComedyClubExtractor
from .transformer import KenoshaComedyClubTransformer


class KenoshaComedyClubScraper(BaseScraper):
    """Scraper for Happenings Magazine's Kenosha Comedy Club category posts."""

    key = "kenosha_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(KenoshaComedyClubTransformer(club))

    async def get_data(self, url: str) -> Optional[KenoshaComedyClubPageData]:
        try:
            response = await self.fetch_json(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to fetch Kenosha Comedy Club posts: {e}", self.logger_context)
            return None

        if not response:
            self._warn_empty_extraction(url)
            return None

        events = KenoshaComedyClubExtractor.extract_events(response, self.logger_context)
        if not events:
            self._warn_empty_extraction(url, extra={"payload_type": type(response).__name__})
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} Kenosha Comedy Club event(s)",
            self.logger_context,
        )
        return KenoshaComedyClubPageData(event_list=events)
