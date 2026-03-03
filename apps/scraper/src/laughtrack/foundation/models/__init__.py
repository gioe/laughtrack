"""
Foundation models for basic data types with no domain    # API models
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
    "EventbriteVenue",ncies.

These models contain pure Python types and enums that don't depend on 
any Laughtrack-specific business logic.
"""

from .api import (
    ComedyCellarLineupAPIResponse,
    ComedyCellarShowsAPIResponse,
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
    LineupDataContainer,
    LineupShowData,
    ShowContent,
    ShowsDataContainer,
)
from .log_level import LogLevel
from .operation_result import DatabaseOperationResult
from .price_range import PriceRange
from .request_data import RequestData
from .types import (
    ConnectionString,
    DatabaseRow,
    HTMLContent,
    HTTPHeaders,
    HTTPParams,
    Input,
    JSONArray,
    JSONData,
    JSONDict,
    JSONValue,
    Output,
    QueryParams,
    R,
    RawScrapedData,
    ScrapingTarget,
    T,
    URL,
    ValidatedData,
)

__all__ = [
    "LogLevel",
    "PriceRange",
    "RequestData",
    "DatabaseOperationResult",
    # API models
    "ComedyCellarLineupAPIResponse",
    "ComedyCellarShowsAPIResponse",
    "EventbriteTicket",
    "LineupDataContainer",
    "LineupShowData",
    "ShowContent",
    "ShowsDataContainer",
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
]
