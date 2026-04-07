"""OvationTix event transformer for the generic platform scraper."""

from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class OvationTixEventTransformer(DataTransformer[OvationTixEvent]):
    """Transforms OvationTixEvent objects into Show objects via event.to_show()."""

    pass
