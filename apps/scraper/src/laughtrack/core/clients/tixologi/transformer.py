"""Shared base transformer for Tixologi venue scrapers."""

from laughtrack.core.entities.event.tixologi import TixologiEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TixologiVenueEventTransformer(DataTransformer[TixologiEvent]):
    """Base transformer for Tixologi-backed venue scrapers.

    All Tixologi venues use the same pass-through transformation by default.
    Subclass and override methods to add venue-specific transformation logic.
    """

    pass
