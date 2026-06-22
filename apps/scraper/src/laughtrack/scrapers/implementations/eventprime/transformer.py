"""EventPrime event -> Show transformer.

EventPrime events are normalized into ``JsonLdEvent`` by the extractor, so the
default ``DataTransformer`` behavior (``to_show`` per event) is sufficient —
mirroring ``json_ld`` / ``anyroad`` / ``tock``.
"""

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class EventPrimeTransformer(DataTransformer[JsonLdEvent]):
    pass
