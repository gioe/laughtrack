"""Wix Events event extraction from the paginated-events API response."""

from typing import Any, Dict, List

from laughtrack.core.entities.event.wix_events import WixEventsEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class WixEventsExtractor:
    """Converts raw Wix Events API JSON into WixEventsEvent objects."""

    @staticmethod
    def extract_events(api_response: Dict[str, Any]) -> List[WixEventsEvent]:
        """Extract WixEventsEvent objects from the Wix paginated-events API response."""
        events = []
        for raw in api_response.get("events", []):
            try:
                event = WixEventsExtractor._parse_event(raw)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"WixEventsExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> WixEventsEvent:
        """Parse a single raw event dict into a WixEventsEvent."""
        return WixEventsEvent(
            id=raw.get("id", ""),
            title=raw.get("title", "").strip(),
            description=raw.get("description", "").strip(),
            slug=raw.get("slug", ""),
            scheduling=raw.get("scheduling", {}),
            registration=raw.get("registration", {}),
        )
