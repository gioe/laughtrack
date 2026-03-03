"""
API response wrapper models for Eventbrite.

This module contains dataclass definitions for complete API responses
from Eventbrite endpoints.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from laughtrack.foundation.models.types import JSONDict

from laughtrack.foundation.models.api.eventbrite.base_models import EventbritePagination
from .main_event_models import EventbriteEvent


@dataclass
class EventbriteListEventsResponse:
    """Complete response from the Eventbrite List Events API."""

    pagination: EventbritePagination
    events: List[EventbriteEvent]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventbriteListEventsResponse":
        """Create EventbriteListEventsResponse from JSON dict."""
        return cls(
            pagination=EventbritePagination.from_json_dict(data.get("pagination", {})),
            events=[EventbriteEvent.from_json_dict(event) for event in data.get("events", [])],
        )
