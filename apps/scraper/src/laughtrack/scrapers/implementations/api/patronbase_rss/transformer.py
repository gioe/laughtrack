"""Pass-through transformer for PatronBase RSS events."""

from laughtrack.core.entities.event.patronbase_rss import PatronBaseRssEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class PatronBaseRssEventTransformer(DataTransformer[PatronBaseRssEvent]):
    """Convert PatronBaseRssEvent objects through their ShowConvertible API."""
