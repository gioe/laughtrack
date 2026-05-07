"""House of Comedy Phoenix event transformer."""

from laughtrack.core.entities.event.house_of_comedy_phoenix import (
    HouseOfComedyPhoenixEvent,
)
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class HouseOfComedyPhoenixTransformer(DataTransformer[HouseOfComedyPhoenixEvent]):
    pass
