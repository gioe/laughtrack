"""
Extractor for the generic OvationTix platform scraper.

Delegates to shared OvationTix extractor utilities — this module exists
to conform to the 5-file scraper structure.
"""

from typing import List, Optional, Tuple

from laughtrack.core.clients.ovationtix.extractor import (
    extract_client_and_production_ids,
    extract_events_from_production,
    is_past_event,
)
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.foundation.models.types import JSONDict


class OvationTixExtractor:
    """Pure parsing utilities for OvationTix API responses."""

    @staticmethod
    def extract_client_and_production_ids(html: str) -> Tuple[Optional[str], List[str]]:
        """Extract the OvationTix client ID and deduplicated production IDs from HTML."""
        return extract_client_and_production_ids(html)

    @staticmethod
    def extract_events_from_production(
        production_data: JSONDict,
        production_id: str,
        client_id: str,
        default_name: str = "Comedy Show",
    ) -> List[OvationTixEvent]:
        """Build OvationTixEvent objects from a Production/performance? API response."""
        return extract_events_from_production(
            production_data, production_id, client_id,
            default_name=default_name,
            event_cls=OvationTixEvent,
        )

    @staticmethod
    def is_past_event(start_date_str: str, timezone: str) -> bool:
        """Return True if the event date is in the past."""
        return is_past_event(start_date_str, timezone)
