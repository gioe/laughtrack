"""Event transformer for The Comedy & Magic Club."""

from laughtrack.core.entities.event.comedy_magic_club import ComedyMagicClubEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComedyMagicClubEventTransformer(DataTransformer[ComedyMagicClubEvent]):
    """Transforms ComedyMagicClubEvent objects into Show domain objects."""
