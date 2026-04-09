"""Madrid Comedy Lab event transformer."""

from laughtrack.core.entities.event.madrid_comedy_lab import MadridComedyLabEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class MadridComedyLabEventTransformer(DataTransformer[MadridComedyLabEvent]):
    """Transformer for converting MadridComedyLabEvent objects to Show objects.

    Delegates to MadridComedyLabEvent.to_show() via the DataTransformer base class.
    """

    pass
