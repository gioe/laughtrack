"""Transformer for iO Theater Crowdwork API events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow


class IOTheaterTransformer(DataTransformer[PhillyImprovShow]):
    pass
