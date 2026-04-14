"""Comedy Cave event transformer."""

from laughtrack.core.entities.event.showpass import ShowpassEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComedyCaveEventTransformer(DataTransformer[ShowpassEvent]):
    """Transforms ShowpassEvent objects into Show objects.

    ShowpassEvent implements ShowConvertible, so the base
    DataTransformer.transform_to_show() delegates to
    ShowpassEvent.to_show() automatically.
    """
