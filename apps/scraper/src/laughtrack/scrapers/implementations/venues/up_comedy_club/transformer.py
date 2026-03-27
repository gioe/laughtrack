"""Transformer for UP Comedy Club Second City platform events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.up_comedy_club import UPComedyClubEvent


class UPComedyClubTransformer(DataTransformer[UPComedyClubEvent]):
    pass
