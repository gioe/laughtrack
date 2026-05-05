"""Event model for Palm Beach Improv at the Kravis Center."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger


_DATE_FORMATS = (
    "%a, %b %d %Y @ %I:%M%p",
    "%a, %b %d %Y @ %I:%M %p",
)
_DEFAULT_TIMEZONE = "America/New_York"


def _parse_kravis_datetime(date_str: str, timezone_name: str) -> Optional[datetime]:
    """Parse Kravis calendar dates like ``Sun, May 31 2026 @ 2:00pm``."""
    try:
        tz = pytz.timezone(timezone_name)
    except pytz.UnknownTimeZoneError:
        Logger.warn(
            f"PalmBeachImprovEvent: unknown timezone {timezone_name!r}; "
            f"falling back to {_DEFAULT_TIMEZONE}"
        )
        tz = pytz.timezone(_DEFAULT_TIMEZONE)
    normalized = " ".join((date_str or "").replace("\xa0", " ").split())
    for fmt in _DATE_FORMATS:
        try:
            naive = datetime.strptime(normalized, fmt)
            return tz.localize(naive)
        except ValueError:
            continue
    return None


@dataclass
class PalmBeachImprovEvent(ShowConvertible):
    """A single Palm Beach Improv performance from the Kravis calendar API."""

    title: str
    date_str: str
    event_url: str
    location: str = ""
    thumbnail: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert the Kravis performance item into a Show."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.event_url:
            return None

        start_dt = _parse_kravis_datetime(
            self.date_str, club.timezone or "America/New_York"
        )
        if start_dt is None:
            return None

        show_url = url or self.event_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(show_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
            room=self.location or None,
        )
