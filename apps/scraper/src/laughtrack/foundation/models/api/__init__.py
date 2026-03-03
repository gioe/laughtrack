"""
API response models for external services.

Contains pure data models for API responses with no domain dependencies.
"""

from .comedy_cellar import (
    ComedyCellarLineupAPIResponse,
    ComedyCellarShowsAPIResponse,
    LineupDataContainer,
    LineupShowData,
    ShowContent,
    ShowsDataContainer,
)
from .eventbrite import (
    EventbriteAddress,
    EventbriteCategory,
    EventbriteDateTime,
    EventbriteFormat,
    EventbriteImage,
    EventbriteImageCropMask,
    EventbritePagination,
    EventbritePrice,
    EventbriteSubcategory,
    EventbriteTextHtml,
    EventbriteTicket,
    EventbriteVenue,
)

__all__ = [
    "ComedyCellarLineupAPIResponse",
    "ComedyCellarShowsAPIResponse",
    "LineupDataContainer", 
    "LineupShowData",
    "ShowContent",
    "ShowsDataContainer",
    # Eventbrite models
    "EventbriteAddress",
    "EventbriteCategory",
    "EventbriteDateTime",
    "EventbriteFormat",
    "EventbriteImage",
    "EventbriteImageCropMask",
    "EventbritePagination",
    "EventbritePrice",
    "EventbriteSubcategory",
    "EventbriteTextHtml",
    "EventbriteTicket",
    "EventbriteVenue",
]
