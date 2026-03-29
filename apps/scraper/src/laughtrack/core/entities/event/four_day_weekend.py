"""
Four Day Weekend Comedy event data model.

Represents a single performance extracted from the OvationTix API.
Each FourDayWeekendEvent maps to one performance (date/time slot),
not a production — productions group multiple recurring performances.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class FourDayWeekendEvent:
    """
    A single upcoming performance from the OvationTix API for Four Day Weekend Comedy.

    One production (e.g. "Four Day Weekend Dallas") has many performances — one per
    show date/time.  This model represents a single performance entry from the
    `performances` array in the `Production({id})/performance?` response.
    """

    production_id: str
    performance_id: str
    production_name: str
    start_date: str          # "YYYY-MM-DD HH:MM" (local time, no timezone)
    tickets_available: bool
    event_url: str
    description: Optional[str] = None
    sections: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        if self.sections is None:
            self.sections = []

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Transform this performance into a Show object."""
        try:
            start_dt = self._parse_start_date(club.timezone)
            if not start_dt:
                Logger.error(
                    f"Could not parse start_date '{self.start_date}' for event "
                    f"'{self.production_name}' (perf {self.performance_id})"
                )
                return None

            tickets = self._extract_tickets()
            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.production_name,
                club=club,
                date=start_dt,
                show_page_url=self.event_url,
                lineup=[],
                tickets=tickets,
                description=self.description,
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"Failed to transform FourDayWeekendEvent: {e}")
            return None

    def _parse_start_date(self, timezone: str) -> Optional[datetime]:
        """Parse 'YYYY-MM-DD HH:MM' local-time string into an aware datetime."""
        try:
            tz = pytz.timezone(timezone)
            naive = datetime.strptime(self.start_date, "%Y-%m-%d %H:%M")
            return tz.localize(naive, is_dst=None)
        except Exception as e:
            Logger.error(f"Error parsing start_date '{self.start_date}': {e}")
            return None

    def _extract_tickets(self) -> List[Ticket]:
        tickets: List[Ticket] = []
        try:
            for section in (self.sections or []):
                for ticket_view in section.get("ticketTypeViews", []):
                    price = ticket_view.get("price")
                    name = ticket_view.get("name", "General Admission")
                    if price is not None:
                        tickets.append(
                            Ticket(
                                price=float(price),
                                purchase_url=self.event_url,
                                sold_out=not self.tickets_available,
                                type=name,
                            )
                        )
        except Exception as e:
            Logger.error(f"Failed to extract tickets for perf {self.performance_id}: {e}")
        return tickets
