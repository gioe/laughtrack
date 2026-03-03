"""
Base classes for data transformation.

This module provides the abstract base class and type definitions
for all data transformers.
"""

from abc import ABC, abstractmethod
from typing import Generic, Optional, get_args, get_origin

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import T
from laughtrack.core.protocols.show_convertible import ShowConvertible


class DataTransformer(ABC, Generic[T]):
    """
    Abstract base class for data transformers.

    Each transformer handles a specific data format (JSON-LD, GraphQL, etc.)
    and converts it to Show objects.
    """

    def __init__(self, club: Club):
        self.club = club

    def can_transform(self, raw_data: T) -> bool:
        """Check if this transformer can handle the given data format.

        Default implementation inspects the generic parameter T of the concrete
        subclass (e.g., DataTransformer[Event]) and returns isinstance(raw_data, T).
        Subclasses can override if they need custom logic.
        """
        expected_type = None

        # Safely inspect the generic parameter from the concrete subclass
        for base in getattr(self.__class__, "__orig_bases__", ()):  # runtime-only attribute
            origin = get_origin(base)
            if origin is DataTransformer or (origin is not None and issubclass(origin, DataTransformer)):
                args = get_args(base)
                if args:
                    expected_type = args[0]
                    break

        # If we couldn't determine expected type, be conservative
        if expected_type is None:
            return False

        try:
            return isinstance(raw_data, expected_type)
        except Exception:
            # In case expected_type isn't a valid isinstance target
            return False

    def transform_to_show(self, raw_data: ShowConvertible) -> Optional[Show]:
        """Transform Event object to Show objects with advanced processing."""
        try:
            return raw_data.to_show(self.club, enhanced=True)
        except Exception as e:
            Logger.error(f"Failed to transform Event data: {e}")
            return None
