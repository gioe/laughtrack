"""Event model for SeeTickets/Eventim whitelabel storefront cards."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class SeeTicketsWhitelabelEvent(ShowConvertible):
    event_id: str
    name: str
    start_date: str
    ticket_url: str
    location: str = ""
    image_url: str = ""
    # Real showtime parsed from the event detail page's JSON-LD startDate
    # (ISO 8601, e.g. "2026-06-29T20:00"). The search-results card carries only
    # a date, so without this the show lands at local midnight. Empty when the
    # detail-page enrichment failed or found no timed startDate; to_show then
    # refuses the unverified performance rather than fabricating midnight.
    start_datetime: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: str | None = None):
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.name or not self.start_date or not self.ticket_url:
            return None

        try:
            tz = ZoneInfo(club.timezone or "America/New_York")
        except Exception:
            tz = ZoneInfo("America/New_York")

        show_date = self._resolve_show_date(tz)
        if show_date is None:
            return None

        tickets = [ShowFactoryUtils.create_fallback_ticket(self.ticket_url)]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=show_date,
            show_page_url=url or self.ticket_url,
            tickets=tickets,
            enhanced=enhanced,
        )

    def _resolve_show_date(self, tz: ZoneInfo) -> datetime | None:
        """Use only an explicitly timed detail value; never synthesize midnight."""
        if not self.start_datetime or not re.search(r"T\d{2}:\d{2}", self.start_datetime):
            return None
        try:
            dt = datetime.fromisoformat(self.start_datetime)
        except ValueError:
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=tz)
