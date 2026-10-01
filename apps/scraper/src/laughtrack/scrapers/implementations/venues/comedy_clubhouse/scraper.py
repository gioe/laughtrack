"""
The Comedy Clubhouse scraper (Chicago, IL).

The approved organizer uses TicketSource's published promoter-list POST endpoint
and requires a validated EOF after every performance page. The legacy HTML
extractor remains supported, but explicit unfinished pagination is not complete.
"""

import asyncio
import json
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.comedy_clubhouse import _parse_iso_local
from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity
from laughtrack.foundation.infrastructure.http.client import _bot_block_reason
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .calendar import ENDPOINT, PAGE_SIZE, MAX_PAGES, is_organizer_url, parse_page
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
            if self.club.id == 189 and is_organizer_url(url):
                return await self._get_public_calendar()
            html = await self.fetch_html(url)
            if not html or not html.strip():
                raise self._source_failure(f"Mandatory calendar returned no HTML: {url}")

            signature = _bot_block_reason(html)
            if signature:
                diagnostics = current_diagnostics()
                if diagnostics is not None:
                    diagnostics.record_bot_block(signature, source="response_body", stage="direct_fetch")
                raise self._source_failure(f"Mandatory calendar blocked ({signature}): {url}")

            soup = BeautifulSoup(html, "html.parser")
            if soup.body and soup.body.has_attr("data-initialeof") and soup.body.get("data-initialeof") not in {"true", "1"}:
                raise self._source_failure(f"TicketSource HTML calendar has unconsumed pagination: {url}")
            events = ComedyClubhouseExtractor.extract_events(html)
            row_count = len(soup.select("div.eventRow"))
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

    async def _get_public_calendar(self):
        """Only a validated EOF permits a successful calendar result."""
        if self.club.timezone != "America/Chicago":
            raise self._source_failure("TicketSource organizer timezone must be America/Chicago")
        events, identities, bookings, slots = [], set(), set(), set()
        for page in range(MAX_PAGES):
            offset = 1 + page * PAGE_SIZE
            body = urlencode({"promoterid": "KEGG", "localtimeoffset": "-360", "eventrefno": "", "startat": offset})
            text = await asyncio.wait_for(self.post_form(
                ENDPOINT, body,
                headers={"Referer": "https://www.ticketsource.com/thecomedyclubhouse", "X-Requested-With": "XMLHttpRequest"},
            ), timeout=30)
            signature = _bot_block_reason(text or "")
            if signature:
                diagnostics = current_diagnostics()
                if diagnostics is not None:
                    diagnostics.record_bot_block(signature, source="response_body", stage="direct_fetch")
                raise self._source_failure(f"TicketSource public calendar blocked ({signature}) at offset {offset}")
            eof, rows = parse_page(json.loads(text))
            for identity, event in rows:
                if identity in identities or event.ticket_url in bookings or event.start_iso in slots:
                    raise self._source_failure(f"Repeated or conflicting TicketSource performance at offset {offset}")
                identities.add(identity)
                bookings.add(event.ticket_url)
                slots.add(event.start_iso)
                events.append(event)
            if eof:
                Logger.info(f"{self._log_prefix}: verified complete TicketSource calendar: {len(events)} performances, {page + 1} pages")
                return ComedyClubhousePageData(event_list=events)
        raise self._source_failure(f"TicketSource calendar did not reach EOF within {MAX_PAGES} pages")
