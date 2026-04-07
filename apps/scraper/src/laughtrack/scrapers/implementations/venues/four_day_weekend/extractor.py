"""
Four Day Weekend Comedy data extraction utilities.

Delegates to shared OvationTix extractor for production ID discovery,
event construction, and past-event filtering.
"""

from typing import List, Optional, Tuple

from laughtrack.core.clients.ovationtix.extractor import (
    extract_client_and_production_ids,
    extract_events_from_production as _extract_events,
    is_past_event,
)
from laughtrack.core.entities.event.four_day_weekend import FourDayWeekendEvent
from laughtrack.foundation.models.types import JSONDict


class FourDayWeekendExtractor:
    """Pure parsing utilities for Four Day Weekend Comedy responses."""

    @staticmethod
    def extract_client_and_production_ids(html: str) -> Tuple[Optional[str], List[str]]:
        """Extract the OvationTix client ID and deduplicated production IDs from HTML."""
        return extract_client_and_production_ids(html)

    @staticmethod
    def extract_events_from_production(
        production_data: JSONDict,
        production_id: str,
        client_id: str,
    ) -> List[FourDayWeekendEvent]:
        """Build FourDayWeekendEvent objects from a Production/performance? API response."""
        base_events = _extract_events(
            production_data, production_id, client_id, default_name="Four Day Weekend"
        )
        return [
            FourDayWeekendEvent(
                production_id=e.production_id,
                performance_id=e.performance_id,
                production_name=e.production_name,
                start_date=e.start_date,
                tickets_available=e.tickets_available,
                event_url=e.event_url,
                description=e.description,
                sections=e.sections,
            )
            for e in base_events
        ]

    @staticmethod
    def is_past_event(start_date_str: str, timezone: str) -> bool:
        """Return True if the event date is in the past."""
        return is_past_event(start_date_str, timezone)
