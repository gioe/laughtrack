"""
Protocols for page data structures used by scrapers.

This module defines a lightweight protocol that ensures any page-data object
exposes an `event_list` property of JSON-LD `Event` objects.
"""

from typing import List, Protocol, runtime_checkable

from laughtrack.foundation.models.types import T


@runtime_checkable
class EventListContainer(Protocol[T]):
    """Protocol that requires an `event_list` attribute of List[Event]."""

    event_list: List[T]

    def is_transformable(self) -> bool:
        return len(self.event_list) > 0
