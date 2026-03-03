"""User database handler for user-specific operations."""

from typing import Optional

from laughtrack.core.entities.user.model import User

from sql.user_queries import UserQueries

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger


class UserHandler(BaseDatabaseHandler[User]):
    """Handler for user database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "user"

    def get_entity_class(self) -> type[User]:
        """Return the User class for instantiation."""
        return User

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: Email address to search for

        Returns:
            User object if found, None otherwise
        """
        try:
            results = self.execute_with_cursor(UserQueries.GET_USERS_FROM_EMAILS, (email,), return_results=True)
            if results:
                return User.from_db_row(results[0])
            return None
        except Exception as e:
            Logger.error(f"Error getting user by email {email}: {str(e)}")
            return None
