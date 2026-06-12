"""
Gotham Comedy Club data transformation utilities.

This module provides utilities for transforming GothamFeedEvent objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.core.clients.gotham.models.models import GothamFeedEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class GothamEventTransformer(DataTransformer[GothamFeedEvent]):
    """
    Transformer for converting GothamFeedEvent objects to Show objects.

    Inherits standard transformation logic from DataTransformer base class,
    which leverages the GothamFeedEvent.to_show() method.
    """

    pass
