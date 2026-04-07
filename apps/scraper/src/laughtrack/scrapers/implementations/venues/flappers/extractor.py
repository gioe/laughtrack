"""HTML extractor for Flappers calendar pages."""

import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.flappers import FlappersEvent

_TIME_RE = re.compile(r"\d{1,2}(?::\d{2})?\s*(?:AM|PM)", re.IGNORECASE)

# Room name normalization
_ROOM_MAP = {
    "main room": "Main Room",
    "mainroom": "Main Room",
    "yoo hoo room": "Yoo Hoo Room",
    "bar": "Bar",
    "patio": "Patio",
}


def _normalize_room(raw: str) -> str:
    """Normalize room text from the button content."""
    lower = raw.lower().strip()
    for key, val in _ROOM_MAP.items():
        if key in lower:
            return val
    return raw.strip()


def _extract_month_year(url: str) -> tuple[int, int]:
    """Extract month and year from calendar URL query params."""
    from datetime import date

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    today = date.today()
    month = int(qs.get("month", [str(today.month)])[0])
    year = int(qs.get("year", [str(today.year)])[0])
    return month, year


class FlappersEventExtractor:
    """Static extractor for Flappers calendar HTML."""

    @staticmethod
    def extract_shows(html: str, url: str = "", timezone: str = "America/Los_Angeles") -> List[FlappersEvent]:
        """Parse Flappers calendar HTML and return all show events.

        Each calendar day cell (<td>) contains <form> elements with
        <button class="event-btn"> holding show data:
          - <b> tag: show title
          - Text after <br>: room name, time
          - Hidden input name="event_id": event ID
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[FlappersEvent] = []

        month, year = _extract_month_year(url) if url else (0, 0)

        for td in soup.find_all("td"):
            # Get the day number from <strong> tag
            day_tag = td.find("strong")
            if not day_tag:
                continue
            try:
                day = int(day_tag.get_text(strip=True))
            except ValueError:
                continue

            # Each form is one show
            for form in td.find_all("form"):
                event = FlappersEventExtractor._parse_form(
                    form, year, month, day, timezone
                )
                if event:
                    events.append(event)

        return events

    @staticmethod
    def _parse_form(
        form: Tag, year: int, month: int, day: int, timezone: str
    ) -> Optional[FlappersEvent]:
        """Parse a single <form> element into a FlappersEvent."""
        # Event ID from hidden input
        event_id_input = form.find("input", {"name": "event_id"})
        if not event_id_input:
            return None
        event_id = event_id_input.get("value", "")
        if not event_id:
            return None

        btn = form.find("button", class_="event-btn")
        if not btn:
            return None

        # Title from <b> tag
        title_tag = btn.find("b")
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        if not title:
            return None

        # Room from data-type attribute
        data_type = btn.get("data-type", "")
        room = _normalize_room(data_type) if data_type else ""

        # Time: find text matching time pattern in the button's content
        btn_text = btn.get_text(separator="\n", strip=True)
        time_match = _TIME_RE.search(btn_text)
        time_str = time_match.group(0) if time_match else ""

        if not time_str:
            return None

        return FlappersEvent(
            title=title,
            event_id=event_id,
            year=year,
            month=month,
            day=day,
            time_str=time_str,
            timezone=timezone,
            room=room,
        )
