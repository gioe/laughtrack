"""
Base API Client for venue-specific API interactions.

This module provides a base class for venue-specific API clients,
establishing consistent patterns for HTTP operations, error handling,
and configuration management.
"""

from abc import ABC
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.data.mixins.http_convenience_mixin import HttpConvenienceMixin
from laughtrack.foundation.infrastructure.logger.logger import Logger


class BaseAPIClient(HttpConvenienceMixin, ABC):
    """
    Base class for venue-specific API clients.

    This class provides common functionality for API interactions:
    - HTTP convenience methods with error handling and retries
    - Standardized logging context
    - Club configuration access
    - Common initialization patterns

    Subclasses should implement venue-specific:
    - API endpoints
    - Request headers and configurations
    - Data extraction methods
    """

    def __init__(self, club: Club):
        super().__init__()
        self._club = club
        self.logger_context = club.as_context()

        # Initialize venue-specific configurations
        self._setup_api_config()

    @property
    def club(self) -> Club:
        """Get the club instance."""
        return self._club

    def _setup_api_config(self) -> None:
        """
        Setup venue-specific API configuration.

        Override this method in subclasses to initialize:
        - API endpoints
        - Request headers
        - Authentication tokens
        - Payload templates
        """
        pass

    def _log_error(self, operation: str, error: Exception, context: Optional[str] = None) -> None:
        """
        Log an error with consistent formatting.

        Args:
            operation: The operation that failed (e.g., "fetching lineup")
            error: The exception that occurred
            context: Additional context (e.g., date_key, url)
        """
        error_msg = f"Error {operation}"
        if context:
            error_msg += f" for {context}"
        error_msg += f": {str(error)}"

        Logger.error(error_msg, self.logger_context)

    def _log_success(self, operation: str, context: Optional[str] = None, details: Optional[str] = None) -> None:
        """
        Log a successful operation with consistent formatting.

        Args:
            operation: The operation that succeeded (e.g., "discovered dates")
            context: Additional context (e.g., date_key, url)
            details: Additional details (e.g., "found 15 items")
        """
        success_msg = f"Successfully {operation}"
        if context:
            success_msg += f" for {context}"
        if details:
            success_msg += f" - {details}"

        Logger.info(success_msg, self.logger_context)
