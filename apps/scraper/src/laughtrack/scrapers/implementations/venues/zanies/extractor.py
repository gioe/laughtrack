"""
HTML extraction for Zanies Comedy Club pages.

Two page types are handled:

- Series pages (/calendar/category/series/...): multiple performances per
  headliner run, rendered as ``li.rhp-event-series-individual`` list items
  inside an accordion widget.
- Single-show pages (/show/...): standalone events with an ``eventStDate``
  span and a "Doors/Show" time span.
"""

import re
from html import unescape
from typing import List, Optional

from laughtrack.core.entities.event.zanies import ZaniesEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _strip_tags(text: str) -> str:
    """Remove all HTML tags from *text* and decode HTML entities."""
    return unescape(re.sub(r"<[^>]+>", "", text)).strip()


# ---------------------------------------------------------------------------
# Series-page patterns
# ---------------------------------------------------------------------------

# Split HTML on each individual-performance list item.
_SERIES_ITEM_SPLIT = re.compile(r'class="[^"]*rhp-event-series-individual[^"]*"')

_SERIES_DATE_RE = re.compile(
    r'class="[^"]*rhp-event-series-date[^"]*"[^>]*>\s*(.*?)\s*</div>',
    re.DOTALL | re.IGNORECASE,
)
_SERIES_TIME_RE = re.compile(
    r'class="[^"]*rhp-event-series-time[^"]*"[^>]*>\s*(.*?)\s*</div>',
    re.DOTALL | re.IGNORECASE,
)
_TICKET_RE = re.compile(
    r'href="(https://www\.etix\.com/ticket/p/[^"]+)"',
    re.IGNORECASE,
)

# Strip a leading 4-digit year from series titles like "2026 Roast Battle".
_YEAR_PREFIX_RE = re.compile(r"^\d{4}\s+")


# ---------------------------------------------------------------------------
# Single-show-page patterns
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL | re.IGNORECASE)

# The eventStDate span uses `class = "..."` (spaces around =) on the live site.
_SINGLE_DATE_RE = re.compile(
    r'class\s*=\s*"[^"]*eventStDate[^"]*"[^>]*>\s*(.*?)\s*</span>',
    re.DOTALL | re.IGNORECASE,
)

# Match the full "Doors: X pm Show: Y pm" string (not crossing tag boundaries).
_SINGLE_TIME_RE = re.compile(
    r"Doors:[^<]*Show:[^<]*(?:am|pm)",
    re.IGNORECASE,
)

_SINGLE_TICKET_RE = re.compile(
    r'href="(https://www\.etix\.com/[^"]+)"',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class ZaniesExtractor:
    """
    Parses HTML from Zanies Comedy Club pages.

    Handles both multi-performance series pages and single-show detail pages.
    """

    @staticmethod
    def extract_series_events(html: str) -> List[ZaniesEvent]:
        """
        Extract all individual performances from a series page.

        The series title is taken from the page's ``<h1>``; each
        ``li.rhp-event-series-individual`` block provides one date/time/ticket.
        Past dates are included — callers may filter as needed.
        """
        if not html:
            return []

        title_m = _TITLE_RE.search(html)
        if not title_m:
            Logger.debug("ZaniesExtractor: no <h1> found on series page")
            return []

        raw_title = _strip_tags(title_m.group(1))
        title = _YEAR_PREFIX_RE.sub("", raw_title).strip()
        if not title:
            return []

        events: List[ZaniesEvent] = []
        # First segment is page preamble, not a performance block.
        blocks = _SERIES_ITEM_SPLIT.split(html)
        for block in blocks[1:]:
            event = ZaniesExtractor._parse_series_block(block, title)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def extract_single_show_events(html: str) -> List[ZaniesEvent]:
        """
        Extract the single event from a ``/show/.../`` page.

        Returns a one-element list on success, or an empty list if any
        required field cannot be extracted.
        """
        if not html:
            return []

        title_m = _TITLE_RE.search(html)
        date_m = _SINGLE_DATE_RE.search(html)
        time_m = _SINGLE_TIME_RE.search(html)
        ticket_m = _SINGLE_TICKET_RE.search(html)

        if not (title_m and date_m and ticket_m):
            Logger.debug(
                "ZaniesExtractor: skipping single-show page — missing title, date, or ticket"
            )
            return []

        title = _strip_tags(title_m.group(1))
        date_str = _strip_tags(date_m.group(1))
        time_str = time_m.group(0).strip() if time_m else ""
        ticket_url = ticket_m.group(1)

        if not title or not date_str or not ticket_url:
            return []

        return [
            ZaniesEvent(
                title=title,
                date_str=date_str,
                time_str=time_str,
                ticket_url=ticket_url,
            )
        ]

    @staticmethod
    def _parse_series_block(block_html: str, title: str) -> Optional[ZaniesEvent]:
        """Parse a single ``li.rhp-event-series-individual`` block."""
        date_m = _SERIES_DATE_RE.search(block_html)
        time_m = _SERIES_TIME_RE.search(block_html)
        ticket_m = _TICKET_RE.search(block_html)

        if not (date_m and ticket_m):
            Logger.debug(
                "ZaniesExtractor: skipping series block — missing date or ticket URL"
            )
            return None

        date_str = _strip_tags(date_m.group(1))
        time_str = _strip_tags(time_m.group(1)) if time_m else ""
        ticket_url = ticket_m.group(1)

        if not date_str or not ticket_url:
            return None

        return ZaniesEvent(
            title=title,
            date_str=date_str,
            time_str=time_str,
            ticket_url=ticket_url,
        )
