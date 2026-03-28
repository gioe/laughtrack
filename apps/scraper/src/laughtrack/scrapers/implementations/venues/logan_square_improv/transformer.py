"""Transformer for Logan Square Improv Crowdwork API events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow


class LoganSquareImprovTransformer(DataTransformer[PhillyImprovShow]):
    pass
