"""
Gotham Comedy Club data transformation utilities.

This module provides utilities for transforming GothamEvent objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.core.entities.event.gotham import GothamEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class GothamEventTransformer(DataTransformer[GothamEvent]):
    """
    Transformer for converting GothamEvent objects to Show objects.

    Inherits standard transformation logic from DataTransformer base class,
    which leverages the GothamEvent.to_show() method.
    """

    pass
