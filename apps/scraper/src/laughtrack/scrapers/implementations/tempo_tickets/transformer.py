"""Tempo Tickets event -> Show transformer.

Each TempoTicketsEvent already implements ShowConvertible.to_show, so the
default DataTransformer behavior is sufficient.
"""

from laughtrack.core.entities.event.tempo_tickets import TempoTicketsEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TempoTicketsTransformer(DataTransformer[TempoTicketsEvent]):
    pass
