"""The Elysian Theater event extraction from Squarespace GetItemsByMonth API response."""

from html import unescape
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.elysian import ElysianEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ElysianEventExtractor:
    """Converts raw Squarespace GetItemsByMonth API JSON into ElysianEvent objects."""

    @staticmethod
    def extract_events(api_response: list) -> List[ElysianEvent]:
        """Extract ElysianEvent objects from the API response list."""
        events = []
        for raw in api_response:
            try:
                event = ElysianEventExtractor._parse_event(raw)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"ElysianEventExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> Optional[ElysianEvent]:
        """Parse a single raw event dict into an ElysianEvent, or return None to skip."""
        # Only include published events
        if raw.get("workflowState") != 1:
            return None

        start_date_ms = raw.get("startDate")
        if not start_date_ms:
            return None

        title = (raw.get("title") or "").strip()
        if not title:
            return None

        return ElysianEvent(
            id=str(raw.get("id", "")),
            title=unescape(title),
            start_date_ms=int(start_date_ms),
            full_url=raw.get("fullUrl", ""),
            excerpt=raw.get("excerpt", ""),
        )
