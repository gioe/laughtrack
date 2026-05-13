"""Event transformer for Soboba Casino Resort."""

from laughtrack.core.entities.event.soboba_casino_resort import SobobaCasinoResortEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SobobaCasinoResortEventTransformer(DataTransformer[SobobaCasinoResortEvent]):
    """Transforms SobobaCasinoResortEvent objects into Show domain objects."""
