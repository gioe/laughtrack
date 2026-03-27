"""The Annoyance Theatre event transformer."""

from laughtrack.core.entities.event.annoyance import AnnoyancePerformance
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class AnnoyanceEventTransformer(DataTransformer[AnnoyancePerformance]):
    """Transforms AnnoyancePerformance objects into Show objects.

    AnnoyancePerformance implements ShowConvertible, so the base
    DataTransformer.transform_to_show() delegates to
    AnnoyancePerformance.to_show() automatically.
    """
