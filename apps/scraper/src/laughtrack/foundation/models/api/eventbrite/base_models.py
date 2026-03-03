"""
Base Eventbrite API models.

This module contains fundamental dataclass definitions used across
Eventbrite API responses.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EventbritePagination:
    """Pagination information from Eventbrite API."""

    object_count: int
    page_number: int
    page_size: int
    page_count: int
    continuation: Optional[str] = None
    has_more_items: bool = False

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbritePagination":
        """Create EventbritePagination from JSON dict."""
        return cls(
            object_count=data.get("object_count", 0),
            page_number=data.get("page_number", 1),
            page_size=data.get("page_size", 50),
            page_count=data.get("page_count", 1),
            continuation=data.get("continuation"),
            has_more_items=data.get("has_more_items", False),
        )


@dataclass
class EventbritePrice:
    """Price information with currency and display formatting."""

    currency: str
    value: int
    major_value: str
    display: str

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbritePrice":
        """Create EventbritePrice from JSON dict."""
        return cls(
            currency=data.get("currency", ""),
            value=data.get("value", 0),
            major_value=data.get("major_value", ""),
            display=data.get("display", ""),
        )


@dataclass
class EventbriteDateTime:
    """Date/time information with timezone support."""

    timezone: str
    utc: str
    local: str

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteDateTime":
        """Create EventbriteDateTime from JSON dict."""
        return cls(timezone=data.get("timezone", ""), utc=data.get("utc", ""), local=data.get("local", ""))


@dataclass
class EventbriteTextHtml:
    """Text content with both plain text and HTML versions."""

    text: Optional[str] = None
    html: Optional[str] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteTextHtml":
        """Create EventbriteTextHtml from JSON dict."""
        return cls(text=data.get("text"), html=data.get("html"))
