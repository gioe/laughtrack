"""Squarespace event extraction from GetItemsByMonth API response."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Pattern
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.squarespace import SquarespaceEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

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
# Date in a ticket-product slug, e.g. "/tickets/p/june-19-2026" -> (june, 19, 2026).
_SLUG_DATE_RE = re.compile(r"([a-z]{3,9})-(\d{1,2})-(\d{4})", re.IGNORECASE)
# Leading "Month DD" in a product title, e.g. "June 19: Friday Night Show".
_TITLE_DATE_RE = re.compile(r"\b([a-z]{3,9})\.?\s+(\d{1,2})\b", re.IGNORECASE)
# Show time in a product title, e.g. "@8pm" / "@ 7:30 pm".
_TITLE_TIME_RE = re.compile(r"@\s*(\d{1,2})(?::(\d{2}))?\s*([ap])m", re.IGNORECASE)
# Default show start hour (local) when a product title carries no @time.
_DEFAULT_HOUR = 19


class SquarespaceExtractor:
    """Converts raw Squarespace GetItemsByMonth JSON into SquarespaceEvent objects."""

    @staticmethod
    def extract_products(
        items: List[Dict[str, Any]],
        base_domain: str,
        timezone_name: str,
        exclude_title_re: Optional[Pattern[str]] = None,
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
                if exclude_title_re is not None and exclude_title_re.search(event.title):
                    Logger.debug(
                        f"SquarespaceExtractor: excluding non-show product '{event.title}' "
                        f"(matched exclude_title_patterns)"
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

        full_url = raw.get("fullUrl") or ""
        start_dt = SquarespaceExtractor._product_start_datetime(full_url, title, tz)
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
            excerpt=raw.get("excerpt") or "",
        )

    @staticmethod
    def _product_start_datetime(full_url: str, title: str, tz) -> Optional[datetime]:
        """Resolve a product's local show datetime from its slug date + title time.

        Date precedence: the ``fullUrl`` slug (most reliable) then a leading
        ``Month DD`` in the title. Time: an ``@time`` in the title, else
        ``_DEFAULT_HOUR``. Returns a tz-aware datetime, or None if no date found.
        """
        ymd = SquarespaceExtractor._date_from_slug(full_url) or SquarespaceExtractor._date_from_title(title)
        if ymd is None:
            return None
        year, month, day = ymd
        hour, minute = SquarespaceExtractor._time_from_title(title)
        try:
            return datetime(year, month, day, hour, minute, tzinfo=tz)
        except ValueError:
            return None

    @staticmethod
    def _date_from_slug(full_url: str) -> Optional[tuple]:
        m = _SLUG_DATE_RE.search(full_url or "")
        if not m:
            return None
        month = _month_num(m.group(1))
        if not month:
            return None
        return int(m.group(3)), month, int(m.group(2))

    @staticmethod
    def _date_from_title(title: str) -> Optional[tuple]:
        m = _TITLE_DATE_RE.search(title or "")
        if not m:
            return None
        month = _month_num(m.group(1))
        if not month:
            return None
        # Title dates carry no year; infer the next occurrence so a Dec show seen
        # in Jan resolves to the correct (current or next) year.
        from datetime import date as _date
        today = _date.today()
        day = int(m.group(2))
        year = today.year
        try:
            if _date(year, month, day) < today:
                year += 1
        except ValueError:
            return None
        return year, month, day

    @staticmethod
    def _time_from_title(title: str) -> tuple:
        m = _TITLE_TIME_RE.search(title or "")
        if not m:
            return _DEFAULT_HOUR, 0
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

    @staticmethod
    def extract_events(
        api_response: List[Dict[str, Any]],
        base_domain: str,
        exclude_title_re: Optional[Pattern[str]] = None,
    ) -> List[SquarespaceEvent]:
        """Extract SquarespaceEvent objects from the GetItemsByMonth API response.

        Args:
            api_response: JSON array returned by the GetItemsByMonth endpoint.
            base_domain: Base URL of the venue site (e.g. "https://thedentheatre.com").
            exclude_title_re: Optional compiled regex; events whose title matches
                are skipped. Used by venues whose events collection mixes public
                shows with non-show entries (e.g. improv-theatre class sessions /
                workshops). Default None keeps every event.

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
                if exclude_title_re is not None and exclude_title_re.search(event.title):
                    Logger.debug(
                        f"SquarespaceExtractor: excluding non-show '{event.title}' "
                        f"(matched exclude_title_patterns)"
                    )
                    continue
                events.append(event)
            except Exception as e:
                Logger.warn(f"SquarespaceExtractor: skipping event due to error: {e}")
        return events

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
