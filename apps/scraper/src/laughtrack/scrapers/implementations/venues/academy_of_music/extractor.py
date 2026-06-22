"""Parse Academy of Music WP REST ``aom_event`` records into events."""

import html as html_lib
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict

from .data import AcademyOfMusicEvent

_BASE_URL = "https://aomtheatre.com"
_DEFAULT_TZ = "America/New_York"

# "Friday, October 9th, 2026 at 8:00pm" (the ordinal suffix is stripped first).
# Collapse an optional space before the meridiem and uppercase it, so both the
# canonical "8:00pm" and a spaced "8:00 pm" variant normalize to "8:00PM" before
# strptime's "%I:%M%p" (which has no space). (%p is case-insensitive in CPython,
# but normalizing keeps the format string honest.)
_ORDINAL_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)", re.IGNORECASE)
_AMPM_RE = re.compile(r"\s*([AaPp][Mm])\b")
_DATE_FMT = "%A, %B %d, %Y %I:%M%p"
_PRICE_RE = re.compile(r"\$?\s*(\d+(?:\.\d{1,2})?)")


def _div_text(html: str, css_class: str) -> Optional[str]:
    """Return the inner text of the first ``<div class="css_class">``."""
    m = re.search(r'class="' + re.escape(css_class) + r'">(.*?)</div>', html, re.S)
    if not m:
        return None
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip()


def _parse_datetime(raw: Optional[str], tz: str) -> Optional[datetime]:
    """Parse 'Friday, October 9th, 2026 at 8:00pm' → tz-aware datetime."""
    if not raw:
        return None
    cleaned = _ORDINAL_RE.sub(r"\1", raw).replace(" at ", " ").strip()
    cleaned = _AMPM_RE.sub(lambda m: m.group(1).upper(), cleaned)
    try:
        return datetime.strptime(cleaned, _DATE_FMT).replace(tzinfo=ZoneInfo(tz))
    except (ValueError, KeyError):
        return None


def _parse_price(raw: Optional[str]) -> Optional[float]:
    """Lowest advertised price; 0.0 for explicit FREE; None when unknown."""
    if not raw:
        return None
    if "free" in raw.lower():
        return 0.0
    m = _PRICE_RE.search(raw)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _ticket_url(html: str) -> str:
    """Absolute /purchase-tickets/?eventId=<id> link, when present."""
    m = re.search(r'href="(/purchase-tickets/\?eventId=\d+)"', html)
    return urljoin(_BASE_URL, m.group(1)) if m else ""


class AcademyOfMusicExtractor:
    @staticmethod
    def extract_events(records: List[JSONDict], tz: str = _DEFAULT_TZ) -> List[AcademyOfMusicEvent]:
        events: List[AcademyOfMusicEvent] = []
        for record in records or []:
            title = html_lib.unescape(((record.get("title") or {}).get("rendered") or "").strip())
            content = (record.get("content") or {}).get("rendered") or ""
            date = _parse_datetime(_div_text(content, "event_start_full"), tz)
            if not title or not date:
                # Skip events with non-standard date formats (e.g. multi-date
                # specials) rather than emit a show with a bad/blank date.
                if title:
                    Logger.debug(f"academy_of_music: skipping unparseable event '{title}'")
                continue
            show_page_url = (record.get("link") or "").strip() or _BASE_URL
            events.append(
                AcademyOfMusicEvent(
                    title=title,
                    date=date,
                    show_page_url=show_page_url,
                    ticket_url=_ticket_url(content),
                    price=_parse_price(_div_text(content, "ticket_price")),
                )
            )
        return events
