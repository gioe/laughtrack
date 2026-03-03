"""
JSON-LD data transformation utilities.

This module provides utilities for transforming Event objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class EventbriteEventTransformer(DataTransformer[EventbriteEvent]):
    pass
