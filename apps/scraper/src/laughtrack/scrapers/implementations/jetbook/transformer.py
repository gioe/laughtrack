"""JetBook event transformer."""

from laughtrack.core.entities.event.jetbook import JetBookEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class JetBookEventTransformer(DataTransformer[JetBookEvent]):
    pass
