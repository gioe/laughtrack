"""Extractor for CIC Theater's recurring public schedule."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.cic_theater import CicTheaterEvent

_DEFAULT_WEEKS = 8
_DEFAULT_TIME = "8:00 PM"
_VENUE_PATTERNS = (
    re.compile(r"The Western Bar\s*&\s*Kitchen\s+4301\s+N\s+Western\s+Ave", re.IGNORECASE),
    re.compile(r"Finley Dunnes Tavern\s+3458\s+N\s+Lincoln\s+Ave", re.IGNORECASE),
)


@dataclass(frozen=True)
class _RecurringShow:
    title: str
    weekday: int
    time: str = _DEFAULT_TIME


class CicTheaterExtractor:
    """Parse recurring show copy and expand it into dated near-future events."""

    @staticmethod
    def extract_events(
        html: str,
        *,
        source_url: str,
        today: date | None = None,
        weeks: int = _DEFAULT_WEEKS,
    ) -> List[CicTheaterEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        shows = CicTheaterExtractor._detect_recurring_shows(text)
        if not shows:
            return []

        venue_note = CicTheaterExtractor._extract_venue_note(text)
        start = today or date.today()
        events: List[CicTheaterEvent] = []
        for week in range(weeks):
            week_start = start + timedelta(days=week * 7)
            for show in shows:
                event_date = CicTheaterExtractor._next_weekday(week_start, show.weekday)
                events.append(
                    CicTheaterEvent(
                        title=show.title,
                        date=event_date.isoformat(),
                        time=show.time,
                        source_url=source_url,
                        venue_note=venue_note,
                    )
                )

        return sorted(events, key=lambda event: (event.date, event.time, event.title))

    @staticmethod
    def _detect_recurring_shows(text: str) -> List[_RecurringShow]:
        lower = text.lower()
        if "wednesday" not in lower or "thursday" not in lower or "8pm" not in lower:
            return []

        shows: List[_RecurringShow] = []
        if "byot" in lower or "bring your own team" in lower:
            shows.append(_RecurringShow(title="BYOT", weekday=2))
        if "open stage" in lower and "da 3 jokers" in lower:
            shows.append(_RecurringShow(title="Open Stage hosted by Da 3 Jokers", weekday=3))

        return shows

    @staticmethod
    def _extract_venue_note(text: str) -> str:
        for pattern in _VENUE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return ""

    @staticmethod
    def _next_weekday(start: date, weekday: int) -> date:
        delta = (weekday - start.weekday()) % 7
        return start + timedelta(days=delta)
