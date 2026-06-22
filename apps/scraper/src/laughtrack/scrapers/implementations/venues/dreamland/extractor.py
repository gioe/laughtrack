"""Parse the Nantucket Dreamland Live Comedy archive HTML into events."""

import html as html_lib
import re
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from laughtrack.foundation.infrastructure.logger.logger import Logger

from .data import DreamlandEvent

_DEFAULT_TZ = "America/New_York"

# Each archive card: a square image figure, then the show-title anchor, then an
# AgileTicketing "next-event" link carrying the date/time/room + buy URL.
_CARD_SPLIT_RE = re.compile(r'class="event-image-wrap"')
_TITLE_RE = re.compile(r'class="show-title">(.*?)</h3>', re.S)
_DETAIL_RE = re.compile(r'href="(https://www\.nantucketdreamland\.org/events/[^"]+)"')
_NEXT_EVENT_RE = re.compile(
    r'class="agile-link next-event"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S
)
# "Jul 3, 2026 at 8:00 pm in the Main Theater"
_DATETIME_RE = re.compile(
    r"([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\s+at\s+(\d{1,2}:\d{2})\s*([AaPp][Mm])"
)
_ROOM_RE = re.compile(r"in the\s+(.+?)\s*$", re.I)


def _clean(text: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", text)).strip()


def _parse_datetime(date_str: str, time_str: str, ampm: str, tz: str) -> Optional[datetime]:
    stamp = f"{date_str} {time_str} {ampm.upper()}"
    for fmt in ("%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
        try:
            return datetime.strptime(stamp, fmt).replace(tzinfo=ZoneInfo(tz))
        except (ValueError, KeyError):
            continue
    return None


class DreamlandExtractor:
    @staticmethod
    def extract_events(html: str, tz: str = _DEFAULT_TZ) -> List[DreamlandEvent]:
        events: List[DreamlandEvent] = []
        if not html:
            return events
        for chunk in _CARD_SPLIT_RE.split(html)[1:]:
            title_m = _TITLE_RE.search(chunk)
            next_m = _NEXT_EVENT_RE.search(chunk)
            if not title_m or not next_m:
                continue
            title = html_lib.unescape(_clean(title_m.group(1)))
            ticket_url = html_lib.unescape(next_m.group(1).strip())
            meta = _clean(next_m.group(2))
            dt_m = _DATETIME_RE.search(meta)
            if not title or not dt_m:
                continue
            date = _parse_datetime(dt_m.group(1), dt_m.group(2), dt_m.group(3), tz)
            if not date:
                Logger.debug(f"dreamland: unparseable date for '{title}': {meta!r}")
                continue
            detail_m = _DETAIL_RE.search(chunk)
            room_m = _ROOM_RE.search(meta)
            events.append(
                DreamlandEvent(
                    title=title,
                    date=date,
                    show_page_url=(detail_m.group(1) if detail_m else ""),
                    ticket_url=ticket_url,
                    room=(room_m.group(1).strip() if room_m else ""),
                )
            )
        return events
