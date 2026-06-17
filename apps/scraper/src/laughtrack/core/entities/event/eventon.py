"""
Data model for a single EventON (WordPress ajde_events) event occurrence.

EventON is a popular WordPress events-calendar plugin (custom post type
``ajde_events``). Its frontend calendar loads events from
``/wp-admin/admin-ajax.php`` (action ``eventon_init_load``), which returns a
JSON list of event objects carrying ``event_start_unix`` — the event's local
wall-clock time encoded as a UTC unix timestamp. To recover the real local
datetime, format that unix value in UTC to get the naive wall-clock components,
then localize to the club's timezone.

The loader response does not include per-event permalinks; those are joined in
from the WP REST API (``/wp-json/wp/v2/ajde_events?include=<ids>``). One
``EventONEvent`` is produced per (future) occurrence.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


def _eventon_unix_to_local(start_unix: int, timezone_name: str) -> Optional[datetime]:
    """Convert an EventON ``event_start_unix`` to a timezone-aware datetime.

    EventON stores the start time as the local wall-clock encoded as a UTC unix
    timestamp (e.g. a 7 PM show is stored such that formatting in UTC yields
    19:00). So read the naive wall-clock from the UTC projection, then localize
    to *timezone_name*. Returns None on failure.
    """
    try:
        naive = datetime.fromtimestamp(int(start_unix), tz=timezone.utc).replace(tzinfo=None)
        return pytz.timezone(timezone_name).localize(naive)
    except Exception:
        return None


@dataclass
class EventONEvent(ShowConvertible):
    """A single future EventON event occurrence."""

    title: str            # e.g. "Mid-Life Crisis: A Comedy Improv Troupe"
    start_unix: int       # EventON event_start_unix (local wall-clock as UTC)
    show_page_url: str    # the /events/<slug>/ detail page permalink

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are
        missing or the occurrence is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_unix or not self.show_page_url:
            return None

        start_dt = _eventon_unix_to_local(self.start_unix, club.timezone or "America/New_York")
        if start_dt is None:
            return None

        if start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(show_page_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
