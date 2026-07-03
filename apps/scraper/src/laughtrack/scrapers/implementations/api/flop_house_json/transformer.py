"""Pass-through transformer for Flop House JSON events."""

from laughtrack.core.entities.event.flop_house_json import FlopHouseJsonEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class FlopHouseJsonEventTransformer(DataTransformer[FlopHouseJsonEvent]):
    """Convert FlopHouseJsonEvent objects through their ShowConvertible API."""
