"""
Eventbrite single event API response models.

This module contains dataclass definitions for the individual event endpoint
(/v3/events/{event_id}/) response structure.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Import common types from other modules to avoid duplication
from laughtrack.foundation.models.api.eventbrite.base_models import EventbriteDateTime, EventbritePrice, EventbriteTextHtml
from laughtrack.foundation.models.api.eventbrite.category_models import EventbriteCategory, EventbriteFormat, EventbriteSubcategory
from laughtrack.foundation.models.api.eventbrite.location_models import EventbriteVenue
from .main_event_models import EventbriteBookmarkInfo, EventbriteMusicProperties
from .organizer_models import EventbriteOrganizer


# Classes that are specific to this module and don't exist elsewhere
@dataclass
class EventbriteCropMask:
    """Image crop mask coordinates."""

    top_left: Dict[str, int]  # {"x": int, "y": int}
    width: int
    height: int


@dataclass
class EventbriteImageOriginal:
    """Original image dimensions."""

    url: str
    width: int
    height: int


@dataclass
class EventbriteLogo:
    """Logo/image information."""

    id: str
    url: str
    crop_mask: Optional[EventbriteCropMask] = None
    original: Optional[EventbriteImageOriginal] = None
    aspect_ratio: Optional[str] = None
    edge_color: Optional[str] = None
    edge_color_set: Optional[bool] = None


@dataclass
class EventbriteTicketAvailability:
    """Ticket availability and pricing information."""

    has_available_tickets: bool
    is_sold_out: bool
    waitlist_available: bool
    minimum_ticket_price: Optional[EventbritePrice] = None
    maximum_ticket_price: Optional[EventbritePrice] = None
    start_sales_date: Optional[EventbriteDateTime] = None


@dataclass
class EventbriteExternalTicketing:
    """External ticketing provider information."""

    external_url: str
    ticketing_provider_name: str
    is_free: bool
    minimum_ticket_price: EventbritePrice
    maximum_ticket_price: EventbritePrice
    sales_start: str
    sales_end: str


@dataclass
class EventbriteEventSalesStatus:
    """Event sales status information."""

    sales_status: str  # "on_sale", "not_yet_on_sale", "sales_ended", "sold_out", "unavailable"
    start_sales_date: Optional[EventbriteDateTime] = None
    message: Optional[str] = None
    message_type: Optional[str] = None  # "default", "canonical", "custom"
    message_code: Optional[str] = None  # Various codes like "tickets_not_yet_on_sale"


@dataclass
class EventbriteOfflineSettings:
    """Offline payment settings."""

    payment_method: str
    instructions: str


@dataclass
class EventbriteCheckoutSettings:
    """Checkout and payment settings."""

    created: str
    changed: str
    country_code: str
    currency_code: str
    checkout_method: str  # "paypal", "eventbrite", "authnet", "offline"
    offline_settings: Optional[List[EventbriteOfflineSettings]] = None
    user_instrument_vault_id: Optional[str] = None


@dataclass
class EventbriteSingleEventResponse:
    """Complete response for a single Eventbrite event from /v3/events/{event_id}/"""

    # Required fields
    id: str
    name: EventbriteTextHtml
    created: str
    changed: str

    # Core event information
    summary: Optional[str] = None
    description: Optional[EventbriteTextHtml] = None
    start: Optional[EventbriteDateTime] = None
    end: Optional[EventbriteDateTime] = None
    url: Optional[str] = None
    vanity_url: Optional[str] = None
    published: Optional[str] = None
    status: Optional[str] = None  # "draft", "live", "started", "ended", "completed", "canceled"
    currency: Optional[str] = None
    online_event: Optional[bool] = None

    # Organization and organizer
    organization_id: Optional[str] = None
    organizer_id: Optional[str] = None
    organizer: Optional[EventbriteOrganizer] = None

    # Branding
    logo_id: Optional[str] = None
    logo: Optional[EventbriteLogo] = None

    # Venue information
    venue_id: Optional[str] = None
    venue: Optional[EventbriteVenue] = None

    # Classification
    format_id: Optional[str] = None
    format: Optional[EventbriteFormat] = None
    category_id: Optional[str] = None
    category: Optional[EventbriteCategory] = None
    subcategory_id: Optional[str] = None
    subcategory: Optional[EventbriteSubcategory] = None

    # Special properties
    music_properties: Optional[EventbriteMusicProperties] = None
    bookmark_info: Optional[EventbriteBookmarkInfo] = None

    # Policy and settings
    refund_policy: Optional[str] = None

    # Ticketing
    ticket_availability: Optional[EventbriteTicketAvailability] = None
    is_externally_ticketed: Optional[bool] = None
    external_ticketing: Optional[EventbriteExternalTicketing] = None

    # Visibility and access
    listed: Optional[bool] = None
    shareable: Optional[bool] = None
    invite_only: Optional[bool] = None
    show_remaining: Optional[bool] = None
    password: Optional[str] = None
    privacy_setting: Optional[str] = None

    # Capacity and timing
    capacity: Optional[int] = None
    capacity_is_custom: Optional[bool] = None
    tx_time_limit: Optional[str] = None
    hide_start_date: Optional[bool] = None
    hide_end_date: Optional[bool] = None

    # Series information
    is_series: Optional[bool] = None
    is_series_parent: Optional[bool] = None
    series_id: Optional[str] = None

    # Seating
    is_reserved_seating: Optional[bool] = None
    show_pick_a_seat: Optional[bool] = None
    show_seatmap_thumbnail: Optional[bool] = None
    show_colors_in_seatmap_thumbnail: Optional[bool] = None

    # Pricing
    is_free: Optional[bool] = None

    # Meta information
    locale: Optional[str] = None
    is_locked: Optional[bool] = None
    source: Optional[str] = None
    version: Optional[str] = None
    resource_uri: Optional[str] = None

    # Sales and checkout
    event_sales_status: Optional[EventbriteEventSalesStatus] = None
    checkout_settings: Optional[EventbriteCheckoutSettings] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteSingleEventResponse":
        """Create EventbriteSingleEventResponse from JSON dict."""
        return cls(
            id=data.get("id", ""),
            name=EventbriteTextHtml.from_json_dict(data.get("name", {})),
            created=data.get("created", ""),
            changed=data.get("changed", ""),
            summary=data.get("summary"),
            description=(
                EventbriteTextHtml.from_json_dict(data.get("description", {})) if data.get("description") else None
            ),
            start=EventbriteDateTime.from_json_dict(data.get("start", {})) if data.get("start") else None,
            end=EventbriteDateTime.from_json_dict(data.get("end", {})) if data.get("end") else None,
            url=data.get("url"),
            vanity_url=data.get("vanity_url"),
            published=data.get("published"),
            status=data.get("status"),
            currency=data.get("currency"),
            online_event=data.get("online_event"),
            organization_id=data.get("organization_id"),
            organizer_id=data.get("organizer_id"),
            organizer=EventbriteOrganizer.from_json_dict(data.get("organizer", {})) if data.get("organizer") else None,
            logo_id=data.get("logo_id"),
            logo=None,  # Logo object not implemented yet
            venue_id=data.get("venue_id"),
            venue=EventbriteVenue.from_json_dict(data.get("venue", {})) if data.get("venue") else None,
            format_id=data.get("format_id"),
            format=EventbriteFormat.from_json_dict(data.get("format", {})) if data.get("format") else None,
            category_id=data.get("category_id"),
            category=EventbriteCategory.from_json_dict(data.get("category", {})) if data.get("category") else None,
            subcategory_id=data.get("subcategory_id"),
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
            listed=data.get("listed"),
            shareable=data.get("shareable"),
            invite_only=data.get("invite_only"),
            show_remaining=data.get("show_remaining"),
            capacity=data.get("capacity"),
            capacity_is_custom=data.get("capacity_is_custom"),
            tx_time_limit=data.get("tx_time_limit"),
            hide_start_date=data.get("hide_start_date"),
            hide_end_date=data.get("hide_end_date"),
            is_series=data.get("is_series"),
            is_series_parent=data.get("is_series_parent"),
            is_reserved_seating=data.get("is_reserved_seating"),
            show_pick_a_seat=data.get("show_pick_a_seat"),
            show_seatmap_thumbnail=data.get("show_seatmap_thumbnail"),
            show_colors_in_seatmap_thumbnail=data.get("show_colors_in_seatmap_thumbnail"),
            is_free=data.get("is_free"),
            locale=data.get("locale"),
            is_locked=data.get("is_locked"),
            source=data.get("source"),
            version=data.get("version"),
            resource_uri=data.get("resource_uri"),
            event_sales_status=None,  # EventbriteEventSalesStatus object not implemented yet
            checkout_settings=None,  # EventbriteCheckoutSettings object not implemented yet
        )
