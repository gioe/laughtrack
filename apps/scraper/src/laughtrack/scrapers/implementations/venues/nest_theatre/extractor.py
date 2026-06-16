"""Extractor for The Nest Theatre's VBO Tickets "showevents" grid HTML."""

import html as _html
import re
from datetime import date
from typing import List, Optional

from laughtrack.core.entities.event.nest_theatre import NestTheatreEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Each event is an <div class="EventGridItem EID<eid> EDID<edid> ...
# data-event-name="<title>" ... data-event-category="<cat>" ...>. We only keep
# data-event-category="Live Shows"; "Classes" (camps/workshops/levels) are
# excluded from the venue's public show calendar.
_ITEM_RE = re.compile(
    r'class="EventGridItem EID(\d+) EDID(\d+)[^>]*?'
    r'data-event-name="([^"]*)"[^>]*?'
    r'data-event-category="([^"]*)"',
)

# A clock time like "7:00pm", "8pm", "9:30 PM".
_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", re.IGNORECASE)
# A month/day, optionally with a 4-digit year: "6/19", "7/11/2026".
_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?")
# Dollar amounts: "$15", "$13.00".
_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")


def _strip_tags(html_fragment: str) -> List[str]:
    """Convert an HTML fragment to a list of non-empty, stripped text lines."""
    text = re.sub(r"<script.*?</script>", "", html_fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = _html.unescape(text)
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _parse_price(lines: List[str]) -> Optional[float]:
    """Return the lowest advertised dollar amount, or None when no price shown."""
    prices: List[float] = []
    for ln in lines:
        prices.extend(float(x) for x in _PRICE_RE.findall(ln))
    return min(prices) if prices else None


def _parse_room(lines: List[str]) -> str:
    """Extract the sub-venue/stage from a 'The Nest Theatre - <room>' line."""
    for ln in lines:
        if "Nest Theatre -" in ln:
            return ln.split(" - ", 1)[1].strip()
    return ""


def _parse_datetimes(date_line: str, today: date) -> List[str]:
    """Parse a free-form VBO date line into local 'YYYY-MM-DD HH:MM:00' strings.

    Handles single ("Wed 6/17 7:00pm") and recurring ("Fri 9:30pm 6/5, 6/12,
    6/19, ...") listings, emitting one datetime per upcoming date. Past dates
    are dropped; a single bare-year date that has already passed rolls to next
    year (it is next year's show), while past dates inside a recurring list are
    simply skipped.
    """
    if not date_line:
        return []
    tm = _TIME_RE.search(date_line)
    if not tm:
        return []
    hour = int(tm.group(1))
    minute = int(tm.group(2) or 0)
    meridiem = tm.group(3).lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    matches = _DATE_RE.findall(date_line)
    if not matches:
        return []
    multi = len(matches) > 1

    out: List[str] = []
    for month_s, day_s, year_s in matches:
        month, day = int(month_s), int(day_s)
        year = int(year_s) if year_s else today.year
        try:
            cand = date(year, month, day)
        except ValueError:
            continue
        if cand < today:
            if multi or year_s:
                continue  # past occurrence of a recurring show, or an explicit past year
            try:
                cand = date(year + 1, month, day)  # single bare-year date → next year's show
            except ValueError:
                continue
        out.append(f"{cand.isoformat()} {hour:02d}:{minute:02d}:00")
    return out


class NestTheatreEventExtractor:
    """Parses NestTheatreEvent objects from the VBO showevents grid HTML."""

    @staticmethod
    def extract_shows(
        html: str, logger_context=None, today: Optional[date] = None
    ) -> List[NestTheatreEvent]:
        if not html:
            return []
        today = today or date.today()

        events: List[NestTheatreEvent] = []
        # Split on each grid item so per-item text stays isolated.
        for block in re.split(r'(?=class="EventGridItem EID)', html):
            m = _ITEM_RE.match(block)
            if not m:
                continue
            _eid, _edid, raw_name, category = m.groups()
            if category.strip().lower() != "live shows":
                continue

            name = _html.unescape(raw_name).strip()
            if not name:
                continue

            lines = _strip_tags(block)
            room = _parse_room(lines)
            price = _parse_price(lines)
            date_line = next(
                (ln for ln in lines if _DATE_RE.search(ln) and _TIME_RE.search(ln)),
                next((ln for ln in lines if _DATE_RE.search(ln)), ""),
            )

            for dt_str in _parse_datetimes(date_line, today):
                events.append(
                    NestTheatreEvent(name=name, dt_str=dt_str, room=room, price=price)
                )

        if not events and logger_context is not None:
            Logger.warn(
                "NestTheatreEventExtractor: no Live Shows parsed from VBO grid",
                logger_context,
            )
        return events
