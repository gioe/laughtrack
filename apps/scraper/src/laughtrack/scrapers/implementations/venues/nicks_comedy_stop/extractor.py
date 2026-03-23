"""Nick's Comedy Stop event extraction from Wix Events API response."""

import re
from typing import Any, Dict, List

from laughtrack.core.entities.event.nicks import NicksEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_HEADLINER_RE = re.compile(r'headliner\s+(.+?)(?:\s+headlines|\s*$)', re.IGNORECASE)
_SUPPORTING_RE = re.compile(r'\bwith\s+(.+?)\s+and\s+(.+?)(?:\s+at\b|\s*$)', re.IGNORECASE)


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
    def parse_lineup_from_description(description: str) -> List[str]:
        """Extract performer names from an event description.

        Recognises two patterns:
        - 'headliner <Name> headlines ...' → headliner at index 0
        - 'with <Name> and <Name>' → supporting acts appended after headliner
        """
        if not description:
            return []

        lineup: List[str] = []

        headliner_match = _HEADLINER_RE.search(description)
        if headliner_match:
            lineup.append(headliner_match.group(1).strip())

        supporting_match = _SUPPORTING_RE.search(description)
        if supporting_match:
            lineup.append(supporting_match.group(1).strip())
            lineup.append(supporting_match.group(2).strip())

        return lineup

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> NicksEvent:
        description = raw.get("description", "").strip()
        return NicksEvent(
            id=raw.get("id", ""),
            title=raw.get("title", "").strip(),
            description=description,
            slug=raw.get("slug", ""),
            scheduling=raw.get("scheduling", {}),
            registration=raw.get("registration", {}),
            lineup=NicksEventExtractor.parse_lineup_from_description(description),
        )
