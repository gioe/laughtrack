"""The Auricle event transformer."""

from laughtrack.core.entities.event.the_auricle import TheAuricleEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TheAuricleEventTransformer(DataTransformer[TheAuricleEvent]):
    """Converts TheAuricleEvent objects to Show objects via TheAuricleEvent.to_show()."""

    pass
