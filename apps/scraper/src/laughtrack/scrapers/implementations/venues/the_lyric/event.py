"""Data model for a single Indy Systems showing convertible to a Show.

Indy Systems (api-*.indy.systems) is the ticketing/CMS platform behind The Lyric
cinema in Fort Collins, CO (lyriccinema.com). It models *every* screening —
films and live events alike — as a "movie", and exposes a same-origin GraphQL
proxy. We model one ``TheLyricEvent`` per dated public showing so each showtime
persists as its own Show, mirroring how comedy clubs program distinct seatings.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class TheLyricEvent(ShowConvertible):
    """A single Indy Systems showing (one comedy showtime) convertible to a Show."""

    name: str  # Movie/event title, e.g. "Lyric Comedy Show"
    start_dt: str  # Showing start, ISO 8601 with offset (Showing.time)
    show_page_url: str  # The venue's own /movie/<urlSlug> page
    timezone_name: str = "America/Denver"

    def _resolve_date(self) -> Optional[datetime]:
        """Parse the showing start into a timezone-aware datetime.

        ``Showing.time`` arrives as a full ISO 8601 string with offset
        (``2026-07-25T20:00:00-06:00``); the venue timezone is passed as a
        fallback so ``Show.date`` is never naive on the rare offset-less value.
        """
        if not self.start_dt:
            return None
        try:
            return DateTimeUtils.parse_datetime_with_timezone(self.start_dt, self.timezone_name)
        except (ValueError, TypeError):
            return None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this Indy Systems showing to a Show domain object."""
        start_date = self._resolve_date()
        if start_date is None:
            return None

        page_url = url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(page_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
