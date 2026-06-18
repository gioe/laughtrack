"""Transformer for Ventura Improv shows."""

from laughtrack.core.entities.event.ventura_improv import VenturaImprovEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class VenturaImprovTransformer(DataTransformer[VenturaImprovEvent]):
    pass
