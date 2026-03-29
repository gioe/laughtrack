"""Comedy Corner Underground event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.comedy_corner_underground import ComedyCornerEvent


class ComedyCornerEventTransformer(DataTransformer[ComedyCornerEvent]):
    pass
