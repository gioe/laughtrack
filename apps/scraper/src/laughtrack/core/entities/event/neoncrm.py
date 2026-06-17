"""
Data model for a single NeonCRM (Neon One) event.

NeonCRM venues publish a static event list at
``https://{org}.app.neoncrm.com/eventList.jsp?categoryId={N}`` (canonical
``/np/clients/{org}/eventList.jsp``). Each row carries an event name, a detail
URL (``event.jsp?event={id}``), and a date range string of the form
"MM/DD/YYYY HH:MM PM - MM/DD/YYYY HH:MM PM ET". One ``NeonCRMEvent`` is produced
per listed event, using the START of the range as the show datetime.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

# NeonCRM list-page datetime, e.g. "07/16/2026 07:00 PM".
_NEONCRM_DT_FORMAT = "%m/%d/%Y %I:%M %p"


def _parse_neoncrm_datetime(start_date_str: str, timezone_name: str) -> Optional[datetime]:
    """Parse a NeonCRM start datetime ("07/16/2026 07:00 PM") and localize it.

    Returns None if parsing fails.
    """
    try:
        naive = datetime.strptime(start_date_str.strip(), _NEONCRM_DT_FORMAT)
        return pytz.timezone(timezone_name).localize(naive)
    except (ValueError, pytz.UnknownTimeZoneError):
        return None


@dataclass
class NeonCRMEvent(ShowConvertible):
    """A single event scraped from a NeonCRM eventList.jsp page."""

    title: str            # e.g. "Left of Centre Players Improv"
    start_date_str: str   # the range START, e.g. "07/16/2026 07:00 PM"
    show_page_url: str    # the event.jsp?event={id} detail page

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are
        missing or the event start is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_date_str or not self.show_page_url:
            return None

        start_dt = _parse_neoncrm_datetime(
            self.start_date_str, club.timezone or "America/New_York"
        )
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
