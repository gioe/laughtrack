"""Scraper for Rick Bronson's House of Comedy Phoenix."""

from datetime import date
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import HouseOfComedyPhoenixPageData
from .extractor import HouseOfComedyPhoenixExtractor
from .transformer import HouseOfComedyPhoenixTransformer

_DEFAULT_SOURCE_URL = "https://az.houseofcomedy.net/upcoming-comedy-shows/"
_DEFAULT_AJAX_URL = "https://az.houseofcomedy.net/wp-admin/admin-ajax.php"
_MONTH_LOOKAHEAD = 8


class HouseOfComedyPhoenixScraper(BaseScraper):
    """Fetch Phoenix shows from the site's ShowClix WordPress AJAX endpoint."""

    key = "house_of_comedy_phoenix"
    default_source_url = _DEFAULT_SOURCE_URL
    default_ajax_url = _DEFAULT_AJAX_URL

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(HouseOfComedyPhoenixTransformer(club))

    @staticmethod
    def _today() -> date:
        return date.today()

    @property
    def _source_url(self) -> str:
        return self.club.scraping_url or self.default_source_url

    @property
    def _ajax_url(self) -> str:
        return self.club.metadata_value("ajax_url") or self.default_ajax_url

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        today = self._today()
        targets: List[ScrapingTarget] = []
        year = today.year
        month = today.month
        for _ in range(_MONTH_LOOKAHEAD):
            targets.append(f"{year:04d}-{month:02d}")
            month += 1
            if month > 12:
                month = 1
                year += 1
        return targets

    async def get_data(self, target: str) -> Optional[HouseOfComedyPhoenixPageData]:
        try:
            year_str, month_str = target.split("-", 1)
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            Logger.warn(f"{self._log_prefix}: invalid Phoenix month target {target!r}", self.logger_context)
            return None

        payload = {
            "action": "get_comedy_shows",
            "month": month,
            "year": year,
            "per_page": -1,
            "offset": 0,
            "is_list_view": "false",
        }
        headers = BaseHeaders.get_headers(
            base_type="form",
            domain=self._source_url,
            Accept="*/*",
        )
        headers["x-requested-with"] = "XMLHttpRequest"
        headers["referer"] = self._source_url

        try:
            html = await self.post_form(
                self._ajax_url,
                payload,
                headers=headers,
            )
        except Exception as e:
            Logger.warn(f"{self._log_prefix}: failed to fetch Phoenix AJAX target {target}: {e}", self.logger_context)
            return None

        if not html:
            Logger.info(f"{self._log_prefix}: no AJAX response for {target}", self.logger_context)
            return None

        events = HouseOfComedyPhoenixExtractor.extract_events(
            html,
            year=year,
            month=month,
            source_url=self._source_url,
        )
        if not events:
            Logger.info(f"{self._log_prefix}: no Phoenix events found for {target}", self.logger_context)
            return None

        return HouseOfComedyPhoenixPageData(event_list=events)
