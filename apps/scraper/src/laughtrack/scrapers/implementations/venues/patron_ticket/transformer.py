"""Pass-through transformer for PatronTicket events."""

from laughtrack.core.entities.event.patron_ticket import PatronTicketEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class PatronTicketEventTransformer(DataTransformer[PatronTicketEvent]):
    pass
