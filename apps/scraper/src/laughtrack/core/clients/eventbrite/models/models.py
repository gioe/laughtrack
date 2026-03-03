"""
Eventbrite API response models.

This module contains dataclass definitions for Eventbrite API responses,
following the scraper architecture patterns for domain-specific models.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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
            page_size=data.get("page_size", 0),
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


@dataclass
class EventbriteImageCropMask:
    """Image crop mask information."""

    top_left: Dict[str, int]  # {"x": int, "y": int}
    width: int
    height: int

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteImageCropMask":
        """Create EventbriteImageCropMask from JSON dict."""
        return cls(top_left=data.get("top_left", {}), width=data.get("width", 0), height=data.get("height", 0))


@dataclass
class EventbriteImage:
    """Image information with cropping and metadata."""

    id: str
    url: str
    crop_mask: Optional[EventbriteImageCropMask] = None
    original: Optional[Dict[str, Any]] = None  # {"url": str, "width": int, "height": int}
    aspect_ratio: Optional[str] = None
    edge_color: Optional[str] = None
    edge_color_set: Optional[bool] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteImage":
        """Create EventbriteImage from JSON dict."""
        crop_mask = None
        if data.get("crop_mask"):
            crop_mask = EventbriteImageCropMask.from_json_dict(data["crop_mask"])

        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            crop_mask=crop_mask,
            original=data.get("original"),
            aspect_ratio=data.get("aspect_ratio"),
            edge_color=data.get("edge_color"),
            edge_color_set=data.get("edge_color_set"),
        )


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
        description = None
        if data.get("description"):
            description = EventbriteTextHtml.from_json_dict(data["description"])

        long_description = None
        if data.get("long_description"):
            long_description = EventbriteTextHtml.from_json_dict(data["long_description"])

        logo = None
        if data.get("logo"):
            logo = EventbriteImage.from_json_dict(data["logo"])

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=description,
            long_description=long_description,
            logo_id=data.get("logo_id"),
            logo=logo,
            resource_uri=data.get("resource_uri"),
            url=data.get("url"),
            num_past_events=data.get("num_past_events"),
            num_future_events=data.get("num_future_events"),
            twitter=data.get("twitter"),
            facebook=data.get("facebook"),
        )


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
        address = None
        if data.get("address"):
            address = EventbriteAddress.from_json_dict(data["address"])

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            resource_uri=data.get("resource_uri", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            age_restriction=data.get("age_restriction"),
            capacity=data.get("capacity"),
            address=address,
        )


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
        subcategories = None
        if data.get("subcategories"):
            subcategories = [EventbriteSubcategory.from_json_dict(sub_data) for sub_data in data["subcategories"]]

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_localized=data.get("name_localized", ""),
            short_name=data.get("short_name", ""),
            short_name_localized=data.get("short_name_localized", ""),
            resource_uri=data.get("resource_uri", ""),
            subcategories=subcategories,
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
class EventbriteTicketAvailability:
    """Ticket availability and pricing information."""

    has_available_tickets: bool
    is_sold_out: bool
    waitlist_available: bool = False
    minimum_ticket_price: Optional[EventbritePrice] = None
    maximum_ticket_price: Optional[EventbritePrice] = None
    start_sales_date: Optional[EventbriteDateTime] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteTicketAvailability":
        """Create EventbriteTicketAvailability from JSON dict."""
        minimum_price = None
        if data.get("minimum_ticket_price"):
            minimum_price = EventbritePrice.from_json_dict(data["minimum_ticket_price"])

        maximum_price = None
        if data.get("maximum_ticket_price"):
            maximum_price = EventbritePrice.from_json_dict(data["maximum_ticket_price"])

        start_sales_date = None
        if data.get("start_sales_date"):
            start_sales_date = EventbriteDateTime.from_json_dict(data["start_sales_date"])

        return cls(
            has_available_tickets=data.get("has_available_tickets", False),
            is_sold_out=data.get("is_sold_out", False),
            waitlist_available=data.get("waitlist_available", False),
            minimum_ticket_price=minimum_price,
            maximum_ticket_price=maximum_price,
            start_sales_date=start_sales_date,
        )


@dataclass
class EventbriteExternalTicketing:
    """External ticketing provider information."""

    external_url: str = ""
    ticketing_provider_name: str = ""
    is_free: bool = False
    minimum_ticket_price: Optional[EventbritePrice] = None
    maximum_ticket_price: Optional[EventbritePrice] = None
    sales_start: str = ""
    sales_end: str = ""

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteExternalTicketing":
        """Create EventbriteExternalTicketing from JSON dict."""
        minimum_price = None
        if data.get("minimum_ticket_price"):
            minimum_price = EventbritePrice.from_json_dict(data["minimum_ticket_price"])

        maximum_price = None
        if data.get("maximum_ticket_price"):
            maximum_price = EventbritePrice.from_json_dict(data["maximum_ticket_price"])

        return cls(
            external_url=data.get("external_url", ""),
            ticketing_provider_name=data.get("ticketing_provider_name", ""),
            is_free=data.get("is_free", False),
            minimum_ticket_price=minimum_price,
            maximum_ticket_price=maximum_price,
            sales_start=data.get("sales_start", ""),
            sales_end=data.get("sales_end", ""),
        )


@dataclass
class EventbriteSalesStatus:
    """Event sales status information."""

    sales_status: str
    start_sales_date: Optional[EventbriteDateTime] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteSalesStatus":
        """Create EventbriteSalesStatus from JSON dict."""
        start_sales_date = None
        if data.get("start_sales_date"):
            start_sales_date = EventbriteDateTime.from_json_dict(data["start_sales_date"])

        return cls(sales_status=data.get("sales_status", ""), start_sales_date=start_sales_date)


@dataclass
class EventbriteOfflineSettings:
    """Offline payment settings."""

    payment_method: str
    instructions: str = ""

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteOfflineSettings":
        """Create EventbriteOfflineSettings from JSON dict."""
        return cls(payment_method=data.get("payment_method", ""), instructions=data.get("instructions", ""))


@dataclass
class EventbriteCheckoutSettings:
    """Checkout and payment settings."""

    created: str
    changed: str
    country_code: str = ""
    currency_code: str = ""
    checkout_method: str = ""
    user_instrument_vault_id: str = ""
    offline_settings: Optional[List[EventbriteOfflineSettings]] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteCheckoutSettings":
        """Create EventbriteCheckoutSettings from JSON dict."""
        offline_settings = None
        if data.get("offline_settings"):
            offline_settings = [
                EventbriteOfflineSettings.from_json_dict(setting_data) for setting_data in data["offline_settings"]
            ]

        return cls(
            created=data.get("created", ""),
            changed=data.get("changed", ""),
            country_code=data.get("country_code", ""),
            currency_code=data.get("currency_code", ""),
            checkout_method=data.get("checkout_method", ""),
            user_instrument_vault_id=data.get("user_instrument_vault_id", ""),
            offline_settings=offline_settings,
        )


@dataclass
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
        # Parse required text fields
        name = EventbriteTextHtml.from_json_dict(data.get("name", {}))

        # Parse optional complex objects
        description = None
        if data.get("description"):
            description = EventbriteTextHtml.from_json_dict(data["description"])

        start = None
        if data.get("start"):
            start = EventbriteDateTime.from_json_dict(data["start"])

        end = None
        if data.get("end"):
            end = EventbriteDateTime.from_json_dict(data["end"])

        organizer = None
        if data.get("organizer"):
            organizer = EventbriteOrganizer.from_json_dict(data["organizer"])

        logo = None
        if data.get("logo"):
            logo = EventbriteImage.from_json_dict(data["logo"])

        venue = None
        if data.get("venue"):
            venue = EventbriteVenue.from_json_dict(data["venue"])

        format_obj = None
        if data.get("format"):
            format_obj = EventbriteFormat.from_json_dict(data["format"])

        category = None
        if data.get("category"):
            category = EventbriteCategory.from_json_dict(data["category"])

        subcategory = None
        if data.get("subcategory"):
            subcategory = EventbriteSubcategory.from_json_dict(data["subcategory"])

        music_properties = None
        if data.get("music_properties"):
            music_properties = EventbriteMusicProperties.from_json_dict(data["music_properties"])

        bookmark_info = None
        if data.get("bookmark_info"):
            bookmark_info = EventbriteBookmarkInfo.from_json_dict(data["bookmark_info"])

        ticket_availability = None
        if data.get("ticket_availability"):
            ticket_availability = EventbriteTicketAvailability.from_json_dict(data["ticket_availability"])

        external_ticketing = None
        if data.get("external_ticketing"):
            external_ticketing = EventbriteExternalTicketing.from_json_dict(data["external_ticketing"])

        event_sales_status = None
        if data.get("event_sales_status"):
            event_sales_status = EventbriteSalesStatus.from_json_dict(data["event_sales_status"])

        checkout_settings = None
        if data.get("checkout_settings"):
            checkout_settings = EventbriteCheckoutSettings.from_json_dict(data["checkout_settings"])

        return cls(
            id=data.get("id", ""),
            name=name,
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
            description=description,
            start=start,
            end=end,
            vanity_url=data.get("vanity_url"),
            organizer=organizer,
            logo_id=data.get("logo_id"),
            logo=logo,
            venue=venue,
            format_id=data.get("format_id"),
            format=format_obj,
            category=category,
            subcategory=subcategory,
            music_properties=music_properties,
            bookmark_info=bookmark_info,
            ticket_availability=ticket_availability,
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
            external_ticketing=external_ticketing,
            is_series=data.get("is_series", False),
            is_series_parent=data.get("is_series_parent", False),
            series_id=data.get("series_id"),
            is_reserved_seating=data.get("is_reserved_seating", False),
            show_pick_a_seat=data.get("show_pick_a_seat", False),
            show_seatmap_thumbnail=data.get("show_seatmap_thumbnail", False),
            show_colors_in_seatmap_thumbnail=data.get("show_colors_in_seatmap_thumbnail", False),
            is_free=data.get("is_free", False),
            version=data.get("version"),
            event_sales_status=event_sales_status,
            checkout_settings=checkout_settings,
        )


@dataclass
class EventbriteListEventsResponse:
    """Complete response from the Eventbrite List Events API."""

    pagination: EventbritePagination
    events: List[EventbriteEvent]

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteListEventsResponse":
        """Create EventbriteListEventsResponse from JSON dict."""
        pagination = EventbritePagination.from_json_dict(data.get("pagination", {}))

        events = []
        if data.get("events"):
            events = [EventbriteEvent.from_json_dict(event_data) for event_data in data["events"]]

        return cls(pagination=pagination, events=events)
