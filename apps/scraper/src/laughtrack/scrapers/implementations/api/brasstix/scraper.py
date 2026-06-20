"""Generic scraper for BrassTix inline calendar pages."""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import BrassTixPageData
from .extractor import extract_brasstix_events
from .transformer import BrassTixTransformer


class BrassTixScraper(BaseScraper):
    """Scrape BrassTix calendar.php pages that embed eventArray JS data."""

    key = "brasstix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(BrassTixTransformer(club))

    async def get_data(self, url: str) -> Optional[BrassTixPageData]:
        normalized_url = URLUtils.normalize_url(url)
        try:
            html = await self.fetch_html(normalized_url)
            if not html:
                Logger.warn(f"{self._log_prefix}: BrassTix calendar returned empty HTML: {normalized_url}")
                return None

            events = extract_brasstix_events(html, normalized_url)
            if not events:
                Logger.warn(f"{self._log_prefix}: no BrassTix events found in {normalized_url}")
                return None
            return BrassTixPageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {normalized_url}: {e}", self.logger_context)
            return None
