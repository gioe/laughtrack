"""Shared base transformer for Tixr venue scrapers."""

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TixrVenueEventTransformer(DataTransformer[TixrEvent]):
    """Base transformer for Tixr-backed venue scrapers.

    All Tixr venues use the same pass-through transformation by default.
    Subclass and override methods to add venue-specific transformation logic.
    """

    pass
