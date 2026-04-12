"""Transformer for TicketWeb events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.ticketweb import TicketWebEvent


class TicketWebTransformer(DataTransformer[TicketWebEvent]):
    pass
