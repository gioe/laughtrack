"""Data model for a production company."""

from dataclasses import dataclass, field
from typing import List, Optional, Set

from psycopg2.extras import DictRow

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.protocols.database_entity import DatabaseEntity


@dataclass
class ProductionCompany(DatabaseEntity):
    """A production company that produces shows across multiple venues."""

    id: int
    name: str
    slug: str
    scraping_url: Optional[str] = None
    website: Optional[str] = None
    visible: bool = True
    show_name_keywords: List[str] = field(default_factory=list)
    venue_club_ids: List[int] = field(default_factory=list)

    @classmethod
    def from_db_row(cls, row: DictRow) -> "ProductionCompany":
        """Create ProductionCompany entity from database row."""
        return cls(
            id=row["id"],
            name=row.get("name", ""),
            slug=row.get("slug", ""),
            scraping_url=row.get("scraping_url"),
            website=row.get("website"),
            visible=row.get("visible", True),
            show_name_keywords=row.get("show_name_keywords") or [],
        )

    @classmethod
    def key_from_db_row(cls, row: DictRow) -> tuple:
        """Create a unique key from a database row."""
        return (row.get("name"),)

    def to_tuple(self) -> tuple:
        """Transform ProductionCompany entity to database tuple."""
        return (
            self.name,
            self.slug,
            self.scraping_url,
            self.website,
            self.visible,
        )

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the ProductionCompany entity."""
        return (self.name,)

    def as_context(self) -> JSONDict:
        """Return a context dictionary for logging."""
        return {
            "production_company_id": self.id,
            "production_company_name": self.name,
            "scraping_url": self.scraping_url,
        }

    def matches_show_name(self, show_name: str) -> bool:
        """Return True if the show name matches this company's keyword filter.

        If show_name_keywords is empty, all shows match (no filtering).
        Otherwise, at least one keyword must appear in the show name
        (case-insensitive substring match).
        """
        if not self.show_name_keywords:
            return True
        name_lower = show_name.lower()
        return any(kw.lower() in name_lower for kw in self.show_name_keywords)

    def get_club_id_for_venue(self, club_ids_in_scope: Set[int]) -> Optional[int]:
        """Return the first venue club_id that is in scope, or None."""
        for cid in self.venue_club_ids:
            if cid in club_ids_in_scope:
                return cid
        return None
