"""Transformer for VBO Tickets events."""

from laughtrack.core.entities.event.vbo_tickets import VboEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class VboTicketsTransformer(DataTransformer[VboEvent]):
    pass
