"""
Data model for scraped page data from Comedy Cellar.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ShowContent:
    """Data model for show content within lineup API response."""

    html: str
    date: str

    @classmethod
    def from_dict(cls, data: dict) -> "ShowContent":
        """Create ShowContent from dictionary."""
        return cls(html=data.get("html", ""), date=data.get("date", ""))


@dataclass
class LineupShowData:
    """Data model for lineup API response show data."""

    id: int
    html: str
    title: str
    description: str

    @classmethod
    def from_dict(cls, data: dict) -> "LineupShowData":
        """Create LineupShowData from dictionary."""
        return cls(
            id=data.get("id", 0),
            html=data.get("html", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
        )


@dataclass
class LineupDataContainer:
    """Data model for lineup data container."""

    show: LineupShowData

    @classmethod
    def from_dict(cls, data: dict) -> "LineupDataContainer":
        """Create LineupDataContainer from dictionary."""
        show_data = data.get("show", {})
        return cls(show=LineupShowData.from_dict(show_data))


@dataclass
class DateAbbreviation:
    """Data model for date abbreviation data."""

    day: str
    month: str
    date: str
    pretty: str

    @classmethod
    def from_dict(cls, data: dict) -> "DateAbbreviation":
        """Create DateAbbreviation from dictionary."""
        return cls(
            day=data.get("day", ""),
            month=data.get("month", ""),
            date=data.get("date", ""),
            pretty=data.get("pretty", ""),
        )


@dataclass
class ShowAge:
    """Data model for show age data."""

    seconds: int
    time: int

    @classmethod
    def from_dict(cls, data: dict) -> "ShowAge":
        """Create ShowAge from dictionary."""
        return cls(seconds=data.get("seconds", 0), time=data.get("time", 0))


@dataclass
class ShowInfoData:
    """Data model for individual show data from shows API."""

    id: int
    time: str
    description: str
    forwardUrl: Optional[str] = None
    soldout: bool = False
    max: int = 0
    special: bool = False
    roomId: int = 0
    cover: int = 0
    note: Optional[str] = None
    mint: bool = False
    weekday: int = 0
    totalGuests: int = 0
    venueMin: int = 0
    venueMax: int = 0
    available: int = 0
    timestamp: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "ShowInfoData":
        """Create ShowInfoData from dictionary."""
        return cls(
            id=data.get("id", 0),
            time=data.get("time", ""),
            description=data.get("description", ""),
            forwardUrl=data.get("forwardUrl"),
            soldout=data.get("soldout", False),
            max=data.get("max", 0),
            special=data.get("special", False),
            roomId=data.get("roomId", 0),
            cover=data.get("cover", 0),
            note=data.get("note"),
            mint=data.get("mint", False),
            weekday=data.get("weekday", 0),
            totalGuests=data.get("totalGuests", 0),
            venueMin=data.get("venueMin", 0),
            venueMax=data.get("venueMax", 0),
            available=data.get("available", 0),
            timestamp=data.get("timestamp", 0),
        )


@dataclass
class ShowsInfoData:
    """Data model for the showInfo object in the shows API response."""

    date: str
    prettyDate: str
    abbr: DateAbbreviation
    shows: List[ShowInfoData]
    age: ShowAge

    @classmethod
    def from_dict(cls, data: dict) -> "ShowsInfoData":
        """Create ShowsInfoData from dictionary."""
        shows_list = []
        for show_dict in data.get("shows", []):
            shows_list.append(ShowInfoData.from_dict(show_dict))

        abbr_data = data.get("abbr", {})
        age_data = data.get("age", {})

        return cls(
            date=data.get("date", ""),
            prettyDate=data.get("prettyDate", ""),
            abbr=DateAbbreviation.from_dict(abbr_data),
            shows=shows_list,
            age=ShowAge.from_dict(age_data),
        )


@dataclass
class ShowsDataContainer:
    """Data model for the data container in shows API response."""

    showInfo: ShowsInfoData

    @classmethod
    def from_dict(cls, data: dict) -> "ShowsDataContainer":
        """Create ShowsDataContainer from dictionary."""
        show_info_dict = data.get("showInfo", {})
        return cls(showInfo=ShowsInfoData.from_dict(show_info_dict))


@dataclass
class ComedyCellarShowsData:
    """Data model for Comedy Cellar shows API response (legacy)."""

    data: ShowsDataContainer

    @classmethod
    def from_dict(cls, data: dict) -> "ComedyCellarShowsData":
        """Create ComedyCellarShowsData from dictionary."""
        data_dict = data.get("data", {})
        return cls(data=ShowsDataContainer.from_dict(data_dict))


@dataclass
class ComedyCellarLineupData:
    """Data model for Comedy Cellar lineup API response (legacy compatibility)."""

    show: LineupShowData

    @classmethod
    def from_dict(cls, data: dict) -> "ComedyCellarLineupData":
        """Create ComedyCellarLineupData from dictionary."""
        show_data = data.get("show", {})
        return cls(show=LineupShowData.from_dict(show_data))


@dataclass
class ComedyCellarLineupAPIResponse:
    """Data model for the complete Comedy Cellar lineup API response.

    This represents the actual structure returned by the lineup API,
    which includes show content, date, and available dates dictionary.

    Example JSON structure:
    {
        "show": {
            "html": "<div>...</div>",
            "date": "Sunday August 17, 2025"
        },
        "date": "2025-08-17",
        "dates": {
            "2025-08-17": "Sunday August 17, 2025",
            "2025-08-18": "Monday August 18, 2025",
            ...
        }
    }
    """

    show: ShowContent
    date: str
    dates: Dict[str, str]

    @classmethod
    def from_dict(cls, data: dict) -> "ComedyCellarLineupAPIResponse":
        """Create ComedyCellarLineupAPIResponse from dictionary."""
        show_data = data.get("show", {})
        return cls(show=ShowContent.from_dict(show_data), date=data.get("date", ""), dates=data.get("dates", {}))


@dataclass
class ComedyCellarShowsAPIResponse:
    """Data model for the complete Comedy Cellar shows API response.

    This represents the actual structure returned by the shows API,
    which includes message and data with showInfo containing all show details.

    Example JSON structure:
    {
        "message": "Ok",
        "data": {
            "showInfo": {
                "date": "2025-08-17",
                "prettyDate": "August 17, 2025",
                "abbr": {...},
                "shows": [...],
                "age": {...}
            }
        }
    }
    """

    message: str
    data: ShowsDataContainer

    @classmethod
    def from_dict(cls, data: dict) -> "ComedyCellarShowsAPIResponse":
        """Create ComedyCellarShowsAPIResponse from dictionary."""
        data_dict = data.get("data", {})
        return cls(message=data.get("message", ""), data=ShowsDataContainer.from_dict(data_dict))
