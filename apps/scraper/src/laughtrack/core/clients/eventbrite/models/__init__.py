"""
Eventbrite API response models.

This module contains all dataclass definitions for Eventbrite API responses,
organized by functional areas.
"""

# Base models
from laughtrack.foundation.models.api.eventbrite.base_models import EventbriteDateTime, EventbritePagination, EventbritePrice, EventbriteTextHtml

# Category models
from laughtrack.foundation.models.api.eventbrite.category_models import EventbriteCategory, EventbriteFormat, EventbriteSubcategory
from .event_models import EventbriteSingleEventResponse

# Image models
from laughtrack.foundation.models.api.eventbrite.image_models import EventbriteImage, EventbriteImageCropMask

# Location models
from laughtrack.foundation.models.api.eventbrite.location_models import EventbriteAddress, EventbriteVenue

# Main event models
from .main_event_models import EventbriteBookmarkInfo, EventbriteEvent, EventbriteMusicProperties

# Organizer models
from .organizer_models import EventbriteOrganizer

# Response models
from .response_models import EventbriteListEventsResponse

# Ticket models
from .ticket_models import (
    EventbriteCheckoutSettings,
    EventbriteExternalTicketing,
    EventbriteOfflineSettings,
    EventbriteSalesStatus,
    EventbriteTicketAvailability,
)

__all__ = [
    "EventbriteSingleEventResponse",
    # Base models
    "EventbritePagination",
    "EventbritePrice",
    "EventbriteDateTime",
    "EventbriteTextHtml",
    # Image models
    "EventbriteImageCropMask",
    "EventbriteImage",
    # Location models
    "EventbriteAddress",
    "EventbriteVenue",
    # Organizer models
    "EventbriteOrganizer",
    # Category models
    "EventbriteFormat",
    "EventbriteSubcategory",
    "EventbriteCategory",
    # Ticket models
    "EventbriteTicketAvailability",
    "EventbriteExternalTicketing",
    "EventbriteSalesStatus",
    "EventbriteOfflineSettings",
    "EventbriteCheckoutSettings",
    # Main event models
    "EventbriteMusicProperties",
    "EventbriteBookmarkInfo",
    "EventbriteEvent",
    # Response models
    "EventbriteListEventsResponse",
]
