"""
SeatEngine Classic scraper.

Handles venues on the legacy SeatEngine platform (cdn.seatengine.com),
which renders events as server-side HTML rather than the
services.seatengine.com REST API used by the newer platform.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url.utils import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.ports.scraping import EventListContainer

from .extractor import SeatEngineClassicExtractor
from .page_data import SeatEngineClassicPageData
from .transformer import SeatEngineClassicTransformer


class SeatEngineClassicScraper(BaseScraper):
    """
    Scraper for venues on the classic SeatEngine platform.

    These venues serve a server-rendered HTML events page at their
    custom domain (e.g. newbrunswick.stressfactory.com/events).
    The new services.seatengine.com REST API returns empty data for
    these venues, so we parse the HTML page directly.

    DB column: clubs.scraper = 'seatengine_classic'
    """

    key = "seatengine_classic"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            SeatEngineClassicTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Return the events page URL as the single scraping target."""
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        """Fetch the events page and extract shows from the HTML."""
        html = await self.fetch_html(url)
        if not html:
            Logger.warn(
                f"{self._log_prefix}: no HTML returned for {url}",
                self.logger_context,
            )
            return SeatEngineClassicPageData(event_list=[])

        base_url = URLUtils.get_base_domain_with_protocol(url)
        shows = SeatEngineClassicExtractor.extract_shows(html, base_url)
        Logger.info(
            f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
            self.logger_context,
        )
        return SeatEngineClassicPageData(event_list=shows)

    def transform_data(self, raw_data: EventListContainer, source_url: str) -> List[Show]:
        return super().transform_data(raw_data, source_url)
