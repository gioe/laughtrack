"""Email notification model for database operations."""

from dataclasses import dataclass
from typing import Optional

from psycopg2.extras import DictRow

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.protocols.database_entity import DatabaseEntity


@dataclass
class EmailNotification(DatabaseEntity):
    """Represents an email notification entity."""

    email: str
    comedian_shows: JSONDict
    id: Optional[int] = None

    @classmethod
    def from_db_row(cls, row: DictRow) -> "EmailNotification":
        """Create EmailNotification entity from database row."""
        return EmailNotification(
            email=row.get("email", ""), comedian_shows=row.get("comedian_shows", {}), id=row.get("id")
        )

    @classmethod
    def key_from_db_row(cls, row: DictRow) -> tuple:
        """Create a unique key from a database row."""
        return (row.get("email"),)

    def to_tuple(self) -> tuple:
        """Transform EmailNotification entity to database tuple."""
        return (self.email, self.comedian_shows)

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the EmailNotification entity."""
        return (self.email,)
