"""Dojour event transformer for the Dojour platform scraper."""

from laughtrack.core.entities.event.dojour import DojourEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class DojourEventTransformer(DataTransformer[DojourEvent]):
    """Transforms DojourEvent objects into Show objects via event.to_show()."""

    pass
