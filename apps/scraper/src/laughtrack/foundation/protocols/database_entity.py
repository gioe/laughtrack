"""Protocol for database entities that can be serialized/deserialized."""

from typing import Protocol, runtime_checkable

try:
    from psycopg2.extras import DictRow
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    DictRow = None


@runtime_checkable
class DatabaseEntity(Protocol):
    """Protocol for entities that can be converted to/from database format.

    Any entity that needs to be stored in or retrieved from the database
    should implement these methods.
    """

    def to_tuple(self) -> tuple:
        """Transform entity to database tuple for INSERT/UPDATE operations.

        Returns:
            tuple: Database values in the correct order for SQL operations
        """
        ...

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the entity based on its attributes.

        This is used to identify the entity in the database, especially for
        deduplication purposes.

        Returns:
            tuple: Unique key tuple representing the entity
        """
        ...

    @classmethod
    def key_from_db_row(cls, row) -> tuple:
        """Extract the unique key from a database row.

        Args:
            row: Database row (DictRow when psycopg2 is available)

        Returns:
            tuple: Unique key for the entity
        """
        ...

    @classmethod
    def from_db_row(cls, row) -> "DatabaseEntity":
        """Create entity instance from database row.

        Args:
            row: Database row (DictRow when psycopg2 is available)

        Returns:
            DatabaseEntity: New entity instance
        """
        ...
