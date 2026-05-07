"""House of Comedy BC event transformer."""

from laughtrack.core.entities.event.house_of_comedy_bc import HouseOfComedyBcEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class HouseOfComedyBcTransformer(DataTransformer[HouseOfComedyBcEvent]):
    pass
