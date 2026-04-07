"""
Comedy @ The Carlson data extraction utilities.

Delegates to shared OvationTix extractor for production ID discovery,
event construction, and past-event filtering.
"""

from typing import List, Optional, Tuple

from laughtrack.core.clients.ovationtix.extractor import (
    extract_client_and_production_ids,
    extract_events_from_production,
    is_past_event,
)
from laughtrack.core.entities.event.comedy_at_the_carlson import ComedyAtTheCarlsonEvent
from laughtrack.foundation.models.types import JSONDict


class ComedyAtTheCarlsonExtractor:
    """Pure parsing utilities for Comedy @ The Carlson OvationTix responses."""

    @staticmethod
    def extract_client_and_production_ids(html: str) -> Tuple[Optional[str], List[str]]:
        """Extract the OvationTix client ID and deduplicated production IDs from HTML."""
        return extract_client_and_production_ids(html)

    @staticmethod
    def extract_events_from_production(
        production_data: JSONDict,
        production_id: str,
        client_id: str,
    ) -> List[ComedyAtTheCarlsonEvent]:
        """Build ComedyAtTheCarlsonEvent objects from a Production/performance? API response."""
        return extract_events_from_production(
            production_data, production_id, client_id,
            default_name="Comedy Show",
            event_cls=ComedyAtTheCarlsonEvent,
        )

    @staticmethod
    def is_past_event(start_date_str: str, timezone: str) -> bool:
        """Return True if the event date is in the past."""
        return is_past_event(start_date_str, timezone)
