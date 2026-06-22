"""AnyRoad event -> Show transformer.

AnyRoad experiences are already normalized into ``JsonLdEvent`` by the
extractor, so the default ``DataTransformer`` behavior (``to_show`` per event)
is sufficient — mirroring ``json_ld`` and ``tock``.
"""

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class AnyRoadTransformer(DataTransformer[JsonLdEvent]):
    pass
