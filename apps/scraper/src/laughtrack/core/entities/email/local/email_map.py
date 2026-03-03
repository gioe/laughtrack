"""Data models for email notification mapping operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Sequence

from psycopg2.extras import DictRow


@dataclass
class ShowNotificationData:
    """Data model for individual show notification information."""

    id: int
    name: str
    date: datetime
    show_page_url: str
    club_name: str
    club_timezone: str


@dataclass
class ComedianShowsData:
    """Data model for comedian shows notification data."""

    comedian_name: str
    shows: List[ShowNotificationData]


@dataclass
class UserEmailMap:
    """Data model for user email notification mapping."""

    email: str
    comedian_shows: Dict[str, List[ShowNotificationData]]

    @classmethod
    def from_db_row(cls, row: DictRow) -> "UserEmailMap":
        """Create UserEmailMap from database row."""
        comedian_shows = {}

        # Parse the comedian_shows JSON structure
        for comedian_name, shows_data in row["comedian_shows"].items():
            show_objects = [
                ShowNotificationData(
                    id=show["id"],
                    name=show["name"],
                    date=show["date"],
                    show_page_url=show["show_page_url"],
                    club_name=show["club_name"],
                    club_timezone=show["club_timezone"],
                )
                for show in shows_data
            ]
            comedian_shows[comedian_name] = show_objects

        return cls(email=row["email"], comedian_shows=comedian_shows)


@dataclass
class EmailMap:
    """Data model for the complete email mapping result."""

    user_email_maps: Dict[str, UserEmailMap]
    total_users: int

    @classmethod
    def from_db_results(cls, results: Sequence[Any]) -> "EmailMap":
        """Create EmailMapResult from database results."""
        user_email_maps = {}

        for row in results:
            user_map = UserEmailMap.from_db_row(row)
            user_email_maps[user_map.email] = user_map

        return cls(user_email_maps=user_email_maps, total_users=len(user_email_maps))
