from dataclasses import dataclass

from psycopg2.extras import DictRow

from laughtrack.foundation.protocols.database_entity import DatabaseEntity


@dataclass
class Scraper(DatabaseEntity):
    """Simple user model focused on email address for notifications."""

    """Data model for scraper type summary with club counts."""

    scraper_type: str
    club_count: int

    @classmethod
    def from_db_row(cls, row: DictRow) -> "Scraper":
        """Create ScraperTypeSummary from database row."""
        return cls(scraper_type=row.get("scraper", ""), club_count=row.get("club_count", 0))
