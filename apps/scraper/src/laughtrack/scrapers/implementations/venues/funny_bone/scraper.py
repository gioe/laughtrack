"""
Funny Bone Comedy Club scraper.

Single-page scraper for funnybone.com venues. All event data (title, date,
time, prices, ticket URL) is available on the shows listing page — no
per-event detail fetching is needed.

Uses the Rockhouse Partners WordPress theme (class="rhpSingleEvent" cards).
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import FunnyBonePageData
from .extractor import FunnyBoneExtractor
from .transformer import FunnyBoneEventTransformer


class FunnyBoneScraper(BaseScraper):
    """
    Scraper for Funny Bone Comedy Club venues (funnybone.com).

    All event data is extracted from the single shows listing page.
    """

    key = "funny_bone"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(FunnyBoneEventTransformer(club))

    async def discover_urls(self) -> List[str]:
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[FunnyBonePageData]:
        try:
            normalized_url = URLUtils.normalize_url(url)
            html = await self.fetch_html(normalized_url)

            if not html:
                Logger.warn(f"{self._log_prefix}: No HTML returned from {normalized_url}", self.logger_context)
                return None

            events = FunnyBoneExtractor.extract_events(html)

            if not events:
                Logger.warn(f"{self._log_prefix}: No events found on {normalized_url}", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Extracted {len(events)} events", self.logger_context)
            return FunnyBonePageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error in get_data: {e}", self.logger_context)
            return None
