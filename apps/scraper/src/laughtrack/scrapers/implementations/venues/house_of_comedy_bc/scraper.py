"""Scraper for House of Comedy British Columbia."""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.tixr.webflow_day_card import (
    WebflowDayCardConfig,
    WebflowDayCardExtractor,
    WebflowDayCardPageData,
    WebflowDayCardTransformer,
)
from laughtrack.shared.types import ScrapingTarget

_DEFAULT_SOURCE_URL = "https://bc.houseofcomedy.net/"
_CONFIG = WebflowDayCardConfig(tixr_group_fragment="tixr.com/groups/comicstripbc/events/")


class HouseOfComedyBcScraper(BaseScraper):
    """Fetch BC shows from Webflow event cards with Tixr ticket links."""

    key = "house_of_comedy_bc"
    default_source_url = _DEFAULT_SOURCE_URL
    config = _CONFIG

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(WebflowDayCardTransformer(club))

    @property
    def _source_url(self) -> str:
        return self.club.scraping_url or self.default_source_url

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        return [self._source_url]

    async def get_data(self, target: ScrapingTarget) -> Optional[WebflowDayCardPageData]:
        url = str(target or self._source_url)
        html = await self.fetch_html(url)
        if not html:
            Logger.warn(f"{self._log_prefix}: empty BC homepage response: {url}", self.logger_context)
            return None

        events = WebflowDayCardExtractor.extract_events(html, source_url=url, config=self.config)
        if not events:
            Logger.warn(f"{self._log_prefix}: no BC Webflow event cards found: {url}", self.logger_context)
            return None

        return WebflowDayCardPageData(event_list=events)
