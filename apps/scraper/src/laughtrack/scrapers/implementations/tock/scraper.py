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
from laughtrack.foundation.infrastructure.http.client import _bot_block_reason, _get_js_browser, HttpClient, with_decodo_session
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.tock.data import TockPageData
from laughtrack.scrapers.implementations.tock.extractor import extract_tock_events, _extract_redux_state
from laughtrack.scrapers.implementations.tock.availability import extract_reservations, VENUES
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
            business_id = {11073: 29114, 16048: 27051}.get(self.club.id)
            if business_id is not None:
                expected_url = "https://www.exploretock.com/" + VENUES[business_id][0]
                if str(target).rstrip("/") != expected_url:
                    raise self._source_failure("BATSU Tock source URL does not match configured venue")
                return await self._get_batsu_data(str(target), business_id)
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

    async def _get_batsu_data(self, target, business_id):
        """Recover affirmed dated reservations, never infer cancellations."""
        if self.club.timezone != VENUES[business_id][1]:
            raise self._source_failure("BATSU timezone does not match verified venue")
        reservations, html = None, None
        diagnostics = current_diagnostics()
        message = "Tock dated reservation snapshot is partial; missing groups are not cancellations; blocking stale reconciliation"
        if diagnostics is not None:
            diagnostics.record_fetch_failed()
            diagnostics.record_scrape_error(message)
        Logger.warn(message)
        try:
            browser = _get_js_browser()
            if browser is None:
                raise ValueError("Tock calendar browser unavailable")
            proxy = with_decodo_session(HttpClient.resolve_proxy_url("tock"))
            html, payload = await browser.fetch_tock_calendar(target, str(business_id), proxy_url=proxy)
            reservations = extract_reservations(
                html, payload, source_url=target, business_id=business_id, timezone=self.club.timezone,
            )
        except Exception as exc:
            failure = f"Tock dated reservation recovery failed: {type(exc).__name__}"
            Logger.warn(failure)
            if diagnostics is not None:
                diagnostics.record_scrape_error(failure)
            # Existing independently dated GA inventory still survives a failed
            # reservation feed. The source identity must be verified below.
            if not html:
                html = await self.fetch_html(target)
        state = _extract_redux_state(html or "")
        business = state.get("app", {}).get("config", {}).get("business", {})
        if (business.get("id") != business_id or business.get("name") != VENUES[business_id][2]
                or state.get("app", {}).get("activeAuth", {}).get("businessId") != business_id):
            raise self._source_failure("Tock fallback business identity mismatch")
        events = extract_tock_events(
            html, source_url=target, timezone=self.club.timezone,
            comedy_filter=is_comedy_filter_enabled(self.club.source_metadata), reservation_events=reservations,
        )
        return TockPageData(events)

    def transform_data(
        self,
        raw_data: TockPageData,
        source_url_or_identifier: ScrapingTarget,
    ) -> List[Show]:
        return super().transform_data(raw_data, source_url_or_identifier)
