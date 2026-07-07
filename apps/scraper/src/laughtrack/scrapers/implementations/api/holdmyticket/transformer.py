"""HoldMyTicket event transformer for the HMT platform scraper."""

from laughtrack.core.entities.event.holdmyticket import HoldMyTicketEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class HoldMyTicketEventTransformer(DataTransformer[HoldMyTicketEvent]):
    """Transforms HoldMyTicketEvent objects into Show objects via event.to_show()."""

    pass
