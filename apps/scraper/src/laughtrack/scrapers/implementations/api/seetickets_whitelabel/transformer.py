"""SeeTickets/Eventim whitelabel event transformer."""

from laughtrack.core.entities.event.seetickets_whitelabel import SeeTicketsWhitelabelEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SeeTicketsWhitelabelTransformer(DataTransformer[SeeTicketsWhitelabelEvent]):
    """Delegates conversion to SeeTicketsWhitelabelEvent.to_show()."""
