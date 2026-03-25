"""Dynasty Typewriter event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.dynasty_typewriter import DynastyTypewriterEvent


class DynastyTypewriterEventTransformer(DataTransformer[DynastyTypewriterEvent]):
    pass
