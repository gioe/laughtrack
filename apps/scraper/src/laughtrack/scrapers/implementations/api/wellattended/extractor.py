"""HTML/RSC extraction for WellAttended venue pages.

WellAttended (``<venue>.wellattended.com``) is a Next.js app using React Server
Components (RSC) streaming. There is no JSON-LD and no ``__NEXT_DATA__``; event
data is embedded in ``self.__next_f.push([1, "<chunk>"])`` segments.

Two methods:

1. :meth:`extract_event_slugs` — parse the venue listing page (the WellAttended
   root) for ``/events/<slug>`` anchor links and return the unique slugs.
2. :meth:`extract_event_occurrences` — parse one ``/events/<slug>`` detail page.
   The RSC flight is concatenated across every push call (a single object can
   span chunk boundaries), then each showing/occurrence object — identified by
   carrying ``thingTitle`` + ``start`` + ``timezone`` — is balanced-extracted and
   parsed. The ``start`` value carries the RSC ``$D`` date marker, which is
   stripped to a plain UTC ISO string. Deleted / hidden / past occurrences are
   dropped; the cheapest ticket-tier ``price`` (cents → dollars) is attached.
"""

import json
import re
from datetime import datetime, timezone as _tz
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from laughtrack.core.clients.rsc.extractor import extract_balanced, extract_push_payloads
from laughtrack.core.entities.event.wellattended import WellAttendedEvent

_EVENTS_PATH_RE = re.compile(r"/events/([a-z0-9][a-z0-9-]*)", re.IGNORECASE)
# RSC serializes a Date as "$D<ISO>" — strip the marker to get the UTC ISO.
_RSC_DATE_PREFIX = "$D"


class WellAttendedExtractor:
    """Extracts show data from WellAttended RSC-rendered HTML pages."""

    @staticmethod
    def _origin(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return (url or "").rstrip("/")

    @staticmethod
    def extract_event_slugs(listing_html: str) -> List[str]:
        """Return unique ``/events/<slug>`` slugs from the venue listing page."""
        if not listing_html:
            return []
        soup = BeautifulSoup(listing_html, "html.parser")
        slugs: List[str] = []
        seen: set = set()
        for anchor in soup.find_all("a", href=True):
            match = _EVENTS_PATH_RE.search(anchor["href"])
            if not match:
                continue
            slug = match.group(1)
            if slug and slug not in seen:
                seen.add(slug)
                slugs.append(slug)
        return slugs

    @staticmethod
    def _enclosing_object(flight: str, anchor_start: int, anchor_end: int) -> Optional[dict]:
        """Return the parsed innermost JSON object that spans the anchor span.

        Steps back over preceding ``{`` positions until the balanced block both
        (a) extends past ``anchor_end`` (spans the anchor) and (b) parses as a JSON
        object. A nearer ``{`` either opens a nested object that closes before the
        anchor (fails the span check) or — because the starting brace is found with
        a non-string-aware ``rfind`` — lands inside a string value containing a
        literal ``{`` (spans the anchor but won't parse); both are skipped by
        stepping further back to the real enclosing object. Returns ``None`` when
        no spanning, parseable object exists.
        """
        search_end = anchor_start
        while True:
            brace = flight.rfind("{", 0, search_end)
            if brace < 0:
                return None
            block = extract_balanced(flight, brace, "{", "}")
            if block and brace + len(block) > anchor_end:
                try:
                    parsed = json.loads(block)
                except (json.JSONDecodeError, ValueError):
                    parsed = None
                if isinstance(parsed, dict):
                    return parsed
            search_end = brace

    @staticmethod
    def _min_tier_price_dollars(flight: str) -> Optional[float]:
        """Cheapest ticket-tier price in dollars, parsed from the flight (cents)."""
        prices: List[int] = []
        for match in re.finditer(r'"classification"\s*:', flight):
            tier = WellAttendedExtractor._enclosing_object(flight, match.start(), match.end())
            if tier is None:
                continue
            price = tier.get("price")
            if isinstance(price, int) and price > 0:
                prices.append(price)
        return min(prices) / 100.0 if prices else None

    @staticmethod
    def extract_event_occurrences(
        detail_html: str, base_url: str, slug: str, now: Optional[datetime] = None
    ) -> List[WellAttendedEvent]:
        """Parse a ``/events/<slug>`` page into one event per upcoming occurrence."""
        flight = "".join(extract_push_payloads(detail_html))
        if not flight:
            return []

        now = now or datetime.now(_tz.utc)
        origin = WellAttendedExtractor._origin(base_url)
        show_page_url = f"{origin}/events/{slug}"
        price = WellAttendedExtractor._min_tier_price_dollars(flight)

        events: List[WellAttendedEvent] = []
        seen: set = set()
        # Anchor on the occurrence's UTC start ("start":"$D<ISO>") and balance-
        # extract its enclosing object; the occurrence also carries thingTitle +
        # timezone. Anchoring on start (not thingTitle) + the enclosing-object
        # finder is robust to nested objects preceding any key.
        for match in re.finditer(r'"start"\s*:\s*"\$D[^"]+"', flight):
            occ = WellAttendedExtractor._enclosing_object(flight, match.start(), match.end())
            if occ is None or "thingTitle" not in occ or "timezone" not in occ:
                continue

            if occ.get("deleted") is True or occ.get("shouldBeShown") is False:
                continue

            start_raw = occ.get("start")
            title = (occ.get("thingTitle") or "").strip()
            if not isinstance(start_raw, str) or not title:
                continue
            start_iso = start_raw[len(_RSC_DATE_PREFIX):] if start_raw.startswith(_RSC_DATE_PREFIX) else start_raw

            start_dt = WellAttendedExtractor._parse_utc(start_iso)
            if start_dt is None or start_dt < now:
                continue

            dedup_key = (occ.get("_id") or "", start_iso)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            events.append(
                WellAttendedEvent(
                    title=title,
                    start_time_utc=start_iso,
                    timezone=occ.get("timezone") or "America/Denver",
                    show_page_url=show_page_url,
                    price=price,
                )
            )
        return events

    @staticmethod
    def _parse_utc(start_iso: str) -> Optional[datetime]:
        """Parse a UTC ISO string (``2026-08-08T01:30:00.000Z``) as tz-aware UTC."""
        try:
            naive = datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%S.%fZ")
            return naive.replace(tzinfo=_tz.utc)
        except (ValueError, TypeError):
            return None
