"""Transformer for the generic ThunderTix calendar API scraper."""

from laughtrack.core.entities.event.thundertix import ThunderTixPerformance
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ThunderTixEventTransformer(DataTransformer[ThunderTixPerformance]):
    """Transforms ThunderTixPerformance objects into Show objects.

    ThunderTixPerformance implements ShowConvertible, so the base
    DataTransformer.transform_to_show() delegates to
    ThunderTixPerformance.to_show() automatically. This subclass exists
    only so DataTransformer.can_transform() can resolve the generic
    parameter via __orig_bases__.
    """
