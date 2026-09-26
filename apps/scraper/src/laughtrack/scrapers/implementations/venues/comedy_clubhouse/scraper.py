"""
The Comedy Clubhouse scraper (Chicago, IL).

The Comedy Clubhouse (1462 N Ashland Ave, Wicker Park) sells tickets through
TicketSource.  All upcoming shows are listed on a single server-rendered page:

  https://www.ticketsource.com/thecomedyclubhouse

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url)              → fetch HTML, extract ComedyClubhouseEvents
  3. transformation_pipeline    → ComedyClubhouseEvent.to_show() → Show objects
"""

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.comedy_clubhouse import _parse_iso_local
from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity
from laughtrack.foundation.infrastructure.http.client import _bot_block_reason
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyClubhousePageData
from .extractor import ComedyClubhouseExtractor
from .transformer import ComedyClubhouseEventTransformer


class ComedyClubhouseScraper(BaseScraper):
    """Scraper for The Comedy Clubhouse (Wicker Park, Chicago) via TicketSource."""

    key = "comedy_clubhouse"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyClubhouseEventTransformer(club)
        )

    @staticmethod
    def _source_failure(message: str, cause=None) -> DataError:
        error = DataError(message, "comedy_clubhouse_calendar", cause)
        error.severity = ErrorSeverity.HIGH
        return error

    async def get_data(self, url: str) -> ComedyClubhousePageData:
        """Require a complete calendar; failed fetches must prevent reconciliation.

        No venue-specific empty-calendar markup has been verified. Until it is,
        a zero-card response is untrusted, even if it contains an empty notice.
        """
        try:
            html = await self.fetch_html(url)
            if not html or not html.strip():
                raise self._source_failure(f"Mandatory calendar returned no HTML: {url}")

            signature = _bot_block_reason(html)
            if signature:
                diagnostics = current_diagnostics()
                if diagnostics is not None:
                    diagnostics.record_bot_block(signature, source="response_body", stage="direct_fetch")
                raise self._source_failure(f"Mandatory calendar blocked ({signature}): {url}")

            events = ComedyClubhouseExtractor.extract_events(html)
            row_count = len(BeautifulSoup(html, "html.parser").select("div.eventRow"))
            if not events or len(events) != row_count:
                raise self._source_failure(
                    f"Unverified or incomplete calendar: {len(events)}/{row_count} event rows at {url}"
                )
            if any(_parse_iso_local(event.start_iso, self.club.timezone or "America/Chicago") is None
                   for event in events):
                raise self._source_failure(f"Calendar contains invalid performance times: {url}")
            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ComedyClubhousePageData(event_list=events)
        except Exception as exc:
            if isinstance(exc, DataError) and exc.severity == ErrorSeverity.HIGH:
                raise
            raise self._source_failure(f"Mandatory calendar failed: {url}: {exc}", exc) from exc
