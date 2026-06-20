"""Tock platform scraper.

Tock business pages render the venue calendar into ``window.$REDUX_STATE``.
Plain HTTP sees Cloudflare for many Tock pages, so this scraper uses the shared
Playwright browser helper for the configured business page and parses the
rendered Redux state.
"""

from __future__ import annotations

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.tock.data import TockPageData
from laughtrack.scrapers.implementations.tock.extractor import extract_tock_events
from laughtrack.scrapers.implementations.tock.transformer import TockTransformer
from laughtrack.scrapers.utils.comedy_filter import is_comedy_filter_enabled
from laughtrack.shared.types import ScrapingTarget


class TockScraper(BaseScraper):
    """Scraper for venues hosted on exploretock.com."""

    key = "tock"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TockTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        source_url = self.club.scraping_url
        if not source_url:
            Logger.warn(
                f"{self._log_prefix}: Club has no Tock source_url configured",
                self.logger_context,
            )
            return []
        return [URLUtils.normalize_url(source_url)]

    async def get_data(self, target: ScrapingTarget) -> Optional[TockPageData]:
        try:
            html = await self._fetch_html_with_js(str(target))
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: Tock page returned empty HTML: {target}",
                    self.logger_context,
                )
                return None

            events = extract_tock_events(
                html,
                source_url=str(target),
                timezone=self.club.timezone,
                comedy_filter=is_comedy_filter_enabled(self.club.source_metadata),
            )
            if not events:
                Logger.warn(
                    f"{self._log_prefix}: No Tock events extracted from {target}",
                    self.logger_context,
                )
                return None

            return TockPageData(events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting Tock page {target}: {e}",
                self.logger_context,
            )
            return None

    def transform_data(
        self,
        raw_data: TockPageData,
        source_url_or_identifier: ScrapingTarget,
    ) -> List[Show]:
        return super().transform_data(raw_data, source_url_or_identifier)
