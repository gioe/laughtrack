"""Event model for World Stage (formerly World Cafe Live).

The Lounge at World Stage and the venue's other rooms publish their schedule
through the public Ciright calendar API rather than per-event detail pages,
so each scraped event collapses to a single row containing title, date, time,
and room name. The same model is reusable for any World Stage room — the
scraper filters on roomId at fetch time.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class WorldStageEvent(ShowConvertible):
    """One confirmed event from the World Stage Ciright calendar API."""

    event_id: int
    title: str
    start_date: str  # MM/DD/YYYY as returned by Ciright
    time: str  # "03:00 PM - 11:00 PM" or "All Day"
    room: str
    source_url: str

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        start = _parse_start(self.start_date, self.time, club.timezone or "America/New_York")
        if start is None:
            return None

        link = url or self.source_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(link)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "World Stage Show",
            club=club,
            date=start,
            show_page_url=link,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
            room=self.room,
        )


def _parse_start(start_date: str, time_str: str, timezone: str) -> Optional[datetime]:
    """Parse Ciright's MM/DD/YYYY + 'HH:MM AM/PM - HH:MM AM/PM' into a tz-aware datetime.

    Falls back to 19:00 (typical Lounge showtime) when the time field is 'All Day'
    or otherwise unparseable; the date is the dedup key in (clubId, date, room),
    so a guessed start time still produces a usable, deduplicable row.
    """
    try:
        date_obj = datetime.strptime(start_date.strip(), "%m/%d/%Y")
    except ValueError:
        return None

    hour, minute = _parse_first_clock(time_str)
    dt_str = f"{date_obj.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}:00"
    return ShowFactoryUtils.parse_datetime_with_timezone_fallback(dt_str, timezone)


def _parse_first_clock(time_str: str) -> tuple[int, int]:
    cleaned = (time_str or "").strip()
    for token in cleaned.replace(" - ", "|").split("|"):
        token = token.strip()
        try:
            t = datetime.strptime(token.upper(), "%I:%M %p")
            return t.hour, t.minute
        except ValueError:
            continue
    return 19, 0
