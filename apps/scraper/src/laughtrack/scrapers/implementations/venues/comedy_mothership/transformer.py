"""Comedy Mothership event transformer."""

from laughtrack.core.entities.event.comedy_mothership import ComedyMothershipEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComedyMothershipEventTransformer(DataTransformer[ComedyMothershipEvent]):
    pass
