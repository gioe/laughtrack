"""The Elysian Theater event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.elysian import ElysianEvent


class ElysianEventTransformer(DataTransformer[ElysianEvent]):
    pass
