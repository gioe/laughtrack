"""Largo at the Coronet event transformer."""

from laughtrack.core.entities.event.largo_at_the_coronet import LargoAtTheCoronetEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class LargoAtTheCoronetEventTransformer(DataTransformer[LargoAtTheCoronetEvent]):
    """Transforms LargoAtTheCoronetEvent objects into Show objects via event.to_show()."""

    pass
