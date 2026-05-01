"""CIC Theater event transformer."""

from laughtrack.core.entities.event.cic_theater import CicTheaterEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class CicTheaterEventTransformer(DataTransformer[CicTheaterEvent]):
    pass

