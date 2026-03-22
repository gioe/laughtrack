"""Goofs Comedy Club event transformer."""

from laughtrack.core.entities.event.goofs import GoofsEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class GoofsEventTransformer(DataTransformer[GoofsEvent]):
    """Transforms GoofsEvent objects into Show objects.

    GoofsEvent implements ShowConvertible, so the base DataTransformer.transform_to_show()
    delegates to GoofsEvent.to_show() automatically.
    """
