"""Lineup item model for database operations."""

from dataclasses import dataclass
from typing import Optional

from psycopg2.extras import DictRow

from laughtrack.foundation.protocols.database_entity import DatabaseEntity


@dataclass
class LineupItem(DatabaseEntity):
    """Represents a lineup item entity (relationship between show and comedian)."""

    show_id: int
    comedian_id: str  # UUID
    id: Optional[int] = None

    @staticmethod
    def create_lineup_item(show_id: int, comedian_uuid: str) -> tuple:
        """
        Transform show ID and comedian UUID into a tuple for database operations.
        """
        return (show_id, comedian_uuid)

    @classmethod
    def from_db_row(cls, row: DictRow) -> "LineupItem":
        """Create LineupItem entity from database row."""
        return cls(
            show_id=row.get("show_id"),  # Required field, use direct access
            comedian_id=row.get("comedian_id"),  # Required field, use direct access
            id=row.get("id"),  # Optional field, can be None
        )

    def to_tuple(self) -> tuple:
        """Transform LineupItem entity to database tuple."""
        return (self.show_id, self.comedian_id)
