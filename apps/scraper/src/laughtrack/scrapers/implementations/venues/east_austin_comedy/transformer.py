"""East Austin Comedy event transformer."""

from laughtrack.core.entities.event.east_austin_comedy import EastAustinComedyEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class EastAustinComedyEventTransformer(DataTransformer[EastAustinComedyEvent]):
    pass
