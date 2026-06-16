"""Event extraction from a VBO Tickets ``showevents`` listing HTML response."""

import re
from html import unescape
from typing import List, Optional

from laughtrack.core.entities.event.vbo_tickets import VboEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# The loadplugin response posts the user session UUID back to the parent frame
# as an unquoted JS object value: ``value: "uuid"``.
_SESSION_RE = re.compile(
    r'value["\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
    re.IGNORECASE,
)

# Each event in the listing is a wrapper div: <div id="EDID123" class="EventListWrapper ...
_EVENT_BLOCK_RE = re.compile(
    r'<div id="EDID\d+" class="EventListWrapper.*?(?=<div id="EDID\d+" class="EventListWrapper|<div[^>]*id="PastEvents|\Z)',
    re.IGNORECASE | re.DOTALL,
)
_NAME_RE = re.compile(r'data-event-name="([^"]*)"', re.IGNORECASE)
_EID_RE = re.compile(r"event\.asp\?eid=(\d+)", re.IGNORECASE)
_DATE_RE = re.compile(r'class="TextEventDate[^"]*">\s*([^<]+?)\s*</div>', re.IGNORECASE)
_PRICE_RE = re.compile(r'class="EventListPrice">\s*([^<]+?)\s*</div>', re.IGNORECASE)
_PRICE_NUM_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{2})?)")

# Stable per-event landing URL (session token deliberately omitted so the
# persisted show_page_url does not rot when the VBO session expires).
_EVENT_URL = "https://plugin.vbotickets.com/v5.0/event.asp?eid={eid}"


class VboTicketsExtractor:
    """Converts VBO Tickets ListEvents HTML into VboEvent objects."""

    @staticmethod
    def extract_session(loadplugin_html: str) -> Optional[str]:
        """Pull the user-session UUID from a loadplugin response, or None."""
        if not loadplugin_html:
            return None
        m = _SESSION_RE.search(loadplugin_html)
        return m.group(1) if m else None

    @staticmethod
    def extract_events(showevents_html: str) -> List[VboEvent]:
        """Extract VboEvent rows from a ``showevents`` listing response."""
        events: List[VboEvent] = []
        for block in _EVENT_BLOCK_RE.findall(showevents_html or ""):
            try:
                event = VboTicketsExtractor._parse_block(block)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"VboTicketsExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_block(block: str) -> Optional[VboEvent]:
        eid_m = _EID_RE.search(block)
        name_m = _NAME_RE.search(block)
        date_m = _DATE_RE.search(block)
        # An event row without an eid or a date is not a bookable show.
        if not eid_m or not date_m:
            return None

        price_min = None
        price_m = _PRICE_RE.search(block)
        if price_m:
            nums = [float(n) for n in _PRICE_NUM_RE.findall(price_m.group(1))]
            if nums:
                price_min = min(nums)

        eid = eid_m.group(1)
        return VboEvent(
            eid=eid,
            name=unescape((name_m.group(1) if name_m else "").strip()),
            date_str=unescape(date_m.group(1).strip()),
            url=_EVENT_URL.format(eid=eid),
            price_min=price_min,
        )
