"""
Category and format-related Eventbrite API models.

This module contains dataclass definitions for event categories
and formats in Eventbrite API responses.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EventbriteFormat:
    """Event format information (e.g., Seminar, Workshop)."""

    id: str
    name: str
    name_localized: str
    short_name: str
    short_name_localized: str
    resource_uri: str

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteFormat":
        """Create EventbriteFormat from JSON dict."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_localized=data.get("name_localized", ""),
            short_name=data.get("short_name", ""),
            short_name_localized=data.get("short_name_localized", ""),
            resource_uri=data.get("resource_uri", ""),
        )


@dataclass
class EventbriteSubcategory:
    """Event subcategory information."""

    id: str
    name: str
    resource_uri: str
    parent_category: Optional[Dict[str, Any]] = None  # Can be recursive

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteSubcategory":
        """Create EventbriteSubcategory from JSON dict."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            resource_uri=data.get("resource_uri", ""),
            parent_category=data.get("parent_category"),
        )


@dataclass
class EventbriteCategory:
    """Event category information."""

    id: str
    name: str
    name_localized: str
    short_name: str
    short_name_localized: str
    resource_uri: str
    subcategories: Optional[List[EventbriteSubcategory]] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteCategory":
        """Create EventbriteCategory from JSON dict."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_localized=data.get("name_localized", ""),
            short_name=data.get("short_name", ""),
            short_name_localized=data.get("short_name_localized", ""),
            resource_uri=data.get("resource_uri", ""),
            subcategories=[EventbriteSubcategory.from_json_dict(sub) for sub in data.get("subcategories", [])],
        )
