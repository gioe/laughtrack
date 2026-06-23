"""TicketSpice event -> Show transformer.

Each TicketSpiceEvent already implements ShowConvertible.to_show, so the default
DataTransformer behavior is sufficient.
"""

from laughtrack.core.entities.event.ticketspice import TicketSpiceEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TicketSpiceTransformer(DataTransformer[TicketSpiceEvent]):
    pass
