"""Vivenu seller page event extractor.

Parses __NEXT_DATA__ JSON embedded in Vivenu seller pages to extract
upcoming events. Vivenu embeds a full event list at:
  props.pageProps.sellerPage.events[]

Each event has an ISO 8601 UTC start timestamp; only events with start > now
are returned (past events are skipped).
"""

import json
import re
from datetime import datetime, timezone
from typing import List

from laughtrack.core.entities.event.vivenu import VivenuEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


class VivenuExtractor:
    """Extracts VivenuEvent objects from a Vivenu seller page HTML."""

    @staticmethod
    def extract_events(html: str, ticket_base_url: str) -> List[VivenuEvent]:
        """
        Parse __NEXT_DATA__ JSON from the seller page HTML and return upcoming VivenuEvents.

        Args:
            html: Raw HTML of the Vivenu seller page.
            ticket_base_url: Base URL for constructing ticket links
                (e.g. "https://tickets.thirdcoastcomedy.club").

        Returns:
            List of VivenuEvent objects for upcoming events (start > now).
        """
        match = _NEXT_DATA_RE.search(html)
        if not match:
            Logger.warn("VivenuExtractor: __NEXT_DATA__ script tag not found in page HTML")
            return []

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            Logger.warn(f"VivenuExtractor: failed to parse __NEXT_DATA__ JSON: {e}")
            return []

        raw_events = (
            data.get("props", {})
            .get("pageProps", {})
            .get("sellerPage", {})
            .get("events", [])
        )
        if not isinstance(raw_events, list):
            Logger.warn("VivenuExtractor: sellerPage.events is not a list")
            return []

        now_utc = datetime.now(timezone.utc)
        events: List[VivenuEvent] = []
        for raw in raw_events:
            try:
                event = VivenuExtractor._parse_event(raw, ticket_base_url, now_utc)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"VivenuExtractor: skipping event due to error: {e}")

        return events

    @staticmethod
    def _parse_event(
        raw: dict, ticket_base_url: str, now_utc: datetime
    ) -> VivenuEvent | None:
        """Parse a single raw Vivenu event dict, returning None to skip."""
        event_id = raw.get("_id", "")
        if not event_id:
            return None

        name = (raw.get("name") or "").strip()
        if not name:
            return None

        start_str = raw.get("start", "")
        if not start_str:
            return None

        try:
            start_utc_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except ValueError:
            return None

        # Skip past events
        if start_utc_dt <= now_utc:
            return None

        event_url = (raw.get("url") or "").strip()
        tz = (raw.get("timezone") or "America/Chicago").strip()

        return VivenuEvent(
            event_id=event_id,
            name=name,
            start_utc=start_str,
            event_url=event_url,
            tz=tz,
            ticket_base_url=ticket_base_url,
        )
