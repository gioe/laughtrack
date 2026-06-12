"""Data models for scraped page data from The Creek and The Cave."""

from dataclasses import dataclass
from typing import List, Optional

from laughtrack.core.clients.punchup.extractor import PunchupShow
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class CreekAndCaveShow(PunchupShow):
    """A show parsed from The Creek and The Cave's Punchup calendar page.

    Subclasses the shared :class:`PunchupShow` (the venue rebuilt its site on
    the Punchup platform) so DataTransformer dispatch is unambiguous, and adds
    the venue's ``vip_ticket_link`` field as an extra ticket row.
    """

    vip_ticket_link: Optional[str] = None

    def _build_tickets(self) -> List[Ticket]:
        """Extend the base ticket list with a VIP ticket row when present."""
        tickets = super()._build_tickets()
        if self.vip_ticket_link:
            tickets.append(
                ShowFactoryUtils.create_fallback_ticket(
                    purchase_url=self.vip_ticket_link,
                    ticket_type="VIP",
                    sold_out=self.is_sold_out,
                )
            )
        return tickets


@dataclass
class CreekAndCavePageData(EventListContainer[CreekAndCaveShow]):
    """
    Container for CreekAndCaveShow objects extracted from the calendar page.

    Follows the standard PageData pattern for the 5-component architecture.
    """

    event_list: List[CreekAndCaveShow]
