from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.ticket.model import Ticket
import pytz
from psycopg2.extras import DictRow

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.protocols.database_entity import DatabaseEntity
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.number.utils import NumberUtils
from gioe_libs.string_utils import StringUtils
from laughtrack.foundation.utilities.url.utils import URLUtils


@dataclass
class Show(DatabaseEntity):
    """Data model for a comedy show that implements DatabaseEntity protocol."""

    name: str
    club_id: int
    date: datetime  # Stored in UTC in database
    show_page_url: str
    lineup: List[Comedian] = field(default_factory=list)
    tickets: List[Ticket] = field(default_factory=list)
    supplied_tags: List[str] = field(default_factory=list)  # Handled via junction table in database
    description: Optional[str] = None
    timezone: Optional[str] = None  # Used for UTC conversion only, not stored in database
    popularity: float = 0.0
    room: Optional[str] = ""
    production_company_id: Optional[int] = None
    id: Optional[int] = None  # Database ID
    operation_type: Optional[str] = None  # 'inserted' or 'updated'

    def __post_init__(self) -> None:
        """Argument-level validation and light normalization for Show instances.

        This enforces core domain invariants at creation time so invalid
        entities don't enter the system. Cross-record validations remain
        at the persistence layer.
        """
        # Normalize simple string fields
        if isinstance(self.name, str):
            self.name = StringUtils.normalize_whitespace(self.name).strip()

        if isinstance(self.room, str):
            self.room = StringUtils.normalize_whitespace(self.room).strip()
        elif self.room is None:
            self.room = ""

        if isinstance(self.show_page_url, str):
            self.show_page_url = self.show_page_url.strip()

        # Light string normalization; defer strict required checks to validator
        if isinstance(self.show_page_url, str) and self.show_page_url:
            normalized_url = URLUtils.normalize_url(self.show_page_url)
            # Only apply normalization if it results in a valid URL; otherwise, leave as-is for validator to flag
            if URLUtils.is_valid_url(normalized_url):
                self.show_page_url = normalized_url

        # Number validations
        club_err = NumberUtils.validate_positive_number(self.club_id, "Club ID", allow_zero=False)
        if club_err:
            raise ValueError(club_err)

        pop_err = NumberUtils.validate_positive_number(self.popularity, "Popularity score")
        if pop_err:
            raise ValueError(pop_err)

        # Datetime validation
        date_err = DateTimeUtils.validate_datetime(self.date, "Show date")
        if date_err:
            raise ValueError(date_err)

    @classmethod
    def create(cls, **kwargs) -> "Show":
        """Factory method to create a Show with proper type conversions."""
        # Handle date conversion if it's a string
        if isinstance(kwargs.get("date"), str):

            date_str = kwargs.get("date")
            timezone_str = kwargs.get("timezone")

            # Ensure we have valid string values for the function
            if date_str is not None and timezone_str is not None:
                kwargs["date"] = DateTimeUtils.parse_datetime_with_timezone(date_str, timezone_str)
            elif date_str is not None:
                # Handle case where timezone is None - pass empty string or default
                kwargs["date"] = DateTimeUtils.parse_datetime_with_timezone(date_str, "")

        return cls(**kwargs)

    @classmethod
    def from_db_row(cls, row: JSONDict) -> "Show":
        """Create Show entity from database row."""
        return cls(
            id=row.get("id"),
            name=row["name"],
            show_page_url=row["show_page_url"],
            description=row.get("description", ""),
            date=row["date"],
            club_id=row["club_id"],
            room=row.get("room", ""),
            popularity=row.get("popularity", 0.0),
            production_company_id=row.get("production_company_id"),
        )

    @classmethod
    def key_from_db_row(cls, row: DictRow) -> tuple:
        """Create a unique key from a database row."""
        return (row.get("club_id"), row.get("date"), row.get("room", ""))

    def to_tuple(self) -> tuple:
        """Transform Show entity to database tuple."""
        return (
            self.name,
            self.show_page_url,
            self.description or "",
            self.date,
            self.club_id,
            datetime.now().isoformat(),
            self.room,
            self.production_company_id,
        )

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the Show entity.

        Normalizes self.date to UTC-naive so that naive show dates and the
        UTC-aware datetimes returned by psycopg2 from TIMESTAMPTZ columns
        compare equal in dict/set keys.
        """
        date = self.date
        if date is not None and date.tzinfo is not None:
            date = date.astimezone(timezone.utc).replace(tzinfo=None)
        return (self.club_id, date, self.room)
