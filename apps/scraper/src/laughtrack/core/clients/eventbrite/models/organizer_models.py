"""
Organizer-related Eventbrite API models.

This module contains dataclass definitions for event organizers
in Eventbrite API responses.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from laughtrack.foundation.models.api.eventbrite.base_models import EventbriteTextHtml
from laughtrack.foundation.models.api.eventbrite.image_models import EventbriteImage


@dataclass
class EventbriteOrganizer:
    """Event organizer information."""

    id: str
    name: str
    description: Optional[EventbriteTextHtml] = None
    long_description: Optional[EventbriteTextHtml] = None
    logo_id: Optional[str] = None
    logo: Optional[EventbriteImage] = None
    resource_uri: Optional[str] = None
    url: Optional[str] = None
    num_past_events: Optional[int] = None
    num_future_events: Optional[int] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteOrganizer":
        """Create EventbriteOrganizer from JSON dict."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=(
                EventbriteTextHtml.from_json_dict(data.get("description", {})) if data.get("description") else None
            ),
            long_description=(
                EventbriteTextHtml.from_json_dict(data.get("long_description", {}))
                if data.get("long_description")
                else None
            ),
            logo_id=data.get("logo_id"),
            logo=EventbriteImage.from_json_dict(data.get("logo", {})) if data.get("logo") else None,
            resource_uri=data.get("resource_uri"),
            url=data.get("url"),
            num_past_events=data.get("num_past_events"),
            num_future_events=data.get("num_future_events"),
            twitter=data.get("twitter"),
            facebook=data.get("facebook"),
        )
