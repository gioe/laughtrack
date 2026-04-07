"""Event transformer for McCurdy's Comedy Theatre."""

from laughtrack.core.entities.event.mccurdys_comedy_theatre import McCurdysEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class McCurdysEventTransformer(DataTransformer[McCurdysEvent]):
    """Transforms McCurdysEvent objects into Show domain objects."""
