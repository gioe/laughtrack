"""Rumor's Comedy Club scraper implementation."""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import RumorsComedyClubPageData
from .extractor import RumorsComedyClubExtractor
from .transformer import RumorsComedyClubTransformer


class RumorsComedyClubScraper(BaseScraper):
    """Scraper for Rumor's Comedy Club in Winnipeg."""

    key = "rumors_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(RumorsComedyClubTransformer(club))

    async def get_data(self, url: str) -> Optional[RumorsComedyClubPageData]:
        try:
            page_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(page_url, scraper_key=self.key)
            if not html_content:
                return RumorsComedyClubPageData(event_list=[])

            events = RumorsComedyClubExtractor.extract_events(html_content)
            Logger.info(f"{self._log_prefix}: extracted {len(events)} Rumor's event(s)", self.logger_context)
            return RumorsComedyClubPageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to scrape Rumor's Comedy Club: {e}", self.logger_context)
            return None
