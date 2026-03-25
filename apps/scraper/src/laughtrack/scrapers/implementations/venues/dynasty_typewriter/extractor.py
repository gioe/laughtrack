"""Dynasty Typewriter event extraction from SquadUp API response."""

from typing import Any, Dict, List

from laughtrack.core.entities.event.dynasty_typewriter import DynastyTypewriterEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class DynastyTypewriterExtractor:
    """Converts raw SquadUp API JSON into DynastyTypewriterEvent objects."""

    @staticmethod
    def extract_events(api_response: Dict[str, Any]) -> List[DynastyTypewriterEvent]:
        """Extract DynastyTypewriterEvent objects from the SquadUp API response dict."""
        raw_events = api_response.get("events", [])
        if not isinstance(raw_events, list):
            return []

        events = []
        for raw in raw_events:
            try:
                event = DynastyTypewriterExtractor._parse_event(raw)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"DynastyTypewriterExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> DynastyTypewriterEvent | None:
        """Parse a single raw event dict into a DynastyTypewriterEvent, or None to skip."""
        event_id = str(raw.get("id", ""))
        if not event_id:
            return None

        title = (raw.get("name") or "").strip()
        if not title:
            return None

        start_at = raw.get("start_at", "")
        if not start_at:
            return None

        url = raw.get("url", "")
        timezone_name = raw.get("timezone_name", "America/Los_Angeles")

        return DynastyTypewriterEvent(
            id=event_id,
            title=title,
            start_at=start_at,
            url=url,
            timezone_name=timezone_name,
        )
