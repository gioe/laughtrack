"""Data model for CIC Theater recurring shows."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class CicTheaterEvent(ShowConvertible):
    """One generated CIC Theater show instance from the public recurring schedule."""

    title: str
    date: str
    time: str
    source_url: str
    venue_note: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            time_obj = datetime.strptime(self.time.strip(), "%I:%M %p")
            dt_str = f"{self.date} {time_obj.hour:02d}:{time_obj.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str,
                club.timezone or "America/Chicago",
            )
        except Exception:
            return None

        source_url = url or self.source_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(source_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "CIC Theater Show",
            club=club,
            date=start_date,
            show_page_url=source_url,
            lineup=[],
            tickets=tickets,
            description=self.venue_note or None,
            room=self._room_name(),
            supplied_tags=["event", "improv"],
            enhanced=enhanced,
        )

    def _room_name(self) -> str:
        if "The Western Bar & Kitchen" in self.venue_note:
            return "The Western Bar & Kitchen"
        if "Finley Dunnes" in self.venue_note:
            return "Finley Dunnes Tavern"
        return ""
