"""SquadUP event transformer for the generic platform scraper."""

from laughtrack.core.entities.event.squadup import SquadUpEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SquadUpEventTransformer(DataTransformer[SquadUpEvent]):
    """Transforms SquadUpEvent objects into Show objects via event.to_show()."""
    pass
