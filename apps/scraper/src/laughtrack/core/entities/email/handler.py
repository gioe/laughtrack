"""Email database handler for email notification operations."""

from typing import List

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from sql.email_queries import EmailQueries

from laughtrack.core.entities.email.local.email_map import EmailMap

from .model import EmailNotification


class EmailHandler(BaseDatabaseHandler[EmailNotification]):
    """Handler for email notification database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "email_notification"

    def get_entity_class(self) -> type[EmailNotification]:
        """Return the EmailNotification class for instantiation."""
        return EmailNotification

    def get_user_email_map(self, show_ids: List[int]) -> EmailMap:
        """
        Get user email mappings for show notifications.

        Args:
            show_ids: List of show IDs to get email mappings for

        Returns:
            EmailMapResult containing structured user email notification data
        """
        try:
            results = self.execute_with_cursor(EmailQueries.GET_USER_EMAIL_MAP, (show_ids,), return_results=True)
            if not results:
                raise ValueError("No email mappings found for provided show IDs")

            # Return structured EmailMapResult instead of raw dictionary
            return EmailMap.from_db_results(results)
        except Exception as e:
            raise ValueError(f"Failed to get user email map: {str(e)}") from e
