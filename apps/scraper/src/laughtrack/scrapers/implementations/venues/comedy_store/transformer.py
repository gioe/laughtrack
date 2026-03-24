"""The Comedy Store event transformer."""

from laughtrack.core.entities.event.comedy_store import ComedyStoreEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComedyStoreEventTransformer(DataTransformer[ComedyStoreEvent]):
    """Transforms ComedyStoreEvent objects into Show objects.

    ComedyStoreEvent implements ShowConvertible, so the base
    DataTransformer.transform_to_show() delegates to
    ComedyStoreEvent.to_show() automatically.
    """
