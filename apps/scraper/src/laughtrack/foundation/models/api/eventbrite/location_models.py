"""
Location-related Eventbrite API models.

This module contains dataclass definitions for addresses and venues
in Eventbrite API responses.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EventbriteAddress:
    """Address information for venues."""

    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteAddress":
        """Create EventbriteAddress from JSON dict."""
        return cls(
            address_1=data.get("address_1"),
            address_2=data.get("address_2"),
            city=data.get("city"),
            region=data.get("region"),
            postal_code=data.get("postal_code"),
            country=data.get("country"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )


@dataclass
class EventbriteVenue:
    """Venue information."""

    id: str
    name: str
    resource_uri: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    age_restriction: Optional[str] = None
    capacity: Optional[int] = None
    address: Optional[EventbriteAddress] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteVenue":
        """Create EventbriteVenue from JSON dict."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            resource_uri=data.get("resource_uri", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            age_restriction=data.get("age_restriction"),
            capacity=data.get("capacity"),
            address=EventbriteAddress.from_json_dict(data.get("address", {})) if data.get("address") else None,
        )
