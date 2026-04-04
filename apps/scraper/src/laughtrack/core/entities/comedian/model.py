import hashlib
from dataclasses import dataclass, field
from typing import Optional

from psycopg2.extras import DictRow

from laughtrack.foundation.protocols.database_entity import DatabaseEntity
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.popularity.scorer import PopularityScorer
from gioe_libs.string_utils import StringUtils


@dataclass
class Comedian(DatabaseEntity):
    """Data model for a comedian that implements DatabaseEntity protocol."""

    name: str
    uuid: Optional[str] = field(default=None)  # Will be set in __post_init__
    sold_out_shows: int = 0
    total_shows: int = 0
    instagram_followers: Optional[int] = None
    tiktok_followers: Optional[int] = None
    youtube_followers: Optional[int] = None
    # Additional database fields
    instagram_account: Optional[str] = None
    tiktok_account: Optional[str] = None
    youtube_account: Optional[str] = None
    website: Optional[str] = None
    linktree: Optional[str] = None
    parent_comedian_id: Optional[int] = None
    # Recency score: set by the popularity update pipeline, not persisted in DB.
    # Represents normalized recent/upcoming show activity (0.0 = no recent shows, 1.0 = max).
    recency_score: float = 0.0

    def __eq__(self, other):
        if not isinstance(other, Comedian):
            return False
        return self.uuid == other.uuid

    def __hash__(self):
        return hash(self.uuid)

    def __post_init__(self):
        """Initialize the comedian with a deterministic UUID based on normalized name if not provided."""
        self.name = self.name.strip()
        if self.uuid is None:
            from laughtrack.utilities.domain.comedian.utils import ComedianUtils

            normalized_name = ComedianUtils.normalize_name(self.name)
            self.uuid = ComedianUtils.generate_uuid(normalized_name)

    @property
    def popularity(self) -> float:
        """
        Calculate comedian popularity based on social media followers and performance metrics.

        Delegates to PopularityScorer utility for consistent scoring across the application.
        When recency_score is set by the popularity update pipeline, it replaces the stale
        sold_out_shows/total_shows performance component.

        Returns:
            float: Popularity score between 0 and 1
        """
        return PopularityScorer.calculate_comedian_popularity(
            instagram_followers=self.instagram_followers,
            tiktok_followers=self.tiktok_followers,
            youtube_followers=self.youtube_followers,
            sold_out_shows=self.sold_out_shows,
            total_shows=self.total_shows,
            recency_score=self.recency_score,
        )

    @classmethod
    def from_db_row(cls, row: DictRow) -> "Comedian":
        """Create Comedian entity from database row."""
        return cls(
            name=row["name"],
            uuid=row["uuid"],
            instagram_followers=row.get("instagram_followers"),
            tiktok_followers=row.get("tiktok_followers"),
            youtube_followers=row.get("youtube_followers"),
            sold_out_shows=row.get("sold_out_shows", 0),
            total_shows=row.get("total_shows", 0),
            # New fields added for database compatibility
            instagram_account=row.get("instagram_account"),
            tiktok_account=row.get("tiktok_account"),
            youtube_account=row.get("youtube_account"),
            website=row.get("website"),
            linktree=row.get("linktree"),
            parent_comedian_id=row.get("parent_comedian_id"),
        )

    @classmethod
    def key_from_db_row(cls, row: DictRow) -> tuple:
        """Create a unique key from a database row."""
        return (row.get("uuid"),)

    def to_tuple(self) -> tuple:
        """Transform Comedian entity to database tuple."""
        return (
            self.uuid,
            self.name,
            self.instagram_followers,
            self.tiktok_followers,
            self.youtube_followers,
            self.sold_out_shows,
            self.total_shows,
            self.popularity,
            self.instagram_account,
            self.tiktok_account,
            self.youtube_account,
            self.website,
            self.linktree,
            self.parent_comedian_id,
        )

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the Comedian entity."""
        return (self.uuid,)

    def to_popularity_tuple(self) -> tuple:
        """Transform Comedian entity to database tuple for popularity update."""
        return (
            self.uuid,
            self.popularity,
        )

    def to_insert_tuple(self) -> tuple:
        return (self.uuid, self.name, self.sold_out_shows, self.total_shows)
