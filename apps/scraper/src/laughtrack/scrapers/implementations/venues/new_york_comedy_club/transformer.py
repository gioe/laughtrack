"""Transformer for New York Comedy Club events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.event import JsonLdEvent


class NewYorkComedyClubTransformer(DataTransformer[JsonLdEvent]):
    pass
