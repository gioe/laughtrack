"""The Bit Theater event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.the_bit_theater import BitTheaterEvent


class BitTheaterEventTransformer(DataTransformer[BitTheaterEvent]):
    pass
