"""Transformer for Philly Improv Theater (PHIT) Crowdwork API events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow


class PhillyImprovTransformer(DataTransformer[PhillyImprovShow]):
    pass
