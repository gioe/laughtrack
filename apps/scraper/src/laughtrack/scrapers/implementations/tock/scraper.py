"""Tock platform scraper.

Tock business pages render the venue calendar into ``window.$REDUX_STATE``.
The shared HTTP client applies its configured browser/proxy fallback when
Cloudflare blocks the initial request. Calendar decoding requires verified
performance dates, not aggregate reservation filters.
"""

from __future__ import annotations

from typing import List

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity
from laughtrack.foundation.infrastructure.http.client import _bot_block_reason
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
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

    @staticmethod
    def _source_failure(message: str, cause=None) -> DataError:
        error = DataError(message, "tock_calendar", cause)
        error.severity = ErrorSeverity.HIGH
        return error

    async def get_data(self, target: ScrapingTarget) -> TockPageData:
        """Fail mandatory-source errors so they cannot authorize stale cleanup."""
        try:
            html = await self.fetch_html(str(target))
            if not html or not html.strip():
                raise self._source_failure(f"Tock mandatory calendar returned no HTML: {target}")
            signature = _bot_block_reason(html)
            if signature:
                diagnostics = current_diagnostics()
                if diagnostics is not None:
                    diagnostics.record_bot_block(
                        signature, source="response_body", stage="direct_fetch"
                    )
                raise self._source_failure(f"Tock mandatory calendar blocked ({signature}): {target}")
            events = extract_tock_events(
                html,
                source_url=str(target),
                timezone=self.club.timezone,
                comedy_filter=is_comedy_filter_enabled(self.club.source_metadata),
            )
            return TockPageData(events)
        except Exception as exc:
            if isinstance(exc, DataError) and exc.severity == ErrorSeverity.HIGH:
                raise
            raise self._source_failure(f"Tock mandatory calendar failed at {target}: {exc}", exc) from exc

    def transform_data(
        self,
        raw_data: TockPageData,
        source_url_or_identifier: ScrapingTarget,
    ) -> List[Show]:
        return super().transform_data(raw_data, source_url_or_identifier)
