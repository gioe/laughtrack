"""Transformer for Rumor's Comedy Club events."""

from laughtrack.core.entities.event.rumors_comedy_club import RumorsComedyClubEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class RumorsComedyClubTransformer(DataTransformer[RumorsComedyClubEvent]):
    pass
