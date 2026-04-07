"""Flappers event transformer."""

from laughtrack.core.entities.event.flappers import FlappersEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class FlappersEventTransformer(DataTransformer[FlappersEvent]):
    """Transforms FlappersEvent objects into Show objects.

    Delegates to FlappersEvent.to_show() via the base class.
    """
