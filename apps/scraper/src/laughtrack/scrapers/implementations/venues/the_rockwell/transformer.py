"""The Rockwell event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.rockwell import RockwellEvent


class RockwellEventTransformer(DataTransformer[RockwellEvent]):
    pass
