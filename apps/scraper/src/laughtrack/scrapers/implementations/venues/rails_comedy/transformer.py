"""Transformer for Rails Comedy Crowdwork API events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow


class RailsComedyTransformer(DataTransformer[PhillyImprovShow]):
    pass
