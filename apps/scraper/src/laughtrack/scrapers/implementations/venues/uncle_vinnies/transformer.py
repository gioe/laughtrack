"""
Uncle Vinnie's Comedy Club data transformation utilities.

This module provides utilities for transforming UncleVinniesEvent objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.core.entities.event.uncle_vinnies import UncleVinniesEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class UncleVinniesEventTransformer(DataTransformer[UncleVinniesEvent]):
    """Transformer for converting UncleVinniesEvent objects to Show objects."""

    pass
