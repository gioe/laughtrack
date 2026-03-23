"""The Rockwell event extraction from Tribe Events REST API response."""

from html import unescape
from typing import Any, Dict, List

from laughtrack.core.entities.event.rockwell import RockwellEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class RockwellEventExtractor:
    """Converts raw Tribe Events REST API JSON into RockwellEvent objects."""

    @staticmethod
    def extract_events(api_response: Dict[str, Any]) -> List[RockwellEvent]:
        """Extract RockwellEvent objects from a single API response page."""
        events = []
        for raw in api_response.get("events", []):
            try:
                event = RockwellEventExtractor._parse_event(raw)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"RockwellEventExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def get_total_pages(api_response: Dict[str, Any]) -> int:
        """Return the total number of pages from the API response."""
        return int(api_response.get("total_pages", 1))

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> RockwellEvent:
        cost_details = raw.get("cost_details") or {}
        cost_values = cost_details.get("values") or []
        return RockwellEvent(
            id=str(raw.get("global_id", raw.get("id", ""))),
            title=unescape((raw.get("title") or "").strip()),
            start_date=raw.get("start_date", ""),
            timezone=raw.get("timezone", "America/New_York"),
            url=raw.get("url", ""),
            cost=raw.get("cost", ""),
            cost_values=[str(v) for v in cost_values],
            description=raw.get("description", ""),
        )
