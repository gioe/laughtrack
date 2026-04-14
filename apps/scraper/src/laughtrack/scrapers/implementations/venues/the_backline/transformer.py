"""Transformer for The Backline Crowdwork API events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow


class TheBacklineTransformer(DataTransformer[PhillyImprovShow]):
    pass
