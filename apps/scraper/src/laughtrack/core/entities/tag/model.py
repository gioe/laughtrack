"""Tag model for database operations."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from psycopg2.extras import DictRow

from laughtrack.foundation.protocols.database_entity import DatabaseEntity


class TagVisibility(Enum):
    """Enum for tag visibility levels."""

    ADMIN = "ADMIN"
    USER = "USER"
    PUBLIC = "PUBLIC"


@dataclass
class Tag(DatabaseEntity):
    """Represents a tag entity."""

    id: Optional[int] = None
    type: str = "show"
    user_facing: bool = False
    name: Optional[str] = None
    restrict_content: bool = False
    slug: Optional[str] = None
    visibility: TagVisibility = TagVisibility.ADMIN

    def to_tuple(self) -> tuple:
        """Transform Tag entity to database tuple."""
        return (
            self.type,
            self.user_facing,
            self.name,
            self.restrict_content,
            self.slug,
            self.visibility.value if self.visibility else "ADMIN",
        )

    @classmethod
    def from_db_row(cls, row: DictRow) -> "Tag":
        """Create Tag entity from database row."""
        visibility_str = row.get("visibility", "ADMIN")
        try:
            visibility = TagVisibility(visibility_str)
        except ValueError:
            visibility = TagVisibility.ADMIN

        return cls(
            id=row.get("id"),
            type=row.get("type", "show"),
            user_facing=row.get("user_facing", False),
            name=row.get("name"),
            restrict_content=row.get("restrictContent", False),
            slug=row.get("slug"),
            visibility=visibility,
        )
