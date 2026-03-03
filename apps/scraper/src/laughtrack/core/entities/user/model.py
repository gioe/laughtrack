from dataclasses import dataclass
from typing import Any, Dict, Optional

from psycopg2.extras import DictRow

from laughtrack.foundation.protocols.database_entity import DatabaseEntity


@dataclass
class User(DatabaseEntity):
    """Simple user model focused on email address for notifications."""

    id: str  # Database uses text for id
    email: str
    name: Optional[str] = None

    def __str__(self) -> str:
        """Returns a string representation of the User object."""
        return f"User(id='{self.id}', email='{self.email}', name='{self.name}')"

    def to_tuple(self) -> tuple:
        """Transform User entity to database tuple."""
        return (self.id, self.email, self.name)

    @classmethod
    def from_db_row(cls, row: DictRow) -> "User":
        """Create User entity from database row."""
        return cls(id=row.get("id", ""), email=row.get("email", ""), name=row.get("name"))
