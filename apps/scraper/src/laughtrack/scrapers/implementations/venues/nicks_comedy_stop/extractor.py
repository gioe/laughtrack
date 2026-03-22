"""Nick's Comedy Stop event extraction from Wix Events API response."""

from typing import Any, Dict, List

from laughtrack.core.entities.event.nicks import NicksEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class NicksEventExtractor:
    """Converts raw Wix Events API JSON into NicksEvent objects."""

    @staticmethod
    def extract_events(api_response: Dict[str, Any]) -> List[NicksEvent]:
        """Extract NicksEvent objects from the Wix paginated-events API response."""
        events = []
        for raw in api_response.get("events", []):
            try:
                event = NicksEventExtractor._parse_event(raw)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"NicksEventExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> NicksEvent:
        return NicksEvent(
            id=raw.get("id", ""),
            title=raw.get("title", "").strip(),
            description=raw.get("description", "").strip(),
            slug=raw.get("slug", ""),
            scheduling=raw.get("scheduling", {}),
            registration=raw.get("registration", {}),
        )
