"""Comedy @ The Carlson event transformer."""

from laughtrack.core.entities.event.comedy_at_the_carlson import ComedyAtTheCarlsonEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComedyAtTheCarlsonEventTransformer(DataTransformer[ComedyAtTheCarlsonEvent]):
    """Transforms ComedyAtTheCarlsonEvent objects into Show objects via event.to_show()."""

    pass
