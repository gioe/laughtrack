"""Transformer for Kenosha Comedy Club events."""

from laughtrack.core.entities.event.kenosha_comedy_club import KenoshaComedyClubEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class KenoshaComedyClubTransformer(DataTransformer[KenoshaComedyClubEvent]):
    pass
