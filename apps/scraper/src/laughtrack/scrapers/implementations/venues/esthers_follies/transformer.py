"""Esther's Follies event transformer."""

from laughtrack.core.entities.event.esthers_follies import EsthersFolliesEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class EsthersFolliesEventTransformer(DataTransformer[EsthersFolliesEvent]):
    pass
