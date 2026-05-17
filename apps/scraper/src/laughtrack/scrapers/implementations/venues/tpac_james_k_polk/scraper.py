"""TPAC James K. Polk Theater scraper using the official comedy endpoint."""

import re
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import TpacJamesKPolkPageData
from .extractor import TpacJamesKPolkExtractor
from .transformer import TpacJamesKPolkEventTransformer

_DEFAULT_CATEGORY_URL = (
    "https://www.tpac.org/multicategory/category_json/0"
    "?category=5&venue=4&team=0&exclude=&per_page=6&came_from_page=event-list-page"
)
_OFFSET_RE = re.compile(r"(/category_json/)\d+")
_PER_PAGE = 6


class TpacJamesKPolkScraper(BaseScraper):
    """Scraper for TPAC's James K. Polk Theater comedy category."""

    key = "tpac_james_k_polk"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TpacJamesKPolkEventTransformer(club))

    async def collect_scraping_targets(self):
        """Return the configured TPAC category JSON URL."""
        return [self.club.scraping_url or _DEFAULT_CATEGORY_URL]

    async def get_data(self, url: str) -> Optional[TpacJamesKPolkPageData]:
        """Fetch category pages and enrich each event from its detail page."""
        try:
            events = []
            seen: set[str] = set()

            for offset in range(0, 120, _PER_PAGE):
                page_url = self._url_for_offset(url, offset)
                payload = await self.fetch_html(page_url, scraper_key=self.key)
                page_events = TpacJamesKPolkExtractor.extract_category_events(
                    payload or "",
                    page_url,
                )
                if not page_events:
                    break

                for event in page_events:
                    if event.detail_url in seen:
                        continue
                    seen.add(event.detail_url)
                    detail_html = await self.fetch_html(event.detail_url, scraper_key=self.key)
                    enriched = TpacJamesKPolkExtractor.enrich_event_from_detail_page(
                        event,
                        detail_html or "",
                    )
                    if enriched.date_str and enriched.time_str:
                        events.append(enriched)
                    else:
                        Logger.warn(
                            f"{self._log_prefix}: skipped event without detail date/time: {event.detail_url}",
                            self.logger_context,
                        )

            if not events:
                Logger.info(
                    f"{self._log_prefix}: no comedy events found from TPAC endpoint",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} comedy events from TPAC endpoint",
                self.logger_context,
            )
            return TpacJamesKPolkPageData(event_list=events)
        except Exception as exc:
            Logger.error(
                f"{self._log_prefix}: error fetching TPAC endpoint {url}: {exc}",
                self.logger_context,
            )
            return None

    @staticmethod
    def _url_for_offset(url: str, offset: int) -> str:
        return _OFFSET_RE.sub(rf"\g<1>{offset}", url, count=1)
