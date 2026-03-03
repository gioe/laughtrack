"""
Foundation protocols with no domain dependencies.

These protocols define interfaces using only standard library and third-party dependencies,
making them reusable across different domains.
"""

from .database_entity import DatabaseEntity
from .event_list_container import EventListContainer

__all__ = [
    "DatabaseEntity",
    "EventListContainer",
]
