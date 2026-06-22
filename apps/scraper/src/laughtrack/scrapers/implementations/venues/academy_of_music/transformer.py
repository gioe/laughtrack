"""Academy of Music event transformer (pass-through to AcademyOfMusicEvent.to_show)."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import AcademyOfMusicEvent


class AcademyOfMusicEventTransformer(DataTransformer[AcademyOfMusicEvent]):
    pass
