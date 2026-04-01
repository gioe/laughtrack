"""Base database handler for standardized database operations."""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional

import psycopg2
import psycopg2.extras
from psycopg2.extras import DictRow, execute_values

from laughtrack.foundation.models.types import T
from laughtrack.adapters.db import create_connection
from laughtrack.foundation.infrastructure.database.operation import DatabaseOperationLogger
from laughtrack.foundation.infrastructure.logger.logger import Logger


class BaseDatabaseHandler(Generic[T], ABC):
    """Base class for database operations with entity-specific abstractions."""

    def __init__(self):
        """Initialize the handler. ConfigManager is handled as singleton."""
        pass

    @abstractmethod
    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""

    @abstractmethod
    def get_entity_class(self) -> type[T]:
        """Return the entity class for instantiation."""

    def create_connection(self) -> psycopg2.extensions.connection:
        """
        Create a database connection using standardized utility.

        Returns:
            psycopg2 connection object with autocommit enabled
        """
        conn = create_connection()
        # Optimize connection settings for better performance
        conn.autocommit = False  # Explicit transaction control
        return conn

    def _get_cursor_factory(self):
        """Get optimized cursor factory for database operations."""
        return psycopg2.extras.DictCursor

    def execute_with_cursor(
        self, operation: str, params: Optional[tuple] = None, return_results: bool = False
    ) -> Optional[List[DictRow]]:
        """
        Execute a database operation with proper cursor handling.

        Args:
            operation: SQL operation to execute
            params: Optional parameters for the operation
            return_results: Whether to fetch results

        Returns:
            Optional list of results if return_results is True
        """
        try:
            with self.create_connection() as conn:
                with conn.cursor(cursor_factory=self._get_cursor_factory()) as cursor:
                    cursor.execute(operation, params) if params else cursor.execute(operation)
                    return cursor.fetchall() if return_results else None
        except Exception as e:
            Logger.error(f"Error executing database operation: {str(e)}")
            raise

    def execute_batch_operation(
        self,
        query: str,
        items: List[tuple],
        template: Optional[str] = None,
        return_results: bool = False,
        log_summary: bool = True,
    ) -> Optional[List[DictRow]]:
        """
        Execute batch database operation with optimized handling and automatic logging.

        Args:
            query: SQL query to execute
            items: List of tuples to process
            template: Optional template for execute_values
            return_results: Whether to return results
            log_summary: Whether to log operation summary (default: True)

        Returns:
            Optional list of results if return_results is True, else None
        """
        if not items:
            raise ValueError("No items provided for batch operation")

        entity_name = self.get_entity_name()
        original_count = len(items)

        try:
            with self.create_connection() as conn:
                with conn.cursor(cursor_factory=self._get_cursor_factory()) as cursor:
                    results = execute_values(
                        cursor, query, items, template=template, page_size=1000, fetch=return_results
                    )

                    # Log operation summary if requested
                    if log_summary:
                        operation_type = self._determine_operation_type(query)
                        if return_results:
                            # RETURNING query — count newly inserted/updated rows.
                            # An empty list means all rows were skipped (ON CONFLICT DO NOTHING),
                            # which is normal when records already exist — log at INFO, not WARNING.
                            processed_count = len(results) if results else 0
                            if processed_count > 0:
                                DatabaseOperationLogger.log_simple_batch_operation(
                                    operation=operation_type, items_count=processed_count, entity_type=entity_name
                                )
                            else:
                                Logger.info(
                                    f"{operation_type} operation: 0 new {entity_name} inserted — all already existed"
                                )
                        else:
                            # UPDATE/DELETE — use cursor.rowcount (no RETURNING clause)
                            affected_rows = cursor.rowcount
                            DatabaseOperationLogger.log_simple_batch_operation(
                                operation=operation_type, items_count=affected_rows, entity_type=entity_name
                            )

                    return results if return_results else None

        except Exception as e:
            Logger.error(
                f"Error in batch operation: {str(e)}\n"
                f"Entity: {entity_name}\n"
                f"Items count: {original_count}\n"
                f"Query: {query}",
            )
            raise

    def _determine_operation_type(self, query: str) -> str:
        """Determine operation type from SQL query."""
        query_upper = query.upper().strip()
        if query_upper.startswith("INSERT"):
            return "insert"
        elif query_upper.startswith("UPDATE"):
            return "update"
        elif query_upper.startswith("DELETE"):
            return "delete"
        else:
            return "operation"
