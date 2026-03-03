"""
Foundation module for Laughtrack.

This module contains foundational components that have no dependencies on other 
Laughtrack-specific modules. They only import from standard library and third-party
libraries, making them reusable and preventing circular imports.

Components:
- models: Basic data types, enums, and type aliases (LogLevel, PriceRange, JSONDict, etc.)
- protocols: Core interfaces and protocols (DatabaseEntity, EventListContainer)
- exceptions: Core exception hierarchy for scraping operations  
- utilities: Pure utility functions for string, datetime, and URL manipulation
- config: Configuration classes and registries with no domain dependencies
"""

from .config import (
    ClubInfo,
    CLUB_REGISTRY,
    get_all_club_info,
    get_all_club_locations,
    get_club_id,
    get_club_info,
    get_club_timezone,
    get_clubs_by_timezone,
)
from .exceptions import (
    DataError,
    ErrorClassifier,
    ErrorSeverity,
    NetworkError,
    RateLimitError,
    ScrapingError,
    UnknownClubError,
)
from .models import (
    DatabaseOperationResult,
    ComedyCellarLineupAPIResponse,
    ComedyCellarShowsAPIResponse,
    ConnectionString,
    DatabaseRow,
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
    HTMLContent,
    HTTPHeaders,
    HTTPParams,
    Input,
    JSONArray,
    JSONData,
    JSONDict,
    JSONValue,
    LineupDataContainer,
    LineupShowData,
    LogLevel,
    Output,
    PriceRange,
    QueryParams,
    R,
    RawScrapedData,
    RequestData,
    ScrapingTarget,
    ShowContent,
    ShowsDataContainer,
    T,
    URL,
    ValidatedData,
)
from .protocols import DatabaseEntity, EventListContainer
from .utilities import DateTimeUtils, StringUtils, URLUtils

__all__ = [
    # Configuration
    "ClubInfo",
    "CLUB_REGISTRY",
    "get_all_club_info",
    "get_all_club_locations",
    "get_club_id", 
    "get_club_info",
    "get_club_timezone",
    "get_clubs_by_timezone",
    # Models - Basic types and enums
    "LogLevel",
    "PriceRange",
    "RequestData",
    "DatabaseOperationResult",
    # API models
    "ComedyCellarLineupAPIResponse",
    "ComedyCellarShowsAPIResponse",
    "LineupDataContainer",
    "LineupShowData",
    "ShowContent",
    "ShowsDataContainer",
    # Eventbrite API models
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
    # Type variables
    "T",
    "R", 
    "Input",
    "Output",
    # JSON types
    "JSONValue",
    "JSONDict",
    "JSONArray", 
    "JSONData",
    # Database types
    "DatabaseRow",
    "QueryParams",
    "ConnectionString",
    # HTTP types
    "HTTPHeaders",
    "HTTPParams",
    "URL",
    # Scraping types
    "HTMLContent",
    "RawScrapedData",
    "ValidatedData",
    "ScrapingTarget",
    # Protocols
    "DatabaseEntity",
    "EventListContainer",
    # Exceptions
    "DataError",
    "ErrorClassifier",
    "ErrorSeverity", 
    "NetworkError",
    "RateLimitError",
    "ScrapingError",
    "UnknownClubError",
    # Utilities
    "DateTimeUtils",
    "StringUtils",
    "URLUtils",
]