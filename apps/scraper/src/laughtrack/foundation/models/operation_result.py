"""Infrastructure data processing utilities."""

from dataclasses import dataclass, field
from typing import List, Tuple

from laughtrack.foundation.models.types import DuplicateKeyDetails


@dataclass
class DatabaseOperationResult:
    """Result of a database operation (batch or single)."""

    inserts: int = 0
    updates: int = 0
    total: int = 0
    errors: int = 0
    # Additional diagnostics
    validation_errors: int = 0
    db_errors: int = 0
    # Related-entity write counts
    comedians_inserted: int = 0
    lineup_items_added: int = 0
    # Structured details
    duplicate_details: List[DuplicateKeyDetails] = field(default_factory=list)
    # Error details: (club_name, error_message) pairs for reporting
    error_entries: List[Tuple[str, str]] = field(default_factory=list)

    def __add__(self, other: "DatabaseOperationResult") -> "DatabaseOperationResult":
        """Add two DatabaseOperationResult instances together."""
        return DatabaseOperationResult(
            inserts=self.inserts + other.inserts,
            updates=self.updates + other.updates,
            total=self.total + other.total,
            errors=self.errors + other.errors,
            validation_errors=self.validation_errors + other.validation_errors,
            db_errors=self.db_errors + other.db_errors,
            comedians_inserted=self.comedians_inserted + other.comedians_inserted,
            lineup_items_added=self.lineup_items_added + other.lineup_items_added,
            duplicate_details=self.duplicate_details + other.duplicate_details,
            error_entries=self.error_entries + other.error_entries,
        )
