"""Ice House Comedy Club event extraction from Tockify API response."""

from typing import Any, Dict, List

from laughtrack.core.entities.event.ice_house import IceHouseEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class IceHouseExtractor:
    """Converts raw Tockify API JSON into IceHouseEvent objects."""

    @staticmethod
    def extract_events(api_response: Dict[str, Any]) -> List[IceHouseEvent]:
        """Extract IceHouseEvent objects from the Tockify API response dict."""
        raw_events = api_response.get("events", [])
        if not isinstance(raw_events, list):
            return []

        events = []
        for raw in raw_events:
            try:
                event = IceHouseExtractor._parse_event(raw)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"IceHouseExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> IceHouseEvent | None:
        """Parse a single raw Tockify event dict into an IceHouseEvent, or None to skip."""
        eid = raw.get("eid") or {}
        uid = str(eid.get("uid", ""))
        if not uid:
            return None

        content = raw.get("content") or {}
        summary = content.get("summary") or {}
        title = (summary.get("text") or "").strip()
        if not title:
            return None

        when = raw.get("when") or {}
        start = when.get("start") or {}
        start_ms = start.get("millis")
        if not isinstance(start_ms, (int, float)):
            return None

        ticket_url = (content.get("customButtonLink") or "").strip()
        tzid = start.get("tzid") or "America/Los_Angeles"

        return IceHouseEvent(
            uid=uid,
            title=title,
            start_ms=int(start_ms),
            ticket_url=ticket_url,
            timezone=tzid,
        )
