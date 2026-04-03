"""
Main event models for Eventbrite API.

This module contains the primary EventbriteEvent model and related
models from the List Events API response.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from laughtrack.foundation.models.api.eventbrite.base_models import EventbriteDateTime, EventbriteTextHtml
from laughtrack.foundation.models.api.eventbrite.category_models import EventbriteCategory, EventbriteFormat, EventbriteSubcategory
from laughtrack.foundation.models.api.eventbrite.image_models import EventbriteImage
from laughtrack.foundation.models.api.eventbrite.location_models import EventbriteVenue
from .organizer_models import EventbriteOrganizer
from .ticket_models import (
    EventbriteCheckoutSettings,
    EventbriteExternalTicketing,
    EventbriteSalesStatus,
    EventbriteTicketAvailability,
)


@dataclass
class EventbriteMusicProperties:
    """Music-specific event properties."""

    age_restriction: Optional[str] = None
    presented_by: Optional[str] = None
    door_time: Optional[str] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteMusicProperties":
        """Create EventbriteMusicProperties from JSON dict."""
        return cls(
            age_restriction=data.get("age_restriction"),
            presented_by=data.get("presented_by"),
            door_time=data.get("door_time"),
        )


@dataclass
class EventbriteBookmarkInfo:
    """User bookmark information for the event."""

    bookmarked: bool = False

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteBookmarkInfo":
        """Create EventbriteBookmarkInfo from JSON dict."""
        return cls(bookmarked=data.get("bookmarked", False))


@dataclass
class EventbriteEvent:
    """Complete Eventbrite event information."""

    id: str
    name: EventbriteTextHtml
    url: str
    status: str
    created: str
    changed: str
    published: str
    currency: str
    online_event: bool
    organization_id: str
    organizer_id: str
    resource_uri: str
    source: str
    description: Optional[EventbriteTextHtml] = None
    start: Optional[EventbriteDateTime] = None
    end: Optional[EventbriteDateTime] = None
    vanity_url: Optional[str] = None
    organizer: Optional[EventbriteOrganizer] = None
    logo_id: Optional[str] = None
    logo: Optional[EventbriteImage] = None
    venue: Optional[EventbriteVenue] = None
    format_id: Optional[str] = None
    format: Optional[EventbriteFormat] = None
    category_id: Optional[str] = None
    category: Optional[EventbriteCategory] = None
    subcategory: Optional[EventbriteSubcategory] = None
    music_properties: Optional[EventbriteMusicProperties] = None
    bookmark_info: Optional[EventbriteBookmarkInfo] = None
    ticket_availability: Optional[EventbriteTicketAvailability] = None
    listed: bool = False
    shareable: bool = False
    invite_only: bool = False
    show_remaining: bool = True
    password: Optional[str] = None
    capacity: Optional[int] = None
    capacity_is_custom: bool = True
    tx_time_limit: Optional[str] = None
    hide_start_date: bool = True
    hide_end_date: bool = True
    locale: str = "en_US"
    is_locked: bool = True
    privacy_setting: str = "unlocked"
    is_externally_ticketed: bool = False
    external_ticketing: Optional[EventbriteExternalTicketing] = None
    is_series: bool = False
    is_series_parent: bool = False
    series_id: Optional[str] = None
    is_reserved_seating: bool = False
    show_pick_a_seat: bool = False
    show_seatmap_thumbnail: bool = False
    show_colors_in_seatmap_thumbnail: bool = False
    is_free: bool = False
    version: Optional[str] = None
    event_sales_status: Optional[EventbriteSalesStatus] = None
    checkout_settings: Optional[EventbriteCheckoutSettings] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteEvent":
        """Create EventbriteEvent from JSON dict."""
        return cls(
            id=data.get("id", ""),
            name=EventbriteTextHtml.from_json_dict(data.get("name", {})),
            url=data.get("url", ""),
            status=data.get("status", ""),
            created=data.get("created", ""),
            changed=data.get("changed", ""),
            published=data.get("published", ""),
            currency=data.get("currency", ""),
            online_event=data.get("online_event", False),
            organization_id=data.get("organization_id", ""),
            organizer_id=data.get("organizer_id", ""),
            resource_uri=data.get("resource_uri", ""),
            source=data.get("source", ""),
            description=(
                EventbriteTextHtml.from_json_dict(data.get("description", {})) if data.get("description") else None
            ),
            start=EventbriteDateTime.from_json_dict(data.get("start", {})) if data.get("start") else None,
            end=EventbriteDateTime.from_json_dict(data.get("end", {})) if data.get("end") else None,
            vanity_url=data.get("vanity_url"),
            organizer=EventbriteOrganizer.from_json_dict(data.get("organizer", {})) if data.get("organizer") else None,
            logo_id=data.get("logo_id"),
            logo=EventbriteImage.from_json_dict(data.get("logo", {})) if data.get("logo") else None,
            venue=EventbriteVenue.from_json_dict(data.get("venue", {})) if data.get("venue") else None,
            format_id=data.get("format_id"),
            format=EventbriteFormat.from_json_dict(data.get("format", {})) if data.get("format") else None,
            category_id=data.get("category_id"),
            category=EventbriteCategory.from_json_dict(data.get("category", {})) if data.get("category") else None,
            subcategory=(
                EventbriteSubcategory.from_json_dict(data.get("subcategory", {})) if data.get("subcategory") else None
            ),
            music_properties=(
                EventbriteMusicProperties.from_json_dict(data.get("music_properties", {}))
                if data.get("music_properties")
                else None
            ),
            bookmark_info=(
                EventbriteBookmarkInfo.from_json_dict(data.get("bookmark_info", {}))
                if data.get("bookmark_info")
                else None
            ),
            ticket_availability=None,  # EventbriteTicketAvailability.from_json_dict not implemented yet
            listed=data.get("listed", False),
            shareable=data.get("shareable", False),
            invite_only=data.get("invite_only", False),
            show_remaining=data.get("show_remaining", True),
            password=data.get("password"),
            capacity=data.get("capacity"),
            capacity_is_custom=data.get("capacity_is_custom", True),
            tx_time_limit=data.get("tx_time_limit"),
            hide_start_date=data.get("hide_start_date", True),
            hide_end_date=data.get("hide_end_date", True),
            locale=data.get("locale", "en_US"),
            is_locked=data.get("is_locked", True),
            privacy_setting=data.get("privacy_setting", "unlocked"),
            is_externally_ticketed=data.get("is_externally_ticketed", False),
            external_ticketing=None,  # EventbriteExternalTicketing.from_json_dict not implemented yet
            is_series=data.get("is_series", False),
            is_series_parent=data.get("is_series_parent", False),
            series_id=data.get("series_id"),
            is_reserved_seating=data.get("is_reserved_seating", False),
            show_pick_a_seat=data.get("show_pick_a_seat", False),
            show_seatmap_thumbnail=data.get("show_seatmap_thumbnail", False),
            show_colors_in_seatmap_thumbnail=data.get("show_colors_in_seatmap_thumbnail", False),
            is_free=data.get("is_free", False),
            version=data.get("version"),
            event_sales_status=None,  # EventbriteSalesStatus.from_json_dict not implemented yet
            checkout_settings=None,  # EventbriteCheckoutSettings.from_json_dict not implemented yet
        )
