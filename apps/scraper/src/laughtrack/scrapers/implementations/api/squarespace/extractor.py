"""Squarespace event extraction from GetItemsByMonth API response."""

import re
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Pattern, Sequence
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.squarespace import SquarespaceEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


def _title_allowed(
    title: str,
    include_title_res: Optional[Sequence[Pattern[str]]],
    exclude_title_res: Optional[Sequence[Pattern[str]]],
) -> bool:
    """Apply the opt-in include/exclude title filter to one event title.

    include-then-exclude semantics (mirrors ticketweb / sellingticket):
      - if include patterns are configured, the title must match at least one;
      - if exclude patterns are configured, the title must match none.
    Both default to empty/None → every title is allowed (existing venues
    unaffected).
    """
    if include_title_res and not any(p.search(title) for p in include_title_res):
        return False
    if exclude_title_res and any(p.search(title) for p in exclude_title_res):
        return False
    return True


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_FULL_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _month_num(token: str) -> Optional[int]:
    """Return a month number only for an exact 3-letter abbrev or full month name.

    Exact-membership (not a 3-char prefix of an arbitrary word) so tokens like
    "marathon" don't false-match to March.
    """
    t = (token or "").lower()
    return _MONTHS.get(t) or _FULL_MONTHS.get(t)
# Date in a ticket-product slug, e.g. "/tickets/p/june-19-2026" or
# "/tickets/p/sat-july-11th-show-8pm" -> (june/july, day, optional year).
_SLUG_DATE_RE = re.compile(
    r"([a-z]{3,9})-(\d{1,2})(?:st|nd|rd|th)?(?:-(\d{4}))?",
    re.IGNORECASE,
)
# Leading "Month DD" in a product title, e.g. "June 19: Friday Night Show" or
# "Sat July 11th Rhino Room Stand Up 8pm".
_TITLE_DATE_RE = re.compile(r"\b([a-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE)
# Show time in a product title, e.g. "@8pm", "@ 7:30 pm", or "Stand Up 8pm".
_TITLE_TIME_RE = re.compile(r"(?:@\s*)?\b(\d{1,2})(?::(\d{2}))?\s*([ap])m\b", re.IGNORECASE)
# Show time in product body copy, e.g. "Show at 9" or "Show at 8:30".
_BODY_SHOW_TIME_RE = re.compile(r"\bshow\s+at\s+(\d{1,2})(?::(\d{2}))?\b", re.IGNORECASE)
# Default show start hour (local) when a product title carries no @time.
_DEFAULT_HOUR = 19
_TEMPLATE_PRODUCT_RE = re.compile(
    r"\b(?:lorem\s+ipsum|sample\s+product|product\s+title)\b",
    re.IGNORECASE,
)


class SquarespaceExtractor:
    """Converts raw Squarespace GetItemsByMonth JSON into SquarespaceEvent objects."""

    @staticmethod
    def extract_products(
        items: List[Dict[str, Any]],
        base_domain: str,
        timezone_name: str,
        include_title_res: Optional[Sequence[Pattern[str]]] = None,
        exclude_title_res: Optional[Sequence[Pattern[str]]] = None,
    ) -> List[SquarespaceEvent]:
        """Extract events from a Squarespace **products/store** collection.

        Some venues sell each show as a dated store product (collection
        typeName='products') instead of using an Events collection, so there is
        no ``startDate`` field — the show date lives in the product ``fullUrl``
        slug (e.g. ``/tickets/p/june-19-2026``) with the time in the title
        (``@8pm``). Items returned via ``{collection}?format=json``.

        Returns SquarespaceEvent objects (same downstream shape as the events
        path); the parsed local datetime is converted to the epoch-ms
        ``start_date_ms`` ``to_show`` expects. Products whose date cannot be
        parsed are skipped (logged), not silently dropped.
        """
        if not isinstance(items, list):
            return []
        try:
            tz = ZoneInfo(timezone_name or "UTC")
        except Exception:
            tz = timezone.utc

        events: List[SquarespaceEvent] = []
        for raw in items:
            try:
                event = SquarespaceExtractor._parse_product(raw, base_domain, tz)
                if not event:
                    continue
                if not _title_allowed(event.title, include_title_res, exclude_title_res):
                    Logger.debug(
                        f"SquarespaceExtractor: dropping product '{event.title}' "
                        f"(title filter)"
                    )
                    continue
                events.append(event)
            except Exception as e:
                Logger.warn(f"SquarespaceExtractor: skipping product due to error: {e}")
        return events

    @staticmethod
    def _parse_product(raw: Dict[str, Any], base_domain: str, tz) -> Optional[SquarespaceEvent]:
        """Parse one store product into a SquarespaceEvent, or None to skip."""
        product_id = raw.get("id") or ""
        title = (raw.get("title") or "").strip()
        if not product_id or not title:
            return None
        excerpt = raw.get("excerpt") or ""
        if SquarespaceExtractor._is_template_product(title, excerpt):
            Logger.debug(
                f"SquarespaceExtractor: skipping template product '{title}'"
            )
            return None

        full_url = raw.get("fullUrl") or ""
        start_dt = SquarespaceExtractor._product_start_datetime(full_url, title, excerpt, tz)
        if start_dt is None:
            Logger.warn(
                f"SquarespaceExtractor: could not parse a show date for product "
                f"'{title}' (fullUrl={full_url!r}); skipping"
            )
            return None

        start_date_ms = int(start_dt.astimezone(timezone.utc).timestamp() * 1000)
        return SquarespaceEvent(
            id=str(product_id),
            title=title,
            start_date_ms=start_date_ms,
            full_url=full_url,
            base_domain=base_domain,
            excerpt=excerpt,
        )

    @staticmethod
    def _product_start_datetime(full_url: str, title: str, excerpt: str, tz) -> Optional[datetime]:
        """Resolve a product's local show datetime from its slug date + product copy time.

        Date precedence: the ``fullUrl`` slug (most reliable) then a leading
        ``Month DD`` in the title. Time: an ``@time`` in the title, then
        Squarespace body copy such as ``Show at 9``, else
        ``_DEFAULT_HOUR``. Returns a tz-aware datetime, or None if no date found.
        """
        ymd = SquarespaceExtractor._date_from_slug(full_url, tz) or SquarespaceExtractor._date_from_title(title, tz)
        if ymd is None:
            return None
        year, month, day = ymd
        hour, minute = SquarespaceExtractor._time_from_title(title, excerpt)
        try:
            return datetime(year, month, day, hour, minute, tzinfo=tz)
        except ValueError:
            return None

    @staticmethod
    def _date_from_slug(full_url: str, tz) -> Optional[tuple]:
        m = _SLUG_DATE_RE.search(full_url or "")
        if not m:
            return None
        month = _month_num(m.group(1))
        if not month:
            return None
        day = int(m.group(2))
        if m.group(3):
            return int(m.group(3)), month, day
        year = SquarespaceExtractor._infer_year(month, day, tz)
        return (year, month, day) if year is not None else None

    @staticmethod
    def _date_from_title(title: str, tz) -> Optional[tuple]:
        m = _TITLE_DATE_RE.search(title or "")
        if not m:
            return None
        month = _month_num(m.group(1))
        if not month:
            return None
        day = int(m.group(2))
        year = SquarespaceExtractor._infer_year(month, day, tz)
        return (year, month, day) if year is not None else None

    @staticmethod
    def _infer_year(month: int, day: int, tz) -> Optional[int]:
        # Yearless product dates carry no year. A recent past date on a current
        # products page is stale and should be skipped; a far-past date usually
        # means the next occurrence crosses the year boundary. "Today" must be
        # the VENUE's calendar date, not the machine's: on a UTC runner between
        # 00:00-04:00 UTC a New York venue's tonight-dated show is still today
        # locally, and machine-local date.today() would misclassify it as stale.
        today = datetime.now(tz).date()
        year = today.year
        try:
            candidate = date(year, month, day)
            if candidate < today:
                if (today - candidate).days <= 180:
                    return None
                year += 1
        except ValueError:
            return None
        return year

    @staticmethod
    def _time_from_title(title: str, excerpt: str = "") -> tuple:
        m = _TITLE_TIME_RE.search(title or "")
        if not m:
            m = _TITLE_TIME_RE.search(excerpt or "")
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            ampm = m.group(3).lower()
            if ampm == "p" and hour != 12:
                hour += 12
            elif ampm == "a" and hour == 12:
                hour = 0
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return _DEFAULT_HOUR, 0
            return hour, minute

        m = _BODY_SHOW_TIME_RE.search(SquarespaceExtractor._plain_text(excerpt))
        if not m:
            return _DEFAULT_HOUR, 0
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        if 1 <= hour <= 11:
            hour += 12
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return _DEFAULT_HOUR, 0
        return hour, minute

    @staticmethod
    def _is_template_product(title: str, excerpt: str) -> bool:
        text = f"{title} {SquarespaceExtractor._plain_text(excerpt)}"
        return bool(_TEMPLATE_PRODUCT_RE.search(text))

    @staticmethod
    def _plain_text(value: str) -> str:
        return re.sub(r"<[^>]+>", " ", value or "")

    @staticmethod
    def extract_events(
        api_response: List[Dict[str, Any]],
        base_domain: str,
        include_title_res: Optional[Sequence[Pattern[str]]] = None,
        exclude_title_res: Optional[Sequence[Pattern[str]]] = None,
    ) -> List[SquarespaceEvent]:
        """Extract SquarespaceEvent objects from the GetItemsByMonth API response.

        Args:
            api_response: JSON array returned by the GetItemsByMonth endpoint.
            base_domain: Base URL of the venue site (e.g. "https://thedentheatre.com").
            include_title_res: Optional compiled regexes; when configured, an
                event is kept only if its title matches at least one (the comedy
                allowlist for a mixed-use arts center). Default None keeps every
                event.
            exclude_title_res: Optional compiled regexes; events whose title
                matches any are dropped (e.g. improv-theatre class sessions /
                workshops). Default None drops nothing.

        Returns:
            List of SquarespaceEvent objects.
        """
        if not isinstance(api_response, list):
            return []

        events = []
        for raw in api_response:
            try:
                event = SquarespaceExtractor._parse_event(raw, base_domain)
                if not event:
                    continue
                if not _title_allowed(event.title, include_title_res, exclude_title_res):
                    Logger.debug(
                        f"SquarespaceExtractor: dropping '{event.title}' (title filter)"
                    )
                    continue
                events.append(event)
            except Exception as e:
                Logger.warn(f"SquarespaceExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def extract_events_stacked_page(
        page_response: Dict[str, Any],
        base_domain: str,
        include_title_res: Optional[Sequence[Pattern[str]]] = None,
        exclude_title_res: Optional[Sequence[Pattern[str]]] = None,
    ) -> List[SquarespaceEvent]:
        """Extract events from a Squarespace events-stacked page JSON response.

        Some Squarespace events collections expose current event records through
        the page's ``?format=json`` response rather than the older
        ``GetItemsByMonth`` API. Those records live under ``upcoming`` and/or
        ``past`` arrays but otherwise use the same ``id`` / ``title`` /
        ``startDate`` fields as the month API.
        """
        if not isinstance(page_response, dict):
            return []

        raw_events: List[Dict[str, Any]] = []
        for key in ("upcoming", "past"):
            items = page_response.get(key)
            if isinstance(items, list):
                raw_events.extend(item for item in items if isinstance(item, dict))

        events = SquarespaceExtractor.extract_events(
            raw_events,
            base_domain,
            include_title_res=include_title_res,
            exclude_title_res=exclude_title_res,
        )
        now_ms = int(time.time() * 1000)
        return [event for event in events if event.start_date_ms >= now_ms]

    @staticmethod
    def _parse_event(raw: Dict[str, Any], base_domain: str) -> SquarespaceEvent | None:
        """Parse a single raw event dict, returning None to skip invalid entries."""
        event_id = raw.get("id") or ""
        if not event_id:
            return None

        title = (raw.get("title") or "").strip()
        if not title:
            return None

        start_date_ms = raw.get("startDate")
        if not isinstance(start_date_ms, (int, float)):
            return None

        full_url = raw.get("fullUrl") or ""
        excerpt = raw.get("excerpt") or ""

        return SquarespaceEvent(
            id=str(event_id),
            title=title,
            start_date_ms=int(start_date_ms),
            full_url=full_url,
            base_domain=base_domain,
            excerpt=excerpt,
        )
