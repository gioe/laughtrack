"""Extractor for the Ventura Improv Company "Coming Up" block on /shows.

The page is a hand-maintained WordPress (GenerateBlocks) layout with a single
"Coming Up" section listing one upcoming show. We isolate that section, strip it
to text lines, and parse the title, the free-form date line ("FRI July 10 -
7PM", no year), the lowest advertised price, and the off-site (NAMBA Arts)
ticket link. Brittle by nature — log and skip rather than raise when the layout
shifts.
"""

import html as _html
import re
from datetime import date, datetime
from typing import List, Optional

from laughtrack.core.entities.event.ventura_improv import VenturaImprovEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Free-form date line: "FRI July 10 - 7PM" / "Sat August 2 - 7:30 PM".
# weekday (ignored) + month name + day + en-dash/hyphen + time.
_DATE_RE = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s+"
    r"([A-Za-z]+)\s+(\d{1,2})\s*[–—\-]\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*([AP]M)",
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")
# Off-site ticket link (NAMBA Arts Tickera/WooCommerce event page).
_TICKET_HREF_RE = re.compile(r'href="(https://(?:www\.)?nambaarts\.com/[^"]+)"', re.IGNORECASE)

_SHOWS_URL = "https://venturaimprov.com/shows/"


def _strip_tags(html_fragment: str) -> List[str]:
    """Convert an HTML fragment to a list of non-empty, stripped text lines."""
    text = re.sub(r"<script.*?</script>", "", html_fragment, flags=re.S)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = _html.unescape(text)
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _parse_datetime(date_line: str, today: date) -> Optional[str]:
    """Parse "FRI July 10 - 7PM" into a local "YYYY-MM-DD HH:MM:00" string.

    The page carries no year; assume the current year and roll to next year only
    when the resulting date is clearly in the past (so a December page listing a
    January show resolves forward).
    """
    m = _DATE_RE.search(date_line or "")
    if not m:
        return None
    month_str, day_str, hour_str, minute_str, meridiem = m.groups()
    minute = minute_str or "00"
    try:
        parsed = datetime.strptime(
            f"{month_str} {int(day_str)} {today.year} {int(hour_str)}:{minute} {meridiem.upper()}",
            "%B %d %Y %I:%M %p",
        )
    except ValueError:
        return None
    if parsed.date() < today:
        try:
            parsed = parsed.replace(year=today.year + 1)
        except ValueError:
            return None
    return parsed.strftime("%Y-%m-%d %H:%M:00")


class VenturaImprovExtractor:
    """Parses VenturaImprovEvent objects from the /shows 'Coming Up' block."""

    @staticmethod
    def extract_shows(
        html: str, logger_context=None, today: Optional[date] = None
    ) -> List[VenturaImprovEvent]:
        if not html:
            return []
        today = today or date.today()

        lower = html.lower()
        idx = lower.find("coming up")
        if idx == -1:
            Logger.warn("VenturaImprovExtractor: no 'Coming Up' block on /shows", logger_context)
            return []

        # Window from "Coming Up" up to the next major section ("Location" /
        # "Parking" / "Connect"), bounded so a layout shift can't run away.
        window = html[idx:idx + 4000]
        end = re.search(r"Location|Parking|Connect", window[len("coming up"):], re.IGNORECASE)
        block = window[: end.start() + len("coming up")] if end else window

        lines = _strip_tags(block)
        # Drop the heading itself.
        lines = [ln for ln in lines if ln.lower() != "coming up"]

        date_idx = next((i for i, ln in enumerate(lines) if _DATE_RE.search(ln)), None)
        if date_idx is None:
            Logger.warn("VenturaImprovExtractor: no parseable date in 'Coming Up' block", logger_context)
            return []

        dt_str = _parse_datetime(lines[date_idx], today)
        if not dt_str:
            return []

        # The title is the last non-empty line before the date line.
        name = next((ln for ln in reversed(lines[:date_idx]) if ln), "").strip()
        if not name:
            Logger.warn("VenturaImprovExtractor: no show title before date line", logger_context)
            return []

        prices = [float(p) for ln in lines for p in _PRICE_RE.findall(ln)]
        price = min(prices) if prices else None

        href = _TICKET_HREF_RE.search(block)
        ticket_url = href.group(1) if href else _SHOWS_URL

        return [VenturaImprovEvent(name=name, dt_str=dt_str, price=price, ticket_url=ticket_url)]
