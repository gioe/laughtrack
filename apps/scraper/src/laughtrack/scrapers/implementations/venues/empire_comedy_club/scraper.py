"""Empire Comedy Club scraper implementation.

Scrapes the shows listing page at empirecomedyme.com/shows/ which contains
all upcoming events in a single HTML page organized by month sections.
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import EmpirePageData
from .extractor import EmpireEventExtractor
from .transformer import EmpireEventTransformer


class EmpireComedyClubScraper(BaseScraper):
    """Scraper for Empire Comedy Club (Portland, ME).

    The venue's shows page renders all upcoming events as static HTML show cards,
    so a single page fetch extracts everything.
    """

    key = "empire_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EmpireEventTransformer(club))

    async def get_data(self, url: str) -> Optional[EmpirePageData]:
        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)
            if not html_content:
                return None

            event_list = EmpireEventExtractor.extract_events(html_content)
            return EmpirePageData(event_list=event_list)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {e}", self.logger_context)
            return None
